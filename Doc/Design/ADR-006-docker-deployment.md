# ADR-006 — Linux Edge PC의 Docker 배포

- 결정 상태: **채택** (현행 범위 기준; 본문의 보류·과거 제안은 구분)
- 결정일: 2026-09-15
- 갱신일: 2026-11-25
- 구현 상태: 독립 Docker·다단계 빌드·혼합 축 통신·저장/장애 복구·Docker/native 비교 완료. Demo Edge #2 및 3축+IO 배포는 미검증.


## 독립 실행 계약

Soft ESC 이미지에는 장치 프로파일·어댑터·선택 동작 모델/실행기를 포함하거나 명시적으로 공급한다. CiA402 Drive와 Modular Remote I/O가 제품 범위이며 현재 IO 포함 이미지의 구현·검증은 RF-013 이후다. DT Demo·Orchestrator·ROS2·Omniverse나 Motion Server 소스/설정을 시작 조건으로 요구하지 않는다.

아래 Edge #2는 새 Linux PC 검증 사례다. 특정 Edge 이름·3축·Loader를 Docker 실행 조건으로 고정하지 않는다. 기존 .env/state·이미지 이름을 유지하며 표준 통신에 필요한 외부 EtherCAT Master만 별도로 연결한다.

## 독립 배포와 Demo 검증 배치

```text
Edge #1: Orchestrator + Motion Server
  EtherCAT Master NIC → 실제 장치 체인 → Edge #2의 EtherCAT NIC
                                        └─ Soft ESC Docker
Orchestrator → 일반 Ethernet/ROS2 → 별도 Omniverse PC
Edge #2 일반 Ethernet → 엔지니어링·운영 접근
```

Soft ESC는 체인 끝의 NIC 하나에서 다수 가상 Slave를 제공하고 수신 프레임을 같은 물리 경로로 반환한다. 중간 삽입용 IN/OUT과 하류 전달은 이번 범위가 아니다. 가상 3직선축+IO 구성은 RF-013/015 이후 검증한다. 기존 RF-005의 실제 장치+가상축 혼합 결과는 재사용하되 IO 구현 완료로 확대하지 않는다.

과거 Master와 Simulator를 한 Edge의 별도 NIC로 구성하는 배치는 장기 옵션이다. 이번 배포 검증은 별도 Master PC와 Soft ESC PC 구성이며 동일 Edge 시험을 선행 조건으로 두지 않는다.

## 실행 구조와 네트워크

Linux Docker Engine의 단일 컨테이너 안에서 KickCAT Slave와 Model Host를 별도 프로세스로 실행한다. 어댑터와 FMU는 Model Host 내부 라이브러리다. Motion Server 소스·설정을 마운트하지 않는다. 현재 `network_mode: host`와 지정 EtherCAT NIC를 사용한다. host 네트워크는 NIC 독점이나 실시간성을 보장하지 않는다. EtherCAT을 포트 publish/일반 NAT로 대체하지 않는다.

현재 권한·NIC 보호·종료 정책은 [RF-012](../RF/RF-012-docker-deployment.md) 및 [운영 스크립트](../../scripts/README.md)를 따른다. NIC 추가 검증은 계속 보류하며 필요 시 별도 RF로 분리한다. Windows Docker Desktop/VM에 동일 물리 NIC 조건을 가정하지 않는다. Soft ESC용 ROS2 또는 신규 관리 API는 Demo에 추가하지 않는다.

## 이미지·설정·저장

- Docker Builder 단계에 컴파일러와 C++ 의존성을 포함한다. 호스트 native 사전 빌드는 필요 없다.
- 실행 이미지는 `ethercat-device-simulator:dev`. F-KR 직선/회전 FMU, 기본 Linux Copley 및 IO FMU를 포함한다. F-KR C++ 코어도 Builder에서 컴파일하며 런타임에는 컴파일러가 없다.
- 설정은 Simulator 자체 `.env`의 BUS와 AXIS_NAMES/MODELS/MODES 목록을 사용한다. IO 필드는 RF-013에서 확정한다.
- `DEVICE_SIMULATOR_STATE_DIR=./state`를 컨테이너 `/state`로 연결한다. 영구 파라미터와 PDO 매핑은 별도 저장 파일이며 이미지 교체 후에도 유지한다.
- Unix 소켓·임시 파일은 영구 저장에서 제외한다. 컨테이너 재시작 시 운전 위치·이전 이동 명령을 복원하지 않는다.
- 데이터 비호환은 오류로 처리한다. 자동 이관/초기화하지 않으며 재시작 절차에서 저장소를 삭제하지 않는다.

고정 이미지/소스/wheel과 오프라인 export·restore·rebuild 절차는 [배포 매뉴얼](../../scripts/deployment/README.md)을 따른다. 기존 11월 3일 새 이미지 사용자 수동 확인과 11월 5일 비교 결과는 RF-012의 검증 근거다.

## 서비스 수명 주기

설정·저장 검증 후 모델/Slave를 시작하고 준비 상태를 제공한다. 비대화식으로 지속 실행하며 수동 stop은 자식 프로세스와 소켓을 정리한다. RF-018에서 모델 정지·종료 시 Slave 통신 유지와 축 Fault 표시를 검증했다. Slave 자체 종료 시에는 모델을 정리하고 컨테이너를 실패 처리한다(RF-012). healthcheck만으로 EtherCAT OP·WKC·운전 준비를 보장하지 않는다.

복구는 현재 축 Fault Reset 및 수동 Docker 재시작·Master 재연결 절차다. 컨테이너 복구와 자동 운전 재개를 동일하게 취급하지 않는다. IO 장애 표현은 RF-013에서 별도 확정한다.

## 남은 Soft ESC 배포 검증

1. 실제 Edge #2 새 Linux PC/OS에서 빌드/배포 재현성과 시작·재부팅 후 저장 복원.
2. 가상 X1/Y/Z+IO와 실제 장치의 혼합 통신·동작·장애 복구.
3. Soft ESC 운영 접근과 EtherCAT 경로 분리 확인. 외부 Pairing/Alignment·ROS2/Omniverse 구현 및 통합 검증은 이 프로젝트 완료 조건에서 제외.

기존 혼합 축·저장·모델 장애 시험 전체를 반복 요구하지 않고 새 구성의 영향 범위를 회귀 검증한다. 시험 시간/성능 합격 수치는 별도 합의한다. RT 환경이 없는 기존 결과를 결정론적 주기 보장으로 해석하지 않는다.

관련: [프로젝트 계획](../project-plan.md), [ADR-001](ADR-001-system-architecture.md), [ADR-004](ADR-004-parameter-sync-persistence.md), [RF-012](../RF/RF-012-docker-deployment.md).
