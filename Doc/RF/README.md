# RF 항목 목록

KickCAT 기본 타당성 검증과 후속 DT 연동 개발을 관리한다. 기준일: 2026-09-22.

| 항목 | 단계 | 내용 | 상태 |
| --- | --- | --- | --- |
| [RF-001](RF-001-linux-kickcat.md) | 1 | Linux KickCAT 빌드·기본 Slave 실행 | 완료 |
| [RF-002](RF-002-windows-pdo-diagnostic.md) | 2 | Windows PySOEM 물리 PDO 검증 | 완료, 보정 ESI 기준 |
| [RF-002-1](RF-002-1-sdo-diagnostic.md) | 2-1 | SDO 읽기·쓰기·복원 및 PDO 회귀 | 기본 경로 완료, Abort는 TD-001로 보류 |
| [RF-003](RF-003-cmmt-model-integration.md) | 3 | VirtualOdBridge·CMMT 모델 연결 | 기본 1축 경로 검증 완료, 오류 응답 TD-001 보류 |
| [RF-004](RF-004-motion-server-axis-panel.md) | 4 | Motion Server·Axis Panel 통합 | 기본 통합 검증 완료, 실제 Fault 주입은 후속 |

[작업 일지](../Work_log.md) · [전체 설계](../project-plan.md) · [TD 목록](../TD/README.md)

- [RF-005 — 혼합 EtherCAT 버스 및 기존 서버 호환성 검증](RF-005-mixed-bus-feasibility.md): 기본 3 Slave 혼합 타당성 검증 완료 (2026-09-22), 전체 주기 성능·확장 시험은 후속.
- [RF-006 — 명령·리드백 라우터](RF-006-command-feedback-router.md): 계획 / 미착수.
- [RF-007 — 모델 상태 초기화 및 모드 전환](RF-007-mode-switching.md): 계획 / 미착수.
- [RF-008 — Omniverse 축·IO 상태 동기화](RF-008-omniverse-sync.md): 계획 / 미착수.

DT 설계 결정은 [전체 구조](../Design/DT-001-system-architecture.md), [모드 전환](../Design/DT-002-mode-switching.md), [모델 경계](../Design/DT-003-model-interface.md)를 참조한다.

- [RF-009 — 양방향 파라미터 동기화](RF-009-parameter-sync.md): 계획 / 미착수.
- [RF-010 — 가상장치 파라미터 영구 저장·복원](RF-010-parameter-persistence.md): 기본 저장/복원 구현, 후속 검증 진행.

관련 설계: [DT-004](../Design/DT-004-parameter-sync-persistence.md).

- [RF-011 — 시뮬레이터 독립 장치 구성](RF-011-device-configuration.md): 초기 구현·4축 기본 동작 확인. 8 ms 안정성 문제 재현, OD role 조회 병목 개선 및 재측정 필요.

관련 설계: [DT-005 독립 설정·혼합 버스 매핑](../Design/DT-005-device-configuration.md).

- [RF-012 — Simulator Docker 패키징](RF-012-docker-deployment.md): 계획 / 미착수.

관련 설계: [DT-006 Docker 배포 및 NIC 구성](../Design/DT-006-docker-deployment.md).

2026-09-22 설정 형식 변경: RF-011은 JSON 단일 구성 로더를 구현하며 RF-012는 JSON을 읽기 전용 마운트한다. 이전 Simulator .env 문법 계획은 대체되었다. 현재 구현 상태는 각 RF를 따른다.

- [RF-013 — 가상 IO 및 IO-Link](RF-013-virtual-io.md): **Pending / 보류**, 사용자와 별도 논의 후 착수.

2026-09-22 범위 조정: RF-011은 독립 JSON 및 다중 가상축만 구현한다. IO 관련 기존 범위는 RF-013으로 이관한다.

- [RF-014 — 동적 PDO 매핑 지원](RF-014-dynamic-pdo-mapping.md): 계획 / 미착수. 기본 고정 매핑 재설정과 구분하며 TD-001 오류 응답과 연계.

- [RF-015 — 가상축 위치 제한 및 회전 경로 동작 정리](RF-015-axis-model-semantics.md): 계획 / 상세 정책 미결정, RF-011과 분리.

RF-011 계측 근거: [프레임·IPC](RF-011-timing-20260922.md), [Python 모델 시간 분리 및 OD 프로파일](RF-011-python-timing-20260922.md). 최적화는 미적용이다.
