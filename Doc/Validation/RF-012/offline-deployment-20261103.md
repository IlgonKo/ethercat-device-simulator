# RF-012 — 오프라인 배포 도구 검증 (2026-11-03)

- 현재 상태: **완료 — 기존 Linux Edge의 격리 디렉터리 검증 범위**
- 관련: [RF-012](../../RF/RF-012-docker-deployment.md), [배포 매뉴얼](../../../scripts/deployment/README.md).

## 변경

Python 런타임 19개/Conan bootstrap 16개 패키지를 버전과 Linux Python 3.12 wheel SHA-256으로 고정했다. Compose/Dockerfile의 Python base는 검증 digest로 고정했다. Conan recipe/package는 검증한 cache archive 전체 해시로 고정하며 기존 KickCAT 의존성 버전은 변경하지 않았다. native build bootstrap도 고정 requirements를 사용한다.

`scripts/deployment/offline.py`는 export/verify/load-image/restore/rebuild를 제공한다. source snapshot + Git/KickCAT bundle + 고정 wheel + Conan cache + FMU 소스/실행물 + runtime/base 이미지를 묶고 manifest로 파일 목록/해시를 검사한다. `.env`, state, 관계없는 untracked 파일은 제외한다. Git commit 외에 현재 추적 파일 snapshot의 해시가 소스를 식별한다. 운영 컨테이너를 자동 실행하거나 운영 :dev 이미지를 바꾸지 않는다.

## 검증 결과

- `build/offline-delivery` 생성 및 verify 통과(약 287MiB).
- 별도 이미지 `ethercat-device-simulator:rf012-locked` load, `build/offline-runtime` source/FMU 복원 통과. `.env`/state가 생성되지 않음 확인.
- 위 묶음만 사용해 `build/offline-rebuilt`에 새 venv·Conan cache 생성. KickCAT → Simulator → Linux Copley FMU → `ethercat-device-simulator:rf012-offline-rebuilt` 전체 재빌드 통과.
- pip는 no-index/require-hashes, Conan remote는 disable, Docker build는 network none/no-cache/pull false로 수행. OS/compiler/CMake는 기존 호스트 도구를 사용했다.
- 재빌드 결과 CTest 3/3, Python unit 48개 중 47 통과·Windows 전용 1 skip.
- 새 이미지에서 F-KR 2축 + Copley 2축 생성/저장 복원/각 100 step, C++ SDO gateway → IPC → 모델 검증 통과.
- 실제 Linux FMU integration 7/7 통과. 테스트 컨테이너는 network none/cap-drop ALL이며 운영 NIC·state를 사용하지 않았다.
- 신규 단위 검사 8개: 정상 manifest, 변조, 누락, 추가 파일, symlink, 외부 경로, 기존 복원 경로 보호, hash에 맞는 wheel만 선택/누락 거부.

전체 재빌드 이후 export compiler/CPU 검사를 보강했다. 최종 묶음은 `build/offline-delivery-20261103`에 다시 생성하며 동일 모델/의존성/빌드 절차를 담는다. 빌드 결과의 비트 단위 동일성은 요구하거나 판정하지 않았다.

## 운영 영향 및 남은 범위

운영 컨테이너 ID `8603937299b88a7bc9485e89541e446fc10924d5e06d492d40f12b0abc2a604e`와 시작 시간 `2026-11-03T03:14:48.155388268Z`가 유지됐고 running이다. 운영 설정·저장 파라미터를 배포 묶음으로 복사하거나 변경하지 않았다.

새 PC/새 OS에서의 확인은 남는다. OS·Docker·Git·Python·GCC/CMake 설치 패키지를 포함하지 않으며, Conan tinyxml2는 GCC 13.3.0 x86_64 사전 빌드 의존성이다. 일반 온라인 Conan recipe revision까지 lock한 것은 아니다. NIC 권한/플래그·Docker/native 성능 비교·동일 Edge Master 배치·Omniverse 경로는 별도 검증이다. 추가 지터 원인 조사는 사용자 결정대로 진행하지 않는다.

## 증거

`build/repro-20261103/locked-image-build.log`, `deployment-unit.log`, `bundle-export.log`, `offline-restore.log`, `offline-rebuild.log`, `offline-tests.log`, `offline-image-smoke.log`. 배포 묶음 자체의 `manifest.json`에는 전체 입력/산출물 해시와 source/image/compiler 정보가 포함된다. build 산출물은 Git에 넣지 않는다.
