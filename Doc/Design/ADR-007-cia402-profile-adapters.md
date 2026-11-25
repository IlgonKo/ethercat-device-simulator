# ADR-007 — 장치 프로파일과 동작 모델 어댑터 구조

- 결정 상태: **채택** (현행 범위 기준; 본문의 보류·과거 제안은 구분)
- 작성일: 2026-10-26
- 갱신일: 2026-11-25
- 구현 상태: CiA402/F-KR/Copley 기존 구현 유지. Modular Remote I/O를 동등한 제품 범위로 추가; 코드 확장은 RF-013에서 진행.
- 관련: [ADR-001](ADR-001-system-architecture.md), [ADR-003](ADR-003-model-interface.md), [프로젝트 계획](../project-plan.md)

## 프로파일·장치 설명·모델 분리

| 구성 | 책임 |
| --- | --- |
| CiA402 Drive 프로파일 | 축 명령·상태·파라미터 및 OD/PDO 계약 |
| EtherCAT Modular Device Profile / Remote I/O | 모듈형 장치 구성·모듈/채널·OD/PDO 계약 |
| 제품별 장치 설명 | Vendor/Product/Revision·ESI·지원 모듈·제조사 확장 |
| 프로파일/모델 어댑터 | OD ↔ 모델 변수·자료형·단위·동작 의미·초기화/Reset 연결 |
| 동작 모델 | 자체 코드/FMU 등으로 장치 또는 연결 대상의 동작 계산 |
| 공통 Host | 모델 인스턴스·실행/시간·IPC·저장·진단 기반 |
| EtherCAT Slave | ESC·Mailbox·SDO/PDO·매핑 검증/활성화/영구 저장 |

프로파일을 선택하는 것과 동작 모델을 선택하는 것은 별개다. 모델이 제공하는 상태 머신·제어 기능을 중복 실행하지 않는다. 모델의 미지원 기능은 어댑터 계약으로 드러낸다. 단순 OD 값 보관이 실제 동작 구현을 대신하지 않는다.

MDP 지원을 CPX라는 이름이나 DI/DO 바이트 복사만으로 정의하지 않는다. 선정 장치의 모듈 식별·구성·데이터 배치·지원 SDO/PDO 계약을 명시하고 검증한다. 모든 제조사/모듈 또는 표준 전체 적합성을 가정하지 않는다. Loader는 Remote I/O에 연결할 동작 모델 사례이며 프로파일 내부에 고정하지 않는다.

## IO 동작 모델 인스턴스와 채널 연결 — 2026-11-25 채택

동작 모델 종류와 인스턴스 ID를 구분하고 모델 인스턴스를 별도로 선언한다. 같은 종류의 모델을 여러 개 생성해도 각 상태·파라미터를 독립 유지한다. Remote I/O 한 대에 여러 동작 모델을 연결할 수 있으며 장치나 모듈 하나당 모델 하나로 고정하지 않는다. 자체 모델과 FMU에 같은 연결 원칙을 적용한다.

연결은 IO 장치 ID·모듈 슬롯·DI/DO/AI/AO 종류·채널 번호와 모델 인스턴스·변수의 명시적 대응이다. DO/AO는 모델 입력, DI/AI는 모델 출력에 연결한다. 외부 IO 프로파일의 입출력 명칭은 EtherCAT Master 관점이다.

- 프로파일: OD/PDO 표현과 모듈/채널 정의.
- 어댑터: 모델 변수 연결·자료형·단위 변환. FMU 변수 이름을 Slave가 직접 해석하지 않는다.
- 동작 모델: 입력에 따른 결과 계산. 자동 DO→DI/AO→AI loopback은 하지 않는다.

존재하지 않는 슬롯/채널/모델 변수, 방향·자료형 불일치는 시작 시 거부한다. 하나의 DI/AI 채널에 복수 모델 출력을 연결하지 않는다. 추가적인 공유/분배 규칙은 별도 명세 없이 임의 도입하지 않는다.

미연결 채널은 허용한다. DI는 False, AI는 raw 0을 제공하고 DO/AO는 수신값만 보관한다. 명시적으로 연결된 모델의 오류를 미연결 기본값으로 숨기지 않으며 진단으로 구분한다. 런타임 장애 시 IO 값/유효성·복구 상세는 RF-013에서 정한다.

선정 아날로그 모듈은 ESI의 signed 16-bit raw 표현을 유지한다. 표현 범위와 정상 신호 범위를 구분하고 물리량 변환은 어댑터의 모델/채널 계약에 따른다. 범위 초과 설정·모델 변환값을 자동 clamp하지 않는다. 모델 선언·채널 binding 환경 변수 문법은 [ADR-005](ADR-005-device-configuration.md)의 BEHAVIOUR_MODELS/BINDINGS 계약을 따른다. 실제 모델 종류별 변수·단위·동작 계약은 별도로 확정하며 기존 축 모델 설정은 유지한다.

## 실린더 동작 모델 재사용 — 2026-11-25

RF-013의 IO 연결 대상으로 `SoftESCDoubleActingCylinder` FMI 3.0 Co-Simulation
FMU를 사용한다. Linux 오프라인 검증은 완료했으며 IO 어댑터·등록·채널 연결은 미구현이다.
프로파일은 공압 계산을 포함하지 않고, 어댑터가 DO/DI의 논리 신호를 FMU의
extend_command/retract_command 및 끝단 센서 변수로 연결한다.

원본 FMU의 두 입력 OFF는 메모리 밸브 방향 유지다. 이전 일정 속도 모델의 OFF 정지
의미를 이름 변환만으로 덧씌우지 않는다. 모델의 파라미터·지원 기능·상충 입력과 장애
시 정책을 별도 계약으로 드러낸다. 공통 FMI 실행기를 재사용하기 전에 이 FMU의 입력
자료형·Event Mode/시간 진행 조건과 대조한다. [검증 근거](../Validation/Pneumatic-Cylinder-Web-FMU-20261125.md).

## OD와 매핑의 단일 책임

장치당 논리 OD 하나와 독립 값/상태를 유지한다. 프로파일 정의는 공유할 수 있지만 장치별 값·파라미터는 공유 원본으로 만들지 않는다. RF-014에 따라 매핑의 검증/저장/활성화는 Slave가 수행하고 모델 IPC에 매핑 절차를 넣지 않는다.

현재 Drive의 0x6040/0x6041 필수 검사 및 AxisFault/Statusword 표현은 IO에 적용하지 않는다. 공통 데이터 전달과 프로파일별 유효성 규칙을 분리한다. IO 모듈 구성과 모델/채널 연결 설정의 상세 키는 RF-013에서 확정한다.

## 현재 코드 배치와 확장 경계

```text
src/
 ├─ ethercat_slave/                 # 기존 C++ 통신/매핑/IPC/진단
 └─ functional_model/
      ├─ configuration.py         # 현재 축 설정; 프로파일별 검증 확장 필요
      ├─ cia402_drive/
      │    ├─ profile/
      │    ├─ adapter/            # f_kr_cmmt.py, copley.py 등
      │    ├─ behaviour_model/    # f_kr_cmmt
      │    └─ model_definitions/  # copley_drive_sim 변수 계약
      ├─ runtime/                 # 현재 축 실행, fleet 및 FMI 실행기
      ├─ ipc/
      ├─ storage/
      └─ diagnostics/
device_descriptions/               # 기존 CMMT 장치 설명
```

Modular Remote I/O 기능 모델은 `cia402_drive`와 같은 수준의 별도 프로파일 영역으로 추가한다. `profile / adapter / behaviour_model` 책임 구분을 유지한다. 정확한 IO 디렉터리명·클래스는 구현 설계에서 확정하며 이 문서의 설명을 이미 존재하는 경로로 해석하지 않는다. 공통 runtime/ipc/storage/diagnostics에 축/IO 특수 규칙을 무조건 넣지 않는다.

현재 `functional_model` 패키지명과 C++ `ethercat_slave` 구조를 유지한다. 저장소·이미지·설정 키 이름을 제품 명칭 변경 때문에 일괄 변경하지 않는다. 외부 Motion Server 스냅샷과 삭제된 config/configs 구성 폴더는 재도입하지 않는다.

## 기존 Drive와 FMU 지원

`axis:cia402-drive`와 모델 ID `f_kr_cmmt`/`copley_drive_sim`을 사용한다. 프로파일 이름은 EtherCAT identity와 별개이며 기존 CMMT-AS 호환 장치 설명·제조사 OD를 유지한다. 일반 모델이 실제 CMMT와 동등하다는 보증이 아니다.

FMI 실행기는 `runtime/fmi`, Copley 변수 계약은 `cia402_drive/model_definitions/copley_drive_sim`, 모델별 정책은 `adapter/copley.py`에 있다. 공통 실행기를 복제하지 않고 실제로 공유 가능한 매핑/정책만 재사용한다. 기타 모델 형식도 해당 로더와 어댑터 계약으로 확장한다.

Copley의 현재 어댑터는 PP/Enable/피드백/Fault Reset 등을 지원하고 Halt bit8을 마스킹한다. 실제 Homing·Stop/Halt 및 PV/PT 어댑터 지원을 전체 Drive 지원으로 확대하지 않는다. 상세 제약은 [RF-017](../RF/RF-017-copley-fmu.md)이 기준이다. F-KR과 Copley의 지원 기능을 동일하게 간주하지 않는다.

## 구현·검증 유지 원칙

기존 RF-016/017/018 완료와 시험 자료를 유지한다. 새 IO 지원은 구성·OD·매핑·IPC·진단·저장 변경의 축 회귀를 포함한다. 동작 모델 형식·프로파일·모듈별 지원표와 시험 결과를 남긴다. 최신 설계는 과거 “향후 FMU/첫 구현” 계획을 대체하며 과거 구현·검증 근거는 해당 RF를 따른다.
