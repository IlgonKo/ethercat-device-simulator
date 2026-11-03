# RF-016 — CiA402 Drive 프로파일 및 F-KR CMMT 어댑터

- 현재 상태: **진행 중**
- 상태 상세: 구조 이관·모델 동등성·혼합 물리 운전 확인. 현 구조의 동일 조건 2축/4축 계측·이동 부하 회귀만 잔여 (2026-10-28).

## 현재 범위

EtherCAT Slave와 Functional Model을 분리하고 기능 모델을 CiA402 profile + 모델별 adapter + behaviour_model로 구성한다. 공통 실행부·IPC·저장소는 기능 모델 runtime에 둔다. 외부 Motion Server 모델 스냅샷 의존은 제거했다. BUS는 `cia402-drive`, 자체 모델은 `f_kr_cmmt`; EtherCAT identity/PDO는 CMMT-AS 호환이다.

## 완료 기준 및 근거

- [x] 폴더 이관, import·resource·빌드·Docker 경로 갱신.
- [x] 공통 OD·제조사 확장·PDO·identity 책임과 파일 분리.
- [x] 어댑터 계약·지원 기능 정의, 미등록 모델·미지원 조합 거부.
- [x] 상태 머신 중복 실행 없음, 축별 OD 소유권 확인.
- [x] 기본값·저장 파라미터·SDO 동등성: 기존 회귀 및 RF-010 물리 58개 readback.
- [x] 1축/4축 OD·PDO·상태 독립성과 기존 모드 회귀: linear/rotary × PP/PV/Homing/CSP/JOG의 800-cycle baseline 및 구성 시험.
- [x] 실제 축·IO + F-KR/Copley 혼합 물리 운전: 사용자 지속 운전 확인, RF-010/018 통신·Fault/Reset·장애 격리.
- [x] Docker 실행·사용자 문서 갱신.
- [ ] 현재 프로세스/어댑터 구조에서 동일 조건 2축/4축 계측 및 이동 부하 회귀 수치 확보.

## 실제 남은 항목

마지막 정량 성능 항목만 남는다. 기본 혼합 운전 성공 여부를 다시 시험하려는 것이 아니다. 2026-10-20 계측은 구조 이관 전 정지 상태 8ms/120초이고, 이관 후 오프라인 dispatch 계측은 IPC·네트워크를 제외했다. 현재 혼합 운전 성공 보고에는 동일 조건 2축/4축 처리 시간 비교가 포함되지 않는다.

RF-017 혼합 이동 성능 및 RF-012 Docker/native 비교와 조건을 맞추면 중복 시험을 줄일 수 있다. 기존 완료 기준을 삭제하지 않고 진행 중으로 유지한다. 30분 등 신규 시험 시간은 아직 확정하지 않았다.

## 근거와 범위 경계

- [구조 이관·baseline·오프라인 성능 기록](../Validation/RF-016/history-through-20261028.md).
- [RF-011](RF-011-device-configuration.md), [RF-010](RF-010-parameter-persistence.md), [RF-018](RF-018-diagnostic-fault.md).
- [DT-007](../Design/DT-007-cia402-profile-adapters.md), [소스 출처](../Design/RF-016-source-provenance.json).

FMU 연결은 RF-017, 동적 PDO·IO·모델 동작 변경은 RF-014/013/015다. 이번 정리는 새 코드 변경이나 물리 시험 기록이 아니다.
