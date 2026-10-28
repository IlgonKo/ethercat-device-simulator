# RF-010 — 가상장치 파라미터 영구 저장 및 복원

- 등록일: 2026-09-15
- 상태: 완료 — 2026-10-28 현재 합의 범위 (관리 API·양방향 동기화·이력 관리 후속 분리)
- 설계: [DT-004](../Design/DT-004-parameter-sync-persistence.md)
- 연계: RF-007 모델 초기화, RF-009 파라미터 동기화

## 현재 합의 범위 — 2026-10-28

시뮬레이터 소유 parameter_set별 영구 저장소, SDO 적용·명시적 저장, 저장 완료 응답, 정상 재시작 복원, 오류 검출·단일 writer, 수동 백업/복원·명시적 초기화 및 지원 스키마 이관을 대상으로 한다. 배포 기본값·영구 설정·실행 상태를 분리한다.

관리 API는 [RF-019](RF-019-parameter-management-api.md), 양방향 파라미터 동기화는 기존 [RF-009](RF-009-parameter-sync.md), 설정 revision·변경 이력은 [RF-020](RF-020-parameter-history.md)으로 이관한다. 이 항목들은 현재 RF-010 완료 조건에서 제외한다. 아래 과거 기록보다 이 범위가 우선한다.

## 완료 기준 및 근거

- [x] 실제 SDO 변경·명시적 저장 후 컨테이너 재생성·Master 초기화 후 복원: F-KR 111, Copley 123 확인 후 원래 100으로 복원·저장.
- [x] 저장 도중 프로세스 종료·쓰기 실패·동시 writer에서 불완전 snapshot 사용 방지: Linux SIGKILL 3경계, 원자적 교체 실패 및 잠금 시험.
- [x] 장치 순서 변경 시 parameter_set 연결 유지: 기존 구성 회귀 시험.
- [x] 최초 생성·손상/누락 필드·스키마 불일치 거부, 백업 복원·명시적 초기화·F-KR 1→2 이관 검증.
- [x] 위치·속도 피드백·Controlword·Enable·진행 명령을 영구 저장하지 않음: 모델 재생성 회귀. Profile Velocity 설정은 저장 대상이며 실제 속도 피드백과 구분.
- [x] Master 초기화 후 저장 항목 유지: F-KR 21개×2 + Copley 8개×2 = 58개 물리 SDO readback이 파일과 일치. 재기입 경계는 아래 처리표 참조.
- [x] ./state bind mount와 독립된 임시 소켓·build 경로, 백업·복원·초기화 운영 절차 문서화.

검증은 정상 재시작과 프로세스 강제 종료까지다. 디스크/파일시스템 결함 또는 실제 전원 차단의 내구성 인증·장시간 스트레스 시험은 수행하지 않았다.

## 검증 기록

RF-011과 연계해 기본 파일 저장·복원 및 오프라인 시험을 구현했다. 현재 진단 fixture 또는 모델 소스 폴더가 영구 저장소 역할을 한다고 간주하지 않는다.

## RF-005에서 이관 (2026-09-22)

서버 초기화의 설정 재기입 목록·소유권과 영구 저장 설정의 충돌·우선순위를 검증한다. [RF-005](RF-005-mixed-bus-feasibility.md)는 기본 혼합 타당성 범위로 완료했으며, 이 후속 항목의 상태는 변경하지 않는다.

## RF-011 연계 초기 구현 (2026-09-22)

storage.directory/parameter_set에 저장한다. 스키마 1, 장치·모델·mode 메타데이터, 20개 기본 구성 OD 값, 체크섬을 기록한다. 임시 파일 fsync 후 원자적 교체하고 저장소 단독 잠금을 유지한다. SDO 0x2005 selection=1/control=1은 저장 완료 후 성공 처리한다. 목표 위치·현재 위치·속도·운전 명령·Enable·Homing 상태는 저장하지 않는다.

오프라인에서 마지막 저장값 복원, 저장하지 않은 변경 폐기, 축 순서 변경, 호환 불일치/손상 거부, 교체 실패 시 이전 파일 보존, 동시 실행 거부를 검증했다. 실제 SDO 저장/재시작, 실제→가상 파라미터 동기화, 서버 초기화 재기입 우선순위, 0x2000 장치 reset의 저장값 복원 의미, 백업·이관·revision 이력/관리 API는 후속이다. 현재 모델의 reset 명령 의미를 프로세스 재시작 복원과 동일하게 취급하지 않는다. RF 전체 완료로 표시하지 않는다.


## 2026-10-28 저장 계약 및 검증

- 현재 경로는 DEVICE_SIMULATOR_STATE_DIR(기본 ./state), AXIS_PARAMETER_SETS 매핑의 파일이다. 이전 storage.directory/JSON 설정은 이력이며 영구 파라미터 JSON 자체는 유지한다.
- 기존 구성/저장 및 실제 Linux Copley 혼합 저장 시험 25개 통과. 별도 임시 저장소에 공통 가감속을 저장한 뒤 미저장 변경을 주고 컨테이너를 제거·새로 생성하여 마지막 저장값 복원, 위치 0·Enable 해제를 확인했다. 실제 EtherCAT SDO를 사용한 시험은 아니다.
- 최초 Profile Velocity 교차 모델 시험에서 F-KR은 저장 목록에 0x6081이 없고 Copley만 저장함을 확인했다. 사용자 결정에 따라 두 모델 모두 저장하도록 변경했다. F-KR 저장 스키마는 2(21개 OD), Copley는 기존 스키마 1(8개 OD)을 유지한다.
- 서비스는 구 F-KR 스키마 1을 자동 보정하지 않고 거부한다. 명시적 오프라인 이관 도구가 기존 체크섬·정체성·전체 목록·값을 검사하고 원본 .schema1.bak을 보존한 뒤 새 파일을 원자적으로 저장한다. 저장소 잠금 필수이며 실행 중 소유 저장소는 이관할 수 없다. 새 값은 --profile-velocity로 반드시 지정한다.
- 사용자 지정 이관값: cmmt-0, cmmt-1 모두 raw 100. 기존 저장 파일에는 해당 값이 없으므로 추정 복원값으로 표현하지 않는다. Copley 파일·다른 기존 파라미터는 변경하지 않는다.
- 동일 스키마 2 재실행은 검증만 하고 값을 다시 덮어쓰지 않는다. 손상·잘못된 목록·실패한 교체 시 원본 보존을 테스트한다. 관리 API·양방향 동기화·revision 이력은 자동으로 완료 처리하지 않는다.

명시적 이관 예시(모델 서비스 종료 후, 새 코드 환경):

```bash
python -m functional_model.storage.migrate --store /state --parameter-set cmmt-0 --mode linear --profile-velocity 100
python -m functional_model.storage.migrate --store /state --parameter-set cmmt-1 --mode linear --profile-velocity 100
```

### Motion Server 초기화 경계

현재 startup.py는 profile settings를 SDO로 읽고 읽은 Profile Velocity를 송신 PDO에 반영한다. 따라서 복원 직후와 Master 초기화 후 값을 각각 확인해야 한다. 운전 중 0x6081은 PDO 값에 의해 갱신될 수 있으므로 SDO 단발 쓰기만으로 유지된다고 가정하지 않는다. 저장은 그 시점의 모델 OD를 기록한다.

서버 초기화는 Controlword 0x0006→0x0007→0x000F 순서를 수행한다. 그러므로 모델이 Enable 상태를 저장하지 않는 것과 Master가 초기화 중 Enable을 보내는 것은 별개다. RF-018의 사용자 확인을 서버 자동 Enable 부재의 코드 증거로 해석하지 않는다. 이 저장소 작업에서 Motion Server 동작은 변경하지 않는다.

### 남은 물리 검증

가상축에만 설정 적용 → SDO readback → 명시적 저장 → Docker 재생성 → Master 연결 전 복원값 확인 → Motion Server 초기화 후 SDO/PDO 값 확인. 실제 장비는 변경하지 않는다. 실제→가상 동기화는 RF-009, 관리 API·백업/이력·이관 확장 등은 기존 요구대로 별도 관리한다.


### 적용 확인

2026-10-28 새 Docker 이미지에서 관련 29개 테스트 통과. Linux cmmt-0/1 원본 백업 및 raw 100 이관 완료, 기존 모든 OD 값 보존과 정상 로드 검증. 실행 컨테이너는 아직 교체 전이며 새 이미지로 재생성해야 한다. Windows 관련 테스트 28개 통과. 물리 SDO 저장 및 Master 초기화 후 확인은 다음 단계다.


### 2026-10-28 — Profile Velocity 저장 이미지 운영 전환

사용자 정지 완료 응답 후 scripts/docker/start.sh로 컨테이너를 새 이미지로 재생성했다. 컨테이너 healthy 및 모델/Slave 신규 프로세스 기동을 확인했다. 저장 파일 cmmt-0/1의 6081:00은 64000000(raw 100)이다. Motion Server는 TCP listener가 남아 있고 bus_disconnected 상태였으므로 새 버스 연결 완료를 확인한 것으로 기록하지 않는다. 사용자에게 재연결·초기화를 요청했으며 그 이후 물리 SDO readback 검증 대기다. 이동·Enable 명령은 보내지 않았다.


### 2026-10-28 — 새 이미지 Master 초기화 후 물리 SDO readback

사용자 버스 재연결 완료 후 Motion Server API를 통해 실제 SDO를 조회했다. Master axis=1/2(F-KR virtual-axis-0/1)의 0x6081:0 uint32 모두 100(0x00000064)을 반환했다. 새 이미지에서 저장 파일 복원 후 Master 초기화와 주기 PDO 통신을 거쳐도 속도값이 유지됨을 확인했다. 서버 initialized=true/runtime_state=normal, 4ms 주기, 6 slaves/5 axes, 상태 조회 21회 모두 WKC 18/18 및 Fault 없음. 이동·Enable·파라미터 쓰기는 요청하지 않았다.

증거: ignored build/diagnostics/rf010-physical/startup-readback.json. 이번 값의 출처는 명시적 파일 이관이다. 실제 EtherCAT SDO 변경·저장 명령 후 재시작 복원 시험까지 수행한 것으로 확대하지 않는다. 해당 write/save/recreate/readback 경로는 다음 검증이다.


### 2026-10-28 — 실제 SDO 변경·저장·컨테이너 재생성 복원 시험

- 사전 확인: 조작권 사용 가능, 전 축 실제 속도 0, trajectory/homing idle, WKC 18/18. 대상은 Master axis=1(F-KR virtual-axis-0/cmmt-0), axis=3(Copley virtual-axis-2/copley-2)로 한정했다. 변경 전 0x6081 값은 두 축 모두 raw 100이며 로컬 증거에 보관했다.
- system/axis/profile을 사용해 F-KR raw 111, Copley raw 123으로 설정했다. 해당 서버 경로는 0x6081 SDO 쓰기와 RxPDO 속도 갱신을 함께 수행하므로 순환 PDO에 의한 기존값 덮어쓰기를 방지한다. system/axis/param_read로 실제 SDO readback 후 system/axis/param_save를 요청하고 재조회했다. 모두 성공.
- scripts/docker/start.sh로 컨테이너를 새로 생성하고 system/bus/reconnect로 버스를 초기화했다. 이후 실제 SDO readback이 F-KR 111, Copley 123으로 유지됨을 확인했다. 따라서 파일 이관만이 아닌 물리 쓰기·저장·재생성·Master 초기화 경로 검증이다.
- 시험 완료 후 동일 API로 두 축의 속도를 raw 100으로 복원·저장하고 SDO readback 및 운영 JSON에서 64000000을 확인했다. 다른 가상축의 저장 속도도 100이다. 복원 후 추가 재생성은 하지 않았다. 시험 조작권 반환 완료. 이동 명령과 별도 Enable 요청은 보내지 않았다.
- 통신은 WKC 18/18이며 가상축 Fault 없음. 단, 재연결 후 실제 축 A0에 Fault가 발생/관측됐다: 0x6041=0x8638, 0x603F=0x8188. 실제 축에 Reset이나 파라미터 쓰기는 하지 않았다. 오류 원인은 이번 시험에서 확정하지 않았으며 전체 장비 정상 상태로 보고하지 않는다. 서버 reconnect 초기화가 실제 축에도 영향을 준다는 경계를 유지한다.
- 증거(ignored): build/diagnostics/rf010-physical/save-original.json, save-write.json, save-reconnect.json, save-verify.json, save-restore.json, post-reconnect-real-axis-diagnostic.json.
- 결과: 두 모델의 0x6081 물리 저장·재생성 복원 및 Master 초기화 후 유지 검증 통과. RF-010 전체의 관리 API·실제→가상 동기화·revision/백업 정책 등은 완료 처리하지 않는다.


## 2026-10-28 최종 검증

- tests/integration/test_parameter_crash_recovery.py 추가. 부분 JSON 쓰기 후, 임시 파일 fsync 후 replace 전, replace 후 디렉터리 fsync 전의 세 경계에서 자식 writer를 멈춘 뒤 실제 SIGKILL했다. 앞 두 경우 기존 111, 마지막 경우 완성된 새 값 222만 로드됐다. 잠금 자동 해제·재저장 333 성공, 남은 임시 파일이 정식 snapshot으로 읽히지 않음 확인.
- 동일 임시 저장소에서 손상 파일 시작 거부, 백업 원문 복원 후 검증, 명시적 이름 변경 후 기본값 신규 생성 확인. Linux Docker에서 관련 회귀 총 30개 통과. 운영 state 및 실제 EtherCAT NIC는 장애 시험에 사용하지 않았다.
- Master 초기화 이후 4개 가상축의 저장 목록 전체를 실제 SDO로 조회했다. F-KR 42개, Copley 16개 총 58개를 타입별 바이트로 변환하여 파일 값과 비교했고 불일치 0, WKC 18/18이었다. 현재 4ms/basic/PP 설정에서의 결과다. 다른 Master/모드/설정에 자동 일반화하지 않는다.
- 증거: ignored build/diagnostics/rf010-physical/full-catalog-readback.json. 앞선 물리 SDO 저장 및 복원 증거와 함께 판정한다. 실제 축 A0의 기존 Fault는 이번 시험에서 Reset/변경하지 않았다.

## 저장 항목과 Master 초기화 우선순위

| 항목 | F-KR | Copley | 초기화/운전 중 소유권 |
| --- | --- | --- | --- |
| 0x216E:01, 0x2194:01..04 단위 | 저장 | 저장 | 프로파일 호환성 검증 후 로드, Master는 읽기. 읽기 전용 값의 불일치 거부 |
| 0x6081:00 Profile Velocity | 저장 | 저장 | Master가 SDO readback을 첫 PDO에 반영. 운전 중 PDO가 현재 OD를 갱신하므로 SDO만 단발 쓰면 덮어써질 수 있음 |
| 0x6083:00, 0x6084:00 가감속 | 저장 | 저장 | 복원값을 Master가 읽음. 명시적 profile 변경 시 쓰기. Copley 가감속은 같은 값 필요 |
| 0x607D:01..02 위치 제한, 0x6067:00/0x6068:00 위치 창 | 저장 | 제외 | 기본 초기화에서 저장값 재기입 없음. 조회·명시적 설정 경로와 구분 |
| 0x607F:00, 0x2183:0C, 0x60C5:00, 0x60C6:00, 0x60A4:01 제한/jerk | 저장 | 제외 | 저장값 복원 후 읽기. 사용자 설정 시 별도 변경 |
| 0x6098:00, 0x6099:01..02, 0x609A:00 Homing 설정 | 저장 | 제외 | 기본 PP 초기화에서 재기입 없음. Homing 설정 명령의 변경은 별개 |
| 0x6040/0x6060, 목표값·피드백, PDO 매핑·보간 설정, 저장/재시작 제어 OD | 제외 | 제외 | Master 초기화/운전 제어 또는 세션 상태. 파라미터 복원 범위 아님 |

우선순위: 모델 기본값 → 검증된 영구 snapshot → Master 초기화의 별도 제어·PDO 설정 → 명시적 사용자 변경 → 명시적 저장 시점의 OD. Master 초기화는 0x2000 restart-clear, 모드, PDO 매핑 및 조건부 CSP 보간 설정을 다루지만 이들은 저장 목록 밖이다. 0x6081은 SDO readback으로 송신 PDO를 초기화하는 경로를 확인했다. 향후 서버 초기화 변경 시 목록 대조를 재검증한다.

저장소는 모델의 Enable/위치를 복원하지 않는다. Motion Server 자체는 초기화에서 0x000F를 보낼 수 있으므로 이를 저장 상태 복원으로 해석하지 않는다. 0x2000 장치 reset은 Docker 재기동·공장 초기화와 동일 계약이 아니며, Copley는 restart-clear(0)만 지원한다.

## 백업·복원·명시적 초기화 운영 절차

Linux 저장소 루트에서 수행한다. 먼저 Master 통신/동작을 정지하고 `bash scripts/docker/stop.sh`로 모델과 Slave를 종료한다. 저장소 잠금 파일을 삭제해 실행 중 writer의 잠금을 우회하지 않는다. 아래는 수동 예시이며 모델/저장공간 이름은 실제 .env와 대조한다.

### 백업

```bash
mkdir -p backups
cp -a state backups/state-20261028-before-maintenance
```

백업 폴더는 매번 고유한 이름으로 만들고 기존 백업에 덮어쓰지 않는다. .env의 장치 ID·모델·mode·parameter_set 매핑 및 사용한 이미지/소스 revision도 함께 보관한다. 기본 ./state 외 경로를 쓰는 경우 실제 마운트 경로를 사용한다.

### 복원

서비스를 정지한 상태에서 대상 원본을 별도 보관하고, 동일 모델/mode/schema의 백업 파일을 임시 이름으로 복사한 뒤 정식 이름으로 이동한다. 예:

```bash
cp -p state/cmmt-0.json backups/cmmt-0-before-restore.json
cp -p backups/state-20261028-before-maintenance/cmmt-0.json state/.cmmt-0.restore
mv state/.cmmt-0.restore state/cmmt-0.json
```

Master를 연결하지 않은 상태에서 Simulator를 기동해 체크섬·타입·목록·단위 검증과 ready를 확인한다. 실패하면 연결하지 말고 원본을 되돌린다. 성공 후 Master를 연결하고 SDO readback을 확인한다. schema 1 F-KR 백업을 새 이미지에 적용하려면 앞서 문서화한 명시적 이관이 필요하다. JSON을 직접 수정하거나 체크섬을 재계산해 손상/호환성 검사를 우회하지 않는다.

### 명시적 기본값 초기화

서비스 정지·백업 후 초기화할 단일 parameter_set 파일을 state 밖으로 옮긴다. 다른 장치 파일은 유지한다.

```bash
mv state/cmmt-0.json backups/cmmt-0-before-reset.json
```

재기동 시 해당 공간이 없으므로 모델 기본값으로 새 snapshot을 생성한다. F-KR의 기본 0x6081은 0이며 이관 시 사용자가 지정했던 100과 다르다. 필요한 설정을 명시적으로 적용·저장하고 readback 후 사용한다. 이 절차는 위치·기계 상태 동기화나 자동 Enable/이동을 요청하는 기능이 아니다.

누락 파일 한 개만 보고 최초 생성인지 사용자의 실수로 삭제됐는지 자동 구분할 수는 없다. 현재 계약은 '파일 부재 시 신규 기본값 생성'이다. 기존 파일 내부 손상/필드 누락은 자동 초기화하지 않고 거부한다. 삭제/이동 의도와 백업 확인은 운영 절차로 보장하며 저장공간 등록 이력은 RF-020에서 검토한다.

강제 종료 후 남은 숨김 임시 파일은 로드 대상이 아니다. 정식 snapshot과 백업을 확인한 후 서비스 정지 중 해당 임시 파일만 정리할 수 있다. state 전체나 .lock 파일을 실행 중 삭제하지 않는다. 전원 차단/스토리지 자체 장애의 결과를 이번 SIGKILL 시험으로 보장하지 않는다.
