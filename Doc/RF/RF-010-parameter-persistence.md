# RF-010 — 가상장치 파라미터 영구 저장 및 복원

- 등록일: 2026-09-15
- 상태: Profile Velocity 양 모델 저장 통일·명시적 이관 및 물리 SDO 저장/재생성 복원 검증 완료 / 전체 요구 잔여
- 설계: [DT-004](../Design/DT-004-parameter-sync-persistence.md)
- 연계: RF-007 모델 초기화, RF-009 파라미터 동기화

## 작업 범위

시뮬레이터 소유 영구 저장소를 구현한다. 안정적인 장치 ID, 스키마/설정 revision, 타입·단위·변경 이력을 관리한다. 배포 기본값·영구 설정·실행 상태를 분리하고 EtherCAT/관리 인터페이스의 변경을 공통 정책으로 처리한다. 저장 형식·데이터 경로·commit 및 응답 시점을 구현 전에 확정한다.

## 완료 기준

- [ ] SDO 및 관리 경로에서 변경한 영구 파라미터가 정상 재시작 후 동일하게 복원됨.
- [ ] 실제→가상 동기화 완료 후 재시작해도 값 유지. 단순 RAM 적용과 저장 완료 구분.
- [ ] 저장 도중 중단·쓰기 실패·동시 갱신에서 불완전 revision을 정상값으로 사용하지 않음.
- [ ] 장치 순번 변경과 다장치 환경에서 다른 장치의 설정을 잘못 로드하지 않음.
- [ ] 최초 초기화와 기존 설정 누락·손상·스키마 불일치 구분, 백업·이관·명시적 초기화 검증.
- [ ] 위치·센서·Controlword·진행 명령 등 실행 상태를 자동 복원하지 않음.
- [ ] Motion Server 연결 후 값 유지 및 초기화 시 재기입 항목의 소유권·우선순위 검증.
- [ ] build/임시 폴더 정리와 독립된 저장 경로 및 컨테이너 볼륨 운영 절차 문서화.

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
