# DT-001 — 전체 소프트웨어 구조

- 결정일: 2026-09-15
- 상태: 사용자 합의 완료, 구현 및 혼합 버스 검증 전

## 목적과 확정 결정

KickCAT 타당성 검증을 바탕으로 Omniverse DT를 가상장치 또는 실제장비의 피드백에 동기화한다. Motion Server는 기존 독립 패키지로 유지하고 제품 코드 및 공개 API를 수정하지 않는다.

Motion Server 한 인스턴스가 동일 EtherCAT 버스의 실제·가상 장치 그룹을 함께 관리한다. 외부 명령·리드백 라우터가 모드에 따라 논리 장치 ID를 선택한 그룹의 서버 장치 ID로 변환한다. 모드 전환으로 서버나 버스를 재시작하지 않는 것을 목표로 한다. NIC 전환 및 서버 두 인스턴스 방식은 현재 채택안이 아니다.

```text
Axis Panel / 제어 Client
          ↕ 기존 명령·응답·상태 프로토콜
명령·리드백 라우터 ← 실제 / 가상 모드 선택
          ↕
Motion Server 1개 (기존 독립 패키지)
          ↕
EtherCAT 버스 (물리 배선은 RF-005에서 검증)
    ├─ 실제 드라이브·IO
    └─ KickCAT → 장치 계층 → 가상축·가상 IO / 향후 FMI 모델

라우터의 선택된 리드백 → Omniverse 연결부 → Omniverse DT
라우터의 전환 제어 → 시뮬레이터 관리 인터페이스 (모델 초기화)
```

## 패키지 책임

| 구성 | 책임 |
| --- | --- |
| Motion Server | 기존 EtherCAT Master 및 장치 제어. 공개 인터페이스와 기존 설정만 사용 |
| EtherCAT Device Simulator | KickCAT, OD·CiA 402, 모델 실행 및 상태 초기화 관리 인터페이스 |
| 명령·리드백 라우터 | 장치 ID 매핑, 모드·전환 세션, 명령·응답·상태 중계, 제어권 관리 |
| Omniverse 연결부 | 선택된 상태의 단위·좌표 변환, 장치와 USD Prim 매핑, 유효성 표시 |
| Omniverse DT | 장치 상태를 장면에 표현. 축·IO 동작 계산의 기준은 시뮬레이션 모델 또는 실제 장비 |

라우터와 Omniverse 연결부는 별도 연동 패키지 안에서 책임을 분리한다. 세부 프로세스 구성과 저장소 분리는 미결정이다. Omniverse 연결 기능을 KickCAT 내부에 결합하지 않는다.

## 명령과 리드백

예: 논리 X축을 실제 모드에서는 서버 Axis 0, 가상 모드에서는 Axis 3으로 매핑한다. 번호는 설명용이며 실제 구성은 설정으로 정의한다. 응답과 피드백도 역매핑해 Client에는 논리 X축으로 제공한다. DT에는 목표값이 아닌 선택한 장치의 실제 위치·IO 피드백을 전달한다.

비선택 그룹도 PDO 교환은 지속한다. 사용자 동작 명령은 선택 그룹에만 보내고 비선택 그룹은 정의된 대기 상태로 유지한다. 라우터를 우회하는 제어 Client의 접속 정책도 구현 전에 정해야 한다.

## 미검증 전제와 채택 검증

- 실제 Slave와 Linux KickCAT이 한 버스에서 정상 프레임 반환·검색·PDO 교환을 할 수 있는지 미검증이다. 위 그림은 논리 구성이며 일반 Ethernet 분기 배선을 지시하지 않는다.
- 기존 Motion Server가 실제·가상 장치 동시 등록, 축별·IO별 명령, 그룹에 한정된 제어를 수정 없이 지원하는지 확인해야 한다.
- 전체 축 명령, 시작 시 자동 Enable, 제어권 및 통신 장애의 영향 범위를 확인해야 한다.
- 기존 API가 필요한 IO와 상태를 제공하는지 확인해야 한다. 없는 정보를 제공한다고 가정하거나 서버 확장을 진행하지 않는다.
- 기존 Axis Panel을 그대로 연결하는 프로토콜 중계 가능성도 확인해야 한다.

[RF-005](../RF/RF-005-mixed-bus-feasibility.md)에서 전제를 검증한다. 충족되지 않으면 근거를 기록하고 구조를 재논의한다. 이번 합의를 검증 완료로 해석하지 않는다.

## 관련 설계

- [모드 전환 및 동기화](DT-002-mode-switching.md)
- [모델 인터페이스와 FMI 방향](DT-003-model-interface.md)
- [명령·리드백 라우터 구현](../RF/RF-006-command-feedback-router.md)

## 파라미터 관리 추가 결정

연동 패키지에 양방향 파라미터 동기화 관리자를 두고, 시뮬레이터에 장치별 영구 저장소를 둔다. Motion Server는 기존 공개 API로 접근한다. 라우터가 저장 파일을 직접 변경하지 않는다. [DT-004](DT-004-parameter-sync-persistence.md)를 따른다.

## 독립 구성과 장치 번호

[DT-005](DT-005-device-configuration.md)에 독립 JSON 구성과 12 Slave 예시를 확정했다. Motion Server는 실제/가상을 구분하지 않고 각 Slave를 일반 장치로 관리한다. Simulator 자체를 추가 Slave로 등록하지 않는다. 실제 축 Slave 0~4·IO 5, 가상 축 6~10·IO 11을 예시로 사용하며 서버 축 번호는 별도 매핑한다. 2026-09-22 결정으로 Simulator는 JSON, Motion Server는 기존 .env를 사용한다. 설정 파일/로더를 공유하지 않는다.

## Edge 배포 구성

[DT-006](DT-006-docker-deployment.md)에 Linux Docker Engine 기반 Simulator 단일 컨테이너를 기록했다. Motion Server는 별도 패키지다. Edge NIC 1은 Master, NIC 2는 실제 장비 체인 끝의 Simulator, NIC 3은 엔지니어링 및 별도 Omniverse PC와 통신한다. 라우터/DT Bridge는 Edge 배치를 제안하며 세부 배포·포트는 구현 시 확정한다.
