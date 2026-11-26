from types import SimpleNamespace
import unittest
from functional_model.runtime.fmi.runner import Fmi3Runner


class FmiRunnerFailureTests(unittest.TestCase):
    def runner(self, callback):
        r = Fmi3Runner.__new__(Fmi3Runner)
        r._initialized, r.failed, r.time = True, False, 0.0
        r._fmu = SimpleNamespace(doStep=callback)
        return r

    def test_step_failure_latches_and_does_not_advance_time(self):
        calls = []
        def failing(*args):
            calls.append(args)
            raise RuntimeError('native FMI error')
        r = self.runner(failing)
        with self.assertRaisesRegex(RuntimeError, 'native FMI'): r.step(.002)
        self.assertEqual(r.time, 0)
        with self.assertRaisesRegex(RuntimeError, 'closed or failed'): r.step(.002)
        self.assertEqual(len(calls), 1)

    def test_unsupported_return_does_not_publish_completed_step(self):
        for result in ((True, False, False, 0), (False, True, False, 0), (False, False, True, 0)):
            r = self.runner(lambda *args: result)
            with self.assertRaises(RuntimeError): r.step(.002)
            self.assertTrue(r.failed)
            self.assertEqual(r.time, 0)

    def test_integer_overflow_is_not_silently_wrapped(self):
        r = self.runner(None)
        r.variables = {'ControlWord': SimpleNamespace(type='UInt16', causality='input')}
        for value in (-1, 65536, 1.5):
            with self.assertRaises(ValueError): r.set('ControlWord', value)

class FmiRunnerInitializationTests(unittest.TestCase):
    def test_initial_settings_are_written_before_exit_and_outputs_are_ready(self):
        from unittest.mock import patch
        calls=[]
        parameter=SimpleNamespace(name='gain',type='Float64',causality='parameter',dimensions=[],valueReference=1,min='0',max='10')
        output=SimpleNamespace(name='result',type='Float64',causality='output',dimensions=[],valueReference=2)
        md=SimpleNamespace(fmiVersion='3.0',coSimulation=SimpleNamespace(modelIdentifier='fake'),guid='token',modelVariables=[parameter,output])
        class FakeFMU:
            component=True
            gain=1
            def __init__(self,**kwargs):pass
            def instantiate(self,**kwargs):calls.append(('instantiate',kwargs))
            def enterInitializationMode(self,**kwargs):calls.append(('enter',))
            def setFloat64(self,refs,values):calls.append(('set',));self.gain=values[0]
            def exitInitializationMode(self):calls.append(('exit',));self.output=self.gain*2
            def getFloat64(self,refs):return [self.output]
            def terminate(self):calls.append(('terminate',))
            def freeInstance(self):calls.append(('free',))
        with patch('fmpy.read_model_description',return_value=md),patch('fmpy.extract'),patch('fmpy.fmi3.FMU3Slave',FakeFMU):
            with Fmi3Runner('unused',{'gain':('Float64','parameter')},initial_values={'gain':3}) as r:
                self.assertEqual(r.get('result'),6)
                with self.assertRaisesRegex(ValueError,'initialization-only'):r.set('gain',4)
            self.assertEqual([c[0] for c in calls],['instantiate','enter','set','exit','terminate','free'])
            self.assertEqual(calls[0][1],dict(eventModeUsed=False,earlyReturnAllowed=False))
            calls.clear()
            with self.assertRaisesRegex(ValueError,'violates max'):Fmi3Runner('unused',{},initial_values={'gain':11})
            self.assertEqual([c[0] for c in calls],['instantiate','enter','free'])
