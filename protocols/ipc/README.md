# EtherCAT Slave ↔ Functional Model IPC

The existing wire contract is unchanged by RF-016. Unix stream socket, one newline-terminated JSON request and response per transaction, maximum received request/response 1 MiB. Payload bytes use lowercase hexadecimal strings. No unsolicited messages.

- `describe`: returns fleet protocol 2; each device contains stable device settings and the protocol 1 per-axis contract (identity, OD entries, Rx/Tx layout and sizes, source/contract hashes).
- `read`: `slave_index`, `index`, `subindex`; response `data` (SDO bytes).
- `write`: same address plus `data`; success `{}`. Product-specific parameter save runs synchronously, including PRE-OP.
- `cycle`: `slave_index`, `data` (exact RxPDO length); response `data` (TxPDO) and `cycles`. All OD access targets the same axis model instance.
- `idle`: `slave_index`; returns current TxPDO, resets the axis elapsed-time origin and does not advance the model.

Indices are integers from 0 to N-1; missing/invalid indices do not route to axis 0. C++ socket send/receive timeout remains 1 second. First model cycle uses 10 ms; following cycles use monotonic elapsed time; gaps above 100 ms fail as before. This is the existing scheduling behavior, not a fixed-step FMI contract.

The generated fixture and live describe response must match before the Slave initializes. A source migration intentionally changes source and contract hashes even when wire OD/PDO values are equivalent. Internal profile name cia402-drive does not change the existing external cmmt_as contract label or EtherCAT identity.

Current error behavior: exceptions close the model connection; C++ can exit on IPC failure. Per-request SDO Abort translation (TD-001), preserving the Slave after Host failure and recovery semantics remain outstanding. RF-016 does not claim those guarantees.

The service owns the private socket directory (0700) and socket (0600). Axis state is independent within one shared Functional Model process; process failure can affect all its axes.
