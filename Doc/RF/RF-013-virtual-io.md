# RF-013 — EtherCAT Modular Device Profile 기반 Remote I/O

- 현재 상태: **진행 중**
- 상태 상세: 2026-11-25 독립 Soft ESC 제품 범위로 확정. 모듈형 Remote I/O·어댑터·Digital IO 동작 모델 설계/구현 대상이며 구현·물리 검증은 미완료.
- 등록일: 2026-09-22
- 설계: [ADR-001](../Design/ADR-001-system-architecture.md), [프로젝트 계획](../project-plan.md), [ADR-005](../Design/ADR-005-device-configuration.md)

## 제품 범위와 이번 구현

EtherCAT Modular Device Profile 기반 Remote I/O를 CiA402 Drive와 함께 독립 제품 범위로 지원한다. 이번 구현은 선정 장치의 모듈 구성과 Digital IO를 제공하고, 모델별 어댑터로 동작 모델에 연결한다. 단순 DI/DO 바이트 교환만으로 Modular Device Profile 지원을 완료했다고 표시하지 않는다.

- 공통 모듈형 프로파일: 장치/모듈 구성·식별·지원 객체·프로세스 데이터 계약.
- 제품별 장치 설명: 실제 Identity·ESI·모듈 정의·제조사 확장·초기화 요구.
- 어댑터: 모듈/채널과 선택한 동작 모델 입출력·단위·실행 의미 연결.
- 동작 모델: 자체 모델/FMU/기타 형식으로 연결 대상 동작 계산. 현재 모든 형식의 범용 로더를 구현했다는 의미는 아님.

DT Demo의 Loader는 밸브/실린더 동작 모델의 검증 사례다. DO → 동작 모델 → DI 경로로 끝단 센서를 생성하며 DO echo로 대체하지 않는다. Loader·Orchestrator·Omniverse를 Remote I/O 프로파일의 실행 의존성으로 넣지 않는다. 연속 Loader 위치용 외부 통신은 이번 범위에서 추가하지 않는다.

## 기존 기반과 변경 지점

현재 설정/Host는 축 전용이다. CiA402 필수 Controlword/Statusword, AxisFault 투영과 공통 전송·검증을 분리한다. Remote I/O를 CiA402 하위 축으로 취급하지 않는다.

장치당 논리 OD 하나를 유지한다. PDO mapping/assignment·저장은 Slave, 동작 파라미터는 기능 모델 소유다. 모델 IPC에 매핑 절차를 추가하지 않는다. 기존 RF-014 축 계약은 유지하고 선정 IO의 매핑/모듈 요구와 충돌하는 규칙은 명시적으로 설계한다.

자체 .env에 모듈/슬롯/채널 및 모델 연결 구성을 추가한다. 실제 변수명과 저장 스키마는 설계 후 확정한다. Motion Server .env를 읽거나 Demo 전용 구성을 코드에 고정하지 않는다.

## 구현 전 확정 사항

1. 선정 CPX 형번·ESI와 지원 모듈/슬롯/채널, 모듈 식별·OD/SDO·PDO 구성 및 오류 응답 계약.
2. 모델 입출력 연결: 밸브 DO 수·극성·출력 OFF·동시 명령 의미, 초기 상태·이동 시간·DI 표현.
3. PRE-OP/버스 단절/모델 장애의 출력·입력 유효성·진단·복구. 버스 단절이 자동 DO 해제를 보장한다고 가정하지 않는다.
4. IO 파라미터 저장 대상·재시작 상태와 기존 저장 기반의 재사용 범위. 운전 상태의 자동 복원을 가정하지 않는다.

## 완료 기준

- [ ] 선정 장치의 MDP·모듈 식별/구성·초기화 OD·PDO 요구와 지원 범위 표.
- [ ] 자체 .env 장치/모듈/채널/모델 구성 및 오류 검증. 미지원 모듈·잘못된 순서/채널 거부.
- [ ] 프로파일/제품 설명과 어댑터/동작 모델 분리, 모듈·채널 독립성 검증.
- [ ] 합의한 Digital IO 및 Loader 동작 모델 연결, OFF/충돌·중간/양단·시간·오류 동작 검증.
- [ ] EtherCAT 검색·SDO·OP·PDO 및 모듈별 데이터 배치 검증. 명시한 MDP 범위에 대해 근거 기록.
- [ ] Host 장애 시 Slave 유지 기반과 IO 진단/입력 유효성/복구 정책 검증. 기존 축 Fault 투영을 대신 적용하지 않음.
- [ ] Drive+IO 혼합 구성·저장/재시작·기존 F-KR/Copley/동적 매핑 회귀. 3축+IO는 Demo에서 가져온 시험 사례.
- [ ] 외부 Master의 일반 IO 명령으로 모델 동작·DI 리드백 확인. 외부 Alignment/Sequence 자체는 제외.

## 제외·후속 및 근거

Analog, IO-Link, IODD/ISDU, 범용 센서 라이브러리, 정밀 공압·압력/부하 계산은 이번 구현에 포함하지 않는다. Modular Device Profile 전체 및 모든 CPX 모듈의 적합성을 선언하지 않고 구현한 범위를 명시한다.

RF-005의 실제 CPX 통신 및 RF-011/014/018의 축 검증은 기반 근거이며 가상 Remote I/O 구현 완료를 대신하지 않는다. 해당 RF 완료 상태는 유지한다. 외부 DT/Sync·Pairing·ROS2·Omniverse 구현은 이 RF의 범위가 아니다.
