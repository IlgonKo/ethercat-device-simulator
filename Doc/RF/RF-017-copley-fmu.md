# RF-017 — Copley FMU 초기 연동

상태: **기본 물리 PP·Fault/Reset 및 RF-018 장애 격리 검증 반영 / 세부 이동·혼합 성능 검증 잔여** (2026-10-28)

## 현재 상태 요약 (2026-10-27)

- 구조: KickCAT EtherCAT Slave 프로세스 + Functional Model 프로세스. 후자에서 FMI3 Co-Simulation FMU를 라이브러리로 실행한다.
- BUS는 `cia402-drive`, 동작 모델은 `f_kr_cmmt` / `copley_drive_sim`으로 선택한다. 외부 EtherCAT identity/PDO는 CMMT-AS 호환을 유지한다.
- Copley 어댑터의 PP 절대·상대 이동, Enable/Disable, Fault/Reset, 파라미터 저장·복원 및 혼합 구성의 비물리 검증 완료.
- referenced bit15는 항상 설정. 실제 Homing은 제공하지 않는다. Halt bit8은 FMU 전달 시 무시하며 정지 기능은 없다.
- 초기화용 restart-clear OD 처리, 미지원 SDO의 정상 Abort 및 후속 SDO/PDO 처리 구현. mailbox buffer 전체 길이 보존으로 ESC 응답 준비 문제 수정.
- Linux 운영 소스·Docker `ethercat-device-simulator:dev`까지 반영했다. 아래 초기 단계의 ‘검증 폴더에만 반영’ 기록은 당시 이력이다.
- 모델 crash/hang/IPC 지연 격리, 물리 PySOEM 최종 재시험, Copley 혼합 4축 장시간 성능 검증은 미완료다. 사용자로부터 최종 물리 동작 성공 확인을 아직 받지 않았다.

## 확정 범위

- KickCAT Slave와 별도인 Functional Model 프로세스 안에서 FMI 라이브러리를 호출한다.
- 초기 어댑터는 PP만 지원한다. FMU의 PV/PT는 이번 검증 범위가 아니다.
- Stop/Halt 지원은 제외한다. Halt bit8은 FMU 전달 시 무시하며 정지 동작을 구현하지 않는다. 원본 Controlword는 OD에 보관한다.
- 가상축은 초기 위치 0을 기준으로 항상 referenced 상태다. 어댑터가 Statusword bit15만 OR한다. FMU의 bit12(set-point acknowledge), bit13 및 Fault/Enable 비트는 변경하지 않는다. 실제 Homing 동작 및 mode6은 제공하지 않는다.
- PP 절대·상대 이동, Enable/Disable, 피드백, 파라미터 적용, Fault/Reset을 검증한다.
- Motion Server 및 운영 `.env`, 영구 저장 파라미터, 실행 중 Docker는 변경하지 않는다.

## 구현

| 위치 | 역할 |
| --- | --- |
| `src/functional_model/runtime/fmi/runner.py` | FMPy 0.3.26 기반 FMI3 CS 로드, 변수 계약 검사, 입출력, 시간 진행, 종료 |
| `src/functional_model/cia402_drive/model_definitions/copley_drive_sim/` | Copley 변수 이름·자료형·방향 및 2ms 주기 |
| `src/functional_model/cia402_drive/adapter/copley.py` | CiA402 OD/PDO ↔ Copley 변환, PP 지원 범위 검사, referenced 처리 |
| `src/functional_model/cia402_drive/profile/configured_od.py` | F-KR 모델에서 분리한 프로파일 기반 OD 구성. F-KR/Copley 공용, 상태 머신 없음 |
| `scripts/linux/build-copley-fmu.py` | 고정 upstream 소스 FMU 해시 확인 후 Linux x86_64 공유 라이브러리 빌드·FMU 패키징 |
| `tests/integration/test_copley_fmu.py` | 실제 FMU를 사용하는 오프라인 기능 시험 |

현재 runner는 FMI3 CS 스칼라 인터페이스의 최초 지원이다. FMI2, Model Exchange, 이벤트 모드, early return, FMU 상태 저장/복원은 지원하지 않는다. 미래 FMU의 입력·동작 계약은 별도로 검증한다.

### 단위·시간·파라미터

- 위치는 현재 OD의 raw position count와 FMU count를 동일하게 사용한다.
- 기존 `0x2194` 단위 지수에서 position/velocity/acceleration 단위 비율을 구한다. 추가 counts-per-unit 설정은 없다.
- ProfileVelocity는 counts/s로 변환하고 ActualVelocity는 FMU의 0.1 counts/s에서 OD 속도로 변환한다.
- Copley의 단일 ProfileAcceleration을 사용하므로 `0x6083`과 `0x6084`가 같아야 실행한다. 순차 SDO 쓰기는 허용하지만 불일치 상태의 step은 진행하지 않는다. 운영 중 변경 트랜잭션 정책은 물리 연동 전에 보완한다.
- 8ms 입력 주기에서 FMU는 2ms씩 4회 실행한다. 나머지 시간은 누적하며 다음 2ms가 모일 때 진행한다. 2ms 미만으로 바뀌는 입력 에지의 보존은 보장하지 않는다.
- profile velocity/acceleration의 양수 값만 허용한다. 미지원 SDO 쓰기, 비영 입력 offset 및 미지원 mode는 OD 변경 전에 거부한다.
- 프로파일 OD의 조회 가능한 한계·제조사 정보가 FMU의 기능 구현을 의미하지 않는다. 소프트웨어 위치 제한은 Copley에서 구현하지 않는다. 파라미터 저장/복원은 아래 후속 구현 범위만 제공한다.
- FaultInject는 오프라인 시험 API이며 임의의 제조사 OD 주소를 만들지 않는다.

### 장애 처리 경계

FMI 호출 예외 또는 지원하지 않는 doStep 반환은 해당 runner를 실패 상태로 고정한다. 실패 step의 시간을 완료 처리하지 않고 자동 재개하지 않는다. 재사용하려면 새 인스턴스가 필요하다.

이는 **EtherCAT Slave 장애 격리 완료가 아니다**. native crash/hang을 runner가 차단하지 못하며, 기존 IPC 오류로 Slave가 종료될 수 있다. 물리 연동 전에 IPC 지연/단절 시 Slave 유지, 오래된 피드백 표시, 복구 정책 및 TD-001 SDO Abort 처리를 구현·검증해야 한다.

## 오프라인 재현

Linux x86_64, C 컴파일러 및 Python venv가 필요하다. 프로젝트 루트에서:

```bash
python3 -m venv build/fmi-venv
build/fmi-venv/bin/pip install -e '.[fmi]'
build/fmi-venv/bin/python scripts/linux/build-copley-fmu.py
PYTHONPATH=src:. COPLEY_TEST_FMU=build/fmu/CopleyDriveSim-linux.fmu \
  build/fmi-venv/bin/python -m unittest \
  tests.unit.test_fmi_runner tests.unit.test_copley_adapter \
  tests.integration.test_copley_fmu -v
```

인터넷 없는 Linux는 소스 FMU를 복사한 뒤 `--source /path/to/CopleyDriveSim.fmu`로 빌드한다. FMPy 및 의존 wheel도 별도로 제공해야 한다. 소스 해시 불일치 시 빌드하지 않는다. 산출 FMU 옆 provenance JSON에 원본 URL/revision/해시·산출 해시·플랫폼을 기록한다.

`DEVICE_SIMULATOR_AXIS_MODELS`에서 `copley_drive_sim`을 선택할 수 있다. registry·Docker artifact 마운트·지원 파라미터 저장 연결을 구현했다. 물리 EtherCAT 운전 검증 및 IPC 장애 격리는 아직 완료하지 않았다.

## 시험 결과

- 실제 upstream Copley FMU를 Linux x86_64에서 빌드하여 FMPy로 실행했다.
- 선형/회전 설정 각각 PP 절대 이동 2000 count, 상대 이동 -750 count 후 1250 count 도달 및 속도 0 확인.
- Enable 상태 전이, Disable, Fault 주입·유지·Reset 및 두 FMU 인스턴스 상태 독립성 확인.
- profile velocity 변경에 따른 실제 도달 주기 수 차이 확인.
- referenced bit15만 추가, 단위 변환, 2ms 분할, 미지원 요청 거부, 가감속 일치 검사 및 실패 후 runner 재사용 거부 검증.
- Linux: 실제 FMU·어댑터·runner 오류 처리 및 F-KR 800-cycle baseline 동등성 포함 13개 테스트 통과.
- Windows: 전체 67개 중 57개 통과, Linux shell/실제 Linux FMU 10개 건너뜀.
- Python wheel 빌드 및 git diff --check 통과.
- 실제 EtherCAT 통신, WKC, 4축 성능 및 장시간 운전 시험은 수행하지 않았다.

검증 원본: [CopleyDriveSim 소스 FMU](https://github.com/Beckhoff-USA-Community/AAG_TwinCAT_CiA402_CANopen_CPP_FMU_MATLAB/blob/68978af04ea475cf89e39ae872cdccb5ddc95e4c/MATLAB_and_Simulink/FMU_DriveSim/CopleyDriveSim.fmu).
소스 SHA256: `e6456f4787b61b209f0e718c62ee3d570560ce975b7aacf733da6d4f21994b4d`.

검증 실행 위치는 Linux `build/copley-offline`이다. 실행 중인 시뮬레이터와 분리하기 위해 이 폴더에 소스 스냅샷을 복사했으며 Linux 운영 소스와 컨테이너 이미지는 갱신하지 않았다.

## 다음 단계

1. IPC 오류/지연 격리 및 TD-001 Abort 호환성 처리.
2. 완료: Copley registry·`.env` FMU 경로·Docker 읽기 전용 artifact 마운트·지원 파라미터 영구 저장 연결. 아래 통합 시험 참조.
3. Motion Server 초기화에 필요한 OD 쓰기 정책 확정. CSP interpolation 설정은 기존 옵션 0으로 비활성화하고 Halt는 미지원으로 유지.
4. 1축 물리 PP 절대·상대 이동 및 Fault/Reset.
5. F-KR CMMT 혼합 구성과 4축 성능 검증.


## 설정·Docker·저장소 연결 (2026-10-26 후속)

다음은 Copley 1축 + F-KR CMMT 1축 구성 예다. 실제 운영 `.env`는 자동 변경하지 않았다.

```ini
DEVICE_SIMULATOR_FMU_DIR=./model_artifacts
DEVICE_SIMULATOR_BUS=0:axis:cia402-drive,1:axis:cia402-drive
DEVICE_SIMULATOR_AXIS_IDS=0:virtual-axis-0,1:virtual-axis-1
DEVICE_SIMULATOR_AXIS_MODELS=0:copley_drive_sim,1:f_kr_cmmt
DEVICE_SIMULATOR_AXIS_MODES=0:linear,1:linear
DEVICE_SIMULATOR_AXIS_PARAMETER_SETS=0:copley-axis-0,1:axis-1
```

- `DEVICE_SIMULATOR_FMU_DIR`는 호스트 폴더이며 기본값은 `./model_artifacts`다. 이 폴더의 `CopleyDriveSim-linux.fmu`를 읽는다. Docker 내부 경로는 `/model_artifacts`로 고정되고 읽기 전용 마운트한다.
- 같은 FMU 파일을 사용해도 축마다 별도 FMI 인스턴스를 생성한다. FMU 파일 경로는 저장 파라미터의 모델 identity에 포함하지 않는다.
- 기존 `axis-0` F-KR 저장값을 Copley에 자동 변환하지 않는다. `copley-axis-0` 등 별도 parameter set을 지정한다. 같은 저장소 이름에 다른 모델을 지정하면 오류로 중단하며 원본 파일을 보존한다.
- 저장 대상은 단위 메타데이터 5개 + `0x6081/0x6083/0x6084` 총 8개다. 위치·속도·Controlword·Fault는 복원하지 않는다.
- 기존 CMMT 저장 명령 `0x2005:3=1`, `0x2005:1=1`을 통해 지원 파라미터만 저장한다. 가감속 불일치 또는 0 이하면 저장·복원을 거부한다.
- 종료/초기화 실패 시 열린 FMU 인스턴스를 해제한다. fixture-only 실행에서도 종료 처리를 수행한다.
- Docker에 FMPy 의존성을 추가했다. 기본 `/tmp`는 실행 금지를 유지하고 FMU 전용 `/run/fmu` tmpfs만 `exec,mode=0700`으로 두며 `TMPDIR`를 지정한다. 읽기 전용 루트·FMU 마운트, cap 제한을 유지한다.

### 준비와 비물리 검증

```bash
# 먼저 위 가상환경 준비 절차를 수행한다.
build/fmi-venv/bin/python scripts/linux/build-copley-fmu.py \
  --output model_artifacts/CopleyDriveSim-linux.fmu
# Copley 모델을 선택한 .env를 사용한다. 영구 저장소 대신 임시 저장소로 검증한다.
build/fmi-venv/bin/python scripts/linux/validate-fleet.py \
  --binary build/timing/cmmt_simulator
# 운영 컨테이너를 정지한 계획된 전환 시점에만 같은 image/store를 갱신한다.
bash scripts/docker/build.sh
bash scripts/docker/validate.sh
```

Edge PC의 DNS 접근이 불가능하여 시험에서는 wheel을 별도로 전달했다. `docker/wheels`에 Linux x86_64 / CPython 3.12용 전체 의존 wheel을 넣으면 Dockerfile은 인터넷 없이 설치한다. 폴더가 비어 있으면 PyPI에서 설치한다. Windows에서 wheel을 준비하는 예:

```powershell
python -m pip download --dest docker/wheels --platform manylinux2014_x86_64 --python-version 312 --implementation cp --abi cp312 --only-binary=:all: -r docker/requirements-fmi.txt
python -m pip download --dest docker/wheels --only-binary=:all: typing-extensions
```

후속 시험 결과:

- Windows 전체 69개: 58개 통과, Linux 전용/FMU 실행 11개 건너뜀.
- Linux 전체 67개: 66개 통과, PySOEM 의존 검사 1개 건너뜀.
- 실제 Copley + F-KR 2축 C++ ESI/OD ↔ Python IPC 계약 검증 통과. 물리 NIC 미사용.
- 읽기 전용 Docker에서 supervisor `--validate-only` 통과.
- 동일 Docker 안 실제 FMU 5개 테스트 통과: PP, Fault/Reset, 파라미터 효과, 혼합 fleet 저장·복원, 수명 주기.
- Compose 설정 렌더링 및 `git diff --check` 통과.

Linux 검증 소스는 `build/copley-offline`, 이미지는 `ethercat-device-simulator:copley-validation`이다. 실제 `.env`·state 및 실행 중 운영 컨테이너/이미지는 교체하지 않았다. 물리 버스에서 실행 가능한 완성 상태로 간주하지 않는다. IPC의 동기식 대기(최대 1초), 예외 시 Slave 종료, SDO Abort TD-001은 다음 단계에서 해결해야 한다.


## 2026-10-27 초기화 OD 및 SDO 오류 복구

`0x2000:01=0` 재시작 명령 해제는 Copley 어댑터가 저장·응답한다. 실제 재시작 값 1은 아직 미지원이며 Abort한다. 단위/변환 지수 등 기존 조회 OD는 그대로 제공한다. CSP 보간·Homing 등 구현하지 않은 기능은 성공으로 가장하지 않고 미지원 응답을 유지한다.

미지원 SDO가 Python 서비스를 종료하던 문제를 수정했다. 프로젝트의 C++ mailbox gateway는 모델 확인 후 응답하고 Abort 이후에도 정상 SDO 및 PDO를 처리한다. KickCAT after-write hook은 모델 OD에 사용하지 않는다. 자세한 wire 검증은 TD-001 참조. 이번 수정은 native FMU 장애/지연 격리까지 완료한 것은 아니다.

## 2026-10-27 Halt 처리 수정

Halt bit8을 거부하여 PDO 처리 중 모델 서비스가 종료되던 문제를 수정했다. 어댑터는 수신 Controlword를 보관하고 FMU에 전달할 때만 `& ~0x0100`으로 bit8을 제거한다. 다른 비트(Enable, new setpoint, relative, Fault Reset)는 보존한다. Halt는 정지를 수행하지 않는다.

Linux 실제 FMU/어댑터 12개 시험과 C++–Python IPC 연속 PDO 시험 통과. Halt가 켜진 PP 이동 완료 및 Fault Reset을 확인했다. Docker 이미지 ethercat-device-simulator:dev 재빌드. 일반 모델 오류·hang을 무시하도록 변경한 것은 아니다.

## CopleyDriveSim의 모델링 한계

사용자 질문은 현재 모델 범위 확인이며, 부하·토크 모델 추가 구현 요청은 아니다.

| 항목 | upstream FMU | 현재 프로젝트 어댑터 |
| --- | --- | --- |
| 드라이브 상태 머신 및 Fault/Reset | 제공 | 연결·검증 |
| PP 위치 궤적/완료 응답 | 제공 | 연결·검증 |
| PV 속도 램프 | 제공 | 미연결 |
| PT 목표 토크 추종 | 단순 1차 지연 응답 | 미연결 |
| 외부 하중·힘·부하 토크 입력 | 없음 | 없음 |
| 관성·마찰·중력 및 모터/기구 동역학 | 없음 | 없음 |
| PP 이동 중 필요한 모터 토크 계산 | 없음 | 없음 |
| 토크 부족에 따른 추종 오차·실속 계산 | 없음 | 없음 |

PT 계산은 `torque += (targetTorque - torque) * dt / max(TorqueTimeConstant, dt)`이다. 단위는 정격 토크의 per-mille이며, 물리 부하로부터 토크를 계산하지 않는다. 토크와 위치·속도의 동역학 연결도 없다. 현재 PP-only 실행에서 TorqueActual을 실제 부하 토크 예측값으로 해석하면 안 된다.

따라서 현재 모델은 드라이브 제어 인터페이스와 단순 이동 응답을 검증하는 용도다. 실제 기계의 부하·토크 성능 예측 모델로 간주하지 않는다. 향후 CMMT FMU도 FMI 준수 여부와 별도로 실제 모델링 범위를 확인해야 한다. 이번 한계 확인으로 새 구현 항목은 추가하지 않는다.

근거: 검토 revision `68978af04ea475cf89e39ae872cdccb5ddc95e4c`의 modelDescription.xml 및 copley_drive_sim_step.m. 소스 FMU 빌드의 revision/hash는 위 재현 절차에 고정한다.

## 후속 장애 격리 설계 (2026-10-28)

공통 Diagnostic 데이터 구조 및 오류별 정책은 [DT-008](../Design/DT-008-diagnostic-fault.md), 구현 추적은 [RF-018](RF-018-diagnostic-fault.md)으로 분리한다. 응답 제한 시간·복구 명령·재Enable 정책은 아직 확정하지 않았다.


## 2026-10-28 현재 상태 갱신 — 이전 단계 기록보다 우선

- RF-018 완료로 crash/hang/IPC 단절·timeout 격리, 물리 WKC 유지, 정상 SDO Abort, 축 Reset 및 Docker 재시작 후 복구를 확인했다. 이를 다시 미구현 작업으로 요구하지 않는다.
- 사용자가 새 PP 이동 및 Fault Reset 후 복귀를 확인했다. 절대/상대 이동 각각의 정량 결과·파라미터 변화의 물리 효과·혼합 4축 장시간 성능은 기존 보고로 확대 인정하지 않는다.
- 남은 범위: 위 세부 물리 항목의 증거 확보 및 명시적 합격 시간/주기 결정. 기존 오프라인 PP/단위/저장 테스트는 유효하다.
- RF-010과 함께 격리 Docker에서 실제 Copley/F-KR 혼합 저장·복원을 재검증했다. 운영 state는 해당 시험에 사용하지 않았다.
