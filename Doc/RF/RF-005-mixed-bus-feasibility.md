# RF-005 — 혼합 EtherCAT 버스 및 기존 서버 호환성 검증

- 등록일: 2026-09-15
- 완료일: 2026-09-22
- 상태: **완료 — 기본 3 Slave 혼합 타당성 검증**
- 설계: [DT-001](../Design/DT-001-system-architecture.md)
- 선행: RF-001~004 기본 통신·모델·통합 검증

## 완료 범위

실제 CMMT-AS 1대, 실제 CPX-AP-I-EC 1대, KickCAT 가상 CMMT-AS 1대를 같은 EtherCAT 라인에 연결한 기본 동작을 검증했다. Motion Server를 독립 패키지로 유지하며 기존 API에서 장치 선택·상태 조회 경로를 확인했다. 아래 완료 기준에 남은 필수 항목은 없다. 후속 제품화·확장·성능 항목은 이관 표에서 별도 관리한다.

## 완료 기준 및 근거

- [x] 동일 EtherCAT 라인의 실제·가상 장비 정상 동작: 사용자 시험 확인.
- [x] 실제 축 선택 시 가상 축 유지, 가상 축 선택 시 실제 축 유지: 사용자 확인.
- [x] 실제 CPX IO 입력 상태 읽기: 사용자 확인.
- [x] 기존 API의 축·IO 선택, 피드백·파라미터 진입점 조사와 지원 제약 기록: 읽기 전용 코드 확인.
- [x] 성공 세션의 설정 주기·기대/실제 WKC 표본·관측 시간 기록: [5분 관측 보고서](RF-005-observation-20260922.md).

| 버스 Slave | 장치 | 서버 식별 |
| --- | --- | --- |
| 0 | 실제 CMMT-AS | Axis 0 |
| 1 | 실제 CPX-AP-I-EC | io0 |
| 2 | 가상 CMMT-AS | Axis 1 |

Simulator 자체의 추가 Slave를 설정하지 않고 가상 CMMT를 세 번째 장치로 취급한 기본 구성이다. 다중 가상 Slave 생성까지 확인한 것은 아니다.

## 통신 관측 결과

2026-09-22 14:42:41~14:47:41 KST에 실행 중인 TCP 서버를 300.043초 동안 관측했다. 서버 보고 설정 주기는 8 ms, 장치 3대·축 2개, 약 1초 간격 bus/status 298회 모두 WKC 9/9였다. 피드백 5,358개 모두 유효했고 관측 연결 끊김·실패 응답은 없었다.

별도 Master 실행, 제어권 획득, 장비 이동·IO 쓰기, 서버 재시작은 하지 않았다. 사용자 동작 시험과 에이전트 읽기 전용 관측을 구분한다. OP 레지스터를 직접 계측한 것이 아니라 normal 상태와 유효한 피드백을 확인했다. 전체 PDO별 오류 0회나 실제 주기 지터를 입증하지 않는다. 원본 위치와 재현 방법은 관측 보고서에 기록했다.

## 후속 이관 — RF-005 완료를 막지 않는 항목

| 항목 | 이관 대상 | 남은 작업 |
| --- | --- | --- |
| 비선택 그룹 대기, 제어권, 전체 명령 영향 | [RF-006](RF-006-command-feedback-router.md), [RF-007](RF-007-mode-switching.md) | 시작 시 전체 Enable·단일 축 restart 시 전체 Disable을 반영한 라우터/전환 정책 |
| 실제·가상 파라미터 적용·저장 | [RF-009](RF-009-parameter-sync.md), [RF-010](RF-010-parameter-persistence.md) | 실제 read/write/save, 쓰기 상태 조건, 서버 초기화 재기입과 저장 설정 충돌 검증 |
| 다축·가상 IO·12 Slave 목표 | [RF-011](RF-011-device-configuration.md) | 다장치 생성·ID 매핑 및 확장 혼합 시험. 현재 3 Slave 결과로 대체하지 않음 |
| Docker 및 Edge 동시 배치 | [RF-012](RF-012-docker-deployment.md) | 컨테이너 raw NIC·종료/재시작·영구 저장과 배치 검증 |
| 전체 PDO WKC 계수·실제 주기 지터 | 별도 성능 검증 (항목 번호 미부여) | 연속 주기 계측 및 목표 성능 기준 확정. 현재는 표본 관측만 완료 |

이관은 해당 기능의 구현 완료를 뜻하지 않는다. 원래의 조건부 기준인 ‘전제 미충족 시 설계 재논의’는 기본 혼합 동작에 대해 발동하지 않았으며, 알려진 제약은 위 후속 항목에서 관리한다.

## 코드 및 실행 근거 (2026-09-22)

Motion Server HEAD는 10308db6b480c41c9be5f96fb44e07f6cafb0f9f이며 사용자 미커밋 변경이 있다. HEAD만으로 실행 소스 전체를 식별하지 않는다. 이번 점검에서 제품 코드를 수정하지 않았다.

### 코드로 확인한 지원 및 제약

- configuration/bus.py의 axis_slave_indices는 IO를 제외한 축 Slave를 순서대로 제공한다. 현재 3 Slave 구성에서는 실제 축 Axis 0 / Slave 0, IO io0 / Slave 1, 가상 축 Axis 1 / Slave 2로 해석한다.
- motion_server/handlers/command/registry.py는 axis별 enable/disable/home/stop/move 및 axes 목록 명령을 제공한다. 라우터의 대상 ID 변환에 사용할 기존 진입점이 있다. 실제 비선택 축 불변 동작까지 코드 조사만으로 확정하지 않는다.
- handlers/status/feedback.py는 actual_positions, actual_velocities, statuswords, mode_displays, process_data_valid 및 IO 상태를 제공한다. 서버 전체 제어권 owner를 사용하며 그룹별 제어권은 아니다.
- handlers/command/io_output_write.py는 IO ID 또는 slave_index로 대상을 선택한다.
- handlers/parameter_access/ethercat.py와 명령 레지스트리에 축별 파라미터 읽기·쓰기·저장 및 IO별 읽기·쓰기 경로가 있다. 저장 명령은 장치 프로파일에 위임한다. 가상장치의 실제 영구 저장 기능이나 모든 객체 지원은 별도 검증이다.
- app/startup.py initialize_drive는 모든 축에 0x0006→0x0007→0x000F를 적용한다. 비선택 실제 축도 시작 시 Enable될 수 있다. 모든 축을 항상 비활성 유지한다는 요구와는 맞지 않으며 시작 후 대기 상태 정책을 RF-006/007에서 결정해야 한다.
- handlers/command/axis_state.py restart_axis는 단일 축 선택이어도 모든 축 위치 hold 및 0x0007 적용을 수행한다. 축 재시작은 그룹 독립 명령으로 취급하지 않는다. 서버/버스 재연결 역시 공통 운용 작업으로 분리해야 한다.
- device/cmmt/profile.py prepare_process_image는 PDO mapping/assignment를 재기입한다. startup.py는 restart 요청 초기화·CSP interpolation mode 적용 및 SDO 읽기값을 profile velocity PDO에 반영한다. 파라미터 전체가 쓰기 없이 보존된다고 주장하지 않는다. 전체 쓰기 목록·영구 저장과의 충돌 검증은 RF-009/010에 남긴다.

### 실행 근거 확인

Linux에서 cmmt-session.py, cmmt_simulator 및 model_service.py가 실행 중인 것을 확인했다. 세션은 manual20260922134744, NIC enp1s0, 모델은 build/model-source-da0b0a3이다. simulator.log의 CMMT_READY rx=24 tx=14와 model-ready를 확인했다. 준비 로그는 Master의 OP/WKC 성공 로그를 대신하지 않는다.

Linux 저장소 HEAD: 5c4431384b98fd8eed63cc9f11ec460b966f3706. KickCAT: 43ad3e9ce390f0f6d9548118098bcaafc0d4f1f1. 미커밋 파일 및 binary의 빌드 출처를 이 HEAD만으로 확정하지 않는다.


## 시험 이력

초기에는 Slave 2가 기본 Board product code 0x00DEFEDE로 응답해 CMMT 설정과 불일치했다. CMMT용 cmmt-session.py 안내 이후 사용자가 혼합 동작 성공과 선택 제어·IO 읽기를 확인했고, 이어서 5분 상태 관측을 수행했다. 최초 점검 시 미확보였던 WKC 표본·설정 주기·관측 시간은 위 최종 결과로 보완했다.

2026-09-22 완료 정리에서 초기 미체크 목록을 완료 기준과 후속 이관으로 분리했다. 과거의 ‘완료 보류’ 문구는 당시 상태이며 현재 판정은 이 문서 상단의 완료 상태를 따른다. 상세 진행 순서는 [작업 일지](../Work_log.md)에 보존한다.
