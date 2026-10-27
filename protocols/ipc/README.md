# EtherCAT Slave ↔ Functional Model IPC

The existing wire contract is unchanged by RF-016. Unix stream socket, one newline-terminated JSON request and response per transaction, maximum received request/response 1 MiB. Payload bytes use lowercase hexadecimal strings. No unsolicited messages.

- `describe`: returns fleet protocol 2; each device contains stable device settings and the protocol 1 per-axis contract (identity, OD entries, Rx/Tx layout and sizes, source/contract hashes).
- `read`: `slave_index`, `index`, `subindex`; response `data` (SDO bytes).
- `write`: same address plus `data`; success `{}`. Product-specific parameter save runs synchronously, including PRE-OP.
- `cycle`: `slave_index`, `data` (exact RxPDO length); response `data` (TxPDO) and `cycles`. All OD access targets the same axis model instance.
- `idle`: `slave_index`; returns current TxPDO, resets the axis elapsed-time origin and does not advance the model.

Indices are integers from 0 to N-1; missing/invalid indices do not route to axis 0. C++ socket send/receive timeout remains 1 second. First model cycle uses 10 ms; following cycles use monotonic elapsed time; gaps above 100 ms fail as before. This is the existing scheduling behavior, not a fixed-step FMI contract.

The generated fixture and live describe response must match before the Slave initializes. A source migration intentionally changes source and contract hashes even when wire OD/PDO values are equivalent. Internal profile name cia402-drive does not change the existing external cmmt_as contract label or EtherCAT identity.

SDO rejection behavior (2026-10-27): read/write validation failures return
`{"error":{"kind":"sdo_abort","code":100728832,"message":"..."}}` on the same connection.
The Slave mailbox gateway translates the code to a single SDO Abort, with full
command byte 0x80, CoE service 2, length 10, and the original index/subindex.
No success reply is queued and no local OD write is committed before model acceptance.
Unsupported access uses 0x06010000; the mailbox checks read-only access (0x06010002),
missing subindex (0x06090011) and payload length (0x06070010) before model dispatch.
The gateway delegates other OD operations to KickCAT and normalizes its Abort command byte.
Cycle exceptions, native FMU crashes/hangs and IPC transport failures remain separate:
this change does not implement nonblocking scheduling or general Host failure recovery.

The service owns the private socket directory (0700) and socket (0600). Axis state is independent within one shared Functional Model process; process failure can affect all its axes.
