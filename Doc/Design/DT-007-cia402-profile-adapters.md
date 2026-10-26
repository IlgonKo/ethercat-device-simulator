# DT-007 — CiA402 프로파일 및 모델 어댑터 구조

- 작성일: 2026-10-26
- 상태: 논리 계층·폴더 구조 확정 / 최초 구조 이관 및 오프라인 검증 완료, 물리 회귀 대기. API·파일 형식·설정 확장은 후속 상세화.
- 연계: [DT-003](DT-003-model-interface.md), [DT-005](DT-005-device-configuration.md), [RF-016](../RF/RF-016-cia402-profile-adapter.md)

## 결정 사항

공통 장치 프로파일은 CMMT가 아닌 CiA402 Drive로 정의한다. 최초 구현은 CiA402 Drive 프로파일과 F-KR Internal 어댑터에 한정한다. CMMT FMU는 아직 제공되지 않았으며 Copley FMU 연결도 이번 구현 범위에서 제외한다. 가상 IO는 RF-013 보류를 유지한다.

프로파일은 장치 인터페이스 정의이고 모델은 동작 계산이다. 같은 프로파일에 여러 모델을 연결할 수 있으며 BUS만으로 모델을 고정하지 않는다. 향후 기본 모델 자동 선택은 선택 사항이고 현재 설정 계약을 변경한 것으로 해석하지 않는다.

FMI는 로드·변수 접근·시간 진행을 표준화하지만 변수명·단위·기능 의미를 통일하지 않는다. 향후 FMU 경로는 공통 CiA402–FMU 어댑터 + 모델별 매핑 + 공통 FMI 실행기를 우선한다. 변수·자료형·스케일 차이는 매핑 데이터로 처리하고, 초기화·상태·핸드셰이크 차이가 있을 때만 모델별 코드를 추가한다. 모델마다 FMI 실행기를 복제하지 않는다.

## 책임 경계

| 구성 | 책임 |
|---|---|
| CiA402 프로파일 | 지원 OD 스키마·자료형·접근 권한, PDO 정의와 검증, 표준 기능 표현 |
| EtherCAT 장치 설명 | Vendor/Product/Revision, ESI 원본·생성 규칙, 제조사 확장 OD |
| 축 런타임 | 축별 OD 값·파라미터·모델 인스턴스·피드백 유효성 관리 |
| 어댑터 | 프로파일 OD와 모델 입출력 연결, 단위·자료형 변환, 초기화·파라미터 적용·Reset 및 지원 기능 연결 |
| 모델 | 드라이브 상태 전이 및 운동 계산. 모델이 제공하는 CiA402 상태 머신을 중복 실행하지 않음 |
| Model Host | 모델 수명 주기·시간 진행·IPC·오류 보고 |
| KickCAT Slave | ESC·프레임·Mailbox·SDO/PDO 통신. 모델 변수나 FMU 구현을 직접 해석하지 않음 |

스키마 정의는 공유할 수 있지만 축별 OD 현재값·상태·저장 파라미터는 독립 유지한다. 기존 모델의 OD를 어댑터가 사용하더라도 새 OD 사본과 서로 다른 값을 보유하지 않도록 단일 권위와 동기화 시점을 정한다. 첫 단계에서는 기존 상태 머신·운동 알고리즘을 변경하지 않는다.

ESI에서 얻는 공통 데이터는 재사용하되 ESI 전체 기능이 구현되었다고 간주하지 않는다. 실제 지원 기능은 프로파일·어댑터·모델의 공통 지원 범위로 결정한다. 미지원 기능은 명시적으로 거부하며 정상 처리로 위장하지 않는다. SDO 저장 성공과 모델 적용 성공의 의미를 구분하고 모델 관련 쓰기는 검증·적용 결과를 반영한다.

## EtherCAT identity와 기존 Motion Server 호환성

CiA402는 Vendor ID/Product Code/Revision을 정하지 않는다. 범용 프로파일로 분리해도 기존 CMMT 호환 identity·ESI·제조사 확장 정의를 별도 장치 설명으로 유지할 수 있다. 초기 리팩터링은 현재 CMMT-AS identity·PDO·Motion Server BUS 설정을 보존한다. 이는 일반 모델을 실제 CMMT와 동등하다고 보증하는 것이 아니다.

범용 identity와 새로운 BUS 값 `axis:cia402-drive`는 별도 설정·호환성 결정이 필요하다. 현재 `axis:cmmt-as`를 즉시 변경하지 않는다. Motion Server는 별도 패키지로 유지하고 이번 작업에서 수정하지 않는다.

## 확정 논리 구조와 실행 구조

가상 디바이스 = EtherCAT Slave + 기능 모델.
기능 모델 = CiA402 Drive 프로파일 + 모델별 어댑터 + 선택한 동작 모델.

```text
가상 디바이스
├─ EtherCAT Slave: ESC / Mailbox / SDO / PDO
└─ 기능 모델
   ├─ CiA402 Drive: 공통 OD·PDO·명령/피드백 인터페이스
   ├─ 모델별 어댑터: 매핑·단위 변환·파라미터 적용
   └─ 동작 모델: F-KR Internal 또는 향후 FMU
```

프로파일은 인터페이스 정의이며 모델이 제공하는 상태 머신을 중복 실행하지 않는다. 모델별 지원 기능 차이는 어댑터가 명시한다. 기능 모델 전체의 패키지 이름은 `functional_model`로 확정하며, 앞선 `simulator`, `device_simulator`, `model_coupler` 중심의 목표 구조 제안을 대체한다.

단일 Docker 컨테이너에서 EtherCAT Slave 프로세스와 기능 모델 프로세스를 실행하고 Unix Socket IPC로 연결한다. 각 축은 기능 모델 프로세스 안의 독립 인스턴스이며 축별 프로세스를 만들지 않는다. 어댑터·자체 모델 및 향후 FMU 라이브러리는 기능 모델 프로세스 내부에서 호출한다. 통신 버퍼와 모델 값의 동기화·오류 계약은 IPC 명세로 정한다. 프로세스 분리만으로 장애 격리 구현이 완료된 것은 아니다.

## 확정 프로젝트 폴더 구조

아래는 사용자와 합의한 구조이며 RF-016에서 최초 코드 이관을 수행했다. 작고 단순한 구현을 불필요하게 여러 파일로 나누거나 후속 FMU용 빈 폴더를 미리 만들지 않는다.

```text
ethercat-device-simulator/
├─ src/
│  ├─ ethercat_slave/               # C++ / KickCAT
│  │  ├─ main.cc
│  │  ├─ esc/
│  │  ├─ mailbox/
│  │  ├─ process_data/
│  │  └─ ipc/
│  └─ functional_model/            # Python 패키지
│     ├─ __main__.py
│     ├─ configuration.py          # 루트 .env 파싱·검증
│     ├─ profiles/
│     │  └─ cia402_drive/
│     │     ├─ profile.py
│     │     ├─ object_dictionary.py
│     │     ├─ pdo.py
│     │     └─ capabilities.py
│     ├─ adapters/
│     │  ├─ contract.py
│     │  ├─ registry.py
│     │  └─ f_kr_internal.py
│     ├─ models/
│     │  └─ f_kr_internal/
│     ├─ runtime/
│     │  ├─ service.py
│     │  └─ axis.py
│     ├─ ipc/
│     └─ storage/
├─ device_descriptions/
│  └─ cmmt_as/
│     ├─ identity.*
│     ├─ esi/
│     └─ extensions.*
├─ protocols/
│  └─ ipc/                         # 두 프로세스 간 메시지 명세
├─ third_party/KickCAT/
├─ docker/
│  ├─ Dockerfile
│  └─ service.py                   # 두 프로세스 실행 관리
├─ scripts/
│  ├─ docker/
│  ├─ linux/
│  └─ windows/
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ fixtures/
├─ Doc/
│  ├─ Design/
│  ├─ RF/
│  ├─ TD/
│  └─ Work_log.md
├─ state/                          # 영구 파라미터
├─ build/                          # 빌드·진단 생성물
├─ pyproject.toml
├─ CMakeLists.txt
├─ compose.yaml
├─ .env.example
└─ .env
```

identity.*와 extensions.*의 파일 형식은 상세 설계 시 결정한다. device_descriptions는 공통 CiA402 기능과 제품 식별 정보를 분리하기 위해 루트에 둔다. 운영 구성은 루트 .env 단일 형식을 유지하며 삭제한 config/configs 폴더를 재도입하지 않는다. 모델 소스는 기능 모델의 구성 요소이므로 src/functional_model/models에 둔다.

## 향후 FMU 확장 위치

```text
src/functional_model/
├─ adapters/fmi.py                # 공통 CiA402–FMU 어댑터
├─ runtime/fmi/                   # FMI 로드·변수 접근·시간 진행
└─ model_definitions/
   ├─ copley_drive_sim/
   └─ cmmt_fmu/
model_artifacts/                  # 배포받은 FMU 파일
```

매핑 데이터로 해결하지 못하는 동작 차이에만 전용 코드를 추가한다. 루트 model_artifacts는 배포 바이너리이고 functional_model/models는 자체 동작 모델 소스다. 이번 최초 구현에는 FMU 경로를 만들거나 연결하지 않는다.

RF-016에서 필요한 자체 모델·OD·codec·ESI parser를 출처와 해시를 기록하여 이관했다. 전체 Motion Server 트리는 복제하지 않았으며 build/model-source-da0b0a3는 과거 검증 자료로만 남는다. 현재 런타임과 Docker는 이 스냅샷을 읽지 않는다.

## Copley 사전 검토와 후속 요구

검토 revision: 68978af04ea475cf89e39ae872cdccb5ddc95e4c. FMI 3.0 CS이며 CiA402 상태 머신·PP/PV/PT를 내부 제공한다. 위치는 counts, 목표/실제 속도는 0.1 counts/s, ProfileVelocity는 counts/s이다. CSP·Homing·PP Halt·소프트웨어 위치 제한은 확인한 계산 코드에 구현되어 있지 않다. 미지원 모드도 표시값을 그대로 돌려주므로 어댑터가 지원 여부를 검증해야 한다. 초기 위치는 0이고 임의 초기 위치 입력 및 FMI 상태 저장/복원은 제공하지 않아 실제축 상태 동기화에 추가 검토가 필요하다.

[입출력 정의](https://github.com/Beckhoff-USA-Community/AAG_TwinCAT_CiA402_CANopen_CPP_FMU_MATLAB/blob/68978af04ea475cf89e39ae872cdccb5ddc95e4c/MATLAB_and_Simulink/FMU_DriveSim/fmu_static/modelDescription.xml), [동작 계산](https://github.com/Beckhoff-USA-Community/AAG_TwinCAT_CiA402_CANopen_CPP_FMU_MATLAB/blob/68978af04ea475cf89e39ae872cdccb5ddc95e4c/MATLAB_and_Simulink/FMU_DriveSim/copley_drive_sim_step.m).

## 첫 구현 순서 및 검증

1. 현재 CMMT profile·VirtualOdBridge·가상 서보 의존 파일과 OD 값 소유권을 확인한다.
2. 공통 CiA402 정의와 CMMT 장치 설명을 분리한다.
3. F-KR Internal 어댑터를 연결하고 기존 모델 계산·상태 전이는 유지한다.
4. 기존 모델 ID f_kr_internal, axis ID, parameter_set 및 저장 파라미터 복원을 유지한다. 저장 스키마 변경이 필요하면 별도 검증된 마이그레이션을 설계한다.
5. 1축 기능 검증 후 4축 OD·PDO·상태 독립성 및 성능을 회귀 검증한다.
6. 기존 Motion Server와 실제/가상 혼합 버스의 identity·SDO·PDO·WKC를 재검증한다.

어댑터의 메서드 시그니처, 단위 계약, 공통/제조사 OD 분류, capabilities 표현, 지원하지 않는 요청의 오류 매핑은 구현 전 상세화한다. FMU·동적 PDO·IO·Omniverse·라우터 및 모델 장애 격리의 완성은 이번 범위에 포함하지 않는다. 기존 DT-003 장애 격리 목표는 별도 유지한다.
