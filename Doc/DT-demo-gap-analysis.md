# Soft ESC — DT Demo Gap Analysis & Development Roadmap

**기준일:** 2026-11-25 · **버전:** 0.1 (검토 초안)

## 1. 목적 및 분석 근거

Fieldbus-level Digital Twin Demo 구현을 위해 기존 Soft ESC의 개발 상태와 최신 DT Demo 요구사항을 비교하고 최소 추가 개발 범위를 정의한다.

- [Soft ESC Repository](https://github.com/IlgonKo/ethercat-device-simulator)

- [RF 현황](https://github.com/IlgonKo/ethercat-device-simulator/blob/main/Doc/RF/README.md)

- [DT Demo 시스템 사양서 v1.1, 2026-11-23](https://github.com/IlgonKo/DT-demo/blob/main/docs/specifications/DT_Demo_System_Specification.md)

- [Motion Server](https://github.com/IlgonKo/motion-server)

분석은 RF 문서와 저장소 구조 및 시스템 사양서 기준이다. Motion Server 최신 변경 코드와 Soft ESC 함수·테스트의 전수 대조는 후속 작업이며 실제 장비 시험은 수행하지 않았다.

## 2. 요약

실질적 신규 개발은 Virtual IO 및 Loader Behavior Model(RF-013)이다. 기존 가상축 모델의 보완(RF-015), Docker 배포(RF-012), Parameter Pairing 및 시스템 통합 검증을 추가한다. 기존 RF-006~009의 정책 및 외부 연동은 최신 Demo 사양에 따라 Orchestrator가 담당한다.

## 3. RF 현황

총 21개(RF-002-1 포함) 중 완료 12개, 예정 7개, 진행 중 1개, 보류 1개이다.

| RF | 상태 | Demo 적용 |
|---|---|---|
| 001~005 및 002-1 | 완료 | 기존 통신 및 혼합 버스 재사용 |
| 006 | 예정 | Command/Feedback Routing: Orchestrator |
| 007 | 예정 | Mode Switching/Alignment: Orchestrator |
| 008 | 예정 | Omniverse 연계: Orchestrator ROS2 |
| 009 | 예정 | 기존 SDO 기반 Parameter Pairing |
| 010 | 완료 | Parameter Persistence 재사용 |
| 011 | 완료 | 다축 구성 재사용 |
| 012 | 진행 중 | Demo 배포 잔여 검증 |
| 013 | 보류 | 범위 재합의 후 신규 개발 |
| 014 | 완료 | Dynamic PDO Mapping 재사용 |
| 015 | 예정 | 직선축 동작 검증·보완 |
| 016~018 | 완료 | Profile Adapter, FMU, Fault 재사용 |
| 019~020 | 예정 | 후속 Parameter API 및 History |

## 4. 책임 분리 및 아키텍처

Orchestrator → Motion Server → 공통 EtherCAT Bus → 실제 장치 및 Soft ESC. Soft ESC 내부는 EtherCAT Slave Interface(C++/KickCAT)와 Python Functional Model로 구성한다. 상태는 가상 장치 → Motion Server → Orchestrator → ROS2 → Omniverse 경로로 전달한다.

- DT: 가상 장치에만 일반 지령 전달.

- Sync: 실제·가상 장치에 동일 논리 지령을 병렬 전달. 동일 주기 실행 또는 완전한 상태 일치를 보장하지 않는다.

- State Alignment: 실제 위치를 읽고 가상축 Servo On 및 일반 PP 이동, Loader IO 지령으로 정렬한다. 실제 Loader 양단 OFF 시 명시적 Alignment에서 실제 Loader 초기 복귀 예외를 허용한다(DT에서도 가능).

- Omniverse는 모든 모드에서 가상 상태만 추종하고 충돌 피드백을 Orchestrator에 전달한다.

- Soft ESC에 External Follow, 상태 덮어쓰기 API, 별도 ROS2 Bridge, 모드 라우터를 추가하지 않는다.

## 5. Priority 1 — RF-013 Virtual IO

[기존 RF-013](https://github.com/IlgonKo/ethercat-device-simulator/blob/main/Doc/RF/RF-013-virtual-io.md)은 보류 상태이며 사용자 재합의 후 착수한다.
Remote IO Device Profile과 Loader Behavior Model을 분리한다. EtherCAT Master 기준 DO → Valve → Cylinder Behavior → 양단 DI 생성으로 구현하며 DO를 DI에 단순 복사하지 않는다. 기존 C++ Slave/Python IPC 구조에서 비-CiA402 Device Profile 수용 방식을 검토한다.

**필수:** CPX Identity, 필요한 OD/SDO, DI/DO PDO, 모듈 구성, 밸브 및 실린더 모델, 양단 센서, 초기 상태, 이동 시간 설정, 오류 및 통신 경계 검증.
**제외 제안:** Analog IO, IO-Link, IODD/ISDU, 범용 센서 모델, 정밀 공압 물리 모델.
**미결정:** CPX-E-EC 또는 CPX-AP-I-EC 최종 형번, 모듈/채널 및 밸브 구성, 출력 해제 시 동작, 초기 상태 및 설정 스키마. 양단 OFF만으로 위치·방향을 확정하지 않는다. 별도 Loader 연속 위치 전송 인터페이스는 추가하지 않는다.

## 6. Priority 2 — RF-015 Axis Model Semantics

[RF-015](https://github.com/IlgonKo/ethercat-device-simulator/blob/main/Doc/RF/RF-015-axis-model-semantics.md)의 직선축 범위부터 검증한다. 기존 F-KR CMMT Behavior Model과 CiA402 Profile Adapter를 재사용하고 부족한 부분만 보완한다.

- PP, PV, Jog, Homing, Servo On/Off, Halt/Quick Stop, Target Reached, 정지 피드백

- S/W Limit 및 한계에서 허용 방향 이동, 파라미터 적용 효과

- X1/Y/Z 독립 3축; X2는 수동 Guide로 가상 Drive 불필요

- 회전축 Modulo/최단 경로, CSP, Blending, 축간 보간은 이번 범위 제외

최신 Motion Server의 실제 명령 및 SDO/PDO 사용 범위를 추출하여 기존 모델과 대조한다. 구현 누락 여부는 아직 확정하지 않았다.

## 7. Priority 3 — RF-012 Deployment

기존 11월 5일 Docker/native 및 2/4축 이동 부하 비교 결과를 재사용한다. Edge #2 Mini PC에서 설치 재현성, 가상 3축+IO 구성, 실제 3축+IO 혼합 버스, 재부팅 후 설정/파라미터 복원, 반복 운전 및 장애 복구를 확인한다. 동일 Edge Master 배치는 이번 Demo 우선순위에서 제외한다. 반복 운전 시간과 합격 기준은 별도 합의한다.

## 8. Parameter Pairing 및 통합 검증

PP Velocity/Acceleration/Deceleration, S/W Limit, RxPDO/TxPDO Mapping 및 Assignment의 실제↔가상 양방향 적용·읽기 검증. RF-010/014 재사용. 일반 SDO 적용과 EtherCAT 상태 전환 및 프로세스 이미지 갱신을 분리한다. 별도 RF-019/020 API는 필요하지 않다. 기존 Motion Server API의 지원 범위는 확인 필요.

## 9. 개발 순서 및 완료 기준

1. RF-013: IO 장치/밸브 확정, Profile/Behavior 설계, DI/DO 및 혼합 통신 시험.

2. RF-015: 최신 Motion Server와 PP/PV/Jog/Homing/Limit/Stop 회귀 검증 및 필요한 보완.

3. RF-012: Edge #2 배포, 3축+IO, 혼합 버스 및 복원 검증.

4. DT-demo: Parameter Pairing, State Alignment, Manual/Auto/Sync, Omniverse 통합 시험.

Auto는 최신 사양의 P1~P6 독립 PP 및 Dwell, PCB Loading/Unloading, Cycle Preparation, Repeat를 검증한다. 모든 대상의 도달·정지 및 필요한 센서 완료를 확인한다. 장애 후 자동 재개하지 않는다. Soft ESC는 Sequence 자체를 구현하지 않는다.

## 10. 다음 결정 및 문서 관리

RF-013의 비-CiA402 Profile 수용 구조와 실제 IO 하드웨어 확정을 우선 논의한다. RF-006~009 및 019~020은 기존 제품 장기 계획으로 유지하고 Demo 의존성만 분리한다. RF 상태 변경 및 구현 착수는 사용자 검토 후 진행한다.
