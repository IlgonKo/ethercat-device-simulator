"""Stage 2-1 checks for the known KickCAT Board, in PRE-OP only."""
import pysoem


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify_assignment_write(slave, result):
    """Always restore after attempting a write, even if its reply is lost."""
    original = slave.sdo_read(0x1C12, 0)
    result.update(index='0x1C12', subindex=0, original=original.hex(), restored=False)
    require(original == b'\x01', 'Unexpected RxPDO assignment count; refusing modification')
    try:
        slave.sdo_write(0x1C12, 0, b'\x00')
        changed = slave.sdo_read(0x1C12, 0)
        result['written'] = '00'
        result['readback'] = changed.hex()
        require(changed == b'\x00', 'SDO changed-value readback mismatch')
    finally:
        slave.sdo_write(0x1C12, 0, original)
        restored = slave.sdo_read(0x1C12, 0)
        result['restored_value'] = restored.hex()
        require(restored == original, 'SDO restoration failed; PDO test must not run')
        result['restored'] = True


def run_sdo_checks(slave, result):
    require(slave.state == pysoem.PREOP_STATE, 'SDO checks require PRE-OP')
    reads = result.setdefault('reads', [])

    def read(index, subindex, expected):
        actual = slave.sdo_read(index, subindex)
        reads.append({'index': f'0x{index:04X}', 'subindex': subindex,
                      'data': actual.hex(), 'expected': expected.hex()})
        require(actual == expected, f'SDO 0x{index:04X}:{subindex} mismatch: {actual.hex()}')
        return actual

    read(0x1000, 0, b'\x00' * 4)
    values = [read(0x1C00, i, bytes([value])) for i, value in enumerate([4, 1, 2, 3, 4])]
    ca = slave.sdo_read(0x1C00, 0, ca=True)
    result['complete_access'] = {'index': '0x1C00', 'data': ca.hex(),
                                 'bytes': len(ca), 'expected_sm_types': '01020304'}
    # Byte 1 is reserved; verify count and SM types at their wire offsets.
    require(len(ca) == 6 and ca[:1] == values[0] and ca[2:] == b''.join(values[1:]),
            f'0x1C00 Complete Access layout mismatch: {ca.hex()}')
    for index, mapping in [(0x1C12, 0x1600), (0x1C13, 0x1A00)]:
        read(index, 0, b'\x01')
        read(index, 1, mapping.to_bytes(2, 'little'))
    verify_assignment_write(slave, result.setdefault('write_restore', {}))
    read(0x1C12, 1, b'\x00\x16')
    result['passed'] = True


def run_sdo_error_checks(slave, result):
    # Exercise error handling without changing any object data.
    aborts = result.setdefault('aborts', [])
    for name, operation, expected in [
        ('write_read_only', lambda: slave.sdo_write(0x1000, 0, b'\x00' * 4), 0x06010002),
        ('read_missing_object', lambda: slave.sdo_read(0x5FFF, 0), 0x06020000),
    ]:
        record = {'test': name, 'expected': f'0x{expected:08X}', 'passed': False}
        aborts.append(record)
        try:
            operation()
        except pysoem.SdoError as exc:
            record['abort_code'] = f'0x{exc.abort_code:08X}'
            require(exc.abort_code == expected, f'{name}: unexpected SDO abort {exc.abort_code:#x}')
            record['passed'] = True
        except Exception as exc:
            record['error'] = repr(exc)
            raise
        else:
            raise RuntimeError(f'{name}: expected an SDO abort')
    result['passed'] = True
