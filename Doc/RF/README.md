# RF 항목 목록

## 현재 상태 요약

상태 기준: **예정 / 진행 중 / 보류 / 완료**. 완료는 각 RF에 명시한 합의 범위를 기준으로 하며 후속 항목의 완료를 의미하지 않는다. 개별 문서의 제목 바로 아래에 현재 상태와 상세 범위를 표시한다. 날짜별 계측 보고서는 요구사항 상태 대신 **검증 기록**으로 표시하고 상위 RF로 연결한다.

| RF | 내용 | 현재 상태 |
| --- | --- | --- |
| [RF-001](RF-001-linux-kickcat.md) | Linux KickCAT 빌드 및 기본 Slave 실행 | **완료** |
| [RF-002-1](RF-002-1-sdo-diagnostic.md) | SDO 읽기·쓰기 및 복원 검증 | **완료** |
| [RF-002](RF-002-windows-pdo-diagnostic.md) | Windows PySOEM 물리 PDO 통신 검증 | **완료** |
| [RF-003](RF-003-cmmt-model-integration.md) | VirtualOdBridge 및 CMMT 가상 서보 모델 연결 | **완료** |
| [RF-004](RF-004-motion-server-axis-panel.md) | Motion Server 및 Axis Panel 통합 테스트 | **완료** |
| [RF-005](RF-005-mixed-bus-feasibility.md) | 혼합 EtherCAT 버스 및 기존 서버 호환성 검증 | **완료** |
| [RF-006](RF-006-command-feedback-router.md) | 명령·리드백 라우터 | **예정** |
| [RF-007](RF-007-mode-switching.md) | 모델 상태 초기화 및 모드 전환 | **예정** |
| [RF-008](RF-008-omniverse-sync.md) | Omniverse 축·IO 상태 동기화 | **예정** |
| [RF-009](RF-009-parameter-sync.md) | 실제·가상 장치 양방향 파라미터 동기화 | **예정** |
| [RF-010](RF-010-parameter-persistence.md) | 가상장치 파라미터 영구 저장 및 복원 | **완료** |
| [RF-011](RF-011-device-configuration.md) | 독립 장치 구성 및 다중 가상축 | **완료** |
| [RF-012](RF-012-docker-deployment.md) | Simulator Docker 패키징 및 실행 검증 | **진행 중** |
| [RF-013](RF-013-virtual-io.md) | 가상 IO 및 IO-Link 시뮬레이션 | **보류** |
| [RF-014](RF-014-dynamic-pdo-mapping.md) | 동적 PDO 매핑 지원 | **완료** |
| [RF-015](RF-015-axis-model-semantics.md) | 가상축 위치 제한 및 회전 경로 동작 정리 | **예정** |
| [RF-016](RF-016-cia402-profile-adapter.md) | CiA402 Drive 프로파일 및 F-KR CMMT 어댑터 | **진행 중** |
| [RF-017](RF-017-copley-fmu.md) | Copley FMU 초기 연동 | **완료** |
| [RF-018](RF-018-diagnostic-fault.md) | 공통 Diagnostic 및 모델 장애 격리 | **완료** |
| [RF-019](RF-019-parameter-management-api.md) | 가상장치 파라미터 관리 API | **예정** |
| [RF-020](RF-020-parameter-history.md) | 파라미터 revision 및 변경 이력 관리 | **예정** |

## 2026-10-28 기존 검증 근거 대조

실제 축·IO + F-KR 2축 + Copley 2축 혼합 환경에서 이미 계속 운전·검증했다. 혼합 연결·물리 SDO/PDO·축 Fault Reset·모델 장애 격리·저장 복원을 신규 미검증 작업으로 반복 등록하지 않는다.

| RF | 판정 | 실제 남은 항목 |
| --- | --- | --- |
| RF-011 | 완료 | 현재 구성·다축 독립성 범위 없음. 기존 오프라인/사용자 물리 확인/RF-010·018 근거 반영 |
| RF-012 | 진행 중 | 배포 재현성, NIC 영향, Docker/native 지연, 동일 Edge 배치·외부 DT 경로 (Slave 자체 실패·복구는 11월 3일 확인) |
| RF-016 | 진행 중 | 현 구조 동일 조건 2축/4축 계측·이동 부하 회귀 |
| RF-017 | 완료 | 초기 연동 범위: 세부 이동·파라미터 효과·혼합 10분 계측 확인. 4ms 전수 준수는 보장하지 않음 |

성능 항목은 묶어서 검증할 수 있지만 기존 완료 기준을 임의 삭제하지 않았다. 30분 등의 신규 합격 조건은 정하지 않았다. 기존 저장/장애 격리 완료 근거는 RF-010/018을 따른다.

## 기록 위치

RF 본문에는 현재 범위·판정·실제 남은 항목을 둔다. 상세 과거 구현/시험 기록은 `Doc/Validation/RF-번호/`에 보관하고 본문에서 연결한다. 과거 JSON/native 명령과 당시 미완료 문구는 현행 계약이 아니다.

- [작업 일지](../Work_log.md) · [프로젝트 계획](../project-plan.md) · [TD 목록](../TD/README.md)
- RF-011 계측: [프레임·IPC](../Validation/RF-011/RF-011-timing-20260922.md), [Python](../Validation/RF-011/RF-011-python-timing-20260922.md), [OD 조회 최적화](../Validation/RF-011/RF-011-role-index-20261020.md).
- 현재 설정은 Simulator 자체 `.env`이며 영구 파라미터 JSON은 유지한다. Motion Server 설정 파일을 읽거나 공유하지 않는다.

## 2026-11-05 RF-014 완료

동적 PDO 매핑·영구 복원·장애 경계·PP 재개·축별 독립성 및 수정 이미지 적용 후 사용자 수동 회귀 확인을 반영했다. 합의 범위 잔여 항목 없음. 상세 근거는 [RF-014](RF-014-dynamic-pdo-mapping.md)를 따른다.
