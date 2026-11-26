# RF-013 자동 경계 시험 — 2026-11-26

- 현재 상태: **자동 시험 세 묶음 통과**. RF-013 전체 완료 판정과 구분한다.
- 기준: [RF-013](../RF/RF-013-virtual-io.md), [5단계 현황](RF-013-stage5-20261126.md).
- 환경: Linux Edge-ubuntu, 현재 작업 트리. 실제 IO FMU Linux 바이너리와 KickCAT 오프라인 ESC/mailbox를 사용했다. NIC·Motion Server·운영 컨테이너는 조작하지 않았다.
- 변경 범위: 자동 시험과 문서. 제품 실행 코드·운영 설정·저장 데이터·운영 이미지는 이번 시험에서 변경하지 않았다.

## 결과

| 묶음 | 직접 확인한 조건 | 결과 |
| --- | --- | --- |
| 아날로그 FMU 연결 | command 미연결 시 초기화만 수행, 5회 입력 갱신에도 모델 시간/계산 횟수 0, 초기 AI 유지, Fault 없음. 다른 모델 계산 지속 | 통과: 실제 FMU |
| 아날로그 FMU 연결 | feedback 미연결 시 command로 계산 지속. 3회 후 모델 시간 24ms, 모델 결과 -32768, 연결 없는 AI는 기본 0 유지 | 통과: 실제 FMU |
| 값 유지·내부 상태 | 입력 station 상실 시 마지막 DI 유지·paused 전환, Fault 없음. 모든 입력의 새 스냅샷 필요. 재개 계산 중에는 이전 값, 성공 완료 후 새 값 반영 | 통과: 결정적 시험 어댑터 |
| 값 유지·내부 상태 | 개별 모델 오류 후 입력 station 복귀에도 Fault 유지·재계산 없음·AI 유지. 다른 모델은 새 AI 갱신 | 통과: 결정적 시험 어댑터 |
| 값 유지·내부 상태 | 계산 제한시간 초과 시 Host Fault 유지, 다른 모델도 새 계산 금지, 뒤늦은 결과 폐기. 입력 재수신/복귀로 해제되지 않음 | 통과: 이벤트로 계산을 막고 단조 시계를 제어 |
| CPX 진단 | 두 station의 0x1001 및 지원 0x6102 모든 subindex에 개별 SDO 쓰기. Abort 명령 0x80 / 코드 0x06010002, 읽기 결과 불변 | 통과: 실제 KickCAT mailbox |
| CPX 진단 | AO 스냅샷으로 시험 모델 a의 오류 주입. 마지막 AI 유지, 모델 b의 AI=3210 갱신, OP 유지, 내부 오류 발생 확인, 진단 OD 전후 동일 | 통과: KickCAT↔Unix IPC↔IO 실행부 |
| CPX 진단 | 오류 입력 주입 이후 100회 교환/메일박스 조사에서 비요청 메시지 없음. 요청한 SDO 응답을 별도 소비·구분하고 최종 BRD WKC=2 확인 | 통과: 관측 구간 내 Emergency 없음 |

## 실행 근거

- IO 단위 시험 23개 + 실제 FMU 통합 시험 12개 = **35개 통과**.
- 전체 Python 단위 회귀 **89개 중 88개 통과, 1개 생략**: Linux에 pysoem이 없어 Windows SDO 복원 시험 생략.
- 운영에 사용한 `ethercat-device-simulator:io-model-keys-20261126` 이미지로 별도 `--network none` 컨테이너를 실행하고 최신 tests만 읽기 전용 마운트: 실제 FMU **12개 통과**. 운영 컨테이너 재시작이나 이미지 재빌드는 하지 않았다.
- `test_remote_io` native 재빌드 성공. 모델 미연결/연결 두 구성 모두 프로토콜 시험 통과. 연결 구성에서 모델 오류·CPX 진단 분리 시험 추가 통과.
- 원시 로그: `build/diagnostics/rf013-boundaries-20261126/{python,unit,docker-fmu,build,mailbox}.log`. build 산출물은 Git 추적 대상이 아니며 이 보고서에 결과와 재현 방법을 남긴다.

```bash
cd /home/festo/Documents/ethercat-device-simulator
PYTHONPATH=src:. build/fmi-venv/bin/python -m unittest discover -s tests/unit -v
IO_TEST_FMU_DIR="$PWD/model_artifacts" PYTHONPATH=src:. build/fmi-venv/bin/python -m unittest tests.integration.test_io_fmu -v
cmake --build build/timing --target test_remote_io -j4
PYTHONPATH=src:. build/fmi-venv/bin/python tests/integration/run_remote_io.py
```

추가 시험은 `tests/unit/test_remote_io.py`, `tests/integration/test_io_fmu.py`, `tests/integration/test_remote_io.cc`에 있다. `run_remote_io.py`의 오류 주입 및 test_io_status 관측은 시험 전용 subclass/adapter에만 존재하며 제품 IPC에 관리 명령을 추가하지 않았다.

## 내부 상태와 진단 해석

- 정상 일시정지는 paused, 계산 진행은 busy_since, 성공 결과 갱신은 steps와 출력 값으로 판정한다. paused 해제만으로 새 결과가 생성됐다고 판단하지 않는다.
- 개별 모델 Fault는 source의 모델 ID, Host Fault는 model_host 범위로 식별한다. 오류 진단 context에는 feedback_valid=false와 restart_required=true가 있다. 별도 정상 상태 조회 API나 CPX 유효성 필드는 추가하지 않았다.
- 사용자가 station·모듈·채널 목록의 진단 중복 기록은 불필요하다고 확인했다. 해당 목록은 완료 조건에서 제외하고 필요시 binding 설정으로 연결 관계를 확인한다.
- 이번 CPX 시험은 **FMU 실행 오류를 CPX 진단으로 전달하지 않는 현행 정책**을 검증했다. 사용자는 DO 이후 DI 도달 제한시간 등 IO 동작 타임아웃을 상위 애플리케이션에서 처리하기로 한 기존 결정을 재확인했다. Soft ESC가 이 오류를 만들거나 CPX로 전달하는 기능은 추가하지 않는다. FMU 실행 제한시간은 별개의 내부 보호다.

## 한계 및 후속

- 메일박스 100회 관측은 약 0.8초의 오프라인 교환 요청 구간이다. 실시간 주기 보장·물리 네트워크 캡처·장시간 무발생 증명을 의미하지 않는다.
- 장애는 시험 어댑터에서 의도적으로 주입했다. 실제 FMU 네이티브 크래시/프로세스 강제 종료를 새로 수행한 시험이 아니다.
- CPX 진단은 현재 최소 지원 범위의 정상값·읽기 전용·모델 오류와의 분리를 검증했다. 제조사 하드웨어 고장을 재현하거나 진단 PDO/이력/Emergency를 구현한 것이 아니다.
- 아날로그 수동/물리 전체 왕복 생략 결정은 유지한다. 현재 혼합 운전 계측, Host 장애·재시작 복구, CPX 재구성·Master 재검색은 별도 잔여다.
