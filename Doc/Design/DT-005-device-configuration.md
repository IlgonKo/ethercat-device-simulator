# DT-005 — JSON 장치 구성과 혼합 버스 번호 매핑

- 최초 결정: 2026-09-15
- 형식 변경 결정: 2026-09-22
- 상태: JSON 단일 형식 채택 완료, 상세 스키마 확정 및 초기 로더·4축 생성 구현, 사용자 동작 시험 완료 보고, 세부 기준 확인 중

## 현재 결정과 이전 결정 대체

Simulator 장치 구성은 **표준 JSON을 단일 형식**으로 사용한다. Motion Server는 기존 .env를 유지한다. 2026-09-15의 ‘Motion Server와 같은 .env 문법’ 결정은 이 결정으로 대체한다. Simulator의 .env 장치 구성 로더, 두 형식 병행 지원 또는 호환 fallback은 구현하지 않는다.

두 제품은 독립 패키지이며 Simulator는 Motion Server .env·장치 설정·소스·설정 로더를 읽지 않는다. 자동 페어링/1:1 복제 옵션은 계속 제외한다. 장치 타입·모듈의 의미를 일치시키되 파일 문법까지 공유하지 않는다.

JSON은 장치 ID·타입·모델·파라미터 저장 공간을 한 항목에 묶는다. IO 구성은 RF-013에서 별도 정의한다. 장치를 재배치할 때 여러 번호 기반 목록을 따로 수정하지 않는다. devices[].slave_index를 필수로 명시하고 이 값의 오름차순으로 가상 Slave를 생성한다. JSON 배열의 나열 순서는 연결 순서를 결정하지 않는다. 배열 길이는 가상 Slave 수량이며 id는 순서와 독립적인 영구 식별자다.

## 설정 소유권

| 대상 | 기준 |
| --- | --- |
| Motion Server 전체 버스 | 기존 .env, 실제·가상 장치 전체 |
| Simulator 가상장치 | 자체 JSON, 생성할 가상장치만 |
| 장치 영구 파라미터 | DT-004의 별도 저장소, parameter_set 논리 이름 기준, 장치 id와 연결 |
| 실제/가상/논리 장치/DT 대응 | 연동 패키지의 독립 매핑 |

Motion Server에 simulator라는 추가 Slave를 등록하지 않는다. 가상 축·IO 각각이 일반 Slave로 보이는 것이 목표다.

## 현재 구현 범위와 축 JSON

2026-09-22 사용자 결정으로 현재 구현은 가상축에 한정한다. CPX 가상 IO·모듈·IO-Link·센서 저장은 [RF-013](../RF/RF-013-virtual-io.md)로 보류하며 별도 논의 후 착수한다. 기존 실제 IO가 있는 혼합 버스 검증 결과는 변경하지 않는다.

아래는 현재 합의한 장치 필드를 표현한다. 공통 경로·CLI·저장 형식의 상세 기본값 및 각 모델의 실제 지원 검증은 아직 구현 전이다.

```json
{
  "schema_version": 1,
  "ethercat": {
    "interface": "enp1s0"
  },
  "storage": {
    "directory": "../state/parameters"
  },
  "devices": [
    {
      "slave_index": 0,
      "id": "virtual-axis-0",
      "type": "cmmt-as",
      "model": {
        "type": "virtual_axis",
        "mode": "linear"
      },
      "parameter_set": "axis-0"
    },
    {
      "slave_index": 1,
      "id": "virtual-axis-1",
      "type": "cmmt-as",
      "model": {
        "type": "virtual_axis",
        "mode": "linear"
      },
      "parameter_set": "axis-1"
    },
    {
      "slave_index": 2,
      "id": "virtual-axis-2",
      "type": "cmmt-as",
      "model": {
        "type": "virtual_axis",
        "mode": "rotary"
      },
      "parameter_set": "axis-2"
    },
    {
      "slave_index": 3,
      "id": "virtual-axis-3",
      "type": "cmmt-as",
      "model": {
        "type": "virtual_axis",
        "mode": "rotary"
      },
      "parameter_set": "axis-3"
    }
  ]
}
```

- slave_index: 필수, 0부터 N-1까지 연속 정수. 중복·누락·음수·비정수·boolean을 거부한다. 배열 순서와 관계없이 해당 값으로 정렬한다.
- id: 필수 영구 장치 식별자. 순서 변경에도 유지한다.
- type: 필수 장치 프로파일. role은 타입에서 결정하므로 별도 필드로 두지 않는다.
- pdo 필드는 두지 않는다. 현재 장치 프로파일의 기본 motion_server_default 매핑으로 시작한다. 임의 SDO 재매핑은 RF-014에서 구현하며, 현재는 같은 고정 매핑의 재설정만 지원한다.
- model.type: 필수 모델 구현 선택. FMI 세부 계약은 후속이다.
- model.mode: 가상축의 linear/rotary 구분. 지원 조합은 검증한다.
- 단위·스케일은 장치 파라미터 모델을 기준으로 한다. 별도 counts_per_unit/scale은 두지 않는다.
- parameter_set: 영구 파라미터 저장소 안의 논리 이름. 파일 경로가 아니다. 신규 공간이면 타입·모델·mode에 맞는 기본값으로 생성하고, 기존 공간은 호환성을 확인해 읽는다.

initial_parameters/initial_preset 및 최초 preset 선택 제안은 parameter_set 저장 공간 매핑으로 대체한다. linear_mm_default / rotary_deg_default는 기본 설정 세트 명명 논의에서 사용한 이름이며, 초기 JSON에 별도 preset 선택 필드로 넣지 않는다. 현재 기본값은 기존 모델의 linear_mm / rotary_deg 구성을 각각 사용한다.

파라미터 쓰기는 실행값에 반영하고 명시적 저장 명령으로 영구화한다. 저장 전 재시작은 마지막 저장값을 복원한다. 초기에는 여러 장치가 같은 parameter_set을 사용하는 구성을 거부한다. 저장 데이터 손상·호환 불일치는 기본값 덮어쓰기 없이 오류로 처리한다. 자세한 정책은 DT-004를 따른다.

표준 JSON 문법, 중복 키, 필드 타입, 지원 장치·모델을 검증한다. 현재 IO 설정은 미지원 오류로 보고하며 자동 대체하거나 무시하지 않는다.

## 장기 목표의 번호와 ID 대응 (IO 부분은 RF-013 보류)

| 대상 | 전체 Slave 번호 | Simulator 내부 순서 | 서버 Axis 번호 | 서버 IO ID |
| --- | --- | --- | --- | --- |
| 실제 축 5대 | 0~4 | 해당 없음 | 0~4 | 해당 없음 |
| 실제 IO | 5 | 해당 없음 | 해당 없음 | io0 |
| 가상 축 5대 | 6~10 | 0~4 | 5~9 | 해당 없음 |
| 가상 IO | 11 | 5 | 해당 없음 | io1 |

이 예시는 각 축 Slave가 단축이고 IO를 제외한 축에 연속 Axis 번호를 부여하는 경우다. 실제 서버 설정·검색 결과에서 확인한다. Slave 번호와 Axis 번호를 같은 값으로 사용하지 않는다.

논리 축 0은 실제 Axis 0 / Slave 0과 가상 Axis 5 / Slave 6에 대응한다. 논리 IO는 서버 io0 / Slave 5와 서버 io1 / Slave 11에 대응한다. 이전 .env 초안의 Simulator 로컬 io0 대신 JSON에서는 장치 id virtual-io0를 사용한다. 서버 IO ID io1과의 연결은 라우터 설정에서 명시한다. 라우터 매핑은 이 관계를 명시적으로 기록한다.

버스 순서가 바뀌어도 안정적인 가상장치 ID와 그 파라미터는 유지한다. ID 중복·누락·지원하지 않는 타입·모델·IO 구성을 시작 전에 검사한다. Slave 순서만으로 다른 장치의 저장 설정을 자동 연결하지 않는다.

## 구성 변경과 물리 검증

장치 타입·수량·순서 변경은 정지 후 재구성하는 작업이다. 장치 구성을 그대로 두고 모드를 전환하는 것과 다르며 Master 쪽 설정 정합성 및 재검색 절차가 필요하다. 자동 파일 공유나 서버 설정 변경으로 해결하지 않는다.

설정 파일만으로 혼합 버스 물리 연결이 생성되지는 않는다. 실제 Slave 뒤에 Linux KickCAT을 연결했을 때 반환 경로, 다중 가상 Slave 검색·identity·PDO·OP 및 IO 모델이 동작하는지는 RF-011의 축 확장과 RF-013의 IO 확장에서 검증해야 한다. 12 Slave 예시는 합의한 목표이며 현재 통신 검증 결과가 아니다.

관련: [전체 구조](DT-001-system-architecture.md), [영구 파라미터](DT-004-parameter-sync-persistence.md), [구성 구현 RF-011](../RF/RF-011-device-configuration.md).


## Docker 설정 전달

구성 JSON을 읽기 전용 마운트하고 Simulator 자체 로더로 읽는다. Compose의 .env는 배포 도구의 별도 개념이며 장치 구성의 대체 형식으로 사용하지 않는다. 실행 시 --config로 JSON 파일을 명시한다. storage.directory 상대 경로는 JSON 파일이 있는 디렉터리를 기준으로 해석한다. [DT-006](DT-006-docker-deployment.md)을 참조한다.

## 연결 순서 명시 결정 (2026-09-22)

초기 JSON 초안의 배열 순서 기반 규칙을 명시적 slave_index로 대체한다. 순서를 바꿀 때 slave_index만 재배치하고 동일 장치의 id는 유지한다. 연결 순서와 영구 파라미터 식별을 분리한다. 이후 축 필드·parameter_set 결정은 위 현재 축 JSON 절을 따른다. 공통 저장 경로는 storage.directory로 확정했으며 이전 data_root 초안을 대체한다.

## 시작·복원 규칙 (2026-09-22 확정)

- --config로 JSON을 지정한다. 파일 내 모든 필드는 필수이며 미지원/알 수 없는 필드는 거부한다. pdo, role, counts_per_unit, scale, initial_parameters는 허용하지 않는다.
- 전체 구성을 검증한 뒤 slave_index 순서로 축별 모델·OD·PDO를 생성한다. 실행 중 설정 재읽기·핫플러그는 지원하지 않는다. 변경은 정지·수정·재시작 후 Master 재검색으로 적용한다.
- parameter_set과 id는 1~64자의 영문·숫자·밑줄·하이픈이며 첫 문자는 영문 또는 숫자다. 각각 중복을 거부한다. 저장 공간 이름은 경로로 해석하지 않는다.
- 없는 저장 공간은 기본값으로 생성한다. 기존 공간은 마지막 저장값을 복원한다. 저장된 장치 타입·모델 타입·linear/rotary가 다르면 시작을 거부하며 자동 변환·초기화하지 않는다. mode를 바꾸려면 새 공간을 지정한다.
- 저장 데이터 손상·누락된 파라미터·스키마/단위 불일치도 전체 시작 오류다. 기존 데이터는 덮어쓰지 않는다.
- 위치·속도·Controlword·Enable·Homing 완료 상태·진행 중 명령은 복원하지 않는다. 새 모델의 초기 정지 상태에서 시작한다. DT 위치 동기화는 RF-007의 별도 절차다.
- RF-011은 다중 구성·분리에 집중한다. 기존 모델의 제한 처리와 회전 경로 계산은 변경하지 않고 [RF-015](../RF/RF-015-axis-model-semantics.md)에서 논의한다.

## 초기 구현과 운영

- 예시: [config/four-axes.json](../../config/four-axes.json). 기존 단일 축 시험 도구를 --config 없이 사용하는 경로에는 영구 저장이 적용되지 않는다. JSON 오류가 이 경로로 fallback하는 동작은 없다.
- 현재 모델 재사용은 --model-root로 지정된 기존 소스 스냅샷에 의존한다. 구성 로더는 Motion Server와 독립이지만, 모델 자체를 독립 배포 패키지로 분리하는 작업은 완료되지 않았다.
- 파라미터 저장 대상은 현재 모델의 NON_PDO_CONFIGURATION_OD_ROLES 20개다. PDO 목표값·운전 상태·명령/상태 객체는 저장하지 않는다. 전체 OD 영구화와 동일하지 않다.
- 저장은 기존 CMMT SDO 0x2005:03=1, 0x2005:01=1 요청으로 수행하고 완료 후 명령을 0으로 해제한다. 선택값 1만 지원한다. PRE-OP에서도 PDO 진행 없이 저장한다. 파일 fsync·원자적 교체 후 성공 상태를 반환한다. 실패는 성공으로 응답하지 않으며 기존 fail-closed IPC 정책을 따른다. 정상 SDO Abort 오류 응답은 TD-001에서 해결한다.
- 저장 루트에 프로세스 단독 잠금을 걸고, 각 parameter_set.json에 스키마·호환 메타데이터·값·체크섬을 기록한다. 백업/이관/관리 API 및 실제↔가상 동기화의 완료 검증은 RF-010/009에 남긴다.
- 실행 및 검증 절차: [RF-011](../RF/RF-011-device-configuration.md).
