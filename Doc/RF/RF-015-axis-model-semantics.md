# RF-015 — 직선축 동작 및 위치 제한 검증

- 현재 상태: **진행 중**
- 상태 상세: 2026-11-25 사용자 동의로 직선축 Demo 대조·검증만 재개. 2026-11-05 보류 중 회전 확장 범위는 계속 보류한다. 신규 구현·시험 완료를 의미하지 않는다.
- 등록일: 2026-09-22
- 관련: [프로젝트 계획](../project-plan.md), [RF-011](RF-011-device-configuration.md)

## 이번 범위

CiA402 Drive에 연결된 F-KR CMMT의 직선축 기능을 대조한다. DT Demo의 X1/Y/Z는 3축 시험 사례이고 제품 최대 축 수나 전용 장치 이름이 아니다. 최신 Motion Server 명령과 모델 지원 동작을 먼저 대조하고 차이가 확인된 부분만 수정한다. Copley 초기 PP 지원 결과로 F-KR의 PV/Jog/Stop 동작까지 검증됐다고 간주하지 않는다.

- PP 이동·완료, Profile Velocity/Acceleration/Deceleration, 소프트웨어 위치 제한과 단위.
- PV/Jog 및 모드 전환, Stop/Quick Stop/Halt에 실제 서버가 보내는 명령의 의미.
- Servo On·Fault Reset·Homing 표시, 정지 중 목표값과 이전 명령의 재실행 여부.
- 일반 Servo On+PP로 지정 목표 위치에 도달하고 피드백을 반환하는 장치 동작. 외부 Alignment 절차는 구현하지 않는다.

Pendant의 PV 거리 기반 감속·한계 접근 정책은 Orchestrator 책임이다. 장치의 제한 처리와 구분하며 동작 모델에 상위 정책을 중복 구현하지 않는다.

## 기존 관찰과 검증 필요성

181° 목표 거부는 당시 0x607D 상한 +180°의 결과이며 고정 모델 한계가 아니다. 모델은 OD 단위·스케일을 사용한다. 과거 PP/CSP 목표 검사, PV/Jog 제한 차이 관찰은 이력이며 최신 구현 대조 전 현재 결함으로 확정하지 않는다.

## 완료 기준

- [ ] 최신 서버 명령/API·OD/PDO·지원 모드 대조표와 실제 부족분 확정.
- [ ] 합의한 직선축 모드별 위치 제한·정지·단위·파라미터 정책 기록.
- [ ] 3축 독립 PP·PV/Jog·정지·Fault Reset·방향/모드 전환 및 경계값 회귀.
- [ ] 지원 SDO 파라미터 적용·readback 및 일반 PP로 지정 위치 이동 검증. 외부 Pairing/Alignment 구현은 제외.
- [ ] 기존 저장 파라미터·RF-014 매핑·RF-018 장애 처리 회귀.

## 제외·후속

회전축 modulo·연속 회전·최단 경로, CSP 확장, blending·보간은 이번 Demo 범위가 아니다. P1~P6는 Orchestrator가 독립 PP와 dwell로 구성한다. 현행 동작을 실제 CMMT 전체 사양 준수로 확대하지 않는다.
