# RF 항목 목록

## 현재 상태 요약

설계 결정은 [ADR 목록](../Design/README.md), 전체 작업 순서는 [프로젝트 계획](../project-plan.md)을 따른다.

제품 작업 상태: **예정 / 진행 중 / 보류 / 완료**. **범위 외**는 외부 구상 참고 이력이며 제품 미완료 작업으로 집계하지 않는다. 완료는 각 RF에 명시한 합의 범위를 기준으로 하며 후속 항목의 완료를 의미하지 않는다. 개별 문서의 제목 바로 아래에 현재 상태와 상세 범위를 표시한다. 날짜별 계측 보고서는 요구사항 상태 대신 **검증 기록**으로 표시하고 상위 RF로 연결한다.

| RF | 내용 | 현재 상태 |
| --- | --- | --- |
| [RF-001](RF-001-linux-kickcat.md) | Linux KickCAT 빌드 및 기본 Slave 실행 | **완료** |
| [RF-002-1](RF-002-1-sdo-diagnostic.md) | SDO 읽기·쓰기 및 복원 검증 | **완료** |
| [RF-002](RF-002-windows-pdo-diagnostic.md) | Windows PySOEM 물리 PDO 통신 검증 | **완료** |
| [RF-003](RF-003-cmmt-model-integration.md) | VirtualOdBridge 및 CMMT 가상 서보 모델 연결 | **완료** |
| [RF-004](RF-004-motion-server-axis-panel.md) | Motion Server 및 Axis Panel 통합 테스트 | **완료** |
| [RF-005](RF-005-mixed-bus-feasibility.md) | 혼합 EtherCAT 버스 및 기존 서버 호환성 검증 | **완료** |
| [RF-010](RF-010-parameter-persistence.md) | 가상장치 파라미터 영구 저장 및 복원 | **완료** |
| [RF-011](RF-011-device-configuration.md) | 독립 장치 구성 및 다중 가상축 | **완료** |
| [RF-012](RF-012-docker-deployment.md) | Simulator Docker 패키징 및 실행 검증 | **진행 중** |
| [RF-013](RF-013-virtual-io.md) | Modular Device Profile 기반 Remote I/O·모델 연결 | **완료** |
| [RF-014](RF-014-dynamic-pdo-mapping.md) | 동적 PDO 매핑 지원 | **완료** |
| [RF-015](RF-015-axis-model-semantics.md) | 직선축 동작·위치 제한 검증 | **진행 중** |
| [RF-016](RF-016-cia402-profile-adapter.md) | CiA402 Drive 프로파일 및 F-KR CMMT 어댑터 | **완료** |
| [RF-017](RF-017-copley-fmu.md) | Copley FMU 초기 연동 | **완료** |
| [RF-018](RF-018-diagnostic-fault.md) | 공통 Diagnostic 및 모델 장애 격리 | **완료** |
| [RF-019](RF-019-parameter-management-api.md) | 가상장치 파라미터 관리 API | **예정** |
| [RF-020](RF-020-parameter-history.md) | 파라미터 revision 및 변경 이력 관리 | **예정** |
| [RF-021](RF-021-pneumatic-cylinder-fmu-improvements.md) | 공압 실린더 FMU 개선·정격 유량 설정 노출 | **예정** |

## 외부 연동 구상 — Soft ESC 범위 외 참고 이력

아래 문서는 과거 요구를 보존하며 외부 프로젝트의 진행 상태를 의미하지 않는다. Soft ESC 완료 기준에 포함하거나 후속 구현 목록으로 실행하지 않는다.

| RF | 내용 | 현재 분류 |
| --- | --- | --- |
| [RF-006](RF-006-command-feedback-router.md) | 명령·리드백 라우터 | **범위 외** |
| [RF-007](RF-007-mode-switching.md) | 외부 모드 전환 구상(참고 이력) | **범위 외** |
| [RF-008](RF-008-omniverse-sync.md) | Omniverse 축·IO 상태 동기화 | **범위 외** |
| [RF-009](RF-009-parameter-sync.md) | 실제·가상 장치 양방향 파라미터 동기화 | **범위 외** |

## 2026-11-26 제품 범위 요약

총 22개 요구 항목 중 **제품 범위 18개: 완료 13 / 진행 중 2 / 예정 3**, 외부 구상 이력 4개다. Soft ESC는 CiA402 Drive와 EtherCAT Modular Device Profile 기반 Remote I/O를 동작 모델에 연결하는 독립 패키지다.

- RF-013: CPX-AP-I DI/DO/AI/AO·실제 FMU 연결·혼합 운전·Host 장애/복구·재구성/재검색 합의 범위 완료. 아날로그 수동/물리 FMU 왕복은 사용자 결정으로 생략. IO-Link·진단 PDO/이력/Emergency·외부 DT 연동은 제외.
- RF-015: 기존 직선축 지원 대조·회귀. 3축은 Demo 요구에서 가져온 시험 구성.
- RF-012: 새 Linux PC와 축+IO 독립 배포·복원·통신 확인. Edge #2는 배포 사례.
- RF-019/020: 후속 제품 기능. 이번 IO 지원의 필수 조건으로 확대하지 않음.
- RF-021: 정격 유량의 FMU 외부 설정 지원. RF-013은 기존 FMU로 계속 진행하며 개선 완료를 기다리지 않음.

DT/Sync·Pairing·정렬 절차·ROS2/Omniverse는 제품 실행 의존성이 아니다. IO-Link·회전 확장·NIC 추가 시험은 기존 후속/보류 경계를 유지한다. 기존 완료 검증을 보존하고 변경 영향만 회귀한다. [제품 정의](../Design/ADR-001-system-architecture.md), [프로젝트 계획](../project-plan.md)를 따른다.

이하 날짜별 상태표와 잔여 항목은 당시 이력이다. 현재 판정은 위 요약과 개별 RF의 최신 범위를 우선한다.

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

## 2026-11-05 성능 비교 반영

RF-016의 현재 구조 2축/4축·이동 부하 비교 완료. RF-012 Docker/native 비교도 완료하여 새 PC/OS 및 동일 Edge Master 배치만 남긴다. NIC 추가 검증·Omniverse는 기존 결정대로 보류/추후 범위다. [공통 보고서](../Validation/RF-016/runtime-comparison-20261105/README.md).
