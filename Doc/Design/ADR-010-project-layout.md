# ADR-010 — 프로젝트 폴더 구조와 생성물 보관

- 결정 상태: **채택** (2026-11-26)
- 적용: Linux 기준 소스 구조, Windows 개발 폴더 정리. 동작 모델/IO 기능 확장을 의미하지 않는다.

## 폴더별 책임

| 경로 | 역할 / 보관 내용 | Git |
|---|---|---|
| src/ | 제품 실행 코드 | 포함 |
| src/ethercat_slave/ | ESC·Mailbox·SDO/PDO·매핑·IPC·Slave 진단 | 포함 |
| src/functional_model/ | 프로파일·어댑터·동작 모델 및 공통 실행 기반 | 포함 |
| …/cia402_drive/profile/ | CiA402 OD·PDO 의미와 프로파일 계약 | 포함 |
| …/cia402_drive/adapter/ | 프로파일과 각 동작 모델 사이 값·단위·상태 변환 | 포함 |
| …/cia402_drive/behaviour_model/ | 제품과 함께 실행하는 자체 동작 모델 코드 | 포함 |
| …/cia402_drive/model_definitions/ | 외부 모델 변수·자료형·지원 기능 정의 | 포함 |
| …/remote_io/ | 향후 MDP/IO 기능 영역. profile/adapter/model_definitions 책임 구분. 구현 전 빈 폴더를 만들지 않음 | 향후 포함 |
| …/runtime/fmi/ | 공통 FMI 로딩·호출 기반 | 포함 |
| …/runtime/ | 인스턴스·주기·서비스 실행 관리 | 포함 |
| …/ipc/ | 기능 모델 프로세스 통신 구현 | 포함 |
| …/storage/ | 파라미터 영구화 코드; 실제 저장 데이터는 state | 포함 |
| …/diagnostics/ | 기능 모델 진단·Fault 처리 | 포함 |
| device_descriptions/ | 제품별 Identity·ESI·확장 OD·모듈 설명. cmmt_as 유지, cpx_ap_i_ec는 구현 시 추가 | 포함 |
| model_sources/ | 장치 종류 → 모델 종류별 원본·출처·재현 정보 | 포함 |
| model_sources/motor_controller/copley/ | C 소스 포함 원본 FMU의 URL·커밋·체크섬·설명 | 포함 |
| model_sources/pneumatic_cylinder/double_acting/ | 실린더 Modelica 소스·자동 왕복 데모·원본 정보 | 포함 |
| model_presets/ | 모델 종류·특성을 담는 재사용 JSON. 운전 조건·초기 조건은 .env IO_MODEL_INSTANCES로 분리 | 포함 |
| model_artifacts/ | 실행용으로 선정한 완전한 FMU 파일. 바이너리와 동반 리소스를 함께 유지 | 설명은 포함, FMU 제외 |
| protocols/ | 프로세스 간 메시지 계약 문서 | 포함 |
| third_party/KickCAT/ | 고정된 KickCAT 외부 소스, Git submodule | submodule |
| scripts/docker/ | 운영 시작·종료·상태·이미지 빌드·입력 준비 | 포함 |
| scripts/deployment/ | 배포 묶음 생성·검증·복원 | 포함 |
| scripts/models/ | 동작 모델 빌드·웹용 소스 생성 | 포함 |
| scripts/validation/ | 재사용 가능한 FMU·Slave·성능 검증 도구 | 포함 |
| scripts/linux/ | Linux 전용 native KickCAT/Slave 빌드 | 포함 |
| scripts/windows/ | Windows 전용 SDO 지원 도구 | 포함 |
| tests/unit/ | 단위 회귀 시험 | 포함 |
| tests/integration/ | 프로세스·FMU·Slave 통합 회귀 시험 | 포함 |
| tests/fixtures/ | 시험 입력·기대 데이터 | 포함 |
| docker/ | Dockerfile·서비스 진입점·의존성 잠금 | 포함 |
| docker/inputs/, docker/wheels/ | 고정 Docker 빌드 입력. 오프라인 빌드 계약 때문에 기존 위치 유지 | 생성물 제외 |
| Doc/Design/ | ADR 설계·의사결정 | 포함 |
| Doc/RF/ | 요구사항 본문과 현재 상태. 검증 보고서는 여기 두지 않음 | 포함 |
| Doc/TD/ | 미해결 기술 부채 | 포함 |
| Doc/Validation/ | 완료 판정 보고서·핵심 수치·출처 증거 | 포함 |
| Doc/Work_log.md | 날짜별 작업 이력 | 포함 |
| Doc/project-plan.md | 최신 범위·진행 순서 | 포함 |
| state/ | 운영 장치 파라미터·PDO 매핑. 재생성 가능한 빌드 파일로 취급하지 않음 | 제외 |
| results/<시험>/<실행ID>/ | summary/manifest·로그·CSV·캡처 등 원본 결과. 성공/실패도 같은 실행 단위에 기록 | 제외 |
| build/ | 빌드 산출물·임시 작업 공간. native build/timing 등 참조 경로는 유지 | 제외 |
| .cache/downloads/ | 고정 원본 다운로드 캐시 | 제외 |
| .cache/toolchains/ | OpenModelica 등 로컬 컴파일 도구·설치본 | 제외 |
| .cache/wheels/ | 일반 개발용 Python wheel 캐시. Docker 입력과 구분 | 제외 |
| .env | 해당 호스트의 운영 설정 | 제외 |
| .env.example | 지원 설정의 예시 | 포함 |
| compose*.yaml / CMakeLists.txt / pyproject.toml | 배포·C++ 빌드·Python 패키지 진입 설정 | 포함 |

`…`는 `src/functional_model`을 뜻한다. 모델 소스 경로 분류는 실행 설정의
모델 식별자(copley_drive_sim 등)를 변경하지 않는다. FMU 소스와 Soft ESC 어댑터는
서로 다른 책임이다. 확정된 최상위 폴더만 생성하고 미래 기능의 빈 디렉터리는 만들지 않는다.

## 생성물과 이력 정리 원칙

- 검증된 FMU는 model_artifacts에, 모델 원본과 해시/재현 정보는 model_sources에 둔다.
- 신규 시험의 원본 결과는 results에, 요약/판정은 Doc/Validation에 둔다. 과거 보고서의
  당시 경로는 이력으로 유지하며 과거 실제 실행 명령을 현재 명령으로 꾸며 바꾸지 않는다.
- 재사용하는 시험 도구는 scripts/validation으로 승격한다. 일회성 이관·디버그 스크립트와
  이전 소스 사본·Git 전달 bundle은 활성 build에서 제거하고 외부 보관한다.
- 실패 로그도 원인 분석의 근거가 될 수 있다. 실패했다는 이유만으로 삭제하지 않는다.
- Windows의 과거 체크아웃은 .git·미커밋 파일·생성물까지 통째로 외부 보관한 뒤 최신
  Linux 기준으로 재구성한다. 보관 위치와 이동 목록은 cleanup-manifest.json에 남긴다.
- 외부 보관 루트: 저장소 옆 ethercat-device-simulator-archive/날짜별 작업 디렉터리.
  acontis 평가판도 현재 제품 실행 의존성이 아니므로 외부 참고 자료로 보존한다.
- Linux 운영 state/.env/모델 파일과 실행 중 Docker는 이동·재시작하지 않는다.
  Linux의 기존 build 가상환경·native 바이너리는 검증 도구가 사용하므로 유지한다.

## 검증

경로 참조 검사, Python 단위 회귀, C++ 회귀, 실린더 FMI3 오프라인 5개 시험,
Copley 소스 빌드와 FMU 회귀, Docker 이미지 빌드를 수행한다. NIC 물리 시험이나
운영 컨테이너 교체는 이 구조 변경 작업에 포함하지 않는다.
