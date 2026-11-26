# TD 항목 목록

미해결 기술 문제와 보류한 후속 작업을 관리한다. 등록은 해결 완료를 의미하지 않는다.

## v1.0 / DT Demo 유지보수

DT Demo 완료 전에는 버그 및 이미 구현된 기능의 미비점만 TD로 보완한다. 신규 기능 RF 구현은 진행하지 않으며 기능 확대를 TD로 우회하지 않는다. 각 TD는 재현/기존 계약/수정 영향/검증 근거를 기록한다. 필요한 수정은 1.0.x 패치 릴리즈로 제공할 수 있다. [ADR-011](../Design/ADR-011-v1-maintenance-policy.md), [v1.0 릴리즈](../Releases/v1.0.0.md)를 따른다.

| 항목 | 문제 | 상태 | 관련 RF |
| --- | --- | --- | --- |
| [TD-001](TD-001-sdo-abort-response.md) | KickCAT SDO Abort 명령 0x83로 인한 PySOEM PacketError | 보류 / 응답 래퍼 구현, 전체 완료 근거 대조 필요 | RF-002-1, RF-003 |

[작업 일지](../Work_log.md) · [RF 목록](../RF/README.md)
