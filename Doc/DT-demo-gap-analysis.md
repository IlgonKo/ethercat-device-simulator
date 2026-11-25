# Soft ESC — DT Demo Gap Analysis & Development Roadmap

**기준일:** 2026-11-25 · **버전:** 0.5 (공압 실린더 FMU 재사용·Linux 오프라인 검증 반영)

> 범위 정정: 이 문서는 Demo 전체 맥락을 담은 입력 분석 자료다. 외부 Orchestrator·Pairing·Alignment·전체 통합 관련 단계는 Soft ESC의 구현 목록이나 완료 조건이 아니다. 이 저장소의 실제 구현 범위와 순서는 [프로젝트 계획](project-plan.md)를 따른다.

## 1. 목적 및 분석 근거

Fieldbus-level Digital Twin Demo 구현을 위해 기존 Soft ESC의 개발 상태와 최신 DT Demo 요구사항을 비교하고 최소 추가 개발 범위를 정의한다.

- [Soft ESC Repository](https://github.com/IlgonKo/ethercat-device-simulator)

- [RF 현황](https://github.com/IlgonKo/ethercat-device-simulator/blob/main/Doc/RF/README.md)

- [DT Demo 시스템 사양서 v1.1, 2026-11-23](https://github.com/IlgonKo/DT-demo/blob/main/docs/specifications/DT_Demo_System_Specification.md)

- [Motion Server](https://github.com/IlgonKo/motion-server)

분석은 RF 문서와 저장소 구조 및 시스템 사양서 기준이다. Motion Server 최신 변경 코드와 Soft ESC 함수·테스트의 전수 대조는 후속 작업이며 실제 장비 시험은 수행하지 않았다.

## 2. 요약

제품은 CiA402 Drive와 EtherCAT Modular Device Profile 기반 Remote I/O를 지원 대상으로 하는 독립 Soft ESC다. 신규 개발은 모듈형 Remote I/O와 어댑터/동작 모델 연결(RF-013)이며 Loader는 그 사용 사례다. 기존 가상축 모델의 보완(RF-015), Docker 배포(RF-012), Parameter Pairing 및 시스템 통합 검증을 추가한다. 기존 RF-006~009의 정책 및 외부 연동은 최신 Demo 사양에 따라 Orchestrator가 담당한다.

## 3. RF 현황

총 21개(RF-002-1 포함) 중 제품 범위는 17개(완료 12, 진행 중 3, 예정 2)다. RF-006~009 4개는 외부 구상 참고 이력으로 구분한다.

| RF | 상태 | Demo 적용 |
|---|---|---|
| 001~005 및 002-1 | 완료 | 기존 통신 및 혼합 버스 재사용 |
| 006 | 범위 외 | Command/Feedback Routing: Orchestrator |
| 007 | 범위 외 | Mode Switching/Alignment: Orchestrator |
| 008 | 범위 외 | Omniverse 연계: Orchestrator ROS2 |
| 009 | 범위 외 | 기존 SDO 기반 Parameter Pairing |
| 010 | 완료 | Parameter Persistence 재사용 |
| 011 | 완료 | 다축 구성 재사용 |
| 012 | 진행 중 | Demo 배포 잔여 검증 |
| 013 | 진행 중 | CPX-AP-I MDP·DI/DO/AI/AO·모델 연결; Loader는 디지털 검증 사례 |
| 014 | 완료 | Dynamic PDO Mapping 재사용 |
| 015 | 진행 중 | 직선축 대조·검증 준비; 회전 확장은 보류 |
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

[기존 RF-013](https://github.com/IlgonKo/ethercat-device-simulator/blob/main/Doc/RF/RF-013-virtual-io.md)은 2026-11-25 사용자 결정으로 CPX-AP-I의 DI/DO/AI/AO를 1차 구현 범위로 확정했다. IO-Link는 제외한다. 세부 모듈/채널·아날로그 표현·동작 계약은 구현 전에 확정한다.
Remote IO Device Profile과 Loader Behavior Model을 분리한다. EtherCAT Master 기준 DO → Valve → Cylinder Behavior → 양단 DI 생성으로 구현하며 DO를 DI에 단순 복사하지 않는다. 기존 C++ Slave/Python IPC 구조에서 비-CiA402 Device Profile 수용 방식을 검토한다.

**필수:** CPX-AP-I Identity, 필요한 OD/SDO, DI/DO/AI/AO PDO, 모듈 구성, 모델 입출력·아날로그 변환/범위 검증. Loader 사례는 밸브·실린더·양단 센서·초기 상태·이동 시간 및 오류 경계를 확인한다.
**이번 범위 제외:** IO-Link, IODD/ISDU, 범용 센서 모델, 정밀 공압 물리 모델.
**확정:** 기본 모듈은 DI8/DO8/AIO4:4, AI/AO는 signed 16-bit raw 표현, 모델은 인스턴스별 생성·채널별 연결. 모델/binding 문법은 ADR-005의 BEHAVIOUR_MODELS/BINDINGS로 채택했다. 실린더는 공개 Modelica 부품으로 만든 FMI 3.0 FMU를 재사용하며 Linux 오프라인 5개 시험을 통과했다. 두 입력 OFF는 밸브 방향 유지이고 이전 단순 모델의 OFF 정지/일정 속도 계약을 대체한다. IO 어댑터·채널 연결은 아직 미구현이다. **미결정:** 아날로그 시험 모델 계약, 물리량 변환·정상 범위, FMU 등록·파라미터 설정/저장, 상충 입력 및 IO 장애/복구 정책. 최신 결정은 ADR-005/007과 RF-013을 따른다. 양단 OFF만으로 위치·방향을 확정하지 않는다. 별도 Loader 연속 위치 전송 인터페이스는 추가하지 않는다.

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

## 9. Demo 분석 당시 작업 흐름 — Soft ESC 완료 기준과 구분

1. 최신 Motion Server 명령/API·OD/PDO·IO 모듈 지원 대조표 작성.
2. RF-013: IO 장치/밸브·채널·초기/이동/장애 정책 및 Profile/동작 모델 계약 확정.
3. RF-013: DI/DO/AI/AO·모델 연결 및 혼합 통신 시험. Loader는 디지털 사례로 사용.
4. RF-015: 직선축 PP/PV/Jog/Homing/Limit/Stop 회귀 및 확인된 부족분 보완.
5. Parameter Pairing 및 일반 PP/IO 기반 State Alignment 검증.
6. RF-012/DT-demo: Edge #2, 가상 3축+IO 배포·복원 및 Manual/Auto/Sync·Omniverse 통합.

Auto는 최신 사양의 P1~P6 독립 PP 및 Dwell, PCB Loading/Unloading, Cycle Preparation, Repeat를 검증한다. 모든 대상의 도달·정지 및 필요한 센서 완료를 확인한다. 장애 후 자동 재개하지 않는다. Soft ESC는 Sequence 자체를 구현하지 않는다.

## 10. 다음 결정 및 문서 관리

RF-013의 비-CiA402 Profile 수용 구조와 실제 IO 하드웨어 확정을 우선 논의한다. RF-006~009는 외부 구상 이력으로 분리하고 RF-019/020은 후속 제품 기능으로 유지한다. 2026-11-25 사용자 동의에 따라 RF-013/015의 범위를 제한하여 진행 중으로 갱신했다. 이번 작업은 문서 정리이며 런타임·코드 변경 또는 물리 시험을 수행하지 않았다. 상세 책임·산출물은 [프로젝트 계획](project-plan.md)를 따른다.
