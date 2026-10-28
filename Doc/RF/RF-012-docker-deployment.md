# RF-012 — Simulator Docker 패키징 및 실행 검증

- 현재 상태: **진행 중**
- 상태 상세: Docker/.env 및 물리 통신·모델 장애 격리 검증 반영 / 저장·배포 세부 기준 확인 중

- 등록일: 2026-09-15
- 설계: [DT-006](../Design/DT-006-docker-deployment.md)
- 연계: RF-003/004 기존 단축 통신, RF-005 혼합 버스, RF-010 저장, RF-011 구성

## 작업 범위

Linux Docker Engine용 이미지와 배포 구성을 작성한다. C++ KickCAT과 Python 모델을 단일 컨테이너로 배포하며 서비스용 실행 관리자를 구현한다. Motion Server 독립 패키지 경계를 유지한다. host 네트워크·지정 NIC·필요 capability, 환경 변수 설정 전달, 영구 데이터 저장소 및 임시 소켓 영역을 구성한다.

## 완료 기준

- [ ] 선택한 Linux/CPU 환경에서 재현 가능한 이미지 빌드 및 의존성·버전·배포 조건 기록.
- [ ] Motion Server 소스/설정 마운트 없이 Simulator를 독립 실행.
- [ ] 터미널 입력 없이 지속 실행, docker stop 신호 처리 및 자식 프로세스·소켓 정리 검증.
- [ ] 모델 실패 시 Slave 생존·장애 노출, 통신 프로세스 실패 시 서비스 실패·정리 및 readiness 검증 (DT-003의 2026-10-26 결정).
- [ ] 전용 NIC 선택·중복 사용 거부·기본 경로 NIC 검사, 실제 권한 및 NIC 플래그 영향 기록.
- [ ] 실제 PySOEM 검색·SDO 정상 경로·OP·PDO 회귀와 WKC, 주기 지연을 비컨테이너 기준과 비교.
- [ ] RF-011 .env 장치 구성 전달 및 모델 생성 검증.
- [ ] RF-010 파라미터 변경 후 컨테이너 재시작·재생성·이미지 교체 시 복원 및 저장 오류 검증.
- [ ] NIC 3을 통한 외부 Omniverse/엔지니어링 통신과 EtherCAT 경로의 역할 분리 확인.
- [ ] RF-005 혼합 버스 및 Edge의 Master/Simulator 동시 배치 결과를 별도 기록.
- [ ] 운영·업데이트·백업·복구 절차 작성. 컨테이너 재시작이 자동 운전 재개를 뜻하지 않음 확인.

## 검증 기록

2026-10-26 초기 Docker 실행 경로를 구현했다. 아래 결과와 남은 검증을 구분한다. 기존 TD-001 및 DC/CSP 성능·재접속 제한을 컨테이너 적용으로 해결했다고 처리하지 않는다.

## Docker 실행과 .env (2026-10-26)

실행 설정과 장치 목록·명시적 Slave 번호·모델 모드·parameter_set을 모두 `.env`로 통합한다. DEVICE_SIMULATOR_CONFIG_FILE과 장치 JSON 마운트는 제거했다. 영구 파라미터 데이터와 내부 ESI/IPC용 JSON은 유지한다.

Motion Server의 `.env`/`.env.example` 명명 규칙을 확인해 일반 설정은 `DEVICE_SIMULATOR_*`, EtherCAT 구현 설정은 `KICKCAT_INTERFACE`로 통일했다. 이는 `MOTION_SERVER_*`/`PYSOEM_INTERFACE`의 구분에 대응한다. 계측은 `DEVICE_SIMULATOR_CYCLE_STATS_LOGS=1`로 표기한다. 초기 `SIM_*` 이름은 교체했으며 예전 이름을 자동 해석하는 별칭은 없다. 두 제품의 설정 파일을 공유하거나 Motion Server 설정을 읽지는 않는다. 파일명은 `.env`, 예제는 `.env.example`을 유지한다.

| 변수 | 용도 |
| --- | --- |
| DEVICE_SIMULATOR_BUS | 명시적 번호:axis:cmmt-as 목록 |
| DEVICE_SIMULATOR_AXIS_IDS / MODELS / MODES / PARAMETER_SETS | 장치 ID, 모델, linear/rotary, 저장 공간 |
| KICKCAT_INTERFACE | EtherCAT NIC |
| DEVICE_SIMULATOR_STATE_DIR | 호스트의 영구 디렉터리; /state에 마운트하고 /state에 파라미터 저장 |
| DEVICE_SIMULATOR_CYCLE_STATS_LOGS | true/false, 주기 계측 로그 활성화 |
| DEVICE_SIMULATOR_SESSION_TIMEOUT | 0이면 무제한; 양수이면 진단용 실행 제한 |
| DEVICE_SIMULATOR_RUN_ID | 로그 식별자; 비우면 UTC 시각으로 자동 생성 |

Compose는 루트 .env를 env_file로 전달한다. 호스트 STATE_DIR는 /state로 마운트되고 컨테이너 내부 값은 /state로 지정된다. 파라미터는 /state에 저장한다. 장치 JSON이나 임시 구성 JSON은 만들지 않는다. `docker compose config`로 최종 환경을 확인한다. 축 설정은 .env의 리터럴 값으로 작성한다. native 실행은 --env-file을 사용한다.

Linux 저장소 루트에서 최초 한 번:

```bash
# 기존 .env가 없을 때만 복사하고 값을 편집한다.
test -e .env || cp .env.example .env
nano .env
docker compose config --quiet
docker compose build
docker compose run --rm simulator --validate-only
```

`--validate-only`는 NIC를 열지 않고 환경 설정·모델 로딩·4축 fixture 생성을 검사한다. 선택된 저장소에서 기존 파라미터를 읽고 잠금을 사용한다. 기존 native Simulator와 같은 저장소를 동시에 사용하지 않는다.

현재 native Simulator와 해당 Master 세션을 정리한 뒤 Docker 실행으로 전환한다. 동일 EtherCAT NIC를 동시에 사용하지 않는다.

```bash
docker compose up -d
docker compose ps
docker compose logs -f --tail=100 simulator
# 중지 (데이터 디렉터리는 보존)
docker compose down
```

설정 변경 후에는 `docker compose up -d --force-recreate`로 반영한다. 바이너리·모델 스냅샷 변경 시에는 먼저 다시 빌드한다. `restart: "no"`이며 재생성·재시작은 운전 재개를 뜻하지 않는다. 기본 저장 위치는 state이며 기존 native 저장값도 같은 위치에서 읽는다. 이전하려면 기존 세션을 정지하고 저장 데이터를 백업한 뒤 파라미터 파일을 새 저장소에 복사·검증한다.

## 이미지와 실행 관리자

실행 이미지 이름은 Compose의 `ethercat-device-simulator:dev`로 고정한다. `.env`의 DEVICE_SIMULATOR_IMAGE는 제거했다. 컨테이너 이름은 DEVICE_SIMULATOR_CONTAINER_NAME으로 지정하며 기본값은 ethercat-device-simulator다.

기반 이미지도 Compose의 build.args.BASE_IMAGE에 `python:3.12-slim`으로 고정하며 DEVICE_SIMULATOR_BASE_IMAGE는 .env에서 제거했다. 기반 이미지 변경은 Compose에서 관리한다.

바이너리 경로는 Compose build.args.DEVICE_SIMULATOR_BINARY의 `build/timing/cmmt_simulator`다. RF-016 이후 MODEL_SOURCE는 제거했고 src/functional_model 및 device_descriptions를 이미지에 포함한다. 실행 NIC인 KICKCAT_INTERFACE는 .env에 유지한다.

- docker/Dockerfile은 기존 Linux 바이너리와 모델 스냅샷을 이미지에 포함하는 런타임 패키징이다. C++를 이미지 안에서 소스부터 빌드하는 단계는 아직 제공하지 않는다. 기존 build-kickcat.sh/build-cmmt.sh 경로를 사용하고 Compose의 build.args.DEVICE_SIMULATOR_BINARY를 실제 최신 산출물에 맞춘다.
- .dockerignore는 지정된 빌드 바이너리와 src/functional_model·device_descriptions·docker 파일을 허용한다. 외부 모델 스냅샷은 빌드 입력에서 제거했다.
- RF-016 이후 Motion Server 체크아웃/설정/모델 스냅샷이 필요 없다. 필요한 기존 코드만 출처를 기록하여 자체 패키지에 이관했다. 제품 배포 라이선스의 법적 검토 완료를 의미하지 않는다.
- docker/service.py는 표준입력 EOF와 무관하게 지속 실행하고 SIGTERM/SIGINT로 종료한다. 두 자식 프로세스 로그는 docker logs로 수집하며 회전 한도는 10 MB × 3이다. run-id는 로그 라벨이며 이전 cmmt-session의 진단 폴더와 같은 의미는 아니다.
- 호스트 네트워크, NET_RAW/NET_ADMIN/DAC_OVERRIDE, 읽기 전용 루트, 임시 /run/simulator·/tmp를 사용한다. setcap 수동 재실행은 Docker 경로에서 필요 없다. 기본 경로 NIC, carrier 및 기존 EtherCAT 소켓을 확인한다. 사용자 요청으로 관리 NIC 변수와 그 검사는 제거했다. 호스트 전체에 대한 원자적 NIC 예약을 보장하는 기능은 아니다.
- healthcheck는 실행 관리자 heartbeat와 자식 생존을 확인한다. Master 연결·OP·WKC 정상이나 모델의 진행 상태까지 보증하지 않는다.
- Model Host 종료만으로 실행 관리자가 살아 있는 Slave를 즉시 종료하지는 않는다. 그러나 현재 C++는 IPC 단절/timeout 시 종료하므로 DT-003의 완전한 Slave 생존·오류 상태 유지·명시적 복구는 아직 미구현이다. 이를 해결하려면 IPC 오류 처리와 장치 상태 계약을 함께 변경해야 한다.

## 이번 검증 범위

- Edge-ubuntu, Linux x86_64, Docker 29.1.4 / Compose 5.0.1에서 이미지 빌드 성공. 기반 이미지 digest: `sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9`.
- NIC를 열지 않는 컨테이너 4축 JSON·모델 초기화·fixture 생성 통과.
- 물리 버스와 분리된 disposable bridge 네트워크에서 4축 Slave 시작, stdin 없는 지속 실행, healthcheck 및 docker stop 종료 코드 0 확인. Slave=0, 모델=SIGTERM(-15)로 정리했다. 시험용 컨테이너 안의 기본 경로만 제거했으며 호스트 경로는 변경하지 않았다.
- 관리 NIC 선택 거부 및 분리된 시험 네트워크의 사용 중 EtherCAT NIC 거부 확인. 실제 enp1s0에서도 시작·정상 종료를 관측했지만 Master/PDO/WKC 검증은 수행하지 않았다.
- 설정·원본 JSON 보존·healthcheck·관리 NIC 보호 단위 테스트 5개 통과.
- 사용자 기존 장치 JSON·파라미터는 덮어쓰지 않고 build/docker-validation의 별도 구성·저장소를 사용했다. 문서의 예제 .env는 사용자가 실제 파일 경로와 NIC에 맞춰야 한다.
- 물리 검색·SDO·OP/PDO·WKC 비교, 저장 후 컨테이너 재생성·복원, 장시간 지연 및 모델 충돌/무한 대기 격리 검증은 남아 있다. RF-012 전체 완료는 아니다.

## RF-005에서 이관 (2026-09-22)

RF-005 기본 3 Slave 완료를 선행 근거로 사용하되 컨테이너 및 Edge 동시 배치·다장치 환경은 이 항목에서 별도로 검증한다. [RF-005](RF-005-mixed-bus-feasibility.md)는 기본 혼합 타당성 범위로 완료했으며, 이 후속 항목의 상태는 변경하지 않는다.

## .env 전체 설정 전환 검증

2026-10-26 사용자 결정에 따라 장치 JSON 로딩·마운트·CONFIG_FILE을 제거했다. 설정·다중 축 독립성·저장/복원 회귀 22개 및 서비스 검사 4개를 Linux에서 통과했다. 새 환경 설정만 전달한 이미지 빌드·4축 초기화도 통과했다. 물리 통신은 재시험하지 않았다.

2026-10-26 축 설정 구조화: Motion Server의 번호:값 목록 규칙에 맞춰 AXIS_IDS/MODELS/MODES/PARAMETER_SETS로 변경했다. 관리 NIC 설정은 제거했다. Linux의 기존 2축 설정과 저장 공간을 동일하게 보존했으며 구성/모델 22개 및 서비스 3개 검사를 통과했다.

2026-10-26 저장 경로 변경: 기본 DEVICE_SIMULATOR_STATE_DIR는 ./state다. 기존 native 사용자 소유(mode 0600) 파라미터를 소유권 변경 없이 읽고 저장할 수 있도록 컨테이너 root에 DAC_OVERRIDE를 추가했다. 루트 파일시스템은 계속 읽기 전용이고 호스트 데이터 마운트는 state로 제한한다. 이 권한은 특정 파일만의 예외가 아니라 컨테이너가 접근 가능한 파일의 DAC 검사를 우회하는 권한이다. 기존 4개 저장 파일은 이미 state에 있었고 state/docker는 없어 파일 이동은 불필요했다. 백업 후 현재 2축의 모델 초기화·복원을 검증했고 4개 파일의 SHA-256 불변을 확인했다.

## Docker 운영 진입점과 이전 런처 정리

scripts/docker/start.sh [--build], stop.sh, build.sh, validate.sh, status.sh, logs.sh를 제공한다. Motion Server의 start/stop 사용 방식을 참고하되 start는 이미지 빌드 성공 후 컨테이너를 재생성하고 healthcheck를 최대 30초 기다린다. 실패 시 최근 로그를 출력하고 실패 코드를 반환한다. --build는 이미지 빌드이며 native C++ 빌드까지 수행하지 않는다.

삭제한 11개 native/Board/Windows 통합 진입점과 유지한 빌드/오프라인/시험 의존 도구는 [scripts 목록](../../scripts/README.md)을 따른다. 이 삭제로 기존 물리 진단 자동화가 Docker용으로 이식된 것은 아니다. 물리 PDO/WKC 회귀는 여전히 후속이다. 현재 주 실행 경로는 Docker이며 Master·Panel은 각 패키지에서 별도로 실행한다.


## 2026-10-28 검증 근거 갱신

RF-018의 운영 Docker 물리 통신·모델 종료/정지 중 Slave 생존·수동 재시작 결과를 참조한다. 모델 장애 격리를 미구현으로 간주하지 않는다. RF-010에서 별도 --network none 컨테이너를 제거하고 같은 임시 bind 저장소로 새 컨테이너를 생성하여 저장값 복원과 미저장 변경 폐기를 확인했다. 이 검증은 물리 SDO·Motion Server 재연결 경로 및 다른 버전 이미지 교체 시험을 대체하지 않는다. 서비스/Slave 자체 실패 시 정리, 배포 재현성·NIC 권한·성능 비교 등 나머지 완료 기준은 유지한다.
