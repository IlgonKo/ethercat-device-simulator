# ADR-001 — Soft ESC 제품 정의와 소프트웨어 구조

- 결정 상태: **채택** (현행 범위 기준; 본문의 보류·과거 제안은 구분)
- 갱신일: 2026-11-25
- 구현 상태: 독립 패키지 범위 확정. Drive 기존 구현·검증 유지, Modular Remote I/O 구현 진행 대상.
- 구현 현황·계획: [프로젝트 계획](../project-plan.md), [RF 목록](../RF/README.md)

## 제품 정의

**Soft ESC는 FMU 또는 다른 형식의 동작 모델을 EtherCAT 장치 프로파일에 연결하여, EtherCAT Master가 제어할 수 있는 가상 장치를 제공하는 독립 실행 패키지다. CiA402 Drive와 EtherCAT Modular Device Profile 기반 Remote I/O를 지원 대상으로 한다.**

두 프로파일은 모두 제품 범위다. 지원 대상 정의와 현재 구현·검증 완료 여부는 구분한다. 모든 FMU·모듈·제조사 장치에 대한 무설정 호환이나 표준 전체 적합성을 선언하는 것은 아니다. 지원 기능은 프로파일·장치 설명·어댑터·동작 모델의 계약과 검증 결과로 명시한다.

DT Demo는 이 패키지의 사용·검증 사례다. Motion Server는 검증에 사용하는 외부 Master 애플리케이션이며 제품의 필수 실행 의존성이 아니다. Orchestrator·ROS2·Omniverse 없이도 구성·실행하고 EtherCAT 장치로 사용할 수 있어야 한다. 다른 Master 호환성은 별도 검증 대상이다.

## 논리 구조

가상 디바이스 = EtherCAT Slave + 기능 모델.
기능 모델 = 장치 프로파일 + 모델별 어댑터 + 선택한 동작 모델.

```text
외부 EtherCAT Master
          ↕
Soft ESC
 ├─ EtherCAT Slave 통신: ESC / Mailbox / SDO / PDO
 └─ 기능 모델
      ├─ 장치 프로파일
      │    ├─ CiA402 Drive
      │    └─ EtherCAT Modular Device Profile / Remote I/O
      ├─ 프로파일·모델별 어댑터
      └─ 동작 모델: 자체 모델 / FMU / 기타 형식
```

- **장치 프로파일:** 외부 Master가 보는 OD·명령·상태·파라미터·프로세스 데이터 계약. Drive와 모듈형 IO의 규칙을 구분한다.
- **장치 설명:** 제조사/제품 식별, ESI, 지원 모듈과 제조사 확장. 프로파일이나 동작 모델 이름과 동일하지 않다.
- **어댑터:** OD와 모델 변수·단위·기능 의미·수명 주기 연결. FMI 자체가 표준화하지 않는 변수 의미와 지원 차이를 처리한다.
- **동작 모델:** 드라이브·장치·연결된 대상의 동작 계산. 이미 모델이 제공하는 상태 머신·제어기를 중복 구현하지 않는다.

Remote I/O의 모듈/슬롯/채널 구성과 데이터 표현은 프로파일·장치 설명의 책임이다. 밸브·실린더 등 연결 대상의 동작은 선택한 동작 모델과 어댑터가 처리한다. Loader를 Remote I/O 프로파일 자체에 고정하지 않는다.

## 실행·데이터 경계

기존 Linux Docker 내 KickCAT Slave와 Functional Model Host 두 프로세스 및 Unix Socket IPC를 유지한다. 어댑터와 FMU/자체 동작 모델은 Host 내부에서 호출한다. 다른 형식 모델의 로더 지원은 구현 계약별로 확장하며 현재 모든 형식이 실행된다고 간주하지 않는다.

장치당 논리 OD는 하나다. Slave가 PDO mapping/assignment와 별도 매핑 파일을 소유한다. 기능 모델은 장치 값·동작 모델·모델 파라미터 저장을 소유한다. IPC에 매핑 준비/활성화/저장 명령을 넣지 않는다. 축별 값/상태 독립성 원칙을 IO 장치·모듈/채널에도 적용한다.

설정은 자체 .env이며 Motion Server 설정을 읽지 않는다. 로컬 Slave 번호, 영구 장치 ID, parameter_set과 외부 Master의 번호를 구분한다. 기존 영구 파라미터·매핑 파일은 별도로 유지한다. 비호환 저장 데이터는 오류로 처리하고 자동 초기화·이관하지 않는다.

## 제품 경계

Soft ESC는 수신한 EtherCAT 명령을 장치 계약에 따라 처리하고 피드백·진단을 제공한다. DT/Sync 선택, 실제/가상 Pairing, 실장비 조작, Sequence/Recipe, ROS2/Omniverse 연결은 외부 기능이다. 이를 위한 상태 덮어쓰기·External Follow·정렬 전용 API를 추가하지 않는다.

현재 검증된 축 Fault/Reset 및 Host 장애 중 Slave 유지 정책을 재사용한다. IO의 오류 표현·DO/DI 유효성은 프로파일에 맞게 정의하며 CiA402 Statusword/Controlword를 강제하지 않는다. 프로세스 분리가 하드 실시간 동작 또는 모든 장애의 통신 유지를 보장하지는 않는다.

관련: [모델 실행](ADR-003-model-interface.md), [프로파일/어댑터](ADR-007-cia402-profile-adapters.md), [구성](ADR-005-device-configuration.md), [저장](ADR-004-parameter-sync-persistence.md), [배포](ADR-006-docker-deployment.md).
