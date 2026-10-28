# EtherCAT Device Simulator

Software-based EtherCAT device simulation, starting with CMMT drives and reusable CiA 402 models.

The intended architecture connects a PySOEM master over EtherCAT to a software ESC and slave communication stack, with device behavior provided by our existing object dictionary and CiA 402 modules.

KickCAT is the selected implementation direction for the software ESC and slave stack. Basic PySOEM PDO and SDO paths have been validated with a corrected test ESI; CMMT-AS single-axis model integration is validated over a Unix socket; SDO Abort interoperability is deferred as TD-001. The acontis evaluation is on hold.

## 프로젝트 문서

- [작업 일지](Doc/Work_log.md): 진행 결과, 결정 사항 및 후속 작업
- [RF 항목 목록](Doc/RF/README.md): 기본 타당성 검증과 후속 DT 연동 개발
- [TD 항목 목록](Doc/TD/README.md): 보류한 기술 문제와 해결 기준
- [설계 및 진행 계획](Doc/project-plan.md): 목적, 실행 구성 및 모듈 책임

기본 타당성 검증에 사용한 실행 구성은 **Windows PC의 Motion Server/PySOEM ↔ 실제 EtherCAT 케이블 ↔ 별도 Linux PC의 KickCAT 시뮬레이터**입니다. Linux 빌드 및 enp1s0에서 기본 Slave 실행·정상 종료를 검증했습니다. Windows PySOEM과의 물리 PDO 교환 1,000회를 검증했습니다. 테스트용 ESI에 0x1C00 정렬 보정이 필요하며, SDO 시험은 2-1단계로 분리했습니다.

진행 순서 (2026-09-14 합의):

1. Linux에서 KickCAT 빌드 및 기본 Slave 시뮬레이션 실행.
2. Windows PySOEM에서 Slave 검색 → OP 전환 → PDO 왕복 검증. 명시적 SDO 시험은 별도 2-1단계.
3. 기존 `VirtualOdBridge`와 가상 서보 모델을 연결해 CMMT 동작 구현.
4. Motion Server와 Axis Panel로 통합 테스트.

**첫 목표는 물리 케이블을 통한 PySOEM과 KickCAT의 기본 통신 확인**입니다. MockMaster는 비교·회귀 테스트용으로 유지합니다. acontis EC-Simulator 검토는 보류합니다.

2-1단계 기본 SDO 읽기·쓰기·복원 및 PDO 회귀를 검증했습니다. SDO Abort 응답 호환성은 [TD-001](Doc/TD/TD-001-sdo-abort-response.md)로 등록하고 구현을 보류합니다.

RF-003 기본 1축 연결을 검증했습니다: CMMT-AS / 기본 PDO, 별도 Python 모델 + Unix 소켓, SDO·CiA 402·Homing·이동·PDO 1,000회 및 SDO/PDO 위치 일치 확인. [구현 및 실행 방법](Doc/RF/RF-003-cmmt-model-integration.md). Motion Server·Axis Panel 통합은 RF-004입니다.

## Motion Server / Axis Panel 수동 테스트

### Linux Docker 실행 (2026-10-26)

실행 인자는 [.env.example](.env.example)을 복사한 `.env`에서 지정합니다. 축 목록·모드·parameter_set까지 모두 같은 `.env`에서 지정합니다. Linux 바이너리와 저장소의 `src/functional_model`·`device_descriptions`를 이미지에 포함합니다. 외부 Motion Server 모델 스냅샷이나 `--model-root`는 사용하지 않습니다.

```bash
test -e .env || cp .env.example .env
nano .env
bash scripts/docker/build.sh
bash scripts/docker/validate.sh
# 기존 native Simulator/Master 세션을 정리한 뒤 실행
bash scripts/docker/start.sh
bash scripts/docker/logs.sh
# 종료: bash scripts/docker/stop.sh
```

Docker의 NIC는 KICKCAT_INTERFACE, 영구 데이터 위치는 DEVICE_SIMULATOR_STATE_DIR에서 설정합니다. 장치는 DEVICE_SIMULATOR_BUS와 DEVICE_SIMULATOR_AXIS_IDS / MODELS / MODES / PARAMETER_SETS로 정의합니다. 최초 Docker 저장소에는 기존 native 파라미터가 자동 복사되지 않습니다. [RF-012 실행 절차와 검증 범위](Doc/RF/RF-012-docker-deployment.md)를 확인하세요. 이미지 빌드·초기화·종료는 검증했으며 물리 PDO 회귀 및 완전한 모델 장애 격리는 후속입니다.

### Docker 운영 스크립트

Motion Server의 start/stop 패턴을 참고해 [scripts/docker](scripts/README.md)에 실행 도구를 모았습니다.

```bash
bash scripts/docker/start.sh --build
bash scripts/docker/status.sh
bash scripts/docker/logs.sh
bash scripts/docker/stop.sh
```

별도 이미지 빌드: `bash scripts/docker/build.sh`. NIC 없는 설정·저장값 검증: `bash scripts/docker/validate.sh` (서비스 정지 상태). 이미지를 다시 만들 필요가 없으면 start.sh의 --build를 생략합니다. start는 기존 컨테이너를 재생성하므로 운전 중 사용하지 않습니다. Motion Server와 Axis Panel은 각 패키지의 실행 도구로 별도 실행합니다.

기존 native/Board/Windows 통합 실행 진입점 11개는 제거했습니다. 빌드 입력 생성·오프라인 검증·로그 분석·SDO 복원 테스트 의존 도구는 유지합니다. [유지·삭제 판단](scripts/README.md)을 참조하세요.

## Omniverse DT 연동 설계 (2026-09-15)

기본 타당성 검증을 완료하고 다음 구조에 합의했습니다. **Motion Server 1개 / 실제·가상 장치 동일 EtherCAT 버스 / 외부 명령·리드백 라우터 / Omniverse 연결부**입니다. Motion Server는 수정 없는 독립 패키지로 유지합니다. 기본 3 Slave 혼합 버스와 실제·가상 장치 선택 동작은 RF-005에서 검증했습니다. 외부 라우터와 모드 전환은 후속 구현입니다.

- [DT-001 전체 구조](Doc/Design/DT-001-system-architecture.md)
- [DT-002 모드 전환과 상태 동기화](Doc/Design/DT-002-mode-switching.md)
- [DT-003 모델 인터페이스와 FMI 확장 방향](Doc/Design/DT-003-model-interface.md)

2026-10-26 모델 실행 구조 결정: **KickCAT Slave 프로세스 ↔ Unix 소켓 ↔ 별도 Model Host**. 어댑터는 라이브러리로 구성하고 Model Host 안에서 Co-Simulation FMU를 호출합니다. 모델 충돌·응답 중단 시 Slave 프로세스를 유지하면서 장애를 명확히 표시하는 것이 목표입니다. Copley FMU의 Linux 단독 실행은 확인했으나 EtherCAT 연동과 장애 격리·복구 구현은 후속입니다. 상세 결정과 미결정 계약은 DT-003을 참조하세요.

실제→가상은 정지한 실제 상태로 모델을 초기화하고, 가상→실제는 실제 장비를 움직이지 않고 현재 실제 상태로 DT를 맞춥니다. 장치 동작은 가상축·가상 IO 모델이 계산하며 FMI는 향후 확장입니다. RF-005는 기본 검증 완료, RF-006~008은 계획 상태로 [RF 목록](Doc/RF/README.md)에서 관리합니다.

양방향 파라미터 동기화와 가상장치 재시작 시 설정 유지 요구를 [DT-004](Doc/Design/DT-004-parameter-sync-persistence.md)에 추가했습니다. RF-009 동기화는 계획 단계이며 RF-010은 기본 저장·복원을 구현하고 후속 검증 중입니다.

[DT-005 독립 장치 구성](Doc/Design/DT-005-device-configuration.md)에 독립 .env 단일 형식(2026-10-26 변경), 별도 설정 소유권, 실제·가상 Slave 배치 및 번호 매핑을 기록했습니다. Motion Server 설정 자동 읽기는 채택하지 않습니다. 구성 로더와 4축 생성의 초기 구현·오프라인 검증을 완료했습니다. [RF-011](Doc/RF/RF-011-device-configuration.md)의 OD 조회 최적화 후 2축·4축 8 ms/120초 정지 상태 재검증을 통과했으며, 2026-10-26 사용자가 4축 동작 정상도 확인했습니다.

[DT-006 Docker 배포](Doc/Design/DT-006-docker-deployment.md): Linux Edge PC의 단일 Simulator 컨테이너, host 네트워크, 외부 설정·영구 저장소를 사용합니다. Edge NIC 3개는 Master / Simulator / 엔지니어링·외부 Omniverse 연결에 각각 사용합니다. [RF-012](Doc/RF/RF-012-docker-deployment.md)는 Docker/.env 초기 실행을 구현하고 물리 통신·저장 회귀 및 장애 격리 검증을 남겨둔 상태입니다.

현재 구현 범위는 **가상축**입니다. RF-011은 독립 .env 설정과 다중 CMMT 축을 담당하며 가상 IO·IO-Link는 [RF-013](Doc/RF/RF-013-virtual-io.md)에 Pending으로 분리했습니다. 기존 IO 설계 예시는 현재 구현 계약이 아니며 별도 재논의합니다.

## .env 4축 구성

장치 구성은 루트 `.env`에서 설정하며 [.env.example](.env.example)을 참고합니다. 개발용 검증 도구도 기본적으로 루트 `.env`를 읽습니다. 별도 파일은 `--env-file`로 지정할 수 있습니다. `config/` 예제 폴더는 제거했습니다.

[RF-011 실행 절차](Doc/RF/RF-011-device-configuration.md#수동-실행과-다음-물리-시험)에 신규 빌드 실행·NIC 없는 검증·물리 시험 순서를 기록했습니다. 현재 자체 모델은 `src/functional_model/cia402_drive/behaviour_model/f_kr_cmmt`에 포함되어 있습니다. [RF-015](Doc/RF/RF-015-axis-model-semantics.md)는 위치 제한/회전 동작 개선을 별도 관리합니다.

## 2026-09-22 성능 계측 결과와 다음 작업

2축은 120초 관측에서 정상 동작했으나 4축은 PDO 처리 지연 및 버스 Fault가 재현됐습니다. [프레임·IPC 계측](Doc/Validation/RF-011/RF-011-timing-20260922.md)과 [Python 세부 계측](Doc/Validation/RF-011/RF-011-python-timing-20260922.md)에 시험 조건과 한계를 기록했습니다. IPC 시간의 약 90%가 모델 계산이며, 별도 오프라인 프로파일에서는 OD role 전체 검색이 모델 시간의 약 97.57%를 차지했습니다.

2026-10-20 OD role 조회 인덱스 최적화를 적용했습니다. [2축/4축 재검증](Doc/Validation/RF-011/RF-011-role-index-20261020.md)은 각각 8 ms·120초 정지 상태에서 Fault 없이 통과했습니다. PDO 처리 평균은 0.223/0.395 ms입니다. 장시간·이동 부하와 나머지 RF-011 기준은 후속이며 IPC 묶음 처리는 미적용입니다.

2026-10-26 사용자가 **최적화 적용 후 4축 동작 테스트 정상**을 확인했습니다. 수동 시험의 상세 시간·모드·WKC 수치는 별도 보고되지 않았으며, RF-011 잔여 완료 기준은 계속 관리합니다.

## RF-016 구현 구조 (2026-10-26)

```text
src/ethercat_slave/                 # C++: EtherCAT Slave + IPC
src/functional_model/
  cia402_drive/
    profile/                       # 공통 OD·PDO 정의
    adapter/                       # F-KR Internal 연결·계약·등록
    behaviour_model/f_kr_cmmt/  # 상태 전이·운동 계산
  runtime/                         # 축 인스턴스와 서비스
  ipc/ storage/ diagnostics/
device_descriptions/cmmt_as/        # 기존 identity·ESI·확장·저장 명령
protocols/ipc/                      # 메시지 계약
```

기존 `.env`, `f_kr_cmmt` 모델 ID 및 저장 파라미터 형식은 유지한다. 내부 프로파일은 cia402-drive지만 BUS 설정은 cia402-drive, 모델 ID는 f_kr_cmmt이며 EtherCAT identity/PDO는 기존 CMMT 호환 값이다. 어댑터는 미지원 운전 모드를 거부한다. 실제 모델 알고리즘은 유지했다. [RF-016](Doc/RF/RF-016-cia402-profile-adapter.md)에 오프라인 검증과 남은 물리 시험을 구분한다.

```bash
bash scripts/linux/build-cmmt.sh     # C++ 변경 시
bash scripts/docker/build.sh
bash scripts/docker/validate.sh
bash scripts/docker/start.sh
```

### Copley FMU 오프라인 검증

FMI3 CS 기반 PP 어댑터와 Linux FMU 빌드 도구의 실행 방법은 [RF-017](Doc/RF/RF-017-copley-fmu.md)을 따른다. `.env`에서 `copley_drive_sim` 선택, FMU 폴더 마운트 및 지원 파라미터 저장을 제공한다. 비물리 통합 검증은 완료했으며 물리 연동 전 IPC 장애 격리가 남아 있다.
