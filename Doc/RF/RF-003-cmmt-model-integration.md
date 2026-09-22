# RF-003 — VirtualOdBridge 및 CMMT 가상 서보 모델 연결

- 단계: 3
- 상태: 기본 1축 SDO/PDO·모델 연결 검증 완료 (2026-09-14). 오류 응답은 TD-001로 보류
- 등록일: 2026-09-14
- 선행 항목: [RF-002](RF-002-windows-pdo-diagnostic.md), [RF-002-1](RF-002-1-sdo-diagnostic.md)
- 관련 미해결 항목: [TD-001 — SDO Abort 응답 호환성](../TD/TD-001-sdo-abort-response.md)
- 다음 단계: [RF-004](RF-004-motion-server-axis-panel.md)

## 목적 및 범위

KickCAT의 소프트웨어 ESC·슬레이브 통신 계층에 기존 `VirtualOdBridge`, OD Model, `VirtualCiA402Servo`를 연결해 CMMT 1축 동작을 구현한다. RF-001/002의 Board 통신 시험을 CMMT 동작 검증으로 해석하지 않는다.

KickCAT은 프레임, ESC 상태 및 CoE 메일박스 처리를 담당한다. 기존 모듈은 OD 값, CiA 402 상태 전이 및 모션 동작을 담당한다. upstream 직접 수정보다 프로젝트의 어댑터/래퍼 구성을 우선 검토한다. 사용자 결정으로 별도 Python 프로세스와 로컬 Unix 소켓을 사용한다.

## 초기 검토 항목 (아래 연결 계약으로 구체화)

- CMMT identity, ESI 및 검증할 RxPDO/TxPDO 구성.
- C++ KickCAT과 기존 Python 모델의 결합 방식 및 프로세스 구성.
- OD 값의 단일 기준과 SDO/PDO 읽기·쓰기 연결 계약.
- 접근 권한·데이터 길이·타입 오류를 Abort로 전달하는 경로. TD-001과 연계한다.
- PDO assignment/mapping 변경 시 process image 반영 범위.
- 프레임 수신 → RxPDO 반영 → Model_Update → TxPDO 제공 순서와 모델 시간 기준.
- 기존 모듈을 중복 복사하지 않고 재사용할 패키지 경계.

## 작업 및 완료 기준

- [x] 연결 계약과 모듈 책임을 문서화한다.
- [x] CMMT 1축 identity/ESI/PDO 구성을 준비한다.
- [x] SDO 요청과 raw PDO를 VirtualOdBridge 및 OD Model에 연결한다.
- [x] VirtualCiA402Servo 갱신과 TxPDO 출력을 연결한다.
- [x] PySOEM 실제 통신으로 CiA 402 상태 전이 및 1축 동작을 검증한다.
- [ ] 오류 전달을 검증하고 TD-001 해결 여부를 명시한다.
- [x] RF-002 및 RF-002-1 회귀 결과와 재현 절차를 기록한다.

## 현재 결과 및 제한

기본 연결은 실제 케이블에서 검증했다. 아래 결과와 제한을 참조한다. 오류 전달의 전체 완료 조건은 TD-001 해결 전까지 미완료로 유지한다. MockMaster는 비교·회귀 테스트용으로 유지한다.


## 확정한 연결 계약 (2026-09-14)

사용자 선택: **CMMT-AS 1축 / motion_server_default PDO**, **별도 Python 프로세스 + Unix 소켓**.

```text
Windows PySOEM → 물리 EtherCAT → cmmt_simulator (KickCAT)
                                    ↕ Unix socket / JSON lines
                               model_service.py
                                    ↕ VirtualOdBridge
                               OD Model ↔ VirtualCiA402Servo
```

- 장치 값의 기준은 Python `VirtualCiA402Servo.od` 하나다. C++ OD 저장소는 SDO 직렬화와 process image를 위한 버퍼다.
- SDO read는 KickCAT Entry의 `before_access`에서 Python OD 값을 받아 응답 버퍼를 채운다. 허용된 SDO write는 `after_access`에서 VirtualOdBridge로 전달한다.
- EtherCAT 통신 객체(identity, SM, PDO mapping/assignment)는 C++ 스택이 담당한다. 모델이 소유하는 장치 객체 46개는 PDO와 required non-PDO 정의에서 선택한다.
- 논리 PDO 쓰기가 처리된 프레임의 반환 후 `Slave::routine()` → RxPDO를 Python OD에 반영 → `model_update()` → TxPDO 게시 순서로 처리한다. 새 결과는 다음 Master PDO 조회에서 관측된다.
- 모델 갱신은 OP에서 확인된 논리 PDO 쓰기에만 수행한다. SDO·상태 조회 프레임은 모델 시간을 진행시키지 않는다.
- Python의 monotonic 시간으로 PDO 간 실제 경과 시간을 `cycle_time`에 전달한다. 첫 주기는 시험 기준 10 ms다. PDO 사이 100 ms 초과 간격은 다음 cycle 요청에서 실패 처리하며 자동 시간 보정·재접속은 하지 않는다. 이는 별도 실시간 watchdog 구현이 아니다.
- IPC는 private 0700 임시 디렉터리의 Unix stream socket, protocol=1 JSON lines이다. startup describe 계약 전체가 fixture와 일치해야 시작한다. 요청은 describe/read/write/cycle/idle이며, 길이 오류·모델 예외·IPC 단절을 성공 응답으로 변환하지 않는다.
- `model_update`, 기존 bridge read/write/PDO 변환 메서드를 그대로 재사용한다. Motion Server의 공개 API·capability 계약과 MockMaster는 변경하지 않는다. IPC는 simulator 내부 계약이다.

## 구현 파일

- [C++ 시뮬레이터](../../simulator/cmmt_simulator.cc): upstream 라이브러리 조합, SDO 콜백, PDO 및 IPC 연결.
- [Python 모델 서비스·ESI 생성](../../simulator/model_service.py): 기존 모델 로딩, 객체 계약 및 fixture 생성, 모델 갱신.
- [빌드](../../scripts/linux/build-cmmt.sh), [Linux 세션 관리자](../../scripts/linux/cmmt-session.py): 두 프로세스 시작·종료, NIC/SSH 보호와 로그 관리.
- [Windows 물리 진단](../../scripts/windows/diagnose-cmmt.py): 검색·SDO·OP·CiA 402·Homing·이동·피드백 검증.
- [모델 연결 테스트](../../tests/test_model_service.py), [의존 소스 내보내기](../../scripts/windows/export-model-source.py).

KickCAT submodule은 `43ad3e9ce390f0f6d9548118098bcaafc0d4f1f1` 그대로이며 원본 수정 없음. `readFrame()`은 Master용으로 EtherCAT 길이 필드를 초기화하므로 시뮬레이터는 원본을 보존하는 raw read + network.route 경로를 사용한다.

## 모델 의존성과 실행 방법

이번 검증은 Windows Motion Server commit `da0b0a3ae727ca9586bc27b6942c95fd88e670a7`의 device/configuration/motion_server/ethercat 및 오류 카탈로그를 내보낸 소스를 사용했다. Linux의 기존 Motion Server checkout에는 VirtualOdBridge가 없어 해당 checkout을 수정하지 않고 별도 `build/model-source-da0b0a3` 경로를 사용했다.

소스는 simulator Git에 중복 등록하지 않는다. 장기 공통 패키지 분리는 미완료이며 현재 `--model-root`로 외부 소스 경로를 명시한다. 서비스는 선택한 소스·데이터 파일의 SHA-256을 계약과 결과에 기록한다. 사용한 기본 non-PDO preset은 기존 `linear_mm`이다.

최신 클론에 VirtualOdBridge가 있으면 그 경로를 `--model-root`로 사용한다. 소스 스냅샷이 필요할 경우 Windows에서:

```powershell
python scripts/windows/export-model-source.py --source C:\Users\Festo\Documents\motion-server
```

이 도구는 지정 revision(기본 HEAD)의 커밋된 의존 파일만 `build/model-source-<12자리 commit>.tar`로 생성한다. 커밋하지 않은 변경은 포함하지 않는다. archive와 metadata를 Linux로 옮겨 별도 빈 폴더에 풀고 그 경로를 선택한다. 스냅샷·카탈로그·생성 ESI는 build 아래의 테스트 자료이며 Git에서 제외한다.

Linux에서 기존 RF-001 빌드 후:

```bash
bash scripts/linux/build-cmmt.sh
sudo setcap cap_net_raw,cap_net_admin=ep build/cmmt/cmmt_simulator
```

재빌드하면 capability가 초기화되므로 다시 설정해야 한다. Windows에서 이번 검증 경로를 재사용하려면:

```powershell
python scripts/windows/diagnose-cmmt.py --model-root /home/festo/Documents/ethercat-device-simulator/build/model-source-da0b0a3
```

진단이 fixture 생성과 두 프로세스 시작·종료를 소유한다. 기존 NIC 사용자가 있으면 거부한다. SSH EOF/stop/최대 600초 제한에 따라 자신의 프로세스만 정리한다. C++ 프로세스에만 NIC capability를 부여한다.

## ESI 및 PDO 범위

- CMMT-AS identity: Vendor 0x1D, Product 8067733, Revision 36120. 제품 identity는 모델의 기존 ESI에서 읽는다.
- RxPDO 24바이트, TxPDO 14바이트. `motion_server_default` 정의와 padding 순서를 그대로 사용한다.
- 생성 ESI는 **제한된 시뮬레이터용 fixture**이다. Festo ESI 전체 및 CMMT 전체 동작을 구현한 것이 아니다.
- `0x1C00`, `0x1C12/13`, `0x1600/1A00`을 명시하고 subindex 1부터 bit offset 16을 사용한다. 자동 생성 mapping/assignment의 bit offset 8도 CA 해석을 깨뜨려 초기 mapping 실패를 유발했다.
- 첫 구현은 고정 PDO다. PDO mapping/assignment 재쓰기는 허용하지 않는다. 향후 Motion Server 초기화가 재매핑을 요구하면 RF-004에서 연결 계약을 확장·검증해야 한다.
- 장치 SDO는 개별 객체 접근을 검증했다. 장치 record의 Complete Access 및 전체 OD는 검증 범위 밖이다.

## 실제 검증 결과

최종 CMMT run ID: `d1ffde3ad7ec4ba5b9a82dcb49abe0ca` (2026-09-14).

| 항목 | 결과 |
| --- | --- |
| 검색 및 매핑 | CMMT-AS identity 확인, Rx 24 / Tx 14바이트, OP |
| SDO 모델 연결 | 0x6083:0을 1000 → 1234로 쓰고 읽기 확인, 1000으로 복원 |
| CiA 402 | Shutdown → Switched On → Operation Enabled 확인 |
| Homing | 기존 모델의 Homing 동작 및 referenced 상태 확인 |
| 위치 이동 | mode 8, target 10000, actual 0 → 9999 |
| PDO | 이동 반복 1,000회 포함 전체 1,026회, 모두 WKC=3 |
| SDO/PDO 일치 | 실제 위치 SDO=9999 / PDO=9999 |
| 종료 | Drive Disable 확인 후 Master INIT, Simulator 정상 종료, 정리 오류 없음 |
| 재현 | 직전 run ecedb246a3a24fc8becd203a597847a0에서도 통과 |

최종 모델 소스 hash: `573b99bfa57732245c07179636bd7ea0d84d5803874b691428ebf578339903f3`.

기존 Board 회귀 run ID: `99315fa2aabd49dea2d789305ef2fd24`. `diagnose-kickcat.py --with-sdo`로 기본 SDO 읽기·쓰기·복원과 PDO 1,000회 WKC=3 통과.

Windows 테스트는 기존 복원 테스트 3개 + 신규 모델 연결 8개 = 11개 통과. Linux에서 신규 모델 연결 8개 통과. Linux 전체 discovery는 Windows 전용 복원 테스트가 PySOEM 미설치로 import 실패했으므로, 그 3개는 PySOEM이 설치된 Windows 결과로 확인했다. Linux에 Master 실행용 PySOEM을 추가 설치하지 않았다.

로그는 양쪽 `build/diagnostics/<run-id>/`에 있다. Windows result.json에는 계약/소스 hash/모든 PDO 표본/정리 결과가 포함된다. Linux에는 simulator.log, model.log 및 사용 fixture가 남는다.

## 남은 범위

TD-001 Abort 정상화와 오류 응답 전체 시험은 보류다. 물리 오류 응답을 통과했다고 간주하지 않는다. DC 동기화, 목표 CSP 주기의 실시간 보증, 다축, 자동 재접속, 공통 패키지 배포 및 RF-004 Motion Server/Axis Panel 통합은 아직 완료하지 않았다.

## RF-004 후속 반영 (2026-09-14)

RF-004에서 Motion Server의 PRE-OP clear/rewrite/restore를 위해 **동일 기본 PDO 구성 재적용**을 추가했다. 앞서 기록한 mapping/assignment 쓰기 금지는 RF-003 최초 구현 당시의 제한이며, 현재는 이 제한된 재적용 절차를 허용한다. 임의 재매핑은 계속 거부한다. Motion Server·Axis Panel 기본 통합 결과는 [RF-004](RF-004-motion-server-axis-panel.md)에 기록했다.
