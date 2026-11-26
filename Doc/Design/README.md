# 아키텍처 결정 기록 (ADR)

Soft ESC의 제품·구조·인터페이스·운영 경계에 대한 결정과 근거를 기록한다. ADR은 Architecture Decision Record의 약자다. 기존 Digital Twin 유래 접두어를 ADR로 통일하고 `Doc/Design` 위치는 유지한다. DT Demo라는 사용 사례 명칭과 분석 자료 이름은 변경하지 않는다.

## 문서별 역할

| 문서 | 관리하는 내용 |
| --- | --- |
| ADR | 채택한 결정·배경·이유·책임 경계·영향 |
| [프로젝트 계획](../project-plan.md) | 구현 현황·작업 순서·미결정 항목·시험 구성 |
| [RF](../RF/README.md) | 기능 요구·작업 범위·완료 기준·상태 및 검증 근거 |
| [검증 기록](../Validation/) | 시험 조건·관측 결과·한계 |
| [작업 일지](../Work_log.md) | 날짜별 작업·결정 변경 이력 |

## 결정 목록

결정 상태의 **채택**은 해당 방향에 합의했다는 뜻이다. 구현 완료를 의미하지 않는다. 본문의 명시적 보류·과거 제안은 현행 결정과 구분하고, 실제 진행 상태는 연결된 RF에서 확인한다.

| 번호 | 결정 주제 | 결정 상태 |
| --- | --- | --- |
| [ADR-001](ADR-001-system-architecture.md) | Soft ESC 제품 정의와 소프트웨어 구조 | 채택 |
| [ADR-002](ADR-002-mode-switching.md) | 외부 상태 정렬에 대한 Soft ESC 지원 경계 | 채택 |
| [ADR-003](ADR-003-model-interface.md) | 동작 모델 연결과 실행 경계 | 채택 |
| [ADR-004](ADR-004-parameter-sync-persistence.md) | Soft ESC 장치 파라미터와 매핑 저장 | 채택 |
| [ADR-005](ADR-005-device-configuration.md) | .env 장치 구성과 혼합 버스 번호 매핑 | 채택 |
| [ADR-006](ADR-006-docker-deployment.md) | Linux Edge PC의 Docker 배포 | 채택 |
| [ADR-007](ADR-007-cia402-profile-adapters.md) | 장치 프로파일과 동작 모델 어댑터 구조 | 채택 |
| [ADR-008](ADR-008-diagnostic-fault.md) | Diagnostic 및 Fault 처리 | 채택 |
| [ADR-009](ADR-009-product-scope-and-boundaries.md) | 독립 Soft ESC 제품 범위와 외부 시스템 경계 | 채택 |

## 작성·변경 원칙

- 파일명은 `ADR-NNN-topic.md`, 문서 제목은 같은 번호를 사용한다.
- 결정 상태와 구현 상태를 분리한다. 신규/변경 결정은 배경·결정·이유·영향 및 관련 RF를 기록한다.
- 작업 진척은 프로젝트 계획/RF에 갱신한다. ADR에 별도 실행 순서나 완료 체크리스트를 중복 관리하지 않는다.
- 기존 결정을 대체하면 무엇이 바뀌었는지와 대체 문서를 명시한다. 검증 결과를 소급 변경하지 않는다.
- ADR-009는 독립 제품 범위·외부 책임 경계 결정이다. 이전 문서의 상세 로드맵은 프로젝트 계획으로 이동했다.

- [ADR-010 — 프로젝트 폴더 구조와 생성물 보관](ADR-010-project-layout.md)
