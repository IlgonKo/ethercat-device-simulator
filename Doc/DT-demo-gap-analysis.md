# Soft ESC — DT Demo 요구 대조 및 남은 작업

- 기준일: **2026-11-26**
- 범위: Soft ESC 제품 기능·배포 준비만 다룬다. 전체 Demo 구현 계획은 외부 프로젝트 책임이다.
- 입력: [DT Demo 시스템 사양서](https://github.com/IlgonKo/DT-demo/blob/main/docs/specifications/DT_Demo_System_Specification.md), [Working Agreements](https://github.com/IlgonKo/DT-demo/blob/main/docs/agreements/DT_Demo_Working_Agreements.md)의 DT/Sync·X1/Y/Z·Loader·Edge #2 요구.
- 현행 상태: [RF 목록](RF/README.md), 우선순위: [프로젝트 계획](project-plan.md).

## 요구 대비 현재 기능

| Demo 요구 | Soft ESC 근거 | 남은 작업 |
| --- | --- | --- |
| X1/Y/Z 3직선축 | RF-015 정책·3축 물리 운전 완료, RF-022 F-KR 직선/회전 FMU 전환 완료 | 최종 장치 이름·버스 번호·단위·한계/프로파일 설정을 배포 구성으로 확정 |
| PP/PV/Jog/Homing/정지·Reset | F-KR 구현·자동 경계 시험·물리 통합 완료 | 기존 근거 재사용. 외부 API/Sequence 연계는 해당 프로젝트에서 확인 |
| Loader DO/DI | RF-013 CPX·실린더 FMU·채널 연결·혼합 동작·복구 완료 | 실제 Demo 모듈/채널 binding·스트로크·공급압/초기 조건 확정 |
| AI/AO | RF-013 signed Int16·아날로그 지연 FMU 자동 시험 완료 | 수동/물리 FMU 왕복은 사용자 결정으로 생략. Demo 필수 조건으로 추가하지 않음 |
| Parameter Pairing 지원 | RF-010 영구 저장, RF-014 PRE-OP 축 매핑 재설정·복원 완료 | 외부 Orchestrator/Motion Server가 비교·복사·Master 재구성 수행 |
| State Alignment 지원 | 일반 PP·IO 명령/피드백 제공 | 외부에서 정렬 순서/허용조건을 결정. 모델 상태 덮어쓰기 API 불필요 |
| 혼합 버스·모델 장애 | RF-005/018 및 RF-013/022 회귀 완료 | 최종 배포 환경의 변경 영향만 확인 |
| Edge #2 독립 실행 | RF-012 다단계 Docker 빌드·배포 도구·현재 벤치 검증 완료 | 실제 새 PC/OS 배포·재부팅 복원·최종 3축+IO 구성 확인 |

RF-015·022는 완료다. 세부 한계/중복 요청/Fault 중 취소는 자동 시험 근거로 인정하며 물리 전수 반복을 추가하지 않는다. RF-022의 WKC 정상 관측은 RT 보증이나 모든 프레임 무손실 보증이 아니다.

## v1.0 이후 작업 경계

현재 기능을 Soft ESC v1.0.0으로 릴리즈한다. DT Demo 완료 전에는 버그/기구현 기능 미비점의 TD 보완만 진행하고 신규 RF 구현은 중단한다. [릴리즈 기록](Releases/v1.0.0.md), [ADR-011](Design/ADR-011-v1-maintenance-policy.md)을 따른다.

- RF-012: 최종 Demo 설정·새 Edge 배포 검증은 Demo 사양 장비 설정 때 함께 수행한다.
- RF-021: DT Demo 이후 진행한다. 현재 실린더 FMU로 Demo를 진행한다.
- RF-019/020: v1.0/DT Demo 범위 외. 장기 구상으로 보존하되 지금 구현하지 않는다.
- 기존 F-KR/Copley/IO 지원 계약을 확대하지 않는다. 외부 통합에서 확인된 기존 기능 결함만 TD로 보완한다.

## 외부 프로젝트에 남는 항목

DT 모드의 가상 대상 선택, Sync의 실제/가상 동일 논리 지령, Pairing·State Alignment·Sequence·ROS2/Omniverse 표시는 Orchestrator 등 외부 구현이다. 가상 동작은 Soft ESC 측 모델이 계산하고 Omniverse는 가상 상태를 추종한다. 같은 명령을 보낸다는 것이 주기 동시성/상태 완전 일치를 보장하지 않는다.

Loader Timeout·상충 명령·인터록은 상위 애플리케이션 책임이다. 모델 실행 오류는 내부 진단에 유지하고 CPX 자체 장치 오류로 변환하지 않는다. 별도 ROS2 Bridge/External Follow/상태 덮어쓰기 기능은 Soft ESC에 추가하지 않는다.

이 문서는 2026-11-25 분석의 RF-013 미구현·RF-015 진행 중 표현을 현재 검증 결과로 대체한다. 실제 Demo 전체 통합 완료나 새 PC 배포 완료를 선언하지 않는다.
