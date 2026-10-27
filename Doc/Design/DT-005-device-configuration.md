# DT-005 — .env 장치 구성과 혼합 버스 번호 매핑

- 최초 결정: 2026-09-15
- 현재 형식 결정: 2026-10-26 (.env 단일 설정으로 전환)
- 상태: 환경 설정 로더 및 다중 가상축 검증 완료, 물리 회귀는 후속

## 현재 결정과 이전 결정 대체

사용자 결정으로 실행 설정과 장치 설정을 모두 Simulator 자체 .env에 통합한다. 2026-09-22 JSON 단일 형식 결정과 2026-10-26 초기 Docker의 .env + JSON 병행 구성을 대체한다. DEVICE_SIMULATOR_CONFIG_FILE 및 JSON 구성 로더는 제거하며 자동 fallback은 없다.

Motion Server는 독립 패키지다. 명명 규칙은 유사하게 사용하지만 Motion Server의 .env·설정 로더를 읽거나 자동 페어링하지 않는다. 장치 영구 파라미터 JSON과 KickCAT ESI/IPC용 내부 JSON은 구성 파일이 아니므로 유지한다.

## 설정 소유권

| 대상 | 기준 |
| --- | --- |
| Motion Server 전체 버스 | Motion Server 자체 .env |
| Simulator 실행·가상장치 | Simulator 자체 .env |
| 장치 영구 파라미터 | 별도 저장소; 안정적인 ID와 PARAMETER_SET 기준 |
| 실제/가상/논리 장치/DT 대응 | 연동 패키지의 독립 매핑 |

## 축 설정

```dotenv
KICKCAT_INTERFACE=enp1s0
DEVICE_SIMULATOR_STATE_DIR=./state
DEVICE_SIMULATOR_BUS=0:axis:cia402-drive,1:axis:cia402-drive
DEVICE_SIMULATOR_AXIS_IDS=0:virtual-axis-0,1:virtual-axis-1
DEVICE_SIMULATOR_AXIS_MODELS=0:f_kr_cmmt,1:f_kr_cmmt
DEVICE_SIMULATOR_AXIS_MODES=0:linear,1:rotary
DEVICE_SIMULATOR_AXIS_PARAMETER_SETS=0:axis-0,1:axis-1
```

- BUS의 명시적 숫자는 로컬 Slave 번호다. 입력 나열 순서와 무관하게 정렬하고 중복·누락·음수·비정수를 거부한다.
- AXIS_IDS/MODELS/MODES/PARAMETER_SETS 목록은 필수다. 각 목록의 번호 집합은 BUS와 정확히 같아야 하며 중복 번호와 누락을 거부한다. ID는 순서와 독립적인 영구 식별자다.
- 현재 타입은 cia402-drive, 모델은 f_kr_cmmt, 모드는 linear/rotary를 지원한다. FMU는 후속이며 가상 IO는 RF-013 보류다.
- PARAMETER_SET은 저장 공간의 논리 이름이며 파일 경로가 아니다. 공간이 없으면 기본값으로 만들고 있으면 호환성을 검증한다. 기본 모델 preset은 linear_mm/rotary_deg다.
- PDO 매핑 선택·counts_per_unit·scale은 추가하지 않는다. 단위·스케일은 장치 파라미터 기준이고 동적 PDO는 RF-014다.
- 값은 한 줄의 리터럴로 작성한다. 따옴표와 주석은 지원한다. 제품 설정에 셸 명령·변수 치환을 사용하지 않는다. native 로더는 중복 키를 거부한다. Compose env_file의 문법 처리는 Compose가 담당한다.

## 장기 목표의 번호와 ID 대응 (IO 부분은 RF-013 보류)

| 대상 | 전체 Slave 번호 | Simulator 내부 순서 | 서버 Axis 번호 | 서버 IO ID |
| --- | --- | --- | --- | --- |
| 실제 축 5대 | 0~4 | 해당 없음 | 0~4 | 해당 없음 |
| 실제 IO | 5 | 해당 없음 | 해당 없음 | io0 |
| 가상 축 5대 | 6~10 | 0~4 | 5~9 | 해당 없음 |
| 가상 IO | 11 | 5 | 해당 없음 | io1 |

이 예시는 각 축 Slave가 단축이고 IO를 제외한 축에 연속 Axis 번호를 부여하는 경우다. 실제 서버 설정·검색 결과에서 확인한다. Slave 번호와 Axis 번호를 같은 값으로 사용하지 않는다.

논리 축 0은 실제 Axis 0 / Slave 0과 가상 Axis 5 / Slave 6에 대응한다. 논리 IO는 서버 io0 / Slave 5와 서버 io1 / Slave 11에 대응한다. 가상 IO의 안정적인 장치 ID는 예시로 virtual-io0를 사용하며 구체적인 .env 필드는 RF-013에서 정한다. 서버 IO ID io1과의 연결은 라우터 설정에서 명시한다. 라우터 매핑은 이 관계를 명시적으로 기록한다.

버스 순서가 바뀌어도 안정적인 가상장치 ID와 그 파라미터는 유지한다. ID 중복·누락·지원하지 않는 타입·모델·IO 구성을 시작 전에 검사한다. Slave 순서만으로 다른 장치의 저장 설정을 자동 연결하지 않는다.

## 구성 변경과 물리 검증

장치 타입·수량·순서 변경은 정지 후 재구성하는 작업이다. 장치 구성을 그대로 두고 모드를 전환하는 것과 다르며 Master 쪽 설정 정합성 및 재검색 절차가 필요하다. 자동 파일 공유나 서버 설정 변경으로 해결하지 않는다.

설정 파일만으로 혼합 버스 물리 연결이 생성되지는 않는다. 실제 Slave 뒤에 Linux KickCAT을 연결했을 때 반환 경로, 다중 가상 Slave 검색·identity·PDO·OP 및 IO 모델이 동작하는지는 RF-011의 축 확장과 RF-013의 IO 확장에서 검증해야 한다. 12 Slave 예시는 합의한 목표이며 현재 통신 검증 결과가 아니다.

관련: [전체 구조](DT-001-system-architecture.md), [영구 파라미터](DT-004-parameter-sync-persistence.md), [구성 구현 RF-011](../RF/RF-011-device-configuration.md).


## Docker 설정 전달

Compose가 루트 .env를 env_file로 전달한다. 장치 JSON 파일 마운트와 DEVICE_SIMULATOR_CONFIG_FILE은 제거한다. 어댑터는 환경 변수에서 구성 객체를 만들고 모델에 전달한다. 임시 장치 구성 JSON도 생성하지 않는다. 호스트 DEVICE_SIMULATOR_STATE_DIR를 /state로 마운트하고 컨테이너에서는 같은 변수의 값을 /state로 고정해 /state에 저장한다. native 실행의 상대 STATE_DIR는 .env 파일 디렉터리를 기준으로 한다. [DT-006](DT-006-docker-deployment.md)을 참조한다.

명시적 번호 원칙은 유지한다. DEVICE_SIMULATOR_BUS의 숫자가 slave_index이며 0부터 연속이어야 한다. 순서를 바꿀 때 해당 네 가지 AXIS 목록의 번호도 함께 옮기되 ID와 PARAMETER_SET은 유지한다.

## 시작·복원 규칙 (2026-09-22 확정)

- Docker는 .env 환경 변수를 사용한다. native 진단은 --env-file로 지정한다. 필수 축 설정 누락, 중복 ID/저장 공간, 미지원 장치·모델, 잘못된 번호 및 버스에 없는 AXIS 목록 항목을 거부한다. PDO/scale/preset 별도 설정은 지원하지 않는다.
- 전체 구성을 검증한 뒤 slave_index 순서로 축별 모델·OD·PDO를 생성한다. 실행 중 설정 재읽기·핫플러그는 지원하지 않는다. 변경은 정지·수정·재시작 후 Master 재검색으로 적용한다.
- parameter_set과 id는 1~64자의 영문·숫자·밑줄·하이픈이며 첫 문자는 영문 또는 숫자다. 각각 중복을 거부한다. 저장 공간 이름은 경로로 해석하지 않는다.
- 없는 저장 공간은 기본값으로 생성한다. 기존 공간은 마지막 저장값을 복원한다. 저장된 장치 타입·모델 타입·linear/rotary가 다르면 시작을 거부하며 자동 변환·초기화하지 않는다. mode를 바꾸려면 새 공간을 지정한다.
- 저장 데이터 손상·누락된 파라미터·스키마/단위 불일치도 전체 시작 오류다. 기존 데이터는 덮어쓰지 않는다.
- 위치·속도·Controlword·Enable·Homing 완료 상태·진행 중 명령은 복원하지 않는다. 새 모델의 초기 정지 상태에서 시작한다. DT 위치 동기화는 RF-007의 별도 절차다.
- RF-011은 다중 구성·분리에 집중한다. 기존 모델의 제한 처리와 회전 경로 계산은 변경하지 않고 [RF-015](../RF/RF-015-axis-model-semantics.md)에서 논의한다.

## 초기 구현과 운영

- 구성 예시는 [.env.example](../../.env.example). 기존 단일 축 시험 도구의 명시적 무설정 경로는 유지하지만 잘못된 .env에서 이 경로로 fallback하지 않는다.
- RF-016에서 자체 모델을 src/functional_model/cia402_drive/behaviour_model/f_kr_cmmt로 이관했다. --model-root와 외부 Motion Server 스냅샷 런타임 의존은 제거했고, 기존 .env 및 영구 파라미터 identity는 유지한다.
- 파라미터 저장 대상은 현재 모델의 NON_PDO_CONFIGURATION_OD_ROLES 20개다. PDO 목표값·운전 상태·명령/상태 객체는 저장하지 않는다. 전체 OD 영구화와 동일하지 않다.
- 저장은 기존 CMMT SDO 0x2005:03=1, 0x2005:01=1 요청으로 수행하고 완료 후 명령을 0으로 해제한다. 선택값 1만 지원한다. PRE-OP에서도 PDO 진행 없이 저장한다. 파일 fsync·원자적 교체 후 성공 상태를 반환한다. 실패는 성공으로 응답하지 않으며 기존 fail-closed IPC 정책을 따른다. 정상 SDO Abort 오류 응답은 TD-001에서 해결한다.
- 저장 루트에 프로세스 단독 잠금을 걸고, 각 parameter_set.json에 스키마·호환 메타데이터·값·체크섬을 기록한다. 백업/이관/관리 API 및 실제↔가상 동기화의 완료 검증은 RF-010/009에 남긴다.
- 실행 및 검증 절차: [RF-011](../RF/RF-011-device-configuration.md).

## 축별 설정 구조화 (2026-10-26)

Motion Server device/cmmt/.env.example의 MOTION_SERVER_CMMT_AXIS_PDO_CONFIGURATIONS처럼 번호:값 목록으로 구조화했다. 축마다 네 개 키를 반복하는 AXIS_0_ID 등의 형식은 제거했다. scripts/docker 진입점은 목록의 역슬래시 줄 연결을 정규화해 Compose에 전달한다. 원본 .env의 값과 순서는 유지한다. ID와 PARAMETER_SET의 값은 유지하며 자동 생성하지 않는다. 관리 NIC 변수와 해당 검사는 제거했다.

- 모델 표시 이름은 **F-KR Internal**, 설정 식별자는 공백 없는 `f_kr_cmmt`이다. 기존 저장 파라미터의 identity.model.type도 같은 식별자로 변경하며 값은 유지하고 checksum을 재계산한다. 실행 중 저장소는 수정하지 않는다.

- `config/`의 중복 예제는 제거했다. 개발용 `validate-fleet.py`도 기본적으로 루트 `.env`를 읽고 테스트 fixture는 `tests/fixtures`에서 관리한다.

## 프로파일과 모델 이름 분리 (2026-10-26)

BUS의 axis:cia402-drive는 기능 프로파일을 선택하고 AXIS_MODELS의 f_kr_cmmt는 자체 CMMT 동작 모델을 선택한다. 기존 cmmt-as/f_kr_internal 설정 별칭은 지원하지 않는다. EtherCAT identity·기본 PDO·Motion Server 설정은 기존 CMMT 호환 값으로 유지한다. state 파일의 identity.type과 identity.model.type도 새 이름으로 갱신하고 checksum을 재계산한다. 값·모드·parameter_set은 변경하지 않으며 정지 상태에서 백업 후 일회성 이관한다.
