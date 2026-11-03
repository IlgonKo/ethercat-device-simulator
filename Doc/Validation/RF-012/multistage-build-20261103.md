# RF-012 — Docker 다단계 소스 빌드 검증 (2026-11-03)

- 현재 상태: **완료 — 격리 빌드·모델 검증 및 사용자 새 이미지 수동 정상 동작 확인**
- 관련: [RF-012](../../RF/RF-012-docker-deployment.md), [현재 매뉴얼](../../../scripts/deployment/README.md).

## 구조 변경

이전 Dockerfile의 호스트 build/timing 실행 파일 복사를 제거했다. Builder 컨테이너에 GCC/G++/make가 포함되고 고정 FMI wheel의 CMake를 사용한다. argparse 3.2, nlohmann/json 3.12.0, tinyxml2 11.0.0 소스 archive를 SHA-256 검증 후 빌드한다. 이어 KickCAT·Simulator·Copley Linux FMU를 컨테이너 안에서 빌드한다. 호스트 compiler/Conan cache/Python 개발 venv는 Docker 배포 경로에서 사용하지 않는다. 기존 native 개발 스크립트는 유지한다.

Builder: `python@sha256:17b9724493d916f56565c131f389faff2597f46dec6ce09516f95125bc9f519f`.
Runtime: `python@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9`.

실행 이미지에는 compiler/SDK/빌드 디렉터리를 복사하지 않는다. Python/FMI venv, 모델, Simulator 실행 파일, Linux FMU가 포함된다. runtime ldd 확인 및 GCC/G++ 부재 검사를 통과했다. venv에 FMPy의 의존성인 CMake wheel은 포함되지만 C/C++ compiler는 없다.

기본 FMU는 이미지 내부 `/model_artifacts`에 있다. 명시적인 기존 DEVICE_SIMULATOR_FMU_DIR 설정은 scripts/docker가 compose.external-fmu.yaml을 선택하여 외부 mount로 유지한다. 운영 .env는 수정하지 않았다. 기본 Compose에 FMU bind mount가 없는 것과 명시적 외부 설정에서만 override가 추가되는 것을 확인했다.

## 준비 및 오프라인 참조

Linux DNS 제한으로 Builder 이미지를 Windows Docker에서 받아 save/scp/load로 전달했다. 의존성 소스도 Windows에서 받아 Linux에 전달하고 lock SHA로 검증했다. image/source/wheel 확보 이후 빌드는 network none/pull false로 진행했다.

digest-only save/load 뒤 BuildKit이 repository digest를 외부 조회하는 현상을 확인했다. 해결은 고정 digest를 inspect로 확인한 뒤 digest 접미사의 로컬 태그를 만드는 방식이다. scripts/docker와 schema 2 rebuild가 이 검사를 수행한다. export는 base/builder를 이름이 있는 태그로 저장한다. 단순 mutable tag를 신뢰하도록 pin을 제거한 것은 아니다.

## 검증

| 항목 | 결과 |
| --- | --- |
| 컨테이너 내 C++ 의존성·KickCAT·Simulator·FMU 소스 빌드 | 통과 |
| Builder CTest | 3/3 통과 |
| Builder Python unit | 49개 중 48 통과, Windows pysoem 전용 1 skip |
| Builder 실제 FMU integration | 7/7 통과 |
| schema 2 bundle export 및 새 경로 offline rebuild | 통과 |
| 최종 Runtime GCC/G++ 부재 및 공유 라이브러리 로드 | 통과 |
| Runtime 내장 FMU로 F-KR 2축 + Copley 2축 생성·저장 복원·100 step/축 | 통과 |
| C++ SDO gateway → IPC → 모델, Abort/복구/OD 불변/PDO 계속 처리 | 통과 |
| Runtime 내장 FMU integration | 7/7 통과 |
| default/external FMU Compose 선택 | 통과 |

이미지: `ethercat-device-simulator:rf012-multistage-offline`.
Runtime 검증에는 외부 FMU 파일을 mount하지 않았고 network none/cap-drop ALL을 적용했다. C++ SDO 시험 실행 파일은 Builder 결과에서 별도로 추출했으며 운영 NIC는 열지 않았다.

`build/offline-multistage-20261103` 묶음(약 652MiB)을 `build/multistage-offline-rebuilt`에 복원하고 Docker로 재빌드했다. 기존 host build 디렉터리/Conan cache를 전달하지 않았다. BuildKit cache는 재사용 가능하며 실제 native compile 및 검증 단계 실행을 로그로 확인했다. 새 OS 전체 설치나 물리 EtherCAT 회귀 시험은 아니다.

## 운영 상태와 남은 범위

자동 검증 당시 운영 컨테이너 ID `8603937299b88a7bc9485e89541e446fc10924d5e06d492d40f12b0abc2a604e`, 시작 시간 `2026-11-03T03:14:48.155388268Z`가 그대로이며 running이다. 운영 :dev 태그·컨테이너·.env·state는 변경하지 않았다. 이후 사용자의 수동 전환 결과는 아래에 구분하여 기록한다.

호스트에는 Docker/Compose 및 현재 운영·배포 스크립트 실행용 Python/Git이 필요하다. compiler는 필요 없다. OS/Docker 설치 패키지는 묶음 외부이다. 새 PC/OS, NIC 권한/플래그, 동일 Edge Master 배치, 외부 DT 경로 및 성능 비교는 별도 범위다.

## 증거

Linux build/repro-20261103 아래 multistage-build.log, multistage-export.log, multistage-offline-rebuild.log, multistage-test-artifact.log, multistage-image-smoke.log. 각 배포 묶음의 manifest.json에 소스 snapshot·입력·이미지 SHA가 있다. build 산출물은 Git에 포함하지 않는다.

## 사용자 수동 테스트 결과 (2026-11-03)

사용자 보고: “새 이미지로 수동 테스트 완료. 정상 동작 확인했음.” 새 Docker 이미지 적용 후 수동 정상 동작 확인을 완료 처리한다. 기존 자동 검증과 별도의 사용자 확인 근거이다. 개별 항목별 수행 여부·WKC 수치·시험 시간·로그는 별도로 제공되지 않았으므로 추정해 채우지 않는다.

준비 중 state JSON 4개를 일반 사용자 권한으로 읽지 못해 cp Permission denied가 발생했다. Simulator 정지 상태에서 sudo cp -a로 백업하고 sudo diff -qr로 대조하는 절차를 매뉴얼에 반영했다. 원본 파라미터의 권한을 완화하지 않는다.
