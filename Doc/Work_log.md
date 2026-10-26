# 작업 일지

프로젝트: EtherCAT Device Simulator

작업 결과, 결정 사항 및 후속 항목을 날짜별로 기록한다. 아래 초기 이력은 2026-09-14의 기존 문서·실행 기록을 정리한 것으로, 이번 문서 정리 중 통신 시험을 다시 실행한 것은 아니다.

## 2026-09-14

| 항목 | 작업 및 결과 | 상태 / 후속 |
| --- | --- | --- |
| 실행 구성 | Windows PySOEM/Motion Server와 별도 Linux KickCAT을 물리 케이블로 직결. Linux enp1s0, 관리 SSH는 eno1 사용 | acontis 보류, MockMaster 유지 |
| [RF-001](RF/RF-001-linux-kickcat.md) | KickCAT 고정 revision 빌드, 내부 예제 및 enp1s0 실행·종료 확인. 일반 IPv4/IPv6 주소 차단 제거, SSH NIC 보호 유지 | 완료. 이 시험 자체는 외부 Master 통신 검증이 아님 |
| [RF-002](RF/RF-002-windows-pdo-diagnostic.md) | 0x1C00 정렬을 명시한 테스트 ESI로 Slave 검색·OP 전환·PDO 1,000회 교환, 매회 WKC=3 확인 | 완료. 입력 12 / 출력 3바이트, CMMT 동작 검증은 아님 |
| [RF-002-1](RF/RF-002-1-sdo-diagnostic.md) | SDO 읽기, assignment count 쓰기·원복, PDO 회귀 성공. 복원 실패 경로 단위 검사 3개 통과 | 기본 경로 완료. Abort 오류 경로 제외 |
| [TD-001](TD/TD-001-sdo-abort-response.md) | RO 쓰기 실패를 캡처. CoE 서비스 2, 명령 0x83, Abort 0x06010002 및 PySOEM PacketError 확인 | 공개 자료로 서비스 2는 정상, 명령은 0x80이어야 함을 확인. 수정은 보류 |
| [RF-003](RF/RF-003-cmmt-model-integration.md) | 기존 VirtualOdBridge·OD·가상 서보 연결 범위 및 결정 사항 등록 | 계획 / 미착수 |
| [RF-004](RF/RF-004-motion-server-axis-panel.md) | Motion Server·Axis Panel 실제 통신 및 MockMaster 비교 시나리오 등록 | 계획 / 미착수 |
| 문서 구조 | 기존 docs 문서를 Doc으로 이동. RF 4단계와 SDO 하위 항목, TD-001, 목록 및 작업 일지 구성 | 기존 명령·결과·run ID·캡처 근거 유지, README 링크 갱신 |

### 이번 결정

- SDO Abort 문제는 TD-001에 등록하고 추후 처리한다. 응답 보정 구현은 착수하지 않는다.
- 보정 시 CoE 서비스를 0x03으로 변경하지 않는다. Abort 명령 0x83의 하위 비트를 정규화하는 방향을 검토한다.
- KickCAT upstream 직접 수정보다 래퍼를 선호한다. 구체적인 후킹 방식은 미확정이다.
- RF-001/002와 정상 SDO 경로의 완료를 CMMT 모델·통합·실시간 성능의 완료로 확대하지 않는다.

### 다음 작업

RF-003 구현 전에 CMMT ESI/PDO, C++·Python 연결, OD 단일 기준, 모델 갱신 순서와 시간 기준을 결정한다. TD-001은 재개 결정 후 구현·재캡처·회귀 시험을 수행한다.

## 2026-09-14 — RF-003 구현 및 물리 검증

- 사용자 선택: CMMT-AS 1축 / motion_server_default PDO, 별도 Python 프로세스 + Unix 소켓.
- Linux 기존 Motion Server에 VirtualOdBridge가 없어 Windows commit da0b0a3의 의존 소스를 build 아래 별도 테스트 경로로 준비했다. 두 Motion Server 작업 트리는 수정하지 않았다.
- 프로젝트 자체 C++ 실행 파일과 Python 모델 서비스를 구현했다. 기존 VirtualOdBridge·VirtualCiA402Servo를 직접 import하며 KickCAT upstream은 수정하지 않았다.
- 생성 fixture에서 모델 객체 46개, Rx 24 / Tx 14바이트 및 명시적인 CA 정렬을 연결했다. 모델 OD가 장치 값의 기준이며 C++ 통신 버퍼와 구분한다.
- 초기 Slave 검색 실패는 Master용 수신 함수의 header length 초기화가 원인이었다. 원본 프레임 수신으로 수정했다. PDO mapping 실패는 자동 생성 assignment/mapping의 bit offset 8이 원인이었고 생성 ESI에서 bit offset 16을 명시했다.
- 새 binary capability는 사용자가 설정했고, 수신 경로 수정 후 재빌드 시 다시 설정했다.
- 최종 CMMT run `d1ffde3ad7ec4ba5b9a82dcb49abe0ca`: SDO 쓰기·복원, OP, CiA 402 Enable, Homing, target 10000 / actual 9999, 총 1,026 PDO 교환 WKC=3, SDO/PDO 위치 일치, 정상 정리.
- Board 회귀 run `99315fa2aabd49dea2d789305ef2fd24`: SDO 읽기·쓰기·복원 + PDO 1,000회 통과.
- Windows 단위/모델 테스트 11개 통과. Linux 신규 모델 테스트 8개 통과. Linux 전체 discovery의 기존 Windows 테스트 1개 모듈은 PySOEM 미설치로 import 실패했으며 Windows에서 검증했다.
- 상태: RF-003 기본 1축 경로 완료. 오류 응답 완료 기준은 TD-001에 따라 보류. 고정 PDO 범위이며 remapping·전체 OD·실시간 성능 검증은 미완료.
- 다음: RF-004에서 Motion Server 초기화·PDO 재설정 요구를 먼저 확인한 뒤 Axis Panel 통합 진행. TD-001 보류 유지, MockMaster 유지.

## 2026-09-14 — RF-004 기본 통합 검증

- 기존 Motion Server가 PRE-OP에서 PDO mapping/assignment를 재설정하는 것을 확인했다. simulator에 동일 기본 설정 clear/rewrite/restore를 허용하는 FixedMapping 검증을 추가했다. 임의 재매핑과 PRE-OP 외 변경은 거부한다. Motion Server와 KickCAT upstream은 수정하지 않았다.
- C++ 빌드 및 정상/거부 단위 검증을 마친 뒤 사용자가 새 binary의 NIC capability를 설정했다.
- 테스트 전용 실행 래퍼는 기존 `.env.example`과 명시 환경을 사용한다. 사용자 활성 `.env`를 수정하지 않는다. CMMT-AS 1축, PP/basic, 10 ms, FreeRun/DC off, TCP 15100으로 구성했다.
- 기존 Axis Panel client와 GUI 클래스로 상태·제어권·Enable·Homing·10 mm 이동 및 표시·이동 중 Stop·Fault Reset 명령·Disable을 검증했다. GUI는 숨긴 상태에서 실제 이벤트 루프와 callback을 검사했다.
- 초기 시험의 Homing 실패는 서버가 이미 Enable한 축을 시험에서 토글해 Disable한 것이 원인이었다. 초기 Disable 확인 후 Enable하는 시험 순서로 수정했다. Fault Reset 대기는 GUI가 응답을 먼저 소비한 시험 관측 문제였고 기록용 client 관측을 추가했다. 두 문제 모두 제품 코드를 바꾸지 않고 시험 코드에서 해결했다.
- PySOEM 실통신 run `5068d8c5adde44efb16fa4699c4e6a0a`: 10.000 mm 표시, 이동 중 23.429 mm에서 정지, Fault Reset ok=true, 정상 정리.
- Mock 비교 run `2d2c4de4d67948d79dc86facdc1aac32`: 같은 시나리오 통과, 10.000 mm 표시, 약 20 mm에서 정지. 통신·명령 시점 차이가 있으므로 정지 위치의 정확한 동등성은 요구하지 않았다.
- RF-003 회귀 run `f958abe28ad343089ac2310c4bdf66b5` 통과. Windows Python 테스트 11개 및 C++ mapping 계약 테스트 통과.
- 한 명령으로 Linux 모델/시뮬레이터·Windows 서버·선택적 Panel을 시작하는 수동 런처를 추가했다. 창 없는 2초 시작·종료 run `cca1184ec7ff4816b9c00d1dbf7f8a30`에서 정상 정리를 확인했다.
- 상태: RF-004 기본 통합 경로 완료. Fault Reset은 정상 상태에서의 명령 경로 검증이며 실제 Fault 주입 후 복구는 후속이다. TD-001 보류, MockMaster 유지. Node-RED 시험은 수행하지 않았다.
- 문서와 코드는 Windows/Linux 저장소에 반영한다. 커밋·푸시는 수행하지 않는다.

## 기록 작성 형식

이후 작업은 날짜, 관련 RF/TD, 수행 내용, 검증 근거, 결정 사항, 남은 작업을 함께 기록한다. 상태를 변경할 때 해당 RF/TD 문서와 목록도 갱신한다.


## 2026-09-15 — 수동 CMMT 세션 실행 제한 제거

- `cmmt-session.py` 기본 실행 시간을 무제한으로 변경하고 `--timeout` 옵션(초, 0은 무제한)을 추가했다.
- 자동 CMMT 진단 및 통합 런처는 `--timeout 600`을 명시해 기존 제한을 유지한다.
- 수동 종료는 `stop` 또는 Ctrl+C를 지원하며 모델·시뮬레이터 정리를 수행한다.
- 검증: Python 구문 확인, Linux 실제 시뮬레이터의 기본 세션 stop 종료·Ctrl+C 종료·명시적 2초 timeout 종료 및 자식 프로세스 정리 통과. C++ 재빌드는 수행하지 않았다.


## 2026-09-15 — DT 연동 구조 및 전환 정책 문서화

- 사용자 합의: Motion Server 독립 패키지 유지, 단일 서버·동일 버스의 실제/가상 그룹을 외부 명령·리드백 라우터로 선택한다. NIC 전환·서버 두 개 방식은 현재 채택하지 않는다.
- [DT-001](Design/DT-001-system-architecture.md), [DT-002](Design/DT-002-mode-switching.md), [DT-003](Design/DT-003-model-interface.md)를 추가했다.
- 정지 상태에서 실제→가상 모델 초기화, 가상→실제 현재 상태 수용을 확정했다. 실제 자동 위치 이동과 진행 명령 인계는 하지 않는다.
- Omniverse는 선택된 피드백을 표현하고 장치 계산은 기존 가상축·가상 IO가 담당한다. FMI는 향후 호환 방향이며 상세 사양은 미결정이다.
- [RF 목록](RF/README.md)에 RF-005~008을 미착수로 등록하고 전체 계획과 README를 연결했다. 혼합 버스·서버 그룹 제어는 아직 미검증이며 기존 feasibility 완료와 구분한다.
- 문서만 변경했다. 신규 기능 구현이나 장비 시험은 수행하지 않았다. TD-001 보류 및 MockMaster 유지.

## 2026-09-15 — 양방향 파라미터 동기화·영구 저장 요구 추가

- 사용자 요청에 따라 실제→가상 및 가상→실제 파라미터 동기화와 가상장치 재시작 시 설정 유지 요구를 [DT-004](Design/DT-004-parameter-sync-persistence.md)에 등록했다.
- [RF-009](RF/RF-009-parameter-sync.md), [RF-010](RF/RF-010-parameter-persistence.md)을 미착수로 등록했다.
- 배포 기본값·장치별 영구 파라미터·실행 상태를 구분하고 build/임시 폴더 밖에 저장한다. 저장 형식·경로 상세는 미결정이다.
- 기존 서버 공개 API 지원과 초기화 재기입 충돌을 RF-005 확인 항목에 추가했다. 문서만 변경했으며 실제 파라미터 읽기·쓰기 또는 기능 구현은 수행하지 않았다.

## 2026-09-15 — 독립 .env 구성 및 실제·가상 버스 매핑 문서화

- [DT-005](Design/DT-005-device-configuration.md) 추가: 설정 문법은 Motion Server와 맞추되 파일·로더 의존을 만들지 않는다. 자동 .env 페어링 옵션은 제외한다.
- 실제 축 Slave 0~4·IO 5, 가상 축 6~10·IO 11 / Simulator 로컬 0~5 예시와 서버 Axis·IO ID·영구 장치 ID의 차이를 기록했다.
- [RF-011](RF/RF-011-device-configuration.md)을 등록하고 RF-005/006 및 계획·문서 목록을 연결했다.
- 문서만 변경했다. 설정 예시는 미구현 규격이며 12 Slave 혼합 통신이나 CPX 모델이 검증됐다는 의미가 아니다.

## 2026-09-15 — Docker 배포 방향 및 Edge NIC 구성 문서화

- [DT-006](Design/DT-006-docker-deployment.md)과 [RF-012](RF/RF-012-docker-deployment.md)을 추가했다. Linux Docker Engine에서 KickCAT C++/Python 모델 단일 컨테이너, host 네트워크, 명시적 NIC 선택, 필요한 capability를 기준으로 한다.
- 외부 read-only 설정 파일, 영구 파라미터 볼륨, 임시 Unix 소켓을 구분했다. 시험용 stdin 의존 supervisor 대신 서비스용 시작·종료·실패 관리자를 계획했다.
- Edge NIC 3개 및 별도 Omniverse PC, 실제 체인 마지막에 Simulator 연결하는 배치를 기록했다.
- 링크 및 Windows/Linux 문서 일치를 검증한다. 이번 변경은 문서뿐이며 Docker 빌드·배포·실제 장비 시험은 수행하지 않았다.

## 2026-09-22 — 실제·가상 혼합 환경 정상 동작 보고

- 사용자가 실제 장비와 가상장비 혼합 환경의 정상 동작을 확인했다.
- [RF-005](RF/RF-005-mixed-bus-feasibility.md)에 사용자 확인 근거와 직전 3 Slave 구성 맥락을 기록하고 기본 혼합 동작 확인 상태로 갱신했다.
- 성공 로그·WKC·성능 수치 또는 12 Slave/가상 IO 검증을 새로 확보한 것은 아니다. 그룹 제어·파라미터 API 등의 미완료 항목은 유지한다.

## 2026-09-22 — RF-005 완료 전 점검

- 기존 서버의 축/IO 선택 명령·피드백·파라미터 API를 읽기 전용으로 조사했다. 시작 시 전체 Enable과 단일 축 restart의 전체 Disable 영향을 확인했다.
- Linux CMMT 세션의 프로세스·준비 로그·버전을 확인하고 [RF-005](RF/RF-005-mixed-bus-feasibility.md)에 근거와 잔여 확인을 기록했다. 준비 로그를 OP/WKC 검증으로 취급하지 않았다.
- 장비 명령·재시작·코드 변경은 수행하지 않았으며 RF-005 완료 상태는 보류했다.

## 2026-09-22 — RF-005 선택 제어·IO 읽기 사용자 확인

- 사용자가 실제/가상 축 양방향 선택 제어 시 비선택 축 유지와 실제 CPX IO 입력 읽기를 확인했다.
- [RF-005](RF/RF-005-mixed-bus-feasibility.md)에 사용자 확인 근거를 추가했다. 성공 세션 WKC·시험 시간·주기 등 기록은 미확보 상태를 유지한다. 장비 시험이나 제품 코드 변경은 수행하지 않았다.

## 2026-09-22 — RF-005 5분 관측 및 기본 범위 완료

- 실행 중인 서버에 제어권 없는 읽기 전용 TCP 관측을 수행했다. 설정 8 ms, 300.043초, WKC 표본 298회 모두 9/9, 피드백 5,358개 모두 유효했다.
- [관측 보고서](RF/RF-005-observation-20260922.md)에 시간·원본 위치·표본 관측 한계를 기록했다. 사용자 동작 확인과 합쳐 기본 3 Slave 타당성 범위를 완료 처리하고 다장치·영구 저장·전체 주기 성능은 후속으로 구분했다.
- 제품 코드·장비 설정 변경 및 동작 명령은 없었다. 관측 연결만 종료했으며 서버·시뮬레이터는 종료하지 않았다.

## 2026-09-22 — RF-005 완료 기준 및 이관 정리

- [RF-005](RF/RF-005-mixed-bus-feasibility.md)를 최종 완료 범위·근거 중심으로 정리하고 과거 완료 보류 문구의 혼동을 제거했다.
- 미체크 제품화/확장 항목은 RF-006/007/009/010/011/012로 명시적으로 이관하고 수신 문서에도 기록했다. 전체 주기 성능 계측은 번호 미부여 후속으로 남겼다.
- 추가 장비 시험이나 코드 변경은 수행하지 않았다. 기본 3 Slave 완료 판정과 표본 관측 한계는 유지한다.

## 2026-09-22 — Simulator JSON 구성 채택

- 사용자 결정에 따라 기존 동일 .env 문법 채택을 대체하고 [DT-005](Design/DT-005-device-configuration.md)를 JSON 단일 형식으로 갱신했다. 과거 작업 일지의 .env 기록은 결정 이력으로 유지한다.
- DT-001/006, RF-011/012, 문서 목록·전체 계획을 일치시켰다. 장치 배열 순서·영구 ID·독립 패키지·별도 파라미터 저장 원칙을 기록했다.
- 상세 JSON 예시는 초안임을 명시했다. 이번 작업은 문서 변경이며 설정 로더·Docker·장치 코드는 변경하지 않았다.

## 2026-09-22 — JSON slave_index 명시 결정

- 사용자 합의에 따라 DT-005 예시에 slave_index를 추가하고 RF-011·전체 계획을 수정했다. 배열 순서 기반 초안은 대체한다.
- 0부터 연속인 필수 정수로 검증하고 해당 값 순으로 생성한다. 영구 id와 전체 버스 번호는 구분한다. 상세 JSON의 나머지 제안 필드는 아직 확정 전이다.
- 문서만 변경했으며 코드나 실행 중 장비에는 변경이 없다.

## 2026-09-22 — 가상축 범위 확정 및 IO 보류

- 사용자 요청에 따라 RF-011을 가상축으로 제한하고 [RF-013](RF/RF-013-virtual-io.md)에 IO/IO-Link 관련 논의를 Pending으로 등록했다. 센서별 ID·저장소 제안은 확정하지 않았다.
- DT-005·DT-004에 최근 축 JSON 및 parameter_set 저장 공간 규칙을 반영했다. initial preset·별도 스케일은 현 계약에서 제외하고 쓰기/저장을 분리했다.
- 실제 CPX 혼합 시험 이력과 장기 IO 목표는 유지한다. 문서만 변경했으며 IO 또는 축 코드를 구현하지 않았다.

## 2026-09-22 — RF-014 동적 PDO 매핑 등록

- 사용자 요청에 따라 [RF-014](RF/RF-014-dynamic-pdo-mapping.md)를 계획/미착수로 등록했다.
- 유효한 재매핑의 배치 갱신·OP/PDO 검증과 잘못된 요청의 정상 Abort를 분리해 완료 기준에 명시했다. RF-004 및 TD-001에 역참조를 추가했다.
- 문서만 변경했다. 매핑 코드·JSON 스키마·장비 상태는 변경하지 않았다.

## 2026-09-22 — RF-011 4축 검증 목표 및 회전축 점검

- 사용자 요청으로 CMMT-AS 검증 목표를 2축에서 4축으로 변경했다.
- 회전축 기본 OD·공통 계산·wrap 미지원 및 PV 위치 한계 초과 시 계속 이동하는 현재 동작을 오프라인으로 확인해 RF-011에 기록했다. 실제 장비 명령 및 모델 코드 변경은 없었다.

## 2026-09-22 — 회전축 위치 제한 설명 정정

- [RF-011](RF/RF-011-device-configuration.md)에 181° 목표 거부는 변경 가능한 Position_limit 기본값에 따른 결과이며 모델 고유 한계가 아님을 명시했다.
- 공통 수치 계산과 OD 단위/스케일을 구분하고, PP/CSP 목표 검사·PV 자동 정지 부재·Jog 감속·공통 상태 표시의 코드상 차이를 기록했다. 실제 CMMT 사양과의 일치는 미확인이다.
- 문서만 변경했으며 모델 코드·파라미터·실제 장비 상태는 변경하지 않았다.

## 2026-09-22 — RF-011 확정 계약 및 4축 초기 구현

- 합의한 linear 2축/rotary 2축, PDO 필드 제거, --config, storage.directory 상대 경로, 시작 시 검증·구성, 마지막 저장 파라미터 복원 및 운전 상태 초기화를 DT-005/RF-011에 반영했다.
- 모델 위치 제한/회전 경로 개선은 RF-015로 분리했다. 기존 모델 동작은 변경하지 않았다.
- JSON 로더, 축별 Python 모델/OD/PDO와 C++ 다중 ESC·IPC 라우팅, RF-010 기본 저장/복원을 구현했다. 실제 CMMT 오류 응답 TD-001 및 임의 PDO RF-014 범위는 유지했다.
- Python 회귀/4축 모드·저장 검증, Linux 빌드·C++ 메모리 내 4 ESC 라우팅, C++/Python 4축 계약 검증을 수행했다. Linux 전체 Python discovery는 Windows 진단 테스트의 pysoem 미설치로 실패했으며 변경 관련 테스트를 별도로 통과했다.
- 검증 바이너리는 build/rf011에 분리했다. 기존 실행 세션/물리 장비/서버 설정을 변경하지 않았고 물리 4축 시험은 미수행이다. 모델 소스의 독립 패키지 분리 및 RF-010 전체 완료 기준은 남아 있다.

## 2026-09-22 — 수동 세션 run-id 재사용 수정

- 같은 run-id의 로그 폴더가 남아 있으면 FileExistsError로 종료되던 문제를 수정했다. 폴더 생성 시 충돌하면 숫자 접미사로 새 폴더를 예약하고 실제 경로를 출력한다.
- 이전 로그·파라미터는 덮어쓰지 않는다. 실행 중 NIC 소유권 및 세션 잠금 검사는 유지한다. 폴더 생성만 임시 경로에서 검증하며 실제 Simulator를 시작하지 않았다.

## 2026-09-22 — 사용자 4축 수동 동작 시험 완료 보고

- four-axes.json 수동 실행 안내 후 사용자가 동작 테스트 완료를 보고했다. RF-011에 사용자 확인 근거로 기록했다.
- 세부 축/모드별 결과, WKC·시간·주기, 저장 후 재시작 복원은 별도 확인 대상으로 유지한다. 코드·장비 상태를 변경하거나 RF 전체를 완료 처리하지 않았다.

## 2026-09-22 — Simulator 2축/4축 프레임·IPC 계측

- 선택적 --timing과 별도 build/timing 바이너리를 추가했다. 수신→응답, 응답 후 모델 처리, 축별 cycle/idle/SDO IPC, 로그 출력 비용을 1초마다 집계한다. 기존 IPC 순차 처리 구조는 유지했다.
- 사용자 NIC 권한 설정·기존 서비스 종료 확인 후, 기존 실제 축/IO를 포함해 각 120초 관측했다. 이동 명령이나 저장 명령은 보내지 않았으며 기존 Master 시작 절차는 실행됐다.
- 2축 PDO 처리 평균/최대 2.489/5.879 ms, Fault 없음. 4축 5.411/11.509 ms, 8 ms 초과 16회와 BUS_PROCESS_DATA_INCOMPLETE 재현. BUS_CONNECTION_LOST는 두 시험에서 없었다.
- 최초 Fault 창에는 PDO 처리 8 ms 초과가 없고 수신 간격 16.823 ms가 관측되어 단일 원인으로 확정하지 않는다. 자세한 시간·계측 범위·원본은 RF-011-timing-20260922.md에 기록했다.
- 테스트용 Master/Simulator는 정상 종료했다. Motion Server 소스·사용자 .env·Linux에서 수정한 기존 2축 JSON은 변경하지 않았다. 계측용 설정과 테스트 로그는 별도 보관했다.

## 2026-09-22 — Python 모델/변환/JSON/응답 시간 분리

- --timing에서 Python 경과/스레드 CPU 계측을 추가하고 wire 형식·모델 동작은 유지했다. PDO 응답 일치 테스트를 포함해 모델 서비스 테스트 9개 통과.
- 2축 120초, 4축은 약 103초에 연결 상실로 관측 종료. 모델 계산 비중은 IPC 왕복 대비 89.90%/90.46%였다.
- 모든 물리 시험 종료 후 오프라인 cProfile로 OD role 전체 검색 병목(7,400개, 주기당 4회, 모델 누적 시간 약 97.57%)을 확인했다. 최적화는 적용하지 않았다.
- RF-011-python-timing-20260922.md와 원본 로그·프로파일을 보관했다. 테스트용 프로세스는 정상 종료했으며 기존 사용자 설정은 유지했다.

## 2026-09-22 — 문서 및 구현 커밋 정리

- README·RF 목록·전체 계획을 현재 구현 및 측정 결과와 일치시켰다. RF-005 기본 혼합 검증 완료와 RF-011 4축 안정성 개선 필요 상태를 구분했다.
- 독립 JSON·다중 가상축·영구 파라미터·C++/Python 계측 구현과 테스트, 설계/RF/TD 문서를 함께 버전 관리한다. OD role 조회 최적화와 묶음 IPC는 아직 구현하지 않았다.
- 원격 main의 기존 KickCAT 서브모듈 및 Acontis 자료를 보존했다. 실행 로그·빌드 결과·모델 소스 복사본·사용자 영구 상태는 커밋 대상에서 제외한다.
- 커밋 전 회귀 검증: Windows Python 테스트 28개, Linux C++ 테스트 2개 통과.

## 2026-10-20 — OD role 조회 최적화 및 2축/4축 재검증

- Simulator 각 OD에 초기 role 인덱스를 설치하고 define/overlay 시 무효화, 다음 조회 시 재구성한다. 값 캐시·외부 모델 소스 수정·IPC 묶음 처리는 하지 않았다.
- Windows Python 33개, Linux 관련 30개 통과. 사용자 설정과 테스트 fixture를 분리했다.
- 사용자 정지 확인 후 8 ms/120초 물리 비교: 2축 WKC 12/12, 4축 18/18, 각 120표본 모두 정상·Fault/invalid feedback 없음. PDO 처리 평균 0.223/0.395 ms, 최대 0.596/0.853 ms.
- 오프라인 2,000회 비교: 모델 평균 1.1498→0.00717 ms, 최종 OD 값 동일. 상세 근거는 RF-011-role-index-20261020.md/json에 기록했다.
- 테스트 프로세스 정상 종료. 사용자 .env·Linux의 2축 구성·영구 파라미터 파일은 변경하지 않았다. 장시간·이동 부하 검증은 남아 있다.

## 2026-10-26 — 4축 동작 정상 확인 및 최적화 변경 버전 관리

- 사용자가 최적화 후 4축 동작 테스트 정상을 확인했다. RF-011·RF 목록·최적화 보고서·README·전체 계획에 반영했다.
- 수동 시험을 10월 20일의 8 ms/120초 자동 계측과 구분하며, 보고되지 않은 시험 시간·운전 모드·동시 이동 범위·WKC 수치를 추정하지 않는다. RF-011 전체 완료 처리는 하지 않았다.
- OD role 인덱스 구현, 회귀 테스트, 테스트 전용 4축 fixture, 오프라인 벤치마크와 계측 보고서를 함께 커밋 대상으로 정리했다. 빌드/원본 로그/영구 상태는 제외한다.
- 커밋 전 재검증: Windows Python 테스트 33개 통과, 문서 내부 링크 및 diff 공백 검사 통과.

## 2026-10-26 — FMI 실행 구조 및 모델 장애 격리 결정

- 사용자 합의로 Co-Simulation을 채택했다. KickCAT Slave와 Model Host를 별도 프로세스로 유지하고 어댑터는 재사용 라이브러리, FMU는 Host 내부에서 로드하는 라이브러리로 정의했다. 별도 FMU Runner와 추가 IPC는 초기 범위에서 제외한다.
- 모델 코드·어댑터·FMU 충돌 또는 응답 중단에도 Slave 프로세스를 유지하는 것이 목적이다. IPC 시간 제한, 오래된 피드백의 정상 표시 금지, 장애 노출 및 명시적 복구·자동 운전 재개 금지를 설계 원칙으로 기록했다. 구체적 오류 코드·timeout·복구 계약과 구현은 후속이다.
- DT-003에 책임 경계, CiA402 상태 머신 중복 실행 금지, SDO 적용 결과 반영 및 기존 자체 모델의 대체 경로를 기록했다. DT-001·DT-006·전체 계획·README에 연결했다. 단일 컨테이너와 Motion Server 독립 패키지 원칙은 유지한다.
- 앞선 CopleyDriveSim Linux 단독 검증(원본 자체 검사 14개, Python FMI 호출 4인스턴스·8 ms 계산 간격·PP 이동·Fault 입력/복구)을 DT-003에 기록했다. 실제 EtherCAT 연동·실시간 성능·Host 장애 격리 검증으로 확대 해석하지 않는다.
- 이번 변경은 문서만 수정했으며 통합 코드나 실행 중인 장비·프로세스는 변경하지 않았다.

## 2026-10-26 — Docker 및 .env 기반 실행 초기 구현

- FMU 도입 전에 실행 구조부터 정리하라는 요청에 따라 compose.yaml, Dockerfile, .env.example 및 비대화형 docker/service.py를 추가했다. 기존 수동/진단 런처는 유지한다.
- 실행 설정은 .env, 장치 정의는 JSON, 영구 파라미터는 /state/parameters로 분리했다. NIC와 저장 경로는 Docker 실행에서만 원본 JSON을 수정하지 않고 유효 구성에 반영한다.
- 기존 Linux 바이너리와 모델 스냅샷을 이미지에 포함해 실행 중 Motion Server 체크아웃 마운트를 제거했다. 소스 빌드 및 모델 패키지 독립 배포 완료로 해석하지 않는다.
- Edge-ubuntu에서 이미지 빌드·NIC 없는 4축 초기화, 물리 버스와 분리된 네트워크에서 4축 Slave 시작·healthcheck·점유 NIC 거부·docker stop 종료 코드 0, 관리 NIC 거부를 확인했다. 실제 enp1s0 시작·정상 종료도 관측했으나 Master/PDO/WKC 시험은 하지 않았다. 테스트 컨테이너는 종료·제거했다.
- 설정 및 healthcheck 관련 단위 테스트 5개 통과. 기존 장치 JSON·영구 파라미터는 보존하고 별도 build/docker-validation 저장소에서 시험했다.
- DT-003의 모델 장애 격리는 부분 설계 상태다. 실행 관리자는 모델 종료만으로 살아 있는 Slave를 즉시 종료하지 않지만 기존 C++는 IPC 오류 시 종료한다. 완전한 Slave 유지·Fault/AL 노출·명시적 복구와 물리 회귀는 RF-012 후속으로 기록했다. 커밋·푸시는 하지 않았다.

## 2026-10-26 — Motion Server와 환경 변수 명명 규칙 통일

- Motion Server의 .env/.env.example 및 Compose를 확인했다. 일반 설정의 MOTION_SERVER_*와 구현별 PYSOEM_* 구분을 따라 Simulator 일반 설정은 DEVICE_SIMULATOR_*, EtherCAT NIC는 KICKCAT_INTERFACE로 변경했다. 계측 이름은 DEVICE_SIMULATOR_CYCLE_STATS_LOGS로 맞췄다.
- 예제·Compose·Dockerfile·서비스 코드·테스트·문서를 함께 변경했다. Linux의 기존 .env는 값과 사용자 경로를 보존하면서 키만 이관하고 이전 파일을 build/env-before-device-names.env에 백업했다. 파일명은 .env/.env.example을 유지한다.
- 단위 테스트 5개, Compose 구성 검사, Linux 이미지 재빌드 및 NIC를 열지 않는 모델 초기화 검증을 통과했다. 실행 중 서비스 재시작이나 물리 통신 시험은 하지 않았다. Motion Server 파일은 수정하지 않았다.

## 2026-10-26 — 장치 구성까지 .env 단일 설정으로 통합

- 사용자 요청으로 JSON 장치 구성과 DEVICE_SIMULATOR_CONFIG_FILE을 제거했다. DEVICE_SIMULATOR_BUS의 명시적 Slave 번호와 AXIS_<번호>_ID/MODEL/MODE/PARAMETER_SET을 도입했다. 예제 4축은 linear 2축·rotary 2축이다.
- Compose env_file로 모든 장치 설정을 전달하고 모델 서비스가 환경 변수에서 직접 구성 객체를 만든다. 임시 구성 JSON도 제거했다. native 런처/검증 도구는 --env-file로 전환했다. 파라미터 저장 및 KickCAT 내부 JSON은 유지한다.
- Linux에서 설정·다중 축·저장/복원 22개 및 서비스 검사 4개 통과. 환경 변수만으로 이미지 빌드·4축 초기화 통과. 잘못된 .env와 미지원 JSON은 자동 fallback하지 않는다.
- Linux 기존 .env가 가리키던 사용자 JSON을 읽어 현재 2축의 ID·모드·저장 공간과 실행 설정값을 보존해 이관했다. 이관 후 2축 모델 초기화도 NIC 접근 없이 통과했다. 이전 .env는 build/env-before-all-settings.env에 백업했다. 사용자 영구 파라미터는 변경하지 않았다.
- DT-005·DT-006·RF-011·RF-012·README·계획과 목록을 갱신했다. 기존 JSON 예제는 .env 예제로 교체했다. 물리 통신 재시험·서비스 재시작 및 커밋·푸시는 하지 않았다.

## 2026-10-26 — 축 설정을 Motion Server 방식의 목록으로 구조화

- 사용자 요청으로 DEVICE_SIMULATOR_MANAGEMENT_INTERFACE와 해당 시작 검사를 제거했다. 기본 경로/캐리어/점유 NIC 확인은 유지한다.
- Motion Server의 device/cmmt/.env.example을 참조해 축별 반복 키를 DEVICE_SIMULATOR_AXIS_IDS/MODELS/MODES/PARAMETER_SETS의 번호:값 목록으로 교체했다. BUS와 각 목록의 번호 집합 일치·중복·누락 검사를 추가했다.
- Linux의 기존 2축 구성 객체가 변경 전후 동일함을 확인하고 .env를 이관했다. 이전 파일은 build/env-before-structured-axes.env에 백업했다. 예제·Compose·로더·서비스·테스트·문서를 함께 갱신했다.
- Linux 모델 포함 22개 및 서비스 3개 테스트 통과. 이미지 재빌드와 NIC 없는 환경 설정 초기화 검증을 수행했다. 실행 중 서비스 재시작·물리 통신 시험·커밋·푸시는 하지 않았다.

## 2026-10-26 — 저장 경로를 ./state로 통일

- Linux .env, .env.example 및 Compose 기본값을 ./state로 변경했다. 기존 4개 파라미터 파일은 이미 state/parameters에 있었고 state/docker는 존재하지 않아 이동/덮어쓰기는 하지 않았다.
- 기존 설정·파라미터를 build/state-path-change-20261026T063744에 백업했다. 일반 사용자 소유 저장값을 읽기 위한 컨테이너 DAC_OVERRIDE를 추가해 소유권·파일 모드는 유지했다.
- 새 경로에서 NIC 없는 2축 모델 초기화·파라미터 복원을 통과했고 모든 파라미터 파일의 SHA-256이 변경 전과 같음을 확인했다. 서비스 자동 시작 및 커밋·푸시는 하지 않았다.

## 2026-10-26 — parameters 하위 폴더 제거

- 사용자 요청으로 STATE_DIR 자체를 파라미터 저장 루트로 변경했다. Linux의 기존 axis-0~3.json 및 저장소 잠금 파일을 state/parameters에서 state로 이동하고 빈 parameters 폴더를 삭제했다.
- 원본은 build/flatten-state-20261026T064113에 백업했다. 최초 이동 시 root 소유 서비스 잠금 파일 권한 때문에 이동이 실패했다. 이후 검증 중 루트에 생성된 임시 기본값 파일은 별도 백업하고 기존 parameters의 원본을 최종 위치에 이동했다.
- 최종 state/axis-0~3.json 모두 이전 백업과 SHA-256이 같음을 확인했다. Docker 이미지 재빌드 및 최종 경로의 2축 모델 초기화·복원 통과. parameters 폴더가 재생성되지 않음을 확인했다.

## 2026-10-26 — Docker 운영 스크립트 추가 및 이전 런처 정리

- Motion Server scripts/host/start.sh [--build], stop.sh를 참조해 scripts/docker의 start/stop/build/validate/status/logs와 공통 설정·환경 정규화 진입점을 추가했다. start는 빌드 성공 후 컨테이너를 재생성하고 healthcheck를 기다리며 실패 시 로그와 오류 코드를 반환한다.
- native CMMT/Board 런처와 이에 의존하는 Windows 진단·통합 런처 11개를 삭제했다. 빌드 산출물 생성, 모델 스냅샷 내보내기, 오프라인 검증/성능 분석 및 SDO 복원 테스트 라이브러리는 유지한다. 상세 판단은 scripts/README.md에 기록했다.
- Linux에도 동일하게 배포하고 삭제 파일은 build/removed-native-scripts-*에 백업했다. 사용자 .env의 여러 줄 구성을 지원하며 PARAMETER_SETS 첫 줄에 누락된 역슬래시만 보완했다. 값 변경 없이 이전 파일을 build/env-before-script-normalization.env에 백업했다.
- Linux에서 셸 구문 검사, 가짜 Docker CLI를 이용한 진입점 테스트 6개, 실제 Docker의 NIC 없는 설정·기존 파라미터 복원 검증을 통과했다. 물리 Slave start/stop은 실행하지 않았으며 Motion Server·실제 장비는 조작하지 않았다. 커밋·푸시는 하지 않았다.

### 2026-10-26 중복 config 폴더 제거

- Docker가 사용하지 않는 config/*.env 예제를 제거하고 개발용 validate-fleet 기본 입력을 루트 .env로 통일했다. tests/fixtures와 과거 계측 기록은 유지했다.

### 2026-10-26 CiA402 프로파일·모델 어댑터 방향 정리

- 공통 CiA402 Drive 프로파일과 F-KR Internal 어댑터를 첫 구현 범위로 확정했다.
- FMI 실행 표준과 모델 의미 매핑을 구분하고 향후 공통 FMU 어댑터·모델별 매핑 방향을 기록했다.
- DT-007에 Copley 제약, identity 호환성 및 전체 폴더 구조 제안을 작성하고 RF-016을 등록했다. 코드/설정/폴더의 실제 이관과 물리 시험은 수행하지 않았다.

### 2026-10-26 가상 디바이스·기능 모델 폴더 구조 확정

- 가상 디바이스 = EtherCAT Slave + 기능 모델, 기능 모델 = CiA402 Drive + 모델별 어댑터 + 동작 모델로 합의했다.
- src/ethercat_slave와 src/functional_model, 루트 device_descriptions·protocols/ipc를 확정하고 DT-007·DT-003·RF-016·전체 계획을 갱신했다.
- 기존 simulator/model_coupler 목표 구조 제안을 대체한다. 두 프로세스 실행 및 기존 CMMT identity 호환성은 유지한다. 이번 작업은 문서만 변경했으며 실제 폴더 이동·코드 구현·서버 재시작은 수행하지 않았다.
