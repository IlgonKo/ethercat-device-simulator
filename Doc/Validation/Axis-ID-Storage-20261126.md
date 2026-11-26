# 축 ID 기반 영구 저장 통일 — 2026-11-26

- 현재 상태: **구현·파일 이관·회귀·Docker 복원 검증 완료**
- 범위: RF-010/011/014 저장 식별자 정리. RF-013 5단계 물리 IO 통합 시험과 별개.

## 현재 계약

`DEVICE_SIMULATOR_AXIS_IDS` 하나로 축의 파라미터와 PDO 매핑 저장소를 연결한다. `DEVICE_SIMULATOR_AXIS_PARAMETER_SETS` 및 내부 구성의 parameter_set 필드는 제거했다. 구 키가 빈 값으로 남은 경우도 설정 오류이며 자동 무시/변환하지 않는다.

- 파라미터: `state/<축 ID>.json`. 기능 모델에서 관리. parameters 하위 폴더 없음.
- PDO 매핑: 기존 `state/pdo-mappings/<축 ID의 UTF-8 hex>.json`. EtherCAT Slave에서 관리. 키 인코딩·파일 형식·복원 경로는 변경하지 않음.
- 저장 schema·identity·checksum·SDO 저장 명령의 의미는 변경하지 않음.
- 버스 순서가 바뀌어도 ID가 같으면 같은 저장소를 선택한다.
- ID 변경은 새 장치이며 기존 파일을 자동 이동/복제하지 않는다. 모델/모드 비호환·손상 파일은 기존대로 오류다.
- CPX는 BUS의 IO ID로 식별하며 현재 파라미터 영구 저장이나 PDO 매핑 파일을 추가하지 않는다.

## 기존 운영 파일 이관

Linux `/home/festo/Documents/ethercat-device-simulator` 기준. 실행 중인 Simulator를 정지한 후 전체 state, .env와 이전 이미지 참조를 보존했다. 저장 루트 잠금을 확보하고 모든 대상의 존재·목적지 충돌·백업과의 일치 여부를 검사했다. 새 이름으로 복사한 임시 저장소를 실제 F-KR/Copley 모델의 strict loader로 검증한 뒤 운영 파일명을 변경했다.

| 이전 파일 | 새 파일 |
| --- | --- |
| state/cmmt-0.json | state/virtual-axis-0.json |
| state/cmmt-1.json | state/virtual-axis-1.json |
| state/copley-2.json | state/virtual-axis-2.json |
| state/copley-3.json | state/virtual-axis-3.json |

F-KR의 기존 `.json.schema1.bak` 두 파일도 같은 축 ID 이름으로 이동했다. 파일 내용과 권한은 유지했다. 파라미터 4개·schema 백업 2개·PDO 파일/잠금 8개의 이관 전후 및 Docker 재기동 후 hash를 대조해 내용이 동일함을 확인했다.

- 백업: `build/backups/axis-id-unification-20261126/`의 `.env`, `state.tar`, `migration-plan.json`, `migration-result.json`.
- 이전 이미지: `ethercat-device-simulator:before-axis-id-20261126`.
- 이번 이관은 승인된 일회성 유지보수 작업이다. 서비스 시작 시 자동 이관 기능을 추가하지 않았다. 과거 이미지로 되돌릴 경우 설정과 state도 대응하는 백업으로 함께 복원해야 한다.

## 검증

| 검증 | 결과 |
| --- | --- |
| Python unit | 78개 실행, 77개 통과·Windows 의존 1개 skip |
| 구성·저장·프로세스 강제 종료 경계 | 29개 통과 |
| ID 전용 파일명 / 번호 재배열 / ID 변경 / 잘못된 ID 경로 | 통과. 이전 파일 유지, 새 ID 독립 저장소 생성 확인 |
| 기존 키·필드 / 중복 ID / 비호환 저장·원자 저장 실패 | 거부 및 기존 파일 보존 확인 |
| 실제 IO FMU | Docker 빌드의 10개 통과 |
| 실제 Copley FMU | Docker 빌드의 8개 통과, 혼합 F-KR/Copley 파라미터 저장·복원 포함 |
| C++ CTest 및 동적 매핑·IPC | 6개 CTest와 4축 매핑/저장/IPC 회귀 통과 |
| 운영 저장 파일 Docker validate | 새 ID 파일로 4축 초기화 성공 |
| 운영 Docker 재생성 | healthy. 초기화 이후 파라미터/PDO 파일 hash 유지 |

새 이미지 `ethercat-device-simulator:axis-id-20261126`를 검증 후 `:dev`에 적용했다. 이미지 ID: `sha256:4f2b2d9d64cd37dc12a4bf763ba9070631ea636836d4d2506d57059837b5b4a6`.

검증 로그는 `build/diagnostics/axis-id-storage-20261126/`에 보관한다. 실제 Motion Server의 SDO 쓰기·물리 이동이나 신규 IO 5단계 시험을 이번 결과에 포함하지 않는다. 기존 4축 운영 구성은 유지했고 .env에서는 폐기한 AXIS_PARAMETER_SETS 블록만 제거했다.

## 다른 저장소에 적용할 때

1. Simulator를 정지하고 .env/state 전체와 이미지 버전을 백업한다.
2. 기존 번호별 PARAMETER_SETS와 AXIS_IDS 대응을 기록한다.
3. 모든 저장 파일과 목적지 충돌을 확인하고 정지 상태에서 각 파라미터 파일을 `<축 ID>.json`으로 이동한다. PDO 매핑의 ID는 그대로 유지한다.
4. .env에서 AXIS_PARAMETER_SETS를 제거하고 새 이미지로 validate한 뒤 시작한다.

이번 변경은 파일명 연결만 바꾼다. 값·schema 비호환을 자동 변환하지 않는다. 기존 F-KR schema 1→2 유지보수 명령은 `--parameter-set` 대신 `--axis-id`로 저장 파일을 지정한다. 이미 schema 2인 운영 파일에 다시 실행할 필요는 없다.

## 후속 설정 키 명칭 변경

같은 날 사용자 결정으로 외부 설정 키를 `DEVICE_SIMULATOR_AXIS_NAMES`로 변경했다. 위 이관 당시의 AXIS_IDS는 이력이며 현재 설정에는 AXIS_NAMES를 사용한다. 내부 고유 ID 값·저장 경로·파일은 바뀌지 않는다. .env 순서 유지 및 전체 구성 객체 동등성을 확인했고 관련 회귀 54개가 통과했다.
