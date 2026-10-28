"""Axis-local diagnostics. Recovery is explicit; unexpected execution faults latch."""
import json
import time
import uuid


class Diagnostic:
    def __init__(self, code, axis, detail, *, latching=True, level='fault', context=None):
        self.value = dict(diagnostic_id=str(uuid.uuid4()),
            definition=dict(code=code, level=level, title=code,
                            description=detail, latching=latching),
            source=dict(type='axis', index=axis),
            history=dict(occurred_at=time.time(), acknowledged_at=None, resolved_at=None),
            detail=detail, context=context or {})
        self.log('detected')

    def log(self, event):
        print(json.dumps(dict(event='diagnostic', action=event, **self.value)), flush=True)

    def acknowledge(self):
        if self.value['history']['acknowledged_at'] is None:
            self.value['history']['acknowledged_at'] = time.time()
            self.log('acknowledged')

    def resolve(self):
        if self.value['history']['resolved_at'] is None:
            self.value['history']['resolved_at'] = time.time()
            self.log('resolved')


class AxisFault:
    """Guards the fixed CMMT PDO. No model recreation or position substitution."""
    def __init__(self, axis, initial):
        self.axis = axis
        self.last = bytes(initial)
        self.fault = None
        self.warning = None
        self.restart_required = False
        self.phase = 'normal'
        self.previous_cw = 0
        self.last_valid_at = None
        self.feedback_valid = True

    def detect(self, code, detail, restart=False):
        if code != 'AXIS_DRIVE_FAULT' or restart:
            self.feedback_valid = False
        if self.fault is None:
            self.fault = Diagnostic(code, self.axis, detail, context={
                'last_valid_at': self.last_valid_at,
                'feedback_valid': code == 'AXIS_DRIVE_FAULT' and not restart,
                'restart_required': restart})
        elif restart and not self.restart_required:
            # Retain the original occurrence and log the additional blocking cause.
            self.fault.value['context']['execution_failure'] = detail
            self.fault.value['context']['restart_required'] = True
            self.fault.value['context']['feedback_valid'] = False
            self.fault.log('escalated')
        self.restart_required |= restart
        self.phase = 'fault'

    def prepare(self, payload):
        cw = int.from_bytes(payload[:2], 'little')
        reset = bool(cw & 0x80 and not self.previous_cw & 0x80)
        self.previous_cw = cw
        if self.phase == 'normal':
            return payload, False
        if self.phase == 'verify_reset':
            # Some FMUs clear Fault while reset is high even with its cause still
            # asserted. Verify on reset-low with all motion bits disabled.
            return (None, False) if cw & 0x80 else (b'\x00\x00' + payload[2:], True)
        if self.phase == 'fault':
            if self.restart_required or not reset:
                if not self.restart_required and self.fault.value['definition']['code'] == 'AXIS_DRIVE_FAULT':
                    return b'\x00\x00' + payload[2:], False
                return None, False
            self.fault.acknowledge()
            # Do not pass old Enable/new-setpoint bits accompanying Reset.
            return b'\x80\x00' + payload[2:], True
        # Following successful reset require Shutdown -> Switch On -> Enable.
        masked = cw & 0x8f
        if self.phase == 'shutdown' and masked == 6:
            self.phase = 'switch_on'
        elif self.phase == 'switch_on' and masked == 7:
            self.phase = 'enable'
        elif self.phase == 'enable' and masked == 15 and not cw & 0x10 and payload[2] == 1:
            self.phase = 'normal'
        else:
            return None, False
        return payload, False

    def accept(self, output, resetting=False):
        if len(output) != len(self.last):
            raise ValueError('Invalid model output size')
        sw = int.from_bytes(output[:2], 'little')
        self.last = bytes(output)
        self.last_valid_at = time.time()
        self.feedback_valid = True
        if sw & 8:
            self.detect('AXIS_DRIVE_FAULT', 'Model reports drive Fault')
        elif resetting and self.fault:
            if self.phase == 'verify_reset':
                self.fault.resolve()
                self.fault = None
                self.phase = 'shutdown'
            else:
                self.phase = 'verify_reset'
        if sw & 0x80 and self.warning is None:
            self.warning = Diagnostic('AXIS_DRIVE_WARNING', self.axis,
                                      'Model reports warning', latching=False, level='alarm')
        elif not sw & 0x80 and self.warning:
            self.warning.resolve()
            self.warning = None

    def response(self):
        data = bytearray(self.last)
        if self.fault:
            sw = (int.from_bytes(data[:2], 'little') & ~0x106f) | 8
            data[:2] = sw.to_bytes(2, 'little')
        return dict(data=data.hex(), fault=self.fault.value if self.fault else None,
                    restart_required=self.restart_required,
                    feedback_valid=self.feedback_valid,
                    last_valid_at=self.last_valid_at)
