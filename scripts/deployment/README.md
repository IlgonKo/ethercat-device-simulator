# Docker 다단계 빌드와 오프라인 배포

대상: Linux x86_64. **호스트에 GCC/G++, CMake, Conan, Python 개발 venv가 필요 없다.** Docker Builder 단계에서 C++ 의존성·KickCAT·Simulator·Copley FMU를 모두 빌드한다. 실행 이미지에는 컴파일러/SDK/소스 빌드 디렉터리를 복사하지 않는다.

호스트에는 Docker Engine/Compose가 필요하다. 현재 저장소 운영·배포 도구를 사용하려면 기존처럼 Python 3와 Git도 필요하다. OS/Docker 설치 패키지는 배포 묶음에 포함하지 않는다.

## 빌드 구조

1. Digest로 고정한 full Python 3.12 Builder 이미지의 GCC/G++/make 사용.
2. 고정 wheel로 FMI 및 CMake 설치. argparse 3.2, nlohmann/json 3.12.0, tinyxml2 11.0.0 소스 archive를 해시 검증 후 컨테이너에서 빌드.
3. KickCAT 및 Simulator를 CMake로 빌드하고 CTest/Python/FMU 검증 실행.
4. Copley 소스 FMU를 Linux FMU로 컴파일.
5. slim 실행 이미지에 Simulator 실행 파일, Python 모델·FMI venv, FMU만 복사.

Docker 빌드에는 호스트 `build/timing/cmmt_simulator`, Conan cache, 사전 컴파일 FMU를 사용하지 않는다. `.dockerignore`에서 호스트 build/state/.env를 제외한다. 기존 native 개발 스크립트는 직접 native 디버깅용으로만 유지한다.

## 새 소스로 이미지 만들기

Git 소스와 KickCAT submodule을 준비한다. 온라인 PC에서:

```bash
git submodule update --init --recursive
python3 scripts/docker/prepare-inputs.py --download
# compose.yaml/docker/dependency-inputs.json의 두 이미지 digest를 docker pull로 준비
bash scripts/docker/build.sh
```

`prepare-inputs.py`는 필요한 source archive/FMU/wheel을 준비하며 컴파일하지 않는다. `--download`를 주지 않으면 외부 접속 없이 존재 여부·해시만 검사한다. `--wheels /path/to/cache`로 고정 wheel을 복사할 수도 있다. 출력은 ignored `docker/inputs`, `docker/wheels`에 저장한다. 이미지 pull 및 입력 다운로드는 네트워크가 되는 PC에서 진행해야 한다.

`.env`가 없는 빌드 전용 환경에서는 다음처럼 직접 빌드할 수 있다.

```bash
python3 scripts/docker/prepare-inputs.py --images
docker build --network none --pull=false \
  --build-arg BASE_IMAGE=python:simulator-runtime-d764629ce0dd \
  --build-arg BUILDER_IMAGE=python:simulator-builder-17b9724493d9 \
  -f docker/Dockerfile -t ethercat-device-simulator:test .
```

기존 `start.sh --build`도 전체 소스 빌드 후 컨테이너를 전환한다. 운영 컨테이너에 적용하지 않고 확인하려면 위처럼 별도 이미지 태그로 먼저 검증한다.

## 내장 FMU와 외부 FMU

v1.0 기본 FMU는 이미지 안의 `/model_artifacts/`에 있다. F-KR 직선/회전 FMU, Copley, 아날로그 지연 FMU를 빌드하고 고정 실린더 FMU를 포함한다. `.env.example`의 외부 FMU 경로는 선택적 override다. 외부 폴더를 사용하면 해당 구성에서 필요한 모든 FMU가 있어야 한다.

v1.0 버전 고정 이미지 이름은 `ethercat-device-simulator:1.0.0`이며 현재 검증한 이미지를 가리킨다. 공개 registry에는 게시하지 않는다. save/load 또는 오프라인 묶음으로 옮긴 다음 기존 실행 스크립트용으로 `docker tag ethercat-device-simulator:1.0.0 ethercat-device-simulator:dev`를 수행한다. [릴리즈 기록](../../Doc/Releases/v1.0.0.md).

기존 `.env`에 `DEVICE_SIMULATOR_FMU_DIR=./model_artifacts`가 있으면 scripts/docker가 `compose.external-fmu.yaml`을 추가하여 외부 FMU를 계속 사용한다. 새 이미지에서 빌드한 내장 FMU를 쓰려면 다음 수동 전환 시 그 설정을 삭제/주석 처리한다. 기존 `.env`를 자동 변경하지 않는다. 직접 Compose를 호출하면서 외부 FMU를 사용하려면 `-f compose.yaml -f compose.external-fmu.yaml`을 명시해야 한다.

## 오프라인 배포 묶음 생성

```bash
python3 scripts/deployment/offline.py export build/offline-multistage \
  --image ethercat-device-simulator:test --wheels docker/wheels
python3 scripts/deployment/offline.py verify build/offline-multistage
```

schema 2 묶음에는 source snapshot/Git/KickCAT bundle, 고정 FMI wheels, C++/FMU 소스 입력, runtime/base/builder 이미지 및 manifest가 들어간다. 호스트 compiler·Conan cache·bootstrap wheel은 필요 없다. 이미지와 입력을 먼저 준비한다. export는 지정한 이미지를 재빌드하지 않으므로 배포할 소스로 만든 이미지를 지정한다.

`.env`, state, 관계없는 untracked 파일은 포함하지 않는다. Git 추적 파일의 현재 내용과 신규 배포 관련 파일을 source snapshot에 담고 파일별 SHA-256을 기록한다. 미커밋 수정이 있으면 commit만이 아니라 snapshot 해시가 실제 소스를 식별한다. manifest는 전송 손상 확인용이며 발행자 서명은 아니다. FMU 등의 외부 배포는 해당 라이선스를 따른다.

## 새 PC에서 복원·실행

묶음을 신뢰하는 경로로 복사한 뒤 `<bundle>`을 절대 경로로 대체한다. 아래는 컨테이너를 시작하지 않는다.

```bash
python3 <bundle>/source/scripts/deployment/offline.py verify <bundle>
python3 <bundle>/source/scripts/deployment/offline.py load-image <bundle>
python3 <bundle>/source/scripts/deployment/offline.py restore <bundle> --work /home/festo/ethercat-device-simulator
```

복원 위치에서 `.env.example`을 `.env`로 복사하고 NIC/장치/모델/파라미터 저장 위치를 설정한다. 예제는 F-KR 4축이며 Copley는 AXIS_MODELS로 선택한다. 모델 종류를 바꿔 새 장치로 시작할 때는 신규 AXIS_NAMES를 사용하며 파라미터와 PDO 매핑 모두 새 ID에 연결된다. 기존 파라미터가 필요하면 정지 상태에서 별도로 백업·이관한다. 기존 Simulator 정지와 전환 준비 후 `docker tag <manifest의 image_id> ethercat-device-simulator:dev`, `bash scripts/docker/validate.sh`, `bash scripts/docker/start.sh` 순서로 수동 적용한다. 배포 이미지를 바로 쓰는 경우 `--build`를 붙이지 않는다. Motion Server에서 버스 재연결·초기화한다.

## 묶음만으로 전체 재빌드

```bash
python3 <bundle>/source/scripts/deployment/offline.py rebuild <bundle> \
  --work /home/festo/simulator-rebuild \
  --image ethercat-device-simulator:offline-rebuilt
```

새 경로에 소스/입력을 복원하고 base/builder 이미지를 load한 뒤 Docker 안에서 전체 빌드한다. 네트워크는 사용하지 않으며 호스트 GCC/Python 3.12/Conan 검사는 하지 않는다. 호스트 Python은 도구 실행용이다. Docker cache가 있으면 재사용하며, 완전 재컴파일이 필요하면 복원 위치에서 `docker build --no-cache --network none --pull=false ...`로 실행한다.

schema 1 묶음의 무결성 조회/기존 runtime load는 유지하지만 새 rebuild는 schema 2를 요구한다. 새 PC/OS의 실제 NIC 통신과 성능은 별도 확인한다. 빌드 내부 테스트가 물리 EtherCAT 검증을 대신하지 않는다.

Docker save/load로 옮긴 multi-platform 이미지의 digest 참조를 BuildKit이 외부 조회하는 경우를 피하기 위해, `prepare-inputs.py --images`는 고정 digest를 먼저 검증한 뒤 digest 접미사가 있는 로컬 태그를 만든다. Compose와 offline rebuild는 이 검증된 로컬 태그를 사용한다. 단순 태그 이름만을 신뢰하는 방식은 아니다.

## 전환 전 파라미터 백업과 원복

Axis Panel에서 정지·Disable하고 Motion Server를 종료한 뒤 Linux 저장소 루트에서 실행한다. 컨테이너가 만든 state JSON은 일반 사용자가 읽지 못할 수 있으므로 관리자 권한으로 복사한다. 원본 권한은 변경하지 않는다.

```bash
cd /home/festo/Documents/ethercat-device-simulator
bash scripts/docker/stop.sh
BACKUP_DIR="build/manual-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -a .env "$BACKUP_DIR/.env"
sudo cp -a state "$BACKUP_DIR/"
sudo diff -qr state "$BACKUP_DIR/state"
docker image inspect ethercat-device-simulator:dev --format '{{.Id}}' > "$BACKUP_DIR/image-id.txt"
docker tag "$(cat "$BACKUP_DIR/image-id.txt")" ethercat-device-simulator:before-multistage
```

위는 STATE_DIR=./state인 현재 환경 예이다. 다른 저장 경로를 설정했다면 해당 경로를 백업한다. diff가 출력 없이 종료 코드 0이면 원본과 백업이 같다. 앞서 일반 cp가 일부 실패했다면 같은 BACKUP_DIR에 sudo cp 명령을 다시 실행할 수 있다. 새 터미널에서는 BACKUP_DIR을 실제 백업 경로로 다시 지정한다.

이전 이미지로 원복할 때는 Motion Server와 Simulator를 먼저 정지한다.

```bash
cp -a "$BACKUP_DIR/.env" .env
docker tag "$(cat "$BACKUP_DIR/image-id.txt")" ethercat-device-simulator:dev
bash scripts/docker/start.sh
```

이 원복은 이미지/.env만 복원하고 state를 덮어쓰지 않는다. 시험 중 저장한 값은 유지되며 원래 파라미터는 백업 state에 있다. 구버전 이미지가 새 파라미터 스키마를 읽을 수 있는지는 별도로 확인한다.
