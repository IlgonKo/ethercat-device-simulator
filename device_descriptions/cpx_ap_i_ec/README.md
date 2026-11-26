# CPX-AP-I-EC limited simulator profile

Source: Festo `festo_cpx_ap_i_ec.xml`, CPX-AP-I-EC-M12 revision 2 (the Device containing AP access 0x27F0).
Reference ESI SHA-256: b11d95f0922884584a8500c0a96c4dddbcfa8e65b87b46882a66699cbbe03b32.
The curated numeric definitions are local; the runtime does not import Motion Server code or its files.

| Field | Value |
| --- | --- |
| Vendor / product / revision | 29 / 8086609 / 2 |
| Profile / device type | 5001 / 72749961 |
| Interface ident | 0x2084 |
| DI8 / DO8 / AIO4/4 idents | 0x2007 / 0x2139 / 0x2134 |
| Module OD distance | 0x10 (AP-Slot SlotIndexIncrement override) |
| PDO index distance | 1 (SlotPdoIncrement) |

Motion Server must use `MOTION_SERVER_IO_<id>_MODULE_PDO_INDEX_STRIDE=0x10` for these module OD addresses. Its name denotes the OD address shift in `module_mapping_entries`, not the assignment PDO index increment. Configuration format is shared; settings are independent.

Supported individual SDO reads: 0x1000, 0x1001, 0x1018, 0x1C00, 0x1C12/13, configured mapping objects, channel process objects, 0x6102:0..4, 0xF000:0..2, 0xF030/F050 configured entries. F000 exposes only index distance and maximum modules (80 including interface); optional general-information/configuration elements are not implemented. Normal 1001/6102 values are zero; model errors never alter them. Invalid F030 requests abort without replacing the actual topology or inventing a manufacturer diagnostic code. EtherCAT AL/watchdog errors remain in ESC registers.

F030 writes accept only the existing expected ident/count in PRE-OP. All other writes, all Complete Access requests and unsupported parameter/AP/save/history objects abort. No CPX PDO persistence. AIO Rx retains 72 bits, including 4 non-channel supply bits and 4 padding bits. The supply bits do not gate models. All ordinary digital channel OD values are stored individually; explicit bit packing avoids KickCAT's byte-pointer aliasing of sub-byte OD entries.

The generated XML is a limited simulation fixture, not a complete vendor ESI implementation or conformance claim.
