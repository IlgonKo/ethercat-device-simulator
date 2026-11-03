# RF-012 — 별도 checkout 오프라인 빌드·패키징 검증 (2026-11-03)

- 현재 상태: **검증 완료 — 오프라인 입력을 사용하는 기존 Edge x86_64 범위**
- 물리 NIC 및 운영 컨테이너를 사용하지 않은 빌드·모델 통합 검증이다. 새 OS 설치부터의 재현성, 물리 EtherCAT 재검증 또는 비트 단위 동일 빌드 판정은 아니다.

## 입력과 격리

작업 위치: `/home/festo/Documents/ethercat-device-simulator/build/repro-20261103/checkout`.

소스 commit: `57d289abaa172b9efd6ea91bced3c928d0cde3f1`. KickCAT: `43ad3e9ce390f0f6d9548118098bcaafc0d4f1f1`.
운영 작업 트리의 미커밋 변경은 포함하지 않았다. 별도 clone, 새 Python venv 두 개와 새 `CONAN_HOME`을 사용했다. 기존 Simulator 실행 파일은 복사하지 않았다.

Linux에서 GitHub/PyPI/Conan DNS 조회가 실패하여 소스는 로컬 Git 저장소에서, 의존성은 오프라인 묶음으로 준비했다.

- Conan 2.10.2 및 bootstrap wheel: Windows에서 내려받아 전송. Linux 전용 distro 1.8.0 포함.
- Conan cache export: argparse 3.2, nlohmann_json 3.12.0, tinyxml2 11.0.0. tinyxml2는 기존 GCC 13.3 x86_64 Debug/Release 바이너리 사용. 모든 외부 라이브러리를 소스 빌드한 것은 아니다.
- FMI Python wheel cache와 FMPy 0.3.26 사용. 전이 의존성 전체가 저장소에 lock된 상태는 아니다.
- 소스 FMU SHA-256: `e6456f4787b61b209f0e718c62ee3d570560ce975b7aacf733da6d4f21994b4d`. Linux FMU는 build-copley-fmu.py로 재빌드.
- Docker base: `python@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9`, 로컬 보유 이미지 사용.
- 모든 입력 wheel/Conan 묶음/FMU 및 생성 실행 파일 해시는 `build/repro-20261103/result-manifest.json`에 기록.

## 실행 순서

1. 별도 clone 및 KickCAT 고정 revision 준비.
2. 새 venv에 오프라인 Conan 설치, 별도 CONAN_HOME에 cache restore, remote disable.
3. `bash scripts/linux/build-kickcat.sh` 실행.
4. `bash scripts/linux/build-cmmt.sh` 실행 및 C++ 테스트 빌드.
5. 별도 FMI venv에 `docker/requirements-fmi.txt` 설치 후 `scripts/linux/build-copley-fmu.py --source ../CopleyDriveSim-source.fmu --output model_artifacts/CopleyDriveSim-linux.fmu` 실행.
6. `docker build --no-cache --network none --pull=false --build-arg BASE_IMAGE=python@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9 -f docker/Dockerfile -t ethercat-device-simulator:rf012-repro-20261103 .` 실행.
7. 새 이미지에서 `--network none --cap-drop ALL`로 테스트. FMU·테스트 실행 파일은 읽기 전용 mount, 저장소는 별도 scratch 사용. 운영 `.env`/state mount 없음.

Dockerfile은 여전히 사전 빌드한 C++ 실행 파일을 패키징한다. Docker build 단독으로 KickCAT/C++/FMU를 소스에서 만드는 구조는 아니다.

## 결과

| 검증 | 결과 |
| --- | --- |
| KickCAT network_simulator / simulated_bus 소스 빌드 | 통과 |
| cmmt_simulator 소스 빌드 | 통과 |
| CTest: mapping / multi-slave / asynchronous host fault | 3/3 통과 |
| Python unit | 40개 중 39 통과, Windows pysoem 전용 1개 skip |
| Linux Copley FMU 소스 빌드 및 새 Docker 이미지 | 통과 |
| 새 이미지에서 F-KR 2축 + Copley 2축 생성·100 step/축·저장 복원 | 통과 |
| C++ SDO gateway → Unix socket → 모델 서비스 | Abort 형식·복구·OD 불변·PDO 계속 처리 통과 |
| 실제 Linux FMU integration tests | 7/7 통과 |

SDO gateway 실행 파일은 fixture manifest, contract, socket 인자가 필요하다. 인자 없이 실행한 첫 시도는 사용법 오류였고, 모델 서비스/fixture 준비 후 정식 검증은 통과했다.
테스트 scratch 권한 및 socket 전용 0700 디렉터리를 준비한 후 통과했다. 운영 권한 설정 변경은 없다.

이미지: `ethercat-device-simulator:rf012-repro-20261103`, ID `sha256:5eb306bf96c1988075371e031614e31ade4e52d14e88acd024ae0254a157ee27`.
운영 컨테이너 ID `8603937299b88a7bc9485e89541e446fc10924d5e06d492d40f12b0abc2a604e`, 시작 시간 `2026-11-03T03:14:48.155388268Z`가 시험 전후 동일하고 running이다. 운영 이미지 태그 교체·컨테이너 재생성은 하지 않았다.

## 증거와 한계

`build/repro-20261103/`에 environment.json, result-manifest.json, prepare.log, kickcat-build.log, native-build.log, fmu-build.log, docker-build.log, python-tests.log, docker-smoke.log, smoke.py를 보관했다. build 산출물은 Git 관리 대상이 아니다.

기존 Edge에서 명시적인 오프라인 입력을 사용한 재빌드는 확인했다. 새로운 PC에서 외부 의존성을 확보하는 절차와 wheel/Conan/base 이미지의 배포·고정은 별도 정리가 필요하다. 물리 NIC 권한/플래그, Docker/native 동일 조건 지연, 동일 Edge Master 동시 배치와 외부 Omniverse 경로는 이 시험의 범위 밖이다.
