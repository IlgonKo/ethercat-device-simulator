# DT-008 — Diagnostic 및 Fault 처리

- 합의 반영일: 2026-10-28
- 상태: 현재 축 Fault/Reset·IPC 격리 구현 및 물리 연동 검증 완료 / 관리·자동 복구 후속 보류
- 관련 요구: [RF-018](../RF/RF-018-diagnostic-fault.md)
- 참조: Motion Server `docs/diagnostic/diagnostic_model.md`, `motion_server/diagnostic/{models,manager,runtime}.py`, `motion_server/app/recovery.py`

## 목적과 경계

현재 구현 및 검증 범위는 [RF-018의 현재 구현 및 검증](../RF/RF-018-diagnostic-fault.md)을 따른다. 이하 설계 전체가 구현됐다는 의미는 아니다. 관리 API·통합 영구 진단 저장소·모델 재생성/위치 수락은 보류 상태다.

### 현재 구현 범위 — 2026-10-28 후속 합의, 아래 장기 복구 설계보다 우선

- 관리 인터페이스(API/CLI), 별도 Model Recovery·Slave Recovery, 실행 중 위치 수락/재동기화 기능은 후속으로 미룬다. 이하 관련 설계는 장기 방향으로 보관하며 현재 구현의 필수 조건으로 적용하지 않는다.
- 현재 사용자 복구 경로는 Motion Server를 통한 축 Fault Reset과 수동 Docker 재시작이다. 축 Fault Reset은 실행 가능한 어댑터/모델의 원인이 해소된 축 Fault를 대상으로 한다. Reset으로 모델을 재생성하거나 공유 Slave/컨테이너를 재시작하지 않는다.
- 모델 crash/hang·IPC 단절 등 축 Reset으로 복구할 수 없는 장애는 사용자가 Docker를 재시작한다. 원인이 남아 있거나 모델 응답을 검증할 수 없으면 Reset 성공으로 표시하지 않는다.
- 일반 축 Fault Reset에는 위치 수락 API를 요구하지 않는다. 모델을 재생성하지 않은 Reset 경로와 모델 재생성 후 위치 수락 경로를 구분한다.
- Docker 재시작은 Slave까지 다시 시작하는 새 실행 세션이다. 기존 EtherCAT 연결 유지 또는 이전 모델 위치 복원을 보장하지 않는다. 사용자가 Motion Server 버스를 재연결/초기화하고 새 위치를 확인한 후 명시적으로 Enable·새 이동 명령을 보낸다. 자동 운전 재개는 하지 않는다.
- 관리 API 보류가 FMU 장애 시 Slave 통신 유지 목표의 취소를 의미하지 않는다. 장애 검출·Fault 반영·명령 차단과 사용자 복구 인터페이스는 별도 범위다. 상세 진단의 현재 확인 수단은 로그이며 관리 조회 기능은 후속이다.

FMU 오류·응답 지연 시 EtherCAT Slave를 유지하는 기능보다 먼저 전체 Diagnostic/Fault 처리 기준을 정의한다. Motion Server와 데이터 구조·수명 주기를 맞추되 패키지 사이에 런타임 의존성을 만들지 않는다. 이 문서는 합의된 목표이며 현재 구현 완료를 의미하지 않는다.

요청 실패(failure), 지속 상태의 진단(diagnostic), 실제 복구(recovery), CiA402 상태 반영을 분리한다. 미지원 SDO 하나로 장치 Fault를 만들거나 모델 서비스를 종료하지 않는다. 내부 예외는 원인을 분류한 후 필요한 경우에만 Diagnostic으로 등록한다.

## 동일하게 적용할 데이터 계약

| 객체 | 필드 |
| --- | --- |
| DiagnosticDefinition | code, level, title, description, latching |
| DiagnosticSource | type, index |
| DiagnosticHistory | occurred_at, acknowledged_at, resolved_at |
| DiagnosticStatus | diagnostic_id, definition, source, history, detail, context |

- Definition은 불변 정의다. level은 `normal / alarm / fault`이며 NORMAL Definition/발생 건은 만들지 않는다. 현재 정상 수준은 활성 진단으로 계산한다.
- `detail: str | None`, `context: dict[str, object] | None`은 optional이다. 외부 직렬화에 노출할 상세 범위는 후속 결정한다.
- 발생 건은 `(code, source.type, source.index)`로 중복을 억제한다. clear 전 반복 검출은 동일 건이며 resolved 후 acknowledge 대기 중 재검출되면 resolved_at을 해제한다. clear 후 재발하면 새 diagnostic_id를 만든다.
- acknowledge는 사용자 확인, resolve는 실제 조건 해제다. acknowledge만으로 실제 복구·운전 재개를 수행하지 않는다.
- non-latching은 resolve 시 clear한다. latching은 resolve와 acknowledge가 모두 완료돼야 clear한다.
- cleared_at은 별도 저장하지 않는다. non-latching은 resolved_at, latching은 두 시각 중 늦은 값으로 계산한다.
- 발생 횟수·응답 시간·마지막 정상 피드백 시각은 별도 통계다. 복구 방법은 Definition 필드가 아니라 별도 정책/핸들러로 연결한다.
- 활성 저장소에서 clear된 진단은 제거한다. 이력 보관 위치·기간은 미결정이다.

## Source와 영향 범위

| Source | 의미 |
| --- | --- |
| simulator:0 | 설정·실행 관리·공통 저장소 |
| ethercat:0 | EtherCAT Slave 통신 실행부 |
| model_host:N | 공유 모델 프로세스와 IPC. 현재 Host는 0 |
| axis:N | 특정 가상축의 모델·장치 상태 |

축 index는 시뮬레이터 내부 축 index다. 실제 장비가 앞에 붙어도 Master 전체 버스 번호로 바꾸지 않는다. 안정적인 장치 ID 및 slave_index와의 대응은 구성 정보로 연결한다. 향후 IO는 별도 범위다.

Source는 발생 위치이며 영향받는 축 집합과 다르다. 한 FMU가 오류를 반환해도 Host가 정상 실행 가능하면 축 단위로 처리한다. native crash/hang 등 Host 실행 신뢰성이 깨지면 해당 Host의 모든 축에 적용한다.

## 오류별 검출·영향·상태 반영

‘축 Fault 반영’은 CiA402 Fault 상태 보고 및 해당 축의 새 운동 명령 실행 차단이다. EtherCAT Slave 종료나 버스 연결 해제를 의미하지 않는다.

| 코드 | 검출 책임자 / Source | 영향 범위 | 수준 / latching | 상태 반영 |
| --- | --- | --- | --- | --- |
| SIMULATOR_INITIALIZATION_FAILED | 실행 관리부 / simulator:0 | 시뮬레이터 시작 | Fault / true | 초기화 실패. 미준비 장치를 정상 Slave로 제공하지 않음 |
| ETHERCAT_TRANSPORT_FAILED | Slave 통신부 / ethercat:0 | 해당 통신 경로 | Fault / true | 통신 불가 보고, 모델 명령 실행 차단. NIC 장애 중 프레임 응답은 보장 불가 |
| MODEL_HOST_DISCONNECTED | Slave IPC 감시부 / model_host:N | 해당 Host의 모든 축 | Fault / true | 축 Fault, 피드백 무효화. EtherCAT 처리 유지 |
| MODEL_RESPONSE_TIMEOUT | Slave 요청 기한 감시부 / model_host:N | 해당 Host의 모든 축 | Fault / true | 위와 동일. 늦은 응답 폐기 |
| AXIS_MODEL_EXECUTION_FAILED | 모델 실행기 / axis:N | 해당 축 | Fault / true | 해당 모델 계산 중단, 축 Fault. 다른 축은 계속 실행 가능 |
| AXIS_ADAPTER_FAULT | 어댑터 입력·조건 검증 / axis:N | 해당 축 | Fault / true | 주기 입력 거부 시 운동 차단. 입력/조건 수정 후 축 Reset으로 재검증 |
| AXIS_MODEL_OUTPUT_INVALID | 모델 실행기·Slave 수신 검증부 / axis:N | 해당 축 | Fault / true | 잘못된 결과 반영 금지, 축 Fault |
| AXIS_DRIVE_FAULT | 어댑터 모델 상태 감시부 / axis:N | 해당 축 | Fault / true | 모델 자체 Fault 전달. Reset을 위한 모델 통신·계산 유지 |
| AXIS_DRIVE_WARNING | 어댑터 모델 상태 감시부 / axis:N | 해당 축 | Alarm / false | 모델 Warning 전달. 경고만으로 명령 차단하지 않음 |
| PARAMETER_SAVE_FAILED | 저장부 / axis:N 또는 simulator:0 | 해당 저장 작업 | Alarm / false | 저장 실패 응답, 기존 파일 보존. 메모리 운전 상태 유지 |
| MODEL_RECOVERY_FAILED | 복구 관리부 / 복구 대상 Source | 복구 대상 축/Host | Fault / true | 기존 Fault·명령 차단 유지, 자동 운전 재개 금지 |

- Host 종료가 확인되면 DISCONNECTED를 우선하고 같은 사건을 timeout으로 중복 등록하지 않는다. timeout 후 종료 확인 시의 발생 건 연결/전환 규칙은 상세 설계에서 확정한다.
- 내부 실행 장애로 Statusword에 Fault를 설정했다고 모델 자체의 AXIS_DRIVE_FAULT를 재생성하지 않는다. 원인과 상태 투영을 구분한다.
- OUTPUT_INVALID는 양쪽에서 검증할 수 있지만 같은 사건의 중복 등록을 막는 식별·전달 계약이 필요하다.
- 위 표의 ‘다른 축 실행 가능’은 격리된 오류 반환 경로에 한한다. 공유 프로세스 오류까지 격리된다는 보장은 아니다.

## 복구와 Resolve 조건

| 코드 | 복구 동작 | Resolve 조건 |
| --- | --- | --- |
| SIMULATOR_INITIALIZATION_FAILED | 설정·파일·파라미터 수정 후 초기화 재시도 | 필수 초기화 및 장치 계약 검증 완료 |
| ETHERCAT_TRANSPORT_FAILED | NIC/통신 경로 복구 후 통신부 재준비 | 통신부 준비·복구 검증 완료. 명령 재개는 별도 절차 |
| MODEL_HOST_DISCONNECTED | Host 재시작/재연결, 새 세션 수립 | 모델 계약·파라미터·정상 응답 검증 완료 |
| MODEL_RESPONSE_TIMEOUT | 기존 세션 격리 후 연결 복구 | 새 세션의 응답 기한·결과 검증 통과. 늦은 응답 하나로 resolve하지 않음 |
| AXIS_MODEL_EXECUTION_FAILED | 모델 재초기화/재생성 | 모델 준비 및 유효 출력 검증 완료 |
| AXIS_ADAPTER_FAULT | 입력/파라미터 원인 수정 후 축 Fault Reset | 비운동 상태에서 입력·모델 실행 검증 및 Reset-low Fault 해제 확인 |
| AXIS_MODEL_OUTPUT_INVALID | 원인 수정 후 모델 재준비 | 자료형·범위·유한값·출력 크기 검증 통과 |
| AXIS_DRIVE_FAULT | CiA402 Fault Reset을 모델에 전달 | 모델 자체 Fault 조건이 실제로 해제됨 |
| AXIS_DRIVE_WARNING | 모델 경고 원인 해소 | 모델이 Warning 해제를 보고함 |
| PARAMETER_SAVE_FAILED | 원인 해소 후 저장 재시도 | 해당 파라미터 저장 실제 성공 |
| MODEL_RECOVERY_FAILED | 동일 대상 복구 재시도 | 해당 복구 절차 성공 |

latching 진단은 resolve 후에도 acknowledge 전까지 활성 상태다. 진단 clear와 장치 운전 재개는 같은 동작이 아니다. 두 상태의 연계 및 Fault Reset이 acknowledge까지 수행하는 범위는 후속 결정한다.

현재 Copley는 재생성 시 초기 위치 0으로 돌아간다. 모델 실행 복구 완료와 위치 동기화 완료를 구분하고, 이전 위치를 복원한 것처럼 취급하지 않는다.

## 사용자 동작과 Reset/Recovery 경계 — 합의

| 사용자 동작 | 역할 |
| --- | --- |
| 진단 조회 | 활성 Alarm/Fault와 원인·영향 범위 확인 |
| Acknowledge | 발생 건 확인. 복구나 운전 재개는 하지 않음 |
| 축 Fault Reset | 해당 축의 어댑터 Fault와 모델 드라이브 Fault 해제 시도. 원인이 제거된 경우에만 해제 |
| Model Recovery | 모델 재생성·IPC 재연결·저장 파라미터 복원. 이후 축 Fault Reset 필요 여부 확인 |
| EtherCAT 오류 확인·상태 복구 | Master가 AL 오류를 확인하고, 원인 제거 후 EtherCAT 상태 전환을 다시 요청 |
| Slave Recovery | EtherCAT Slave 실행부의 NIC·소켓 등 통신 자원 복구. 필요하면 Master의 버스 재연결 수행 |
| Simulator Restart | Slave·모델 서비스 등 전체 실행부 재시작 |

- 어댑터 Fault Reset은 별도 사용자 명령 대신 축 Fault Reset 내부 처리에 포함한다. 원인에 따라 어댑터 오류 상태의 재검증·해제와 모델 드라이브 Reset을 수행한다. 축을 차단하는 원인이 남아 있으면 외부 CiA402 Fault를 해제하지 않는다.
- 모델 Host가 없거나 모델 실행이 불가능하면 Model Recovery로 실행 기반을 복구한 뒤 필요한 축 Reset을 수행한다.
- Slave가 검출한 IPC 장애도 모델/Host 복구 대상이다. 검출 주체가 Slave라는 이유만으로 Slave 실행부를 재시작하지 않는다.
- Slave Recovery는 축 Fault Reset과 분리한다. 공유 Slave 실행부 복구는 모든 연결 가상축의 통신에 영향을 줄 수 있다. 축 하나의 Reset으로 공유 Slave를 재시작하지 않는다.
- Master의 EtherCAT AL 오류 확인·상태 복구와 CiA402 축 Fault Reset은 별개다. NIC 장애 중에는 EtherCAT 경유 Reset/응답을 보장할 수 없다.
- 미지원 SDO의 Abort는 요청 실패이며 Reset 대상이 아니다.
- 모든 Reset/Recovery/Restart 성공 후 자동 축 Enable 및 이전 이동 명령 재실행을 금지한다. 통신·모델 준비와 운전 재개를 분리한다.

위 표는 역할 합의다. 관리 API/CLI 이름·전송 방식, Fault Reset의 acknowledge 연계는 미확정이다. 어댑터 자체 Fault의 세부 진단 코드·검출/Resolve 조건도 구현 전 오류 처리표에 추가한다.

## 장애·복구 중 피드백과 운전 재개 — 합의

| 상황 | 처리 원칙 |
| --- | --- |
| 모델 오류·응답 지연 | 영향받는 축을 Fault로 표시하고 새 이동 명령 실행 차단 |
| 유효한 모델 출력이 없는 동안 | 마지막 정상 위치 보관. 진단 조회에 피드백 무효 여부와 마지막 정상 시각 제공 |
| 속도·토크 피드백 | 보관값과 유효값을 구분. 임의로 0을 넣어 정상 정지로 표현하지 않음 |
| 모델 복구 완료 | 새 출력과 파라미터 검증 후 모델 준비 상태로 전환. 운전 가능 상태와 구분 |
| 복구 전후 위치 불일치 | 자동 위치 복원·이동 금지. 위치 재동기화 전 Enable 차단 |
| 운전 재개 | 필요한 Fault Reset·위치 확인 후 명시적 Enable과 새 명령으로 재개 |

현재 PDO에는 별도 피드백 유효성 필드가 없으므로 Master에는 CiA402 Fault로 알리고 상세 유효성은 시뮬레이터 진단 조회에서 제공한다. 기존 PDO에 임의 필드를 추가하지 않는다. 마지막 정상 시각 등은 DiagnosticDefinition에 추가하지 않고 별도 상태/통계로 제공한다.

모델 오류로 계산이 멈춘 경우의 보관값은 현재 위치·속도·토크를 보증하지 않는다. 모델 자체 드라이브 Fault라도 계산·출력은 유효할 수 있으므로 Fault 여부와 피드백 유효성을 별도로 관리한다.

## 위치 재동기화 — 복구 위치 수락 방식 합의

1차 구현은 사용자가 복구된 모델 위치를 새 기준으로 수락하는 방식으로 확정한다. 아래 절차의 관리 명령 형식·판정 수치·새 명령 재수락 조건은 상세 설계 대상으로 남긴다.

1. 장애 시 Slave가 마지막 정상 피드백과 모델 세션을 보관하고 영향 축의 운동 명령 실행을 차단한다.
2. Model Recovery는 새 세션에서 저장 파라미터와 출력 유효성을 검증한다. 이전 세션의 응답과 대기 중 이동 요청은 재사용하지 않는다.
3. 복구된 모델의 위치를 별도로 확인하고 이전 위치와 비교한다. 위치 일치 허용오차·정지 판정·정상 응답 횟수는 후속 결정한다. 무효한 속도 보관값으로 정지를 판정하지 않는다.
4. 사용자가 복구된 모델의 현재 위치를 새 기준으로 수락한다. Copley 재생성 시에는 0을 새 현재 위치로 수락한다. 이전 위치로 이동시키거나 피드백만 이전 값으로 덮어쓰지 않는다.
5. 수락 시 새 세션의 위치와 유효성 정보를 일관되게 공개하고, 연동 측에서 Master의 현재 위치 재조회와 DT 표시 갱신을 확인한다. 시뮬레이터 혼자 Master/DT 내부 상태의 동기화 완료를 보증하지 않는다. 관리 명령과 확인 방식은 미확정이다.
6. 축 Reset 및 명시적 Enable 후 새 이동 요청만 실행한다. 장애 이전 Controlword/목표 위치가 PDO에 반복되어도 자동 재실행하지 않도록 명령 재수락 조건을 별도 정의한다.

실제 장비를 움직여 가상축에 맞추지 않는다. 실제/가상 모드 전환 동기화는 [DT-002](DT-002-mode-switching.md)의 별도 절차다. 향후 모델이 명시적 초기 상태 설정을 지원하면 정지 상태 주입을 검토할 수 있지만, 현재 Copley는 임의 초기 위치 및 실제 FMI 상태 복원을 지원하지 않는다.

좌표 offset으로 이전 표시 위치를 유지하거나 모델에 이전 상태를 주입하는 기능은 1차 구현 범위에서 제외한다. 향후 좌표 변환을 도입하려면 절대 목표·상대 이동·위치 제한·참조 상태까지 일관되게 변환해야 하며, 위치 표시 연속성이 모델의 내부 동적 상태 복원을 의미하지 않는다.

### 위치 수락 거부·보류 — 합의

복구된 위치를 수락하지 않으면 해당 축은 재동기화 대기 상태를 유지하고 Enable·이동을 차단한다. EtherCAT 통신과 진단 조회는 계속 유지한다. 수락 거부 자체로 다른 정상 축을 차단하지 않으며, 공유 Host 장애에 따른 영향 범위는 기존 정책을 따른다.

| 사용자 선택 | 처리 |
| --- | --- |
| 나중에 수락 | 재동기화 대기 및 해당 축 운전 차단 유지 |
| 복구 재시도 | Model Recovery 재실행 후 복구 위치 재확인. 현재 Copley는 다시 0으로 초기화되므로 이전 위치 복원이 아님 |
| 시험 종료 | 해당 축을 운전하지 않고 시험 종료 |

Model Recovery 성공과 위치 수락 여부는 별도 상태다. 정상 복구 후 사용자가 수락하지 않은 상황을 새로운 모델 오류나 MODEL_RECOVERY_FAILED로 등록하지 않는다. 진단·상태 조회에 ‘위치 수락 대기 — 운전 차단’을 표시한다. 기존 진단의 resolve/acknowledge 수명 주기는 유지하며, 진단 clear만으로 위치 수락을 대신하지 않는다.

수락 거부·보류를 이유로 자동 수락하거나 이전 위치까지 자동 이동하지 않는다. 이전 위치 복원은 현재 범위에서 지원하지 않으며, 모델 초기 위치 설정·좌표 변환은 별도 확장 대상이다. 대기 상태의 구체적 API 필드와 CiA402 상태 표현은 운전 재개 계약의 상세 설계에서 결정한다.

## 운전 재개 정책 — 합의

- 위치 수락은 현재 복구 세션에만 유효하다. 재장애·모델 재생성 시 무효화한다.
- 모델 준비·위치 수락이 완료되고 차단 원인이 해소된 경우 축 Fault Reset에 따른 해제를 허용한다. 위치 수락과 Reset은 별도 동작이다.
- 이전 Enable 유지값으로 재개하지 않고 복구 후 새 Enable 절차를 요구한다.
- PP는 새로운 이동 요청 신호를 기준으로 실행한다. 목표 위치 값의 변화 여부로 새 요청을 판정하지 않는다.
- 장애 전 대기 명령과 이전 세션의 늦은 응답을 폐기한다.
- 시뮬레이터의 축 Fault Reset은 처리 대상의 관련 진단만 acknowledge한다. 다른 축·공통 Host/통신 장애를 일괄 확인하지 않는다. acknowledge와 실제 resolve는 분리한다.

## Motion Server 코드 확인 및 적용 조건 — 2026-10-28

확인 대상: 별도 Motion Server 저장소 HEAD `1c159b6d7e050963b0bf9c1f16b989a8bbca8c16`의 로컬 코드. 아래는 코드 검토 결과이며 물리 복구 시험 완료가 아니다. Motion Server 코드는 변경하지 않았다.

| 동작 | 확인한 실제 순서 | 근거 (Motion Server 저장소 기준) |
| --- | --- | --- |
| system/axis/fault_reset | 원래 CW에서 bit7만 low 2주기 → high 2주기 → low 2주기, 이후 0x0006 5주기 → 0x0007 5주기 | motion_server/handlers/command/axis_state.py: reset_faults |
| system/axis/enable | 0x000F 설정 후 3주기 교환 | 같은 파일: enable |
| system/axis/disable | 현재 위치로 내부 목표 정렬, 0x0007 설정 후 3주기 교환 | 같은 파일: disable |
| PP move_abs/move_rel | 목표 위치 설정, CW 0x000F → 0x003F → 0x000F. 각 단계에서 SW bit12 ACK 0 → 1 → 0 대기, 단계당 최대 100주기 | motion_server/control/setpoint_output.py: command_profile_positions, pp_setpoint_handshake; device/cmmt/profile.py |
| 상대 이동 | 현재 실제 위치 + 거리로 절대 목표를 계산한 후 동일 PP handshake | motion_server/handlers/command/motion.py: move_relative; motion_server/app/runtime.py: relative_target_positions |

### 서버 수정 없이 적용할 시뮬레이터 측 조건

1. 복구 세션의 위치 수락 전에는 Reset/Enable/PP 실행을 허용하지 않는다. 이때 받은 Reset을 보류했다가 수락 직후 실행하지 않는다. 수락 이후 bit7 low를 관측한 다음 rising edge를 새 Reset으로 받는다.
2. Reset 처리 중 이전 CW의 Enable·new-setpoint 비트가 그대로 남을 수 있다. 원본 PDO 관측과 모델 전달 명령을 분리해 Reset만 처리하고 운동은 차단한다. Reset이 성공해도 곧바로 기존 0x000F/0x003F를 모델에 통과시키지 않는다.
3. Reset 후 서버가 보내는 0x0006 → 0x0007 순서를 관측하고 모델의 비활성 상태를 확인한다. 그 뒤 bit7=0, bit4=0인 Enable Operation 요청(현 서버 0x000F)을 새 Enable로 수락한다. 프레임 횟수를 5/3으로 고정하지 않고 상태 전환으로 판정한다. 초기 비활성 모델도 이 순서로 준비할 수 있다.
4. Operation Enabled 확인 후 PP 요청 bit4 low를 관측하고 다음 rising edge에서 목표를 수락한다. Enable 프레임의 bit4 low도 기준으로 사용할 수 있다. bit4가 high인 채 반복되는 이전 PDO는 새 요청으로 처리하지 않는다. 목표 값이 같아도 새 edge면 새 요청이다.
5. 실제 모델이 요청을 수락한 경우에만 SW bit12 ACK를 반영하고, 요청 low에 따라 ACK를 해제한다. 차단 요청에 성공 ACK를 합성하지 않는다. 기존 서버의 100주기 handshake 한도 내 응답 여부는 구현 후 검증한다.
6. 재장애 시 위 준비 상태와 edge 관측 기록을 무효화한다. 모델 세션 식별자는 IPC 응답 검증에도 적용한다. 보관된 실제 피드백과 모델에 전달하는 초기 정지 목표를 구분하며, 새 PP 요청 전까지 오래된 목표를 실행하지 않는다.

적용 범위는 현재 Copley 및 F-KR의 PP 복구 경로다. CSP/PV/JOG에는 같은 PP edge 조건을 적용할 수 없으며 모드별 재개 계약을 추가로 결정한다. 원시 Controlword 쓰기도 동일한 시뮬레이터 상태 검증을 우회하지 못하게 한다.

### 운용 절차와 한계

- 모델 복구와 위치 수락은 시뮬레이터 관리 기능에서 수행한다. 기존 Motion Server에는 이 기능이 없으므로 기존 API로 된 것처럼 표현하지 않는다. 관리 인터페이스는 후속 구현한다.
- 수락 후 현재 위치를 Master에서 재조회하고 DT를 갱신한다. 기존 `system/axis/disable`은 목표를 현재 위치로 정렬하므로 재개 준비 시 사용할 수 있다. 이후 `system/axis/fault_reset` → Fault 해제/Switched On 상태 확인 → `system/axis/enable` → Operation Enabled 확인 → 새 `move_abs` 또는 `move_rel` 순서로 운용한다.
- 서버 Reset 응답의 완료 문구는 실제 Fault 해제의 보증이 아니다. 코드가 Statusword 해제를 필수 성공 조건으로 검사하지 않으므로 상태를 별도로 확인해야 한다.
- 서버의 Reset은 해당 축 Source의 Fault들을 acknowledge한다. 시뮬레이터 진단 저장소와 별개이며, 시뮬레이터는 합의한 관련 원인만 acknowledge하는 정책을 자체 구현한다.
- 서버의 위치 명령은 전체 축 중 하나라도 Fault이면 거부한다(`command_position_axes` → `faulted_axes`). 시뮬레이터가 다른 축을 정상 유지해도 서버에서 다른 축의 신규 위치 명령이 거부될 수 있다. 서버 수정 없이 축별 신규 운전 독립성까지 보장할 수 없다.
- EtherCAT PDO에는 API 요청 ID나 발행 시각이 없다. 새 edge는 새 버스 요청을 뜻할 뿐, 장애 전에 외부 클라이언트가 예약했다가 나중에 재전송한 명령인지 구분할 수 없다. 운용 측에서 자동 명령 공급을 중지하고 대기 요청을 폐기한 뒤 재개해야 한다. 시뮬레이터가 폐기할 수 있는 범위는 자기 대기 명령·이전 IPC 응답이다.
- 위 조건은 기존 서버의 PP 순서와 정적으로 호환된다. 실제 복구·PP ACK·동일 목표 재명령·거부 상태 지속·재장애 시험은 RF-018 구현 후 수행한다.

## Diagnostic으로 승격하지 않는 요청 실패

| 상황 | 응답 | 상태 |
| --- | --- | --- |
| 미지원 SDO·쓰기 금지 OD | SDO Abort | 정상 처리 계속 |
| 잘못된 SDO 값·길이 | SDO Abort | 기존 OD 유지 |
| 미지원 관리 명령 | 요청 실패 | 기존 상태 유지 |
| 현재 정책의 Halt bit8 | FMU 전달 시 무시 | 모델 실행 계속, 정지 기능 없음 |

정상 계산을 불가능하게 만드는 잘못된 주기 PDO는 SDO 요청 실패와 다르다. 입력 오류의 진단 코드, 검출 임계값, 축 단위 처리 정책을 추가로 결정해야 한다. 임의로 정상 처리하거나 모든 오류를 무시하지 않는다.

## 책임 분리

- 실행 관리부: Diagnostic 발생 건과 수명 주기 통합 관리.
- Slave 실행부: IPC/통신 감시 및 즉시 Fault·출력 무효화. 통합 관리자 응답을 기다리지 않는다.
- 모델 Host: 축별 모델 실행 및 장치 상태 보고.
- 복구 관리부: 복구 수행, 성공/실패 보고.
- CiA402 프로파일: 내부 상태를 Statusword 등 외부 장치 인터페이스로 표현.
- 모델별 어댑터: 모델 고유 Fault/Warning을 공통 의미로 변환.

DiagnosticManager 자체가 Statusword를 직접 수정하지 않는다. 별도 Fault 정책이 영향 범위·모델 실행 허용·피드백 유효성을 결정한다. Python Host가 실패해도 Slave의 장애 검출과 상태 반영은 살아 있어야 한다. 프로세스별 이벤트 전달·순서·중복 억제·보관 방식은 구현 전 확정한다.

## 후속 관리·자동 복구 단계의 결정 사항 — 현재 보류

1. 관리 명령 계약: 진단 조회·Model Recovery·위치 수락을 제공할 인터페이스, 대상 세션과 위치 확인 방식. PP 재개 정책은 합의 및 코드 검토 완료이며 위치 비교 허용오차·정지 판정 수치, 비PP 모드의 재개 계약은 미확정이다.
2. 진단 조회/acknowledge/복구의 사용자 인터페이스와 명령 계약. Fault Reset의 acknowledge 연계, 대상·결과·실패 응답, 어댑터 Fault의 구체적 코드와 Resolve 조건.
3. 검출 기준: 모델 응답 deadline, 유휴 상태 제외, 정상 복귀 판정, 비정상 PDO 정책. 앞서 언급한 32ms는 확정값이 아니다.
4. 실행 관리부/Slave/Host 사이 진단 전달·중복 억제와 단일 소유권. 통신 루프 비차단 보장.
5. 로그·진단 이력의 저장 위치, 보관 기간, 재시작 후 유지 여부와 시험 기준.

이 목록은 논의 순서이며 새로운 인터페이스·수치·자동 복구 정책에 대한 승인이 아니다.


## Motion Server Fault 대응 연동 확인 — 2026-10-28

Motion Server 「프로젝트 설계 및 의사결정」 스레드에서 개별 축 Drive Fault 공통 대응 구현을 확인했다. Fault 최초 검출 시 잔여 위치·속도 지령과 동작 비트를 정리하고 Enable Operation 요청을 제거한다(Controlword 0x0007). Jog/Homing은 진입 전 모드로 RxPDO 복원하고 PP/PV/CSP는 유지한다. 클라이언트 jog_stop 수락 여부와 별도로 수행하며 자동 Reset·Enable·이전 동작 재개는 하지 않는다. 다축 연계 정책은 별도 범위다.

Copley virtual-axis-2의 JOG 미지원 Fault 후 PP 복원 및 Motion Server 축 Fault Reset 정상 복귀를 사용자가 수동 확인했다. 이에 따라 시뮬레이터에서 미지원 JOG 모드를 Reset 시 특별 허용하거나 임의로 PP로 치환하는 변경은 하지 않는다. 지원 모드로 원인을 해소한 뒤 Reset하는 기존 계약을 적용한다. 상세 시험 범위와 미확인 항목은 RF-018의 수동 시험 결과를 따른다.
