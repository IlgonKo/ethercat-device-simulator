"""Failure-path checks for restoring a temporarily changed assignment."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/windows'))
from sdo_checks import verify_assignment_write


class AssignmentSlave:
    def __init__(self, lose_reply=False, reject_restore=False):
        self.value = b'\x01'
        self.writes = []
        self.lose_reply = lose_reply
        self.reject_restore = reject_restore

    def sdo_read(self, index, subindex):
        return self.value

    def sdo_write(self, index, subindex, value):
        self.writes.append(value)
        if value == b'\x01' and self.reject_restore:
            raise RuntimeError('restore rejected')
        self.value = value
        if value == b'\x00' and self.lose_reply:
            raise TimeoutError('write applied but reply lost')


class RestoreTests(unittest.TestCase):
    def test_lost_write_reply_still_restores_and_fails(self):
        slave = AssignmentSlave(lose_reply=True)
        result = {}
        with self.assertRaises(TimeoutError):
            verify_assignment_write(slave, result)
        self.assertEqual(slave.value, b'\x01')
        self.assertEqual(slave.writes, [b'\x00', b'\x01'])
        self.assertTrue(result['restored'])

    def test_restore_failure_cannot_report_success(self):
        result = {}
        with self.assertRaisesRegex(RuntimeError, 'restore rejected'):
            verify_assignment_write(AssignmentSlave(reject_restore=True), result)
        self.assertFalse(result['restored'])

    def test_unexpected_start_value_is_never_modified(self):
        slave = AssignmentSlave()
        slave.value = b'\x02'
        with self.assertRaisesRegex(RuntimeError, 'Unexpected'):
            verify_assignment_write(slave, {})
        self.assertEqual(slave.writes, [])


if __name__ == '__main__':
    unittest.main()
