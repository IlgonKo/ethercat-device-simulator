# Simulator scripts

## Docker 운영 — Linux Edge PC

Motion Server의 scripts/host/start.sh [--build], stop.sh 패턴을 참고했다. Simulator는 scripts/docker에 모은다. 어느 작업 디렉터리에서도 실행할 수 있으며 .env는 셸 코드로 실행하지 않고 prepare-env.py가 줄 연결을 처리해 build/compose.env로 정규화하고 Compose가 읽는다. 원본 .env는 변경하지 않는다. Python 3이 필요하다. 여러 줄 설정은 각 연결할 줄 끝에 역슬래시(\)가 필요하다. 정규화 파일은 생성물이며 직접 편집하지 않는다.

```bash
bash scripts/docker/start.sh --build  # 이미지 빌드 후 시작/재생성
bash scripts/docker/start.sh          # 기존 이미지로 시작/재생성, .env 반영
bash scripts/docker/status.sh
bash scripts/docker/logs.sh           # Ctrl+C는 로그 보기만 종료
bash scripts/docker/stop.sh           # 컨테이너 정리, 저장 데이터 유지
```

별도 빌드는 build.sh, NIC 없는 설정·모델·저장값 검증은 validate.sh다. validate.sh는 같은 저장소를 사용하는 서비스가 실행 중이면 거부한다. native 세션과 다른 Compose 프로젝트의 중복 사용은 서비스의 NIC/저장소 잠금 검사도 따른다.

start는 NIC를 실제로 연다. Motion Server를 정지하고 기존 native Simulator가 없는 상태에서 전환한다. 설정 변경 후 start는 컨테이너를 재생성하며 저장 데이터는 유지한다. healthcheck 성공은 프로세스 준비만 뜻하고 OP/PDO/WKC 정상 보장은 아니다. 자동 운전 재개를 수행하지 않는다.

## 유지한 개발·검증 도구

| 위치 | 이유 |
| --- | --- |
| linux/build-kickcat.sh | C++ 의존성/toolchain 준비. 현재 Dockerfile은 소스 빌드 대신 기존 바이너리를 패키징 |
| linux/build-cmmt.sh | Docker에 넣을 cmmt_simulator 빌드 |
| linux/validate-fleet.py | 물리 NIC 없는 C++/Python 계약 검사; 모델/바이너리 변경 검증 |
| linux/benchmark-role-index.py | 기존 모델 OD 조회 성능 회귀 검사 |
| linux/summarize-timing.py | Docker 로그의 C++ 계측 분석 |
| linux/summarize-python-timing.py | Docker 로그의 Python 계측 분석 |
| windows/sdo_checks.py | 테스트가 사용하는 SDO 복원 검사 라이브러리. Docker 실행 스크립트는 아님 |

build-cmmt.sh 산출물은 build/timing/cmmt_simulator이며 Compose와 동일한 경로를 사용한다. Python 기능 모델은 저장소 src/functional_model에서 이미지에 복사한다. 외부 모델 스냅샷이나 MODEL_SOURCE는 필요 없다. start --build는 이미지를 빌드하며 C++ 컴파일은 build-cmmt.sh로 별도 수행한다.

## 삭제한 이전 진입점 (2026-10-26)

- linux/cmmt-session.py: stdin/SSH 수명 기반 native 실행, Docker 서비스로 대체.
- linux/diagnostic-session.py, run-simulator.sh, smoke-simulator.py, prepare-board-fixture.py: 초기 Board feasibility 전용 실행·fixture 경로.
- windows/diagnose-kickcat.py, diagnose-cmmt.py: 삭제한 native/Board 세션을 SSH로 실행하던 시험 진입점.
- windows/integration_bench.py, run-integration-bench.py, diagnose-integration.py, run-motion-server.py: native Simulator와 별도 Motion Server/Axis Panel 실행까지 소유하던 통합 벤치.

기존 RF/TD의 해당 명령은 당시 검증 이력이다. 현재 실행에는 위 Docker 스크립트를 사용한다. 삭제된 시험 진입점을 Docker 물리 회귀 시험으로 대체 완료했다는 뜻은 아니며 물리 PDO/WKC와 오류 복구 검증은 RF-012에 남는다. 필요하면 Git 이력에서 당시 코드를 확인할 수 있다.

## RF-016 개발 검증

```bash
python3 -m pip install -e .
python3 -m unittest discover -s tests
bash scripts/linux/build-cmmt.sh
python3 scripts/linux/validate-fleet.py --binary build/timing/cmmt_simulator
```

개발 검증에 --model-root는 사용하지 않는다. windows/export-model-source.py는 자체 모델 이관 후 삭제했다. tests/unit/test_sdo_restore.py는 Windows용 pysoem 의존성이 없는 환경에서는 건너뛴다.
