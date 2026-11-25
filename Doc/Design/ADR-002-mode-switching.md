# ADR-002 — 외부 상태 정렬에 대한 Soft ESC 지원 경계

- 결정 상태: **채택** (현행 범위 기준; 본문의 보류·과거 제안은 구분)
- 갱신일: 2026-11-25
- 구현 상태: Soft ESC 구현 경계 정리. 외부 모드 전환/Alignment 구현 문서가 아님.
- 관련: [프로젝트 계획](../project-plan.md), [RF-015](../RF/RF-015-axis-model-semantics.md), [RF-013](../RF/RF-013-virtual-io.md)

## 입력 조건

DT Demo에서는 외부 제어기가 일반 Servo On+PP와 IO 명령으로 가상장치를 원하는 상태로 이동시킨다. Soft ESC는 외부 모드나 실제 장치 상태를 직접 읽지 않는다.

## Soft ESC 지원 요구

- 축: 일반 Enable·PP 목표/프로파일 적용, 실제 위치·속도·도달/정지·Fault 피드백 제공.
- IO: 정상 DO 적용 후 Loader 동작을 계산하고 양단 DI 제공. 채널·시간·OFF/오류 정책은 RF-013에서 확정.
- 파라미터: 지원 SDO 읽기/쓰기·readback·저장, PRE-OP PDO 재설정과 오류 응답 제공.
- 장애: 기존 RF-018 축 Reset 및 수동 Docker 복구 경계 유지. IO 진단은 별도 정의.

정렬을 이유로 모델 위치·센서·Statusword를 직접 덮어쓰거나 스냅샷 복원/External Follow API를 추가하지 않는다. 정렬 성공 판정·허용오차·실장비 복귀·상위 상태 전이·명령 재전송 정책은 외부 책임이다.

## 검증 경계

일반 명령만으로 가상축 이동/정지와 Loader DI 변화가 가능하고 올바른 피드백을 반환하는지 검증한다. Orchestrator의 전환/정렬 기능이나 실제 Loader 제어를 Soft ESC 완료 조건에 포함하지 않는다. 과거 내부 상태 초기화 관리 API 초안은 이번 구현 범위에서 제외한다.
