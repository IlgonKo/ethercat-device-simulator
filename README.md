# Soft ESC — EtherCAT Device Simulator

Soft ESC는 **FMU 또는 다른 형식의 동작 모델을 EtherCAT 장치 프로파일에 연결하여, EtherCAT Master가 제어할 수 있는 가상 장치를 제공하는 독립 실행 패키지**입니다. **CiA402 Drive와 EtherCAT Modular Device Profile 기반 Remote I/O**를 지원 대상으로 합니다.

장치 프로파일·제품별 장치 설명·모델 어댑터·동작 모델을 분리합니다. DT Demo, Motion Server, Orchestrator, ROS2/Omniverse는 외부 사용 시스템이며 실행 의존성이 아닙니다. 저장소·이미지·설정 키 이름은 기존 `ethercat-device-simulator`/`DEVICE_SIMULATOR_*`를 유지합니다.

## 제품 범위와 구현 상태 — 2026-11-25

| 영역 | 현재 상태 |
| --- | --- |
| KickCAT 기반 EtherCAT·SDO/PDO·실제/가상 혼합 버스 | 기존 합의 범위 검증 완료 |
| CiA402 Drive·F-KR CMMT·Copley FMI3 Co-Simulation | 모델별 지원 범위 구현·검증 완료 |
| 독립 .env·영구 파라미터·동적 PDO 저장·축 Fault/Host 장애 격리 | 기존 축 범위 검증 완료 |
| Modular Device Profile 기반 Remote I/O | 제품 범위 확정, RF-013 구현 진행 대상. 현재 실행 코드에는 미구현 |
| IO 어댑터·동작 모델 | CPX-AP-I DI/DO/AI/AO 연결 구현 준비. 복동 실린더 FMI3 Linux 오프라인 검증 완료, IO 연결 미구현. IO-Link 제외 |
| Linux Docker | 기존 축 배포·비교 검증 완료. 새 PC·축+IO 배포 검증 잔여 |

실린더 모델의 출처·소스·Export·재검증 절차는 [모델 README](model_sources/pneumatic_cylinder/double_acting/README.md), 결과는 [Linux FMU 검증 보고서](Doc/Validation/Pneumatic-Cylinder-Web-FMU-20261125.md)를 참조합니다.

지원 대상 정의가 모든 모델·모듈·Master에 대한 적합성 검증 완료를 의미하지는 않습니다. 현재 Copley의 기능 제약과 모델별 지원표는 각 RF를 따릅니다.

DT Demo의 X1/Y/Z 3축과 Loader는 요구 대조·시험 사례입니다. 제품 축 수를 3으로 제한하거나 Remote I/O를 Loader 전용으로 만들지 않습니다. 제품 구조는 [ADR-001](Doc/Design/ADR-001-system-architecture.md), 현재 구현과 다음 작업은 [프로젝트 계획](Doc/project-plan.md)를 기준으로 합니다.

## 프로젝트 문서

- [아키텍처 결정 기록(ADR)](Doc/Design/README.md): 결정·근거·책임 경계
- [작업 일지](Doc/Work_log.md): 진행 결과, 결정 사항 및 후속 작업
- [RF 항목 목록](Doc/RF/README.md): Soft ESC 구현 상태·잔여 작업과 외부 구상 이력
- [TD 항목 목록](Doc/TD/README.md): 보류한 기술 문제와 해결 기준
- [설계 및 진행 계획](Doc/project-plan.md): 목적, 실행 구성 및 모듈 책임
- [프로젝트 계획](Doc/project-plan.md) · [Demo 입력 분석 자료](Doc/DT-demo-gap-analysis.md)

## 초기 타당성 검증 이력 — 현재 제품 범위와 구분

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

Docker의 NIC는 KICKCAT_INTERFACE, 영구 데이터 위치는 DEVICE_SIMULATOR_STATE_DIR에서 설정합니다. 장치는 DEVICE_SIMULATOR_BUS와 DEVICE_SIMULATOR_AXIS_IDS / MODELS / MODES / PARAMETER_SETS로 정의합니다. 최초 Docker 저장소에는 기존 native 파라미터가 자동 복사되지 않습니다. [RF-012 실행 절차와 검증 범위](Doc/RF/RF-012-docker-deployment.md)를 확인하세요. 기존 축의 이미지 빌드·물리 PDO·Host 장애 격리는 검증했으며 신규 IO는 별도 회귀 대상입니다.

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

## 독립 패키지의 구조와 외부 사용 경계

KickCAT Slave와 Functional Model Host는 별도 프로세스이며 어댑터/동작 모델은 Host 안에서 실행합니다. 모델 Host 장애 중 Slave 유지와 수동 복구는 RF-018 범위로 검증했습니다. 자체 모델과 Copley FMU의 지원 범위는 RF-016/017을 따릅니다.

CiA402 Drive와 Modular Remote I/O는 장치 프로파일 영역으로 구분합니다. Remote I/O의 모듈/채널은 장치 인터페이스, 밸브/실린더 등 동작은 어댑터와 동작 모델의 책임입니다. RF-013에서 공통 실행부의 축 전용 가정을 분리하고 IO를 연결합니다.

외부 모드 라우팅·Pairing·정렬·시퀀스·ROS2/Omniverse는 Soft ESC 기능에 포함하지 않습니다. 과거 RF-006~009는 외부 구상 이력으로 보존합니다. 현재 구현은 일반 SDO/PDO·장치 명령·피드백과 독립 저장/실행을 제공합니다.

- [제품 구조](Doc/Design/ADR-001-system-architecture.md) · [모델 실행](Doc/Design/ADR-003-model-interface.md) · [프로파일/어댑터](Doc/Design/ADR-007-cia402-profile-adapters.md)
- [장치 구성](Doc/Design/ADR-005-device-configuration.md) · [영구 저장](Doc/Design/ADR-004-parameter-sync-persistence.md) · [독립 Docker](Doc/Design/ADR-006-docker-deployment.md)

## .env 4축 구성

장치 구성은 루트 `.env`에서 설정하며 [.env.example](.env.example)을 참고합니다. 개발용 검증 도구도 기본적으로 루트 `.env`를 읽습니다. 별도 파일은 `--env-file`로 지정할 수 있습니다. `config/` 예제 폴더는 제거했습니다.

[RF-011 실행 절차](Doc/RF/RF-011-device-configuration.md#정지-후-재구성-절차)에 신규 빌드 실행·NIC 없는 검증·물리 시험 순서를 기록했습니다. 현재 자체 모델은 `src/functional_model/cia402_drive/behaviour_model/f_kr_cmmt`에 포함되어 있습니다. [RF-015](Doc/RF/RF-015-axis-model-semantics.md)는 직선축 요구 대조·회귀를 관리하며 회전 확장은 보류합니다.

## 2026-09-22 성능 계측 결과와 다음 작업

2축은 120초 관측에서 정상 동작했으나 4축은 PDO 처리 지연 및 버스 Fault가 재현됐습니다. [프레임·IPC 계측](Doc/Validation/RF-011/RF-011-timing-20260922.md)과 [Python 세부 계측](Doc/Validation/RF-011/RF-011-python-timing-20260922.md)에 시험 조건과 한계를 기록했습니다. IPC 시간의 약 90%가 모델 계산이며, 별도 오프라인 프로파일에서는 OD role 전체 검색이 모델 시간의 약 97.57%를 차지했습니다.

2026-10-20 OD role 조회 인덱스 최적화를 적용했습니다. [2축/4축 재검증](Doc/Validation/RF-011/RF-011-role-index-20261020.md)은 각각 8 ms·120초 정지 상태에서 Fault 없이 통과했습니다. PDO 처리 평균은 0.223/0.395 ms입니다. 현재 구조의 정량 성능·이동 부하 검증은 RF-016/017에서 추적합니다. 이 수치는 당시 정지 시험 결과입니다.

2026-10-26 사용자가 **최적화 적용 후 4축 동작 테스트 정상**을 확인했습니다. 수동 시험의 상세 시간·모드·WKC 수치는 별도 보고되지 않았으며, RF-011은 기존 구성·독립성 및 RF-010/018 근거를 종합하여 2026-10-28 완료 처리했습니다.

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

기존 `.env`, `f_kr_cmmt` 모델 ID 및 저장 파라미터 형식은 유지한다. 내부 프로파일은 cia402-drive지만 BUS 설정은 cia402-drive, 모델 ID는 f_kr_cmmt이며 EtherCAT identity/PDO는 기존 CMMT 호환 값이다. 어댑터는 미지원 운전 모드를 거부한다. 실제 모델 알고리즘은 유지했다. [RF-016](Doc/RF/RF-016-cia402-profile-adapter.md)에 기존 구조와 완료된 물리 검증 근거를 기록한다.

```bash
bash scripts/linux/build-cmmt.sh     # C++ 변경 시
bash scripts/docker/build.sh
bash scripts/docker/validate.sh
bash scripts/docker/start.sh
```

### Copley FMU 오프라인 검증

FMI3 CS 기반 PP 어댑터와 Linux FMU 빌드 도구의 실행 방법은 [RF-017](Doc/RF/RF-017-copley-fmu.md)을 따른다. `.env`에서 `copley_drive_sim` 선택, FMU 폴더 마운트 및 지원 파라미터 저장을 제공한다. 혼합 물리 PP·저장·Fault/Reset 및 RF-018 IPC 장애 격리를 확인했다. 세부 물리 이동·파라미터 효과와 정량 성능 근거는 RF-017에 남는다.

폴더 역할과 생성물 보관 정책: [ADR-010](Doc/Design/ADR-010-project-layout.md).
