# RF-018 — 공통 Diagnostic 및 모델 장애 격리

- 상태: 축 Fault/Reset 및 비차단 IPC 구현·격리 네트워크 검증 완료 / JOG Fault/PP 복원/축 Reset 수동 검증 완료 · Host 장애 물리 검증 잔여
- 등록일: 2026-10-28
- 설계 기준: [DT-008](../Design/DT-008-diagnostic-fault.md)

## 목적

Motion Server와 동일한 Diagnostic 데이터 구조·수명 주기를 사용한다. 시뮬레이터별 검출 책임, 영향 범위, 상태 반영과 복구를 정의한 뒤 FMU 오류·지연에도 EtherCAT Slave가 유지되는 구조를 구현한다. Motion Server 패키지를 수정하거나 런타임 의존성을 추가하지 않는다.

## 현재 구현 및 검증 — 2026-10-28

- `AxisFault`: 축별 Fault/Warning 발생 건, acknowledge/resolve JSON 로그, 마지막 정상 PDO 보관, Statusword Fault 투영. 잘못된 주기 입력은 AXIS_ADAPTER_FAULT이며 원인 수정 후 Reset 가능하다. 계산 예외·출력 길이 이상은 실행/출력 Fault로 latch하고 Docker 재시작을 요구한다.
- 모델 드라이브 Fault는 계산 가능한 동안 비운동 Controlword로 모델 계산을 유지한다. Reset에는 기존 Enable·이동 비트를 전달하지 않고, Reset-low에서도 Fault가 해제됐는지 확인한다. Copley FaultInject가 계속 활성화된 경우 어댑터가 Reset을 거부한다.
- 어댑터 Fault Reset은 내부 모델을 먼저 Disable한 뒤 수행한다. 성공 후 Shutdown→Switch On→새 Enable을 요구한다. 현재 재Enable 경로는 PP 모드만 지원하며, 비PP 모드의 장애 후 재개는 후속이다. 기존 정상 운전의 비PP 기능은 변경하지 않는다.
- IPC는 단일 전용 worker가 직렬 처리하고 EtherCAT 스레드는 future를 비차단 조회한다. 축별 동시 대기 요청은 하나이며 전체 queue는 64개로 제한한다. SDO도 비동기 mailbox 처리로 전환했다. 느린 모델 때문에 출력 갱신 간격이 늘어날 수 있으며 하드 실시간 보장은 아니다.
- `DEVICE_SIMULATOR_MODEL_TIMEOUT_MS` 기본 100ms, 허용 10..5000ms. worker의 개별 RPC 전송·수신 deadline이며 queue 대기 시간은 포함하지 않는다. 기존 100ms PDO gap 제한과 별개다. deadline 초과·연결 단절 시 세션을 폐기하고 전체 Host 축에 Fault를 유지한다. 자동 재연결 및 늦은 응답 재사용은 없다.
- Host 장애 후 0x6041 조회는 Slave 보관값으로 응답하고 모델이 필요한 SDO는 Abort로 응답한다. 마지막 위치·속도·토크를 정상 새 피드백처럼 생성하지 않는다. Fault 및 유효성/재시작 필요 여부를 로그·내부 IPC에 표시한다.
- 파라미터 저장 실패는 Alarm 및 SDO Abort이며 기존 파일을 보존한다. 일반 SDO 거부는 축 Fault로 승격하지 않는다.
- 통합 관리 API·영구 진단 이력·모델 자동 복구는 미구현이다. Docker health는 프로세스 생존 중심이며 살아 있는 모델의 내부 Fault 전체를 나타내지 않는다. NIC 자체 장애 시 프레임 응답 보장은 불가하다.

검증:

- 기존 정상 모델 800-cycle baseline을 포함한 Python 회귀 및 실제 Linux Copley FMU 시험.
- CTest: 고정 PDO 매핑, 4 ESC routing, 응답 지연/단절 중 비차단 routing·늦은 응답 거부.
- 실제 모델 서비스 + 비동기 C++ mailbox에서 정상 SDO, Abort, 이후 PDO 연속 처리 검증.
- `tests/integration/validate_fault_bus.py`: 별도 Docker `--network none` 안에 veth 쌍을 생성하고 PySOEM + 운영 바이너리 + F-KR 2축/Copley 2축으로 OP 통신. 축별 입력 Fault, Motion Server와 같은 Reset·Enable 순서, PP ACK 0→1→0 통과. Host SIGSTOP(timeout)·SIGKILL(disconnect) 각각 80주기 WKC=12/12 유지, 전체 축 Fault·Statusword SDO·모델 SDO Abort·Reset 불가 검증. 실제 하드웨어 NIC와 사용자 state는 사용하지 않는다.
- 이 검증은 Motion Server 실행 프로세스/Axis Panel을 통한 물리 라인 검증을 대체하지 않는다. 운영 컨테이너는 자동 재시작하지 않는다.

수동 적용/복구:

1. 새 이미지 적용은 Motion Server 운전을 정지한 뒤 기존 Docker start 스크립트로 컨테이너를 재생성한다. 단순 `docker restart`는 이미 생성된 컨테이너의 구 이미지를 교체하지 않는다.
2. PP 축의 복구 가능한 Fault: 원인 입력/파라미터 수정 → Motion Server 축 Fault Reset → Fault 해제·Switched On 확인 → Enable → 새 PP 명령.
3. 모델 실행 실패·Host 단절/timeout: Docker 수동 재시작 → Motion Server 버스 재연결/초기화 → 새 위치 확인 → 명시적 Enable·새 명령. 축 Reset으로 Host 장애를 해제하지 않는다.

## 합의 내용

### 현재 범위 우선 적용 — 2026-10-28

- 사용자 복구는 Motion Server의 축 Fault Reset과 수동 Docker 재시작으로 한정한다. 실행 가능한 어댑터/모델의 원인이 해소된 Fault는 축 Reset으로 처리하고, 모델 실행/IPC 장애 등은 수동 재시작한다.
- 관리 API/CLI, 별도 Model/Slave Recovery, 위치 수락·재동기화 기능은 후속으로 보류한다. 아래 관련 합의는 장기 설계이며 현재 구현·완료 조건에 포함하지 않는다.
- 일반 축 Reset에 위치 수락을 요구하지 않는다. Reset은 모델 재생성이나 공유 Slave 재시작을 수행하지 않는다. 원인 미해소/모델 응답 불가 시 해제 성공을 보고하지 않는다.
- Docker 재시작 후 새 세션의 버스 재연결/초기화·위치 확인·명시적 Enable·새 이동 명령은 수동으로 수행한다. 통신 연속성·이전 위치 복원·자동 운전 재개를 가정하지 않는다.
- FMU 장애 시 EtherCAT Slave 유지 목표와 내부 진단·명령 차단은 유지한다. 관리 조회 대신 우선 로그로 원인을 확인한다.

### 공통 원칙 및 후속 복구 설계

- Definition/Source/History/Status, normal/alarm/fault, acknowledge/resolve/clear 규칙.
- 오류별 검출 책임·영향 범위·상태 반영·Resolve 조건은 DT-008 표를 따른다.
- SDO 요청 거부와 장치/모델 Fault 분리. 모델 자체 Fault와 실행 장애의 합성 Fault 중복 금지.
- 공유 Host 장애와 개별 축 실행 오류의 영향 범위를 구분한다.
- Diagnostic 통합 관리와 Slave의 즉시 보호 조치는 분리한다.
- 축 Fault Reset은 어댑터 Fault와 모델 드라이브 Fault를 원인별로 처리한다. 실행 기반 복구는 Model Recovery, NIC·소켓 등 공유 통신부 복구는 Slave Recovery로 분리한다.
- Master의 EtherCAT AL 오류 확인·상태 복구는 CiA402 축 Fault Reset과 별개다. 축 Reset으로 공유 Slave를 재시작하지 않는다.
- Reset/Recovery/Restart 후 자동 Enable 및 이전 이동 명령 재실행을 금지한다. 사용자 동작별 역할은 DT-008의 합의 표를 따른다.

- 피드백 정책 합의: 모델 출력 무효 시 마지막 정상값과 시각을 보관하고 유효성을 별도 표시한다. Master에는 CiA402 Fault, 상세 정보는 시뮬레이터 진단 조회로 제공한다.
- 모델 준비와 운전 가능 상태를 구분하며, 위치 불일치 시 재동기화 전 Enable을 차단한다. 필요한 Reset·위치 확인 후 명시적 Enable 및 새 명령으로 재개한다.
- 위치 재동기화는 사용자가 복구된 모델 위치를 새 기준으로 수락하는 방식으로 확정한다. Copley 재생성 시 0을 수락하며, 이전 위치로 자동 이동·좌표 offset·이전 모델 상태 주입은 1차 범위에서 제외한다.

위치 수락 거부·보류 시 해당 축의 재동기화 대기 및 Enable·이동 차단을 유지하고 EtherCAT 통신·진단 조회를 제공한다. 사용자는 나중에 수락, 복구 재시도 또는 시험 종료를 선택한다. 수락 대기는 새로운 모델 Fault가 아니며 Model Recovery 성공과 별도 상태로 표시한다. 자동 수락·이전 위치 자동 이동은 하지 않는다.

## 구현 전 결정

현재 우선 검토·구현 대상은 축 Reset 가능한 Fault/재시작 필요한 Fault의 분류, 원인 해소 판정, Motion Server Reset·Enable·PP 순서의 실제 검증 및 장애 격리 조건이다. 아래 관리 인터페이스·위치 수락 관련 상세 결정은 보류한다.

운전 재개 정책 합의 및 Motion Server 코드 검토를 DT-008에 반영했다. 위치 수락의 세션 제한, Reset 후 새 Enable, PP bit4 새 edge, 관련 진단만 acknowledge하는 정책을 따른다. 기존 서버의 Reset(펄스 후 0x0006→0x0007), Enable(0x000F), PP(0x000F→0x003F→0x000F) 순서를 시뮬레이터에서 검증한다. 구현·물리 검증 완료를 의미하지 않는다.

다음은 관리 명령 인터페이스와 세션·위치 확인 계약이다. 이어 비PP 모드 재개 조건, 어댑터 Fault 코드·Resolve 조건, 응답 기한, 잘못된 PDO 처리, 프로세스 간 이벤트 전달, 이력 보관 정책을 확정한다. Motion Server의 전체 축 Fault 검사와 외부 클라이언트 대기 요청 식별 불가 제약은 DT-008을 따른다.

## 예정 검증

현재 단계에서는 정상 축 Reset, 원인 미해소/모델 응답 불가 시 Fault 유지, Reset으로 모델·Slave가 재시작되지 않음, 명시적 Enable·새 PP 요청 및 수동 Docker 재시작 후 새 세션 초기화를 검증한다. 아래 위치 수락/Model Recovery API에 의존하는 항목은 후속 단계로 보류한다.

진단 수명 주기·중복 억제, 축/Host 영향 범위, FMU 오류·hang·IPC 단절·지연 주입, 늦은 결과 폐기, 메일박스/PDO 응답 유지, 정상 복구와 재Enable 조건. 구체적 합격 수치는 상세 정책 확정 후 정한다.

위치 수락 거부·보류 중 통신/조회 유지, 해당 축 운전 차단, 불필요한 모델 오류 미생성, 복구 재시도 후 위치 재확인 및 명시적 수락 후 재개 절차도 검증한다.

이전 Enable/PP bit가 남은 Reset 펄스, 수락 전 Reset 폐기, 0x0006→0x0007 이후 Enable, PP ACK 0→1→0, 동일 목표 새 요청, 반복 high 차단, 재장애 시 세션 무효화 및 다른 축/공통 진단 미확인을 검증한다.

기존 SDO Abort 및 Halt 무시 처리는 RF-017/TD-001에 기록되어 있다. 이번 장애 격리/Reset 추가 구현은 위 현재 구현 절을 따르며, 운영 물리 라인 시험과 보류된 관리 기능까지 완료됐다는 의미는 아니다.


## 사용자 수동 시험 결과 — 2026-10-28

- 대상: Copley 모델의 `virtual-axis-2`. Motion Server 로그의 axis=3은 Master 버스 번호이며 시뮬레이터 내부 축 번호 2와 구분한다.
- Motion Server와 Axis Panel에서 JOG 요청으로 미지원 모드 Fault를 발생시킨 뒤, 수정된 Motion Server의 PP 복원 및 축 Fault Reset으로 정상 복귀함을 사용자가 확인했다.
- 수정 전에는 JOG 모드가 RxPDO에 남고 Fault 상태에서 jog_stop이 거부되어 Reset에서도 미지원 모드 검증에 걸렸다. 반복 SDO 요청 문제가 아니라 주기 PDO의 모드 값이 남는 문제였다.
- Motion Server의 「프로젝트 설계 및 의사결정」 스레드(01a021b7-133b-7801-a2a2-1986dbed08f9)의 개별 축 Drive Fault 대응을 기준으로 한다. Fault 최초 검출 시 해당 축의 위치 목표를 현재 위치로, 속도 지령을 0으로 정리하고 Controlword 0x0007로 운전 허가를 해제한다. Jog/Homing은 진입 전 모드로 PDO 복원하며 PP/PV/CSP는 유지한다. 자동 Reset·Enable·이전 동작 재개와 다축 연계 처리는 포함하지 않는다.
- 이번 PP → JOG → Fault → PP 복원 → 사용자 축 Fault Reset 경로에는 시뮬레이터의 미지원 JOG Reset 예외를 추가하지 않는다. 원인 해소 후 Reset이라는 기존 정책을 유지한다.
- 증거 수준: 사용자 수동 성공 보고. 시험 시간·주기·WKC 수치, 재Enable 후 새 이동, Host timeout/단절 및 Docker 복구의 물리 시험 결과까지 확인한 것으로 확대하지 않는다. Host 장애 격리의 자동 veth 검증과 이번 수동 축 복구 시험을 구분한다.
