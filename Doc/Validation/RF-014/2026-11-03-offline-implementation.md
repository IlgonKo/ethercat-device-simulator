# RF-014 오프라인 구현 검증 — 2026-11-03

- 현재 상태: 오프라인 검증 통과 / 물리 EtherCAT 검증 대기
- 대상: Linux Edge PC, NIC 없이 실행한 테스트 및 네트워크 없는 Docker 빌드
- 이미지: `ethercat-device-simulator:rf014`
- 이미지 ID: `sha256:b2f60c9ebafa80c0ff523034817fbde70d46f9f6d9243652247329e97a56e5ff`
- 기존 `:dev` 이미지, 운영 컨테이너, .env, 기존 파라미터 파일은 전환·수정하지 않음.

| 검증 | 결과 |
| --- | --- |
| C++ CTest | 5/5 통과. 후보 검증, 기존 다축 라우팅/비동기 Host Fault, 별도 저장 복원 포함 |
| Python unit | 56개 중 55 통과, Windows PySOEM 의존 시험 1개 skip |
| 실제 Linux Copley FMU | 8/8 통과. PP 목표 래치·운전 재개 및 Fault Reset 포함 |
| F-KR/Copley 혼합 4축 | Docker builder에서 각 축 SDO·SAFE-OP·OD IPC·재시작 복원 통과 |
| F-KR/Copley 혼합 2축 | 완성된 runtime 이미지의 Slave 실행 파일로 동일 시험 통과 |
| runtime 시작 | 현재 .env를 파싱하여 격리된 임시 state로 --validate-only 통과. read-only, network none, cap-drop ALL |
| 문서/소스 공백 검사 | git diff --check 통과 |

## 재현

- C++: `ctest --test-dir build/timing --output-on-failure`
- Python: `PYTHONPATH=src:. python3 -m unittest discover -s tests/unit -v`
- FMU: `COPLEY_TEST_FMU=model_artifacts/CopleyDriveSim-linux.fmu PYTHONPATH=src:. python3 -m unittest tests.integration.test_copley_fmu -v`
- 통합: `python3 tests/integration/run_dynamic_mapping.py --axes 4 --fmu-dir model_artifacts`
- FMU Python 의존성이 없는 호스트에서는 Docker builder의 검증을 사용한다. Dockerfile에서 네이티브 빌드·회귀·실제 FMU·혼합 4축 통합 시험을 수행한다.
- 통합 runner는 TemporaryDirectory 내 파라미터/매핑 저장소만 사용하며 NIC를 열지 않는다.

## 시험 중 발견 및 수정

- Copley FMU의 Disable Voltage는 velocity를 0으로 만들지만 내부 moving/ppTarget을 지우지 않는다. 새 시작 비트가 없어도 Enable 시 이전 이동이 재개됐다.
- 어댑터는 운전 비활성화 이후 새 PP 시작 전까지 FMU ProfileVelocity 입력을 0으로 제한한다. OD의 Profile Velocity와 Target Position은 유지한다. 새 시작 요청 없이 위치가 변하면 Adapter Fault로 처리한다.
- PDO에서 빠진 OD를 내부 고정 표현에서 다시 쓰지 않도록 선택 갱신을 적용하고 실제 write 호출 부재를 시험했다.
- 이전 활성 주기 응답이 비활성 확인 응답으로 잘못 취급되지 않도록 요청별 active 상태를 추적한다.

## 범위의 한계

실제 케이블·Windows PySOEM·Motion Server의 CA 미지원 탐색 호환성, OP/WKC, 실제 주기 성능, 물리 버스에서의 전환 순간 Host Fault는 미검증이다. 전원 차단 및 fsync/rename 실패의 모든 지점에 대한 장애 주입 시험도 완료한 것으로 간주하지 않는다. RF-014 완료 처리는 이 검증들을 확인한 뒤 판단한다.
