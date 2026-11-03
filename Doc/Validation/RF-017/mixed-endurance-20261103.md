# RF-017 — 혼합 가상 4축 10분 반복 이동 (2026-11-03)

- 문서 유형: **검증 기록**
- 관련: [RF-017](../../RF/RF-017-copley-fmu.md), [RF-016](../../RF/RF-016-cia402-profile-adapter.md)
- 판정: 현재 구성의 10분 반복 운전 성공. 주기별 4ms 보장이나 최대 부하 인증은 아님.

## 구성·방법

Windows Motion Server basic/PP, 설정 주기 4ms. 실제 축·IO + F-KR 2축/Copley 2축 혼합 버스, 총 6 Slave/5 Axis. Master Axis 1~4(가상축)에만 명령을 보냈다. 각 축 속도 10mm/s, F-KR 가감속 1000mm/s², Copley 동일 가감속 500mm/s². 가상 4축에 다축 move_rel API로 함께 명령하여 0↔10mm를 반복했다. 동시 시작의 sub-cycle 동기성/DC 동기 구동을 검증한 것은 아니다.

각 이동은 전 가상축의 위치 오차 ≤0.002mm·속도 ≤0.01을 연속 2회 확인한 뒤 다음 명령을 보냈다. 요청 사이 약 50ms 대기하며 axes/status와 bus/status를 순서대로 조회했다. 두 조회는 하나의 원자적 표본이 아니며 전 EtherCAT 프레임을 캡처하지 않았다.

## 준비 단계에서 확인한 사항

첫 시도에서 F-KR 두 축이 unreferenced 상태여서 PP setpoint handshake가 실패했다. Copley 두 축에는 이동이 일부 적용됐으며 실패 처리 후 Disable·설정 복원·조작권 반환했다. API 실패가 다축 명령의 원자적 취소를 뜻하지 않음을 관측했다. 이후 F-KR 가상축에만 home을 수행하고 PP 복귀·referenced를 확인한 뒤 모든 가상축을 0으로 맞췄다. 이 준비 단계는 본 10분 성공 집계에서 제외한다. 실제 축에 Home/이동/Reset/Enable 명령을 보내지 않았다.

## 반복 이동 결과

- 실제 반복 구간: 600.912초, 542회 편도 = 271회 왕복. 전 이동 목표 도달 확인.
- 본 구간 상태 조회: 11385회. WKC 불일치 0회, Fault 표본 0회. 모두 WKC 18/18.
- 최종 집계 카운터 11,387회에는 종료 복원 후 조회 1회도 포함된다. samples.jsonl에는 준비 단계 표본도 있어 start/duration으로 분리한다.
- 실제 축 피드백 위치 변동 최대 약 0.001mm. 실제 축에 시험 명령을 보내지 않았으며 이 변동을 가상축 간섭으로 확정하지 않는다.
- C++ 집계에서 IPC 실패 0. Python 4축 cycle_request 합계 599,915회.

## 처리 시간 (ms)

Docker 로그의 약 1초 집계 창 600개를 가중 평균했다. 선택 시작/종료 경계에 걸친 창을 포함하므로 C++ elapsed span은 601.167초로 정확한 이동 구간과 약간 다르다. C++/Python 창도 서로 정렬되어 있지 않다. 양쪽 최대값을 더해 단일 최악 cycle로 표현하지 않는다.

| 항목 | 평균 | 최대 |
| --- | --- | --- |
| 프레임 수신 후 응답까지 | 0.010532 | 0.133412 |
| 프레임 처리 전체 | 0.020407 | 0.160152 |
| 수신 프레임 간격 | 4.007649 | 21.998029 |
| 로컬 축 0 모델 계산 | 0.023230 | 0.099264 |
| 로컬 축 1 모델 계산 | 0.021065 | 0.209970 |
| 로컬 축 2 모델 계산 | 0.071956 | 0.301950 |
| 로컬 축 3 모델 계산 | 0.065762 | 0.217826 |

비동기 IPC 응답 수거까지는 축별 평균 약 3.99ms, 최대 약 10.08ms였다. submit부터 다음 pump에서 응답을 수거할 때까지이며 소켓 대기/스케줄링을 포함한다. 순수 FMU 계산 시간이 아니다.

수신 간격 rx_gap은 최대 21.998ms, 8ms 초과 10회였다. WKC 상태 조회와 운전은 정상이어도 모든 프레임이 4ms 간격이었다는 의미는 아니다. Master 송신 지터·OS 스케줄링·네트워크·수신 측 관측 영향을 분리할 자료가 없으므로 원인을 확정하지 않는다. 엄격한 주기 보장이 필요하면 RF-016 성능 비교와 함께 송신/수신 timestamp 계측이 필요하다.

## 복원

가상 4축 위치 0·속도 0, 각 Profile Velocity 100 복원 및 실제 SDO readback 확인. 가감속은 원래 F-KR 1000/Copley 500을 유지했다. 전 가상축 Operation Enabled 해제, Fault 없음, 버스 normal/WKC 18/18, 조작권 owner=null 확인. 저장 명령은 보내지 않았다. F-KR referenced 상태는 준비 단계 Home 이후 유지되며 처음의 미원점 상태까지 되돌린 것은 아니다.

## 증거·판정 경계

Linux ignored build/diagnostics/rf017-endurance-20261103: before.json, samples.jsonl, result.json, after.json, timing.log, cpp-summary.json, python-summary.json, rf017-endurance.py, summarize-run.py. 준비 실패 기록은 별도 rf017-endurance-precheck-20261103에 보관한다.

RF-017의 기본 연동·세부 이동·파라미터 효과에 이번 혼합 반복 운전 근거를 추가한다. 10분은 이번 관측 조건이며 일반 제품 내구시간 SLA가 아니다. 현 구조 2축/4축 동일 조건 비교(RF-016), Docker/native 비교(RF-012)는 아직 수행하지 않았다.
