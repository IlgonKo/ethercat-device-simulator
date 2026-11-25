# ADR-009 — 독립 Soft ESC 제품 범위와 외부 시스템 경계

- 결정일: 2026-11-25
- 결정 상태: **채택**
- 범위: 제품 책임과 확장 원칙. 구현 완료 판정을 의미하지 않는다.
- 관련: [ADR-001](ADR-001-system-architecture.md), [ADR-003](ADR-003-model-interface.md), [ADR-007](ADR-007-cia402-profile-adapters.md)
- 구현 현황·작업 순서: [프로젝트 계획](../project-plan.md), [RF 목록](../RF/README.md)

## 배경

DT Demo 요구를 반영하는 과정에서 외부 라우팅·Pairing·정렬·DT 통합 작업이 Soft ESC 구현 범위로 섞였다. 사용자는 DT와 독립적으로 FMU 또는 다른 형식의 동작 모델을 EtherCAT 가상장치로 제공하는 패키지를 요구했다. Drive와 Remote I/O를 함께 제품 범위로 정의하고 사용 사례와 제품 책임을 분리한다.

## 결정

1. Soft ESC는 FMU 또는 다른 형식의 동작 모델을 EtherCAT 장치 프로파일에 연결하는 독립 실행 패키지다. CiA402 Drive와 EtherCAT Modular Device Profile 기반 Remote I/O를 모두 제품 범위로 한다.
2. 장치 프로파일·제품별 Identity/ESI·모듈 설명·모델 어댑터·동작 모델을 분리한다. 지원 범위는 계약과 검증으로 명시하며 제품 범위 선언을 모든 모델/모듈의 구현·적합성 완료로 해석하지 않는다.
3. DT Demo·Motion Server·Orchestrator·ROS2/Omniverse를 실행 의존성으로 요구하지 않는다. 모드 라우팅·실제/가상 Pairing·실장비 제어·정렬 절차·Sequence·DT 연결은 외부 책임이다.
4. Soft ESC는 일반 EtherCAT 명령·SDO/PDO·장치 피드백을 제공한다. 외부 정렬을 위한 내부 상태 덮어쓰기·External Follow·별도 정렬 API를 추가하지 않는다.
5. 3축·Loader·Edge #2는 사용·검증 사례다. 제품 최대 축 수, Remote I/O 동작 모델, 배포 호스트를 이 사례에 고정하지 않는다.
6. 기존 완료 검증은 유지하고 확장 영향만 회귀한다. 모델/모듈별 지원 기능과 시험 조건을 기록하며 기존 축 결과를 IO 지원·실시간성 보장으로 확대하지 않는다.

장치당 논리 OD 하나, Slave의 매핑 소유/저장, 기능 모델의 동작 파라미터 저장 및 매핑 절차를 넣지 않는 모델 IPC 원칙은 기존 결정을 유지한다. IO에 CiA402 전용 필수 객체·축 Fault 표현을 강제하지 않는다.

## 선택 이유와 제외한 대안

Demo 전용 패키지는 다른 Master·모델·장치 구성에서 재사용하기 어렵고 외부 제어 정책에 의존한다. CiA402 전용 제품 정의는 합의한 Remote I/O 지원 범위를 담지 못한다. 단순 DO/DI 바이트 연결만으로는 모듈형 장치 계약과 동작 모델의 책임이 드러나지 않는다. 독립 프로파일·어댑터 구조로 이 경계를 유지한다.

## 영향

- 제품 구성은 자체 .env와 저장소를 유지하고 외부 서버 설정을 읽지 않는다.
- Remote I/O 구현은 프로파일별 구성·매핑 검증·진단/입출력 유효성 및 모델 연결을 포함한다. 세부 모듈/채널·로더 계약은 구현 전에 확정한다.
- RF-006~009의 외부 구상은 참고 이력으로 분리한다. RF-013/015/012와 기존 기반의 실제 작업·진행 상태는 RF 및 프로젝트 계획에서 관리한다.
- 확정된 결정 변경은 ADR의 근거와 상태에 반영하고, 작업 진척만으로 결정 상태를 변경하지 않는다.

## 입력 자료와 문서 분리

[DT Demo 분석 자료](../DT-demo-gap-analysis.md)와 [시스템 사양](https://github.com/IlgonKo/DT-demo/blob/main/docs/specifications/DT_Demo_System_Specification.md)은 사용 사례 입력이다. 외부 시스템 전체 계획을 이 패키지의 완료 기준으로 가져오지 않는다.

기존 로드맵 문서의 구현 현황 표·구조 변경 작업·사용 사례 표·작업 순서·미결정 사항은 [project-plan.md](../project-plan.md)로 이동했다. 작업별 완료 기준과 검증은 RF에 유지한다.
