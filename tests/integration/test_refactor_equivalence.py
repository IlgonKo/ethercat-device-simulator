"""Golden values captured from commit 92f3df2 before source migration."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
from functional_model.runtime.axis import Model

class RefactorEquivalenceTests(unittest.TestCase):
    def test_original_contract_parameters_and_800_pdo_cycles(self):
        baseline = json.loads((Path(__file__).parents[1]/'fixtures/rf016-baseline.json').read_text())
        def digest(value):
            return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
        for key, expected in baseline['cases'].items():
            with self.subTest(case=key):
                axis_mode, mode = key.split(':')
                model = Model(dict(slave_index=0, id='axis-0', type='cia402-drive',
                    model=dict(type='f_kr_cmmt', mode=axis_mode), parameter_set='axis-0'))
                outputs = []
                for i in range(baseline['cycles_per_case']):
                    cw = [6, 7, 15][i] if i < 3 else 31
                    payload = struct.pack('<HbiIihihB', cw, int(mode), 10000, 100, 100, 0, 0, 0, 0)
                    with patch('functional_model.runtime.axis.time.monotonic', return_value=10+i*.008):
                        outputs.append(model.dispatch(dict(op='cycle', data=payload.hex())))
                description = model.describe()
                description.pop('model_source_hash'); description.pop('contract_hash')
                self.assertEqual(digest(description), expected['description'])
                self.assertEqual(digest(outputs), expected['outputs'])
                self.assertEqual(digest(model.parameter_values()), expected['parameters'])
