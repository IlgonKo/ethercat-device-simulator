# RF-016 — CiA402 Drive 프로파일 및 F-KR Internal 어댑터

- 등록일: 2026-10-26
- 상태: 구조 이관·오프라인 검증 완료 / 물리 버스 회귀 대기
- 설계: [DT-007](../Design/DT-007-cia402-profile-adapters.md)

## 범위

공통 CiA402 Drive 프로파일, 기존 CMMT-AS 장치 설명 분리, F-KR Internal 어댑터 및 기존 Model Host 연결. 현재 Motion Server 무수정, CMMT identity와 PDO, 기존 모델 계산·상태 전이·파라미터를 유지한다. 폴더 구조는 DT-007로 확정했다. src/ethercat_slave와 src/functional_model로 분리하며, 기능 모델은 profiles/cia402_drive + adapters + models로 구성한다. 필요한 자체 모델·OD·codec·ESI 파서를 이관했으며 외부 Motion Server 스냅샷 런타임 의존을 제거했다.

## 완료 기준

- [x] 확정 폴더 구조로 이관하고 패키지 import·빌드·Docker 경로를 갱신.

- [x] 공통 OD·제조사 확장·PDO·identity의 책임과 파일 분리.
- [x] 어댑터 계약과 지원 기능 정의, 미등록 모델·미지원 조합 거부.
- [x] 기존 가상 모델 상태 머신 중복 실행 없음 및 축별 OD 값 소유권 확인.
- [x] 기본값과 저장 파라미터 복원·SDO 적용의 동등성 검증.
- [x] 1축 및 4축 OD/PDO/모델 상태 독립성, 기존 운전 모드 회귀.
- [ ] 2축/4축 계측 비교 및 실제/가상 혼합 버스 검증. 물리 시험 결과와 오프라인 검증을 구분.
- [x] Docker 빌드·실행 경로와 사용자 문서 갱신.

FMU 실행·Copley 연결·CMMT FMU는 후속. 범용 EtherCAT identity 및 axis:cia402-drive 설정 전환은 별도 합의. 동적 PDO(RF-014), IO(RF-013), 모델 동작 변경(RF-015)은 포함하지 않는다.

## 2026-10-26 구현 및 검증

- C++ 통신 코드를 src/ethercat_slave로 옮기고 IPC client를 분리했다. 작은 ESC/Mailbox 연결은 main.cc에서 유지하며 빈 폴더를 만들지 않았다.
- 기능 모델을 profiles/cia402_drive, adapters, models/f_kr_internal, runtime, ipc, storage, diagnostics로 분리했다. 모델 OD가 유일한 값 저장소이며 어댑터는 같은 OD를 사용한다.
- CMMT identity·원본 ESI·통신/제조사 확장 및 저장 명령 처리는 device_descriptions/cmmt_as로 분리했다. 공통 PDO 매핑 이름 motion_server_default와 외부 cmmt_as contract label은 유지한다.
- 공통 어댑터는 profile/od/capabilities와 read_sdo, write_sdo, apply_outputs, step, read_inputs를 요구한다. 모델별 model/bridge 내부 속성은 공통 계약에 포함하지 않는다. 현재 F-KR Internal 지원 모드는 1/3/6/8/-3이며 0은 미선택 값으로 허용한다. 미지원 모드는 모델 적용 전에 거부한다. 실제 동작 알고리즘은 변경하지 않았다.
- 자체 모델 소스와 상태 머신을 저장소로 이관했다. 역할 인덱스 최적화는 유지한다. 출처와 원본 SHA-256은 [source provenance](../Design/RF-016-source-provenance.json)에 기록했다. MODEL_SOURCE와 --model-root 및 기존 snapshot export 도구를 제거했다.
- .env 및 state JSON identity/schema/parameter_set은 유지했다. 기존 4개 저장 파일을 Docker에서 로드했다. 소스가 바뀌어 source/contract hash는 바뀌며 이는 파라미터 호환성 키가 아니다.
- Windows unittest: 총 53개, 47개 통과·Linux shell 전용 6개 skip. Linux: integration 33개 통과, unit 18개 중 17개 통과·pysoem 미설치 Windows SDO 모듈 1개 skip. Windows에서는 해당 SDO 시험 통과.
- 이관 전 commit 92f3df2에서 확보한 baseline과 linear/rotary × PP/PV/Homing/CSP/JOG 총 10조합·800 PDO cycle 출력, OD/PDO contract 및 영구 파라미터 값 일치. source/contract hash는 비교에서 제외했다.
- Linux C++ 빌드 및 CTest 2개 통과. 신규 4축 fixture/모델 IPC 계약 검증 통과. wheel 단독 설치 및 모델 생성 통과.
- Docker 이미지 빌드·실제 저장값 로드 검증 통과. 물리 NIC와 분리된 internal Docker network에서 4축 서비스 ready/healthcheck 후 docker stop 정상 종료(code 0)를 확인했다. 진단 timeout은 기존 정책대로 실패 종료이며 정상 stop과 구분했다.

### 오프라인 성능 참고

PP 정지 상태, 50회 warm-up 후 1,000회 fleet PDO dispatch를 계측했다. IPC·네트워크·실시간 scheduling은 포함하지 않는다. 단일 회차 비교이며 물리 8 ms 안정성 결과로 해석하지 않는다.

| 축 | 이전 평균 / p95 / 최대 (ms) | 이후 평균 / p95 / 최대 (ms) |
|---|---|---|
| 2 | 0.0818 / 0.0854 / 0.0909 | 0.0626 / 0.0700 / 0.1091 |
| 4 | 0.1652 / 0.1770 / 0.2017 | 0.1260 / 0.1345 / 0.3417 |

평균은 감소했으나 관측 최대치는 증가했다. 물리 버스 WKC·지연·이동 부하 회귀가 끝나기 전 RF-016 전체 완료로 처리하지 않는다. 실제 Motion Server/Axis Panel을 시작하거나 실제 축 이동을 실행하지 않았다.
