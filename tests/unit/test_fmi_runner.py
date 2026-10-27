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
