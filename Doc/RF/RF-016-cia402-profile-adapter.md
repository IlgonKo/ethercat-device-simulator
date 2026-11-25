# RF-016 — CiA402 Drive 프로파일 및 F-KR CMMT 어댑터

- 현재 상태: **완료**
- 상태 상세: 구조 이관·동등성·혼합 운전 및 2026-11-05 현재 구조의 동일 조건 2축/4축 정지·PP 계측 완료. 합의 범위 잔여 없음.
- 완료일: 2026-11-05

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
- [x] 현재 프로세스/어댑터 구조에서 동일 조건 2축/4축 계측 및 이동 부하 회귀 수치 확보.

## 현재 완료 판정

2026-11-05 F-KR/Copley 혼합 2축/4축, 정지/PP, Docker/native를 동일 4ms 설정에서 각각 두 번 비교했다. 총120,307 PDO 교환의 WKC 불일치0, Fault0, PP224편도 완료. 현재 구조의 비교 수치를 확보하여 마지막 항목을 완료한다. [보고서](../Validation/RF-016/runtime-comparison-20261105/README.md).

이는 실제 RT 주기 보장이나 임의 최대 축수 성능 인증이 아니다. Python/컴파일러 차이를 포함한 현재 배포 방식 비교이며 비RT Master 지터 추가 원인 조사는 하지 않았다. 아래 2026-11-03 기록의 “2축 비교 미검증”은 이번 결과로 해소됐다.

## 근거와 범위 경계

- [구조 이관·baseline·오프라인 성능 기록](../Validation/RF-016/history-through-20261028.md).
- [RF-011](RF-011-device-configuration.md), [RF-010](RF-010-parameter-persistence.md), [RF-018](RF-018-diagnostic-fault.md).
- [ADR-007](../Design/ADR-007-cia402-profile-adapters.md), [소스 출처](../Design/RF-016-source-provenance.json).

FMU 연결은 RF-017, 동적 PDO·IO·모델 동작 변경은 RF-014/013/015다. 이번 정리는 새 코드 변경이나 물리 시험 기록이 아니다.

## 2026-11-03 혼합 4축 이동 계측 반영

[RF-017 계측](../Validation/RF-017/mixed-endurance-20261103.md)에서 4ms 설정/600.912초·271왕복, WKC 조회 정상·Fault 없음 및 처리 시간을 확보했다. 이동 부하 근거는 확보됐으며 동일 조건 2축 비교가 남는다. rx_gap 최대 21.998ms·8ms 초과 10회의 원인은 이번 자료로 분리할 수 없다. 엄격한 4ms 준수로 판정하지 않고 후속 비교 시 송신/수신 지터를 구분한다.

## 2026-11-03 양단 캡처로 지터 범위 확인

[동시 캡처 보고서](../Validation/RF-016/jitter-capture-20261103.md): 이동 중 같은 프레임의 Windows TX 간격 11.311ms / Linux 커널 도착 간격 11.320ms. 긴 간격은 Windows 송신 캡처 단계에 이미 존재했다. 준비/복원 포함 최대는 약19ms이며 본 이동과 구분한다. 과거22ms 사건의 원인을 소급 확정한 것은 아니다. 사용자 결정에 따라 비RT Motion Server 환경의 추가 지터 원인 조사는 진행하지 않는다. 동일 조건 2축/4축 비교는 별도 미검증 항목으로 남긴다.
