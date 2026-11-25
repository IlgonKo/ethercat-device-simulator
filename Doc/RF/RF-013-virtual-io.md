# RF-013 — EtherCAT Modular Device Profile 기반 Remote I/O

- 현재 상태: **진행 중**
- 상태 상세: 2026-11-25 독립 Soft ESC 제품 범위로 확정. CPX-AP-I의 DI/DO/AI/AO 및 모델 어댑터가 1차 구현 대상이며 IO-Link는 제외한다. 복동 실린더 FMI 3.0 동작 모델의 Linux 오프라인 검증은 완료했으며 IO 어댑터·MDP 구현·물리 검증은 미완료.
- 등록일: 2026-09-22
- 설계: [ADR-001](../Design/ADR-001-system-architecture.md), [프로젝트 계획](../project-plan.md), [ADR-005](../Design/ADR-005-device-configuration.md)

## 제품 범위와 이번 구현

EtherCAT Modular Device Profile 기반 Remote I/O를 CiA402 Drive와 함께 독립 제품 범위로 지원한다. 1차 구현 대상은 CPX-AP-I(EtherCAT 연결: CPX-AP-I-EC)이며 모듈 구성과 DI/DO/AI/AO를 제공하고 모델별 어댑터로 동작 모델에 연결한다. Analog IO를 후속으로 미뤘던 이전 범위는 이 결정으로 대체한다. 단순 DI/DO 바이트 교환만으로 Modular Device Profile 지원을 완료했다고 표시하지 않는다.

- 공통 모듈형 프로파일: 장치/모듈 구성·식별·지원 객체·프로세스 데이터 계약.
- 제품별 장치 설명: 실제 Identity·ESI·모듈 정의·제조사 확장·초기화 요구.
- 어댑터: 모듈/채널과 선택한 동작 모델 입출력·단위·실행 의미 연결.
- 동작 모델: 자체 모델/FMU/기타 형식으로 연결 대상 동작 계산. 현재 모든 형식의 범용 로더를 구현했다는 의미는 아님.

DT Demo의 Loader는 밸브/실린더 동작 모델의 검증 사례다. DO → 동작 모델 → DI 경로로 끝단 센서를 생성하며 DO echo로 대체하지 않는다. Loader·Orchestrator·Omniverse를 Remote I/O 프로파일의 실행 의존성으로 넣지 않는다. 연속 Loader 위치용 외부 통신은 이번 범위에서 추가하지 않는다.

## 1차 지원 범위 — 2026-11-25 확정

| 종류 | Master 관점 | 모델 연결 방향 |
| --- | --- | --- |
| DI | 디지털 입력 읽기 | 동작 모델 출력 → 어댑터 → 입력 프로세스 데이터 |
| DO | 디지털 출력 쓰기 | 출력 프로세스 데이터 → 어댑터 → 동작 모델 입력 |
| AI | 아날로그 입력 읽기 | 동작 모델 출력 → 어댑터 변환 → 입력 프로세스 데이터 |
| AO | 아날로그 출력 쓰기 | 출력 프로세스 데이터 → 어댑터 변환 → 동작 모델 입력 |

IO-Link는 1차 구현 범위에서 제외한다. 기본 검증 구성은 슬롯1 DI8(CPX-AP-I-8DI-M8-3P), 슬롯2 DO8(CPX-AP-I-8DO-M8-3P), 슬롯3 AI4/AO4(CPX-AP-I-4AI4AO-U-I-M12)로 확정했다. 모든 CPX 모듈 지원을 의미하지 않는다.

선정 AI/AO의 PDO는 ESI 기준 signed 16-bit little-endian raw 정수로 표현한다. 표현 범위 -32768..32767과 정상 신호 범위를 구분한다. 물리량 단위·변환·정상 신호 범위는 모델/채널 계약에서 정하며 32767=10V 같은 공통 가정은 두지 않는다. 범위 초과 설정·모델 변환값은 오류로 처리하고 자동 clamp하지 않는다. Loader의 디지털 사용 사례만으로 AI/AO 검증을 대신하지 않는다.

## 확정한 구성·모델 연결

모듈은 [ADR-005](../Design/ADR-005-device-configuration.md)의 `DEVICE_SIMULATOR_IO_io0_MODULES=1:DI:8,2:DO:8,3:AIO:4:4` 문법을 사용한다. Motion Server parser/ESI 검증은 통과했으나 Soft ESC parser는 아직 미구현이다.

모델 인스턴스별 생성·채널별 명시적 연결·미연결 처리·오류 구분은 [ADR-007](../Design/ADR-007-cia402-profile-adapters.md)의 합의 원칙을 따른다. IO 하나에 여러 모델을 연결할 수 있다. 설정 키는 `DEVICE_SIMULATOR_BEHAVIOUR_MODELS`와 `DEVICE_SIMULATOR_IO_<io_id>_BINDINGS`로 확정했다. 모델 선언은 `ID:종류`, 연결은 `슬롯:종류:채널=ID.입출력명`이다. 실린더 동작은 아래의 검증된 공압 FMU 재사용 결정을 따른다. 이전 virtual_cylinder 예시가 실제 구현 모델 등록을 뜻하지 않는다. 아날로그 시험 모델 계약은 미확정이며 예시 loader0 등의 인스턴스 이름을 제품에 하드코딩하지 않는다. 기존 축의 AXIS_MODELS는 유지한다.

## 기존 기반과 변경 지점

현재 설정/Host는 축 전용이다. CiA402 필수 Controlword/Statusword, AxisFault 투영과 공통 전송·검증을 분리한다. Remote I/O를 CiA402 하위 축으로 취급하지 않는다.

장치당 논리 OD 하나를 유지한다. PDO mapping/assignment·저장은 Slave, 동작 파라미터는 기능 모델 소유다. 모델 IPC에 매핑 절차를 추가하지 않는다. 기존 RF-014 축 계약은 유지하고 선정 IO의 매핑/모듈 요구와 충돌하는 규칙은 명시적으로 설계한다.

자체 .env에 모듈/슬롯/채널 및 모델 연결 구성을 추가한다. 환경 변수 문법은 ADR-005의 채택 내용을 따르며, 실제 동작 모델의 입출력명·파라미터 저장 스키마는 별도 확정한다. Motion Server .env를 읽거나 Demo 전용 구성을 코드에 고정하지 않는다.

## 복동 실린더 FMU 재사용 — 2026-11-25 채택

직접 작성할 일정 속도 모델 대신 공개 PneumaticCircuits 부품을 조합한
`SoftESCDoubleActingCylinder` FMU를 IO 연결용 동작 모델로 사용한다. `loader0`는
인스턴스 예시이며 프로파일이나 동작 모델에 고정하지 않는다.

- 선택 산출물: Playground Export, FMI 3.0 Co-Simulation, solver `auto`, Linux x86-64.
- 보관: `model_artifacts/SoftESCDoubleActingCylinder-fmi3-web.fmu`. 파일 해시·환경·결과는
  [Linux 검증 보고서](../Validation/Pneumatic-Cylinder-Web-FMU-20261125.md)에 기록했다.
- 출처·고정 커밋·Modelica 소스·Export 방법: [모델 README](../../model_sources/pneumatic_cylinder/README.md).
- Linux에서 100mm 왕복(8ms/1ms), 50mm 변경, 무공압, 명시적 이벤트 처리의 5개 시험을 통과했다.
  현재 사용 가능한 것은 동작 모델의 오프라인 실행이며 Soft ESC에 IO 모델로 등록된 상태는 아니다.

| 기존 binding 논리 신호 | FMU 변수 | 의미 |
| --- | --- | --- |
| extend | extend_command | 전진 파일럿 Boolean 입력 |
| retract | retract_command | 후진 파일럿 Boolean 입력 |
| extended | extended_sensor | 전진 끝단 Boolean 출력 |
| retracted | retracted_sensor | 후진 끝단 Boolean 출력 |

이 대응은 어댑터 구현에 적용할 연결 계약이며 binding 파서가 현재 지원한다는 뜻은 아니다.
FMU는 위치(m), 속도(m/s), 절대압(Pa), 공압력(N)도 제공한다. 이 값을 AI로 연결할지와
raw 변환은 별도 채널 계약으로 정하며, 이를 자동으로 EtherCAT 채널에 추가하지 않는다.

동작 모델은 3/2 파일럿 밸브·5/2 메모리 밸브·복동 실린더를 포함한다. **두 입력 OFF는
정지가 아니라 밸브 방향 유지**다. 움직임은 공압·부하·기구 파라미터에 따라 계산한다.
초기 위치는 기본 0m, 스트로크 100mm, 공급압 6bar(gauge), 센서 폭 1mm다. 끝단은
탄성 접촉이어서 작은 위치 초과가 가능하다. `opposing_force`는 고정 파라미터이며
동적으로 변화하는 외력 입력은 아니다. 제조사 정밀 모델이나 실제 장비 정확도 보증은 아니다.

이 결정은 앞서 논의한 `virtual_cylinder`의 OFF/OFF 정지·전진/후진 각 1초·일정 속도
구현 계획을 대체한다. 그 이전 계약은 작업 일지에 이력으로 보존한다. 두 입력 ON은
원본 밸브의 압력/이력에 따르며 정상 시험 명령으로 사용하지 않았다. 어댑터의 상충
명령 진단·재개 조건은 IO 장애 정책과 함께 확정한다. FMU에 없는 정지/Reset 기능을
구현된 것으로 간주하지 않는다.

일반 Co-Simulation(eventModeUsed=false, earlyReturnAllowed=false)을 사용한 8ms
직접 호출이 통과했다. 명시적 Event Mode를 쓰려면 Boolean 입력 갱신 시 Event Mode
전환과 Early Return을 처리해야 한다. Windows에서 따로 만든 FMI 2.0 FMU의
0.1ms 세분화 조건을 이 FMI 3.0 산출물에 그대로 적용하지 않는다.

## 구현 전 확정 사항

1. 확정한 기본 모듈 구성의 Identity·ESI revision·초기화 OD/SDO·PDO 및 오류 응답 계약 대조. raw 표현은 확정했으며 물리량 변환·정상 신호 범위를 명세한다.
2. 아날로그 시험 모델의 입출력·단위·동작 계약. 실린더 FMU의 등록 식별자·artifact 지정·초기 파라미터 설정/저장, 두 입력 ON 및 재개 정책을 확정한다. 공압 FMU에 고정 전진/후진 시간을 요구하지 않는다.
3. PRE-OP/버스 단절/모델 장애의 출력·입력 유효성·진단·복구. 버스 단절이 자동 DO 해제를 보장한다고 가정하지 않는다.
4. IO 파라미터 저장 대상·재시작 상태와 기존 저장 기반의 재사용 범위. 운전 상태의 자동 복원을 가정하지 않는다.

## 완료 기준

- [ ] 선정 장치의 MDP·모듈 식별/구성·초기화 OD·PDO 요구와 지원 범위 표.
- [ ] 자체 .env 장치/모듈/채널/모델 구성 및 오류 검증. 미지원 모듈·잘못된 순서/채널 거부.
- [ ] 프로파일/제품 설명과 어댑터/동작 모델 분리, 모듈·채널·동일 종류의 여러 모델 인스턴스 상태 독립성 검증.
- [ ] BEHAVIOUR_MODELS/BINDINGS 문법·모델 인스턴스 생성·채널 연결 구현, 기존 AXIS_MODELS 유지 회귀.
- [ ] 채널별 binding과 존재/방향/자료형 검사, 복수 모델의 단일 DI/AI 쓰기 거부 검증.
- [ ] 미연결 DI=False/AI=raw 0 및 DO/AO 수신값 보관, 자동 loopback 없음, 연결된 모델 오류를 미연결 기본값으로 숨기지 않음 확인.
- [x] 선택한 실린더 FMU의 Linux 구조·입출력·왕복·파라미터·무공압·라이프사이클 오프라인 검증.
- [ ] 실린더 FMU 어댑터·두 DO 입력/두 끝단 DI 출력 연결, 밸브 방향 유지 및 다중 인스턴스 독립성 검증.
- [ ] 상충 입력과 PRE-OP/버스 단절/모델 장애의 진단·복구 정책 확정 및 시험.
- [ ] FMU 초기 위치·스트로크·공급압 등 파라미터의 설정/저장과 재시작 초기화 검증. 이전 운전 상태의 자동 복원을 가정하지 않음.
- [ ] AI/AO 양방향 모델 연결·자료형/단위 변환·합의한 범위 경계/잘못된 값 처리·채널 독립성 검증.
- [ ] DI/DO/AI/AO 혼합 모듈 구성의 프로세스 데이터 배치 및 모델 입출력 대응 검증.
- [ ] EtherCAT 검색·SDO·OP·PDO 및 모듈별 데이터 배치 검증. 명시한 MDP 범위에 대해 근거 기록.
- [ ] Host 장애 시 Slave 유지 기반과 IO 진단/입력 유효성/복구 정책 검증. 기존 축 Fault 투영을 대신 적용하지 않음.
- [ ] Drive+IO 혼합 구성·저장/재시작·기존 F-KR/Copley/동적 매핑 회귀. 3축+IO는 Demo에서 가져온 시험 사례.
- [ ] 외부 Master의 일반 IO 명령으로 모델 동작·DI 리드백 확인. 외부 Alignment/Sequence 자체는 제외.

## 제외·후속 및 근거

IO-Link, IODD/ISDU, 범용 센서 라이브러리, 제조사 실측 기반의 정밀 공압 모델 개발·정량 검증은 이번 구현에 포함하지 않는다. 선택한 공개 FMU가 제공하는 압력·부하 계산은 재사용한다. DI/DO/AI/AO는 모두 1차 구현 범위다. Modular Device Profile 전체 및 모든 CPX 모듈의 적합성을 선언하지 않고 구현한 범위를 명시한다.

RF-005의 실제 CPX 통신 및 RF-011/014/018의 축 검증은 기반 근거이며 가상 Remote I/O 구현 완료를 대신하지 않는다. 해당 RF 완료 상태는 유지한다. 외부 DT/Sync·Pairing·ROS2·Omniverse 구현은 이 RF의 범위가 아니다.
