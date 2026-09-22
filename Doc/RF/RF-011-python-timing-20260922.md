# RF-011 — Python 모델 계산과 IPC 비용 분리 계측 (2026-09-22)

## 목적과 계측 범위

[1차 프레임/IPC 계측](RF-011-timing-20260922.md)에 이어 C++ IPC 왕복 중 Python 모델 계산의 비중을 분리했다. 기존 순차 IPC와 모델 알고리즘은 변경하지 않았다.

- 같은 물리 축 1개 + IO 1개 + 가상축 2/4개, Windows Motion Server, Linux Simulator, 8 ms, DC off/sync_mode=2, PP 정지 상태.
- 테스트용 Master 포트 15100. 상태 조회/heartbeat만 전송하며 이동·파라미터 저장 명령은 보내지 않는다. 기존 시작 초기화/Enable 절차는 실행한다.
- C++ 바이너리는 1차 계측과 동일한 build/timing/cmmt_simulator를 사용했다. Python 모델 서비스에 선택적 계측만 추가했다.
- cmmt-session.py의 --timing을 Python에도 전달한다. wire JSON 요청/응답 형식은 바꾸지 않는다.
- Python에서 RxPDO→OD 변환, model_update, OD→TxPDO/hex 변환, JSON 해석·생성, 응답 write/flush를 분리한다. perf_counter_ns 경과 시간과 thread_time_ns CPU 시간을 함께 기록한다.
- cycle_request는 JSON 해석 시작부터 응답 flush 반환까지다. socket read에서 기다리는 시간은 제외한다. cycle_dispatch/core/model은 포함 관계이므로 모두 더하지 않는다.
- 1초 집계, 초기 10초에 걸치는 창 제외, 표본 수 가중 평균. Python과 C++ 집계 경계는 약간 다르므로 평균 비중 및 차이는 근사치이고 개별 요청의 정밀 차감이 아니다.

## 실제 선로 시험 결과

| 항목 | 가상 2축 | 가상 4축 |
| --- | ---: | ---: |
| Master 관측 시작 KST | 19:00:36.505 | 19:03:08.047 |
| 실제 관측 시간 | 120.014 s | 102.913 s, 연결 상실로 중단 |
| WKC 표본 | 120회 모두 12/12 | 102회 18/18, 종료 후 1회 0/12 |
| Fault | 없음 | BUS_CONNECTION_LOST |
| IPC 왕복 평균, 축당 | 1.246478 ms | 1.331667 ms |
| 모델 계산 평균, 축당 | 1.120582 ms | 1.204606 ms |
| 모델 계산 CPU 평균, 축당 | 1.114876 ms | 1.197613 ms |
| IPC 대비 모델 계산 비중 | 89.90% | 90.46% |
| RxPDO→OD 평균, 축당 | 0.027808 ms | 0.028949 ms |
| OD→TxPDO/hex 평균, 축당 | 0.019188 ms | 0.020238 ms |
| JSON 해석 평균, 요청당 | 0.007978 ms | 0.008188 ms |
| JSON 생성 평균, 요청당 | 0.008047 ms | 0.008243 ms |
| 응답 write/flush 평균 | 0.010317 ms | 0.010648 ms |
| Python cycle_request 평균 | 1.204845 ms | 1.292323 ms |
| C++ 왕복 - Python 처리 평균의 차이 | 약 0.041633 ms | 약 0.039343 ms |
| Simulator PDO 처리 평균/최대 | 2.507 / 6.085 ms | 5.356 / 12.792 ms |
| Simulator PDO 처리 8 ms 초과 | 0회 | 12회 |
| 계측 IPC 실패/timeout | 0 | 0 |

4축 BUS_CONNECTION_LOST occurred_at은 19:04:50.778955 KST다. 이번 진단 표본에는 BUS_PROCESS_DATA_INCOMPLETE가 먼저 기록되지 않았으며 1차 측정의 순서와 동일하다고 단정하지 않는다. 연결 종료 이후 expected WKC 12는 정상 운전의 18과 구분한다. raw server_status의 마지막 성공 응답은 normal이지만 그 뒤 bus/status가 bus_disconnected를 확인했다.

두 시험 모두 종료 후 테스트 프로세스 exit=0으로 정리했다. 모델 로그에는 예외 traceback 또는 PDO gap 100 ms 초과 메시지가 없었다. IPC 계측 실패 0은 모든 선로 프레임의 성공을 의미하지 않는다. 사용자 .env와 기존 Linux 2축 JSON은 유지했다.

## 모델 내부 오프라인 프로파일

물리 측정이 모두 종료된 뒤 동일 Linux 모델 소스 스냅샷으로 1축 PP/Enable/정지 상태의 model_update를 2,000회 실행했다. 실제 장비·NIC를 열지 않았다. cProfile을 사용하므로 절대 시간 비교가 아닌 병목 순위 확인용이다.

- OD 항목 수: **7,400개**.
- model_update: 2,000회, 누적 약 2.4065 s.
- definition_by_role: **8,000회**, 누적 약 2.3481 s, model_update 대비 **97.57%**.
- _apply_od_commands에서 reset 명령, save 명령, 운전 모드, 목표 위치를 read_role로 읽는다. definition_by_role는 매번 전체 entries.values()를 순회해 해당 role을 찾는다.
- 즉 정지 상태에서도 축당 매 주기 **7,400개 × 4번** 전체 검색을 수행한다. 실제 위치 적분/운동 계산보다 OD 역할 조회에 지배적인 비용이 발생했다.
- 확인 소스: build/model-source-da0b0a3/device/virtual_device/od_model.py:83, device/virtual_servo_drive/servo_model.py:44/93. 소스 변경은 하지 않았다.

## 결론과 다음 개선 후보

IPC 왕복의 약 90%는 모델 계산이고 모델 계산 경과 시간과 CPU 시간이 거의 같다. 주된 비용을 프로세스 대기나 JSON 직렬화로 설명하기 어렵다. 반복적인 OD role 전체 검색이 구체적인 계산 병목으로 확인됐다.

따라서 우선 후보는 **OD 정의 시 role→주소/정의 인덱스를 구성하고 실행 중 바로 조회하도록 개선**하는 것이다. define/overlay 등 정의 변경 시 인덱스 일관성과 기존 누락·중복 role 오류 의미를 보존해야 한다. 축별 OD 격리도 유지해야 한다. 이 보고서는 최적화 구현 완료를 뜻하지 않는다.

IPC 묶음 처리는 부가 비용을 줄일 수 있으나 동일 모델 계산을 유지하면 지배적인 비용은 남는다. 먼저 조회 병목 개선 후 동일 2/4축 조건에서 frame/IPC/모델 시간과 Fault를 재측정하는 것이 합리적이다. 4축 연결 상실의 모든 경로를 이 검색 하나의 원인으로 확정하지 않으며, Master 상태 조회 실패와 OS/선로 지연도 별도 구분한다.

## 도구·원본

- scripts/linux/summarize-python-timing.py <model.log> --skip-seconds 10 --output <summary.json>.
- build/timing-bench/timing220260922190028/ 및 timing420260922190259/: simulator.log, model.log, master.log, messages.jsonl, summary.json, timing-summary.json, python-timing-summary.json, phase-comparison.json.
- build/timing-bench/model-cpu-profile/: model.prof, profile.txt, summary.json.
- build/timing-bench/profile-model.py: 오프라인 프로파일 실행 코드.
- build/timing-bench/python-measurement-build.json: 계측 소스 SHA256. 이전 C++ 바이너리 fingerprint는 measurement-build.json에 보관한다.
- 원본은 Windows/Linux에 동기화하며 build 경로는 Git 추적에서 제외된다. 이 보고서는 추적 대상 문서다.

검증: 모델 계측 on/off의 PDO 응답 일치와 단계 시간 합산 테스트를 포함해 Linux model_service 테스트 9개 통과. 실제 Python socket 처리 계측은 위 물리 시험에서 검증했다.
