# RF-004 — Motion Server 및 Axis Panel 통합 테스트

- 단계: 4
- 상태: 기본 통합 경로 검증 완료 (2026-09-14)
- 선행 항목: [RF-003](RF-003-cmmt-model-integration.md)
- 관련 보류 항목: [TD-001](../TD/TD-001-sdo-abort-response.md)

## 실행 구성 및 계약

```text
Windows Axis Control Panel
          ↕ TCP 127.0.0.1:15100
Windows Motion Server / PySOEMMaster
          ↕ 전용 NIC / 실제 EtherCAT 케이블
Linux cmmt_simulator (KickCAT)
          ↕ private Unix socket
Python VirtualOdBridge / OD / VirtualCiA402Servo
```

대상은 CMMT-AS 1축, motion_server_default (Rx 24 / Tx 14바이트), linear_mm preset이다. Motion Server는 basic / PP / 10 ms / FreeRun / DC off로 실행한다. MockMaster 비교 시험도 같은 설정을 사용했다.

기존 Motion Server와 Axis Panel의 소스·공개 API·설정 파일은 변경하지 않는다. simulator 저장소의 실행 래퍼가 명시적인 환경과 기존 `.env.example`을 읽어 별도 테스트 구성을 만든다. 사용자의 활성 `.env`를 수정하거나 이 시험에 읽어 적용하지 않는다. 포트 15100이 이미 사용 중이면 기존 서버를 종료하지 않고 실행을 거부한다.

## PDO 초기화 지원

Motion Server의 `CMMTDeviceProfile.prepare_process_image()`는 PRE-OP에서 다음 절차를 수행한다. 이 경로를 생략하거나 성공으로 위장하지 않는다.

1. 0x1C12/13 assignment count를 0으로 설정한다.
2. 0x1600/1A00 mapping count를 0으로 설정한다.
3. 기본 PDO mapping 항목을 차례로 쓴다.
4. mapping count, assignment 항목 및 assignment count를 복원한다.
5. 실제 SDO readback으로 mapping을 검증한 후 config_map/OP로 진행한다.

RF-004에서 simulator에 **동일한 기본 PDO 구성의 재적용**을 지원했다. 장치 값 연결은 그대로 Python OD가 담당하며 통신 mapping/assignment는 KickCAT 계층이 담당한다.

- 내부 `FixedMapping`은 fixture의 기본 mapping 값을 기준으로 count=0 또는 원래 값 복원을 허용한다.
- 다른 mapping 값, 잘못된 count·subindex, PRE-OP 외 쓰기는 허용하지 않는다.
- count 복원 없이 SAFE-OP/OP에 진입하면 simulator가 실패 종료한다.
- 이 보호 장치에서 거부된 쓰기는 정상 SDO Abort로 변환하지 않고 세션을 실패 종료한다. TD-001을 해결한 것으로 취급하지 않는다.
- 임의 PDO 재매핑 지원은 범위 밖이다. KickCAT upstream 소스와 Motion Server 초기화는 변경하지 않았다.

관련 구현: [FixedMapping](../../simulator/fixed_mapping.h), [C++ 연결](../../simulator/cmmt_simulator.cc), [검증](../../tests/test_fixed_mapping.cc).

## 수동 테스트: 시뮬레이터를 독립 실행

Linux 터미널에서 다음 명령으로 시작한다. 기본 실행 시간 제한은 없으며 `stop` + Enter 또는 Ctrl+C로 종료한다. 터미널 입력이 닫혀도 자식 프로세스를 정리한다.

```bash
cd /home/festo/Documents/ethercat-device-simulator
python3 scripts/linux/cmmt-session.py \
  --run-id "manual$(date +%Y%m%d%H%M%S)" \
  --model-root /home/festo/Documents/ethercat-device-simulator/build/model-source-da0b0a3 \
  --nic enp1s0
```

`"event": "ready"` 확인 후 Windows에서 Motion Server와 Axis Panel을 각각 실행한다. 종료 순서는 Panel → Motion Server → simulator이다. 시간 제한이 필요하면 `--timeout 600`처럼 초 단위로 지정한다. 자동 진단과 통합 런처는 기존 600초 제한을 명시적으로 유지한다. 프로세스 실패 감지와 시작·통신 제한 시간은 그대로 유지한다.

## 수동 테스트: 한 명령으로 실행

Windows PowerShell에서:

```powershell
cd C:\Users\Festo\Documents\ethercat-device-simulator
python scripts/windows/run-integration-bench.py --source C:\Users\Festo\Documents\motion-server --panel
```

이 명령은 Linux 시뮬레이터와 모델, Windows Motion Server, Axis Panel을 함께 시작한다. 별도의 simulator 또는 같은 NIC를 사용하는 Master를 동시에 실행하지 않는다. 기본 Linux 모델 경로는 RF-003에서 준비한 `/home/festo/Documents/ethercat-device-simulator/build/model-source-da0b0a3`이다. 다른 소스를 사용하면 `--model-root`로 지정한다.

Panel에서:

1. endpoint가 `127.0.0.1:15100`이고 축 1개, 유효한 상태/위치가 표시되는지 확인한다.
2. `Request Authority`로 제어권을 얻는다.
3. Motion Server는 초기화 중 축을 Enable한다. 버튼이 Disable을 표시하면 이미 Enable 상태이므로 그대로 Homing을 진행한다. Disable 상태라면 Enable한다.
4. Homing을 실행하고 완료·referenced 상태를 확인한다.
5. PP mode에서 목표 위치 `10` mm, profile velocity `100` mm/s를 입력해 이동한다. 실제 위치 표시가 `10.000` mm에 도달하는지 확인한다.
6. 목표 위치 `100` mm로 이동시키고 도중에 Stop한다. 목표에 도달하기 전에 멈추는지 확인한다.
7. Fault Reset 명령은 처리 후 Switched On 상태(기본 statusword mask 0x23)로 돌아온다. 다시 이동하려면 Enable 상태를 확인한다.

런처 터미널에서 Ctrl+C 또는 Panel 창을 닫으면 자신이 시작한 프로세스를 정리한다. 기본 실행 시간은 준비 완료 후 540초(9분)이며 자동 종료한다. `--duration`으로 1~540초를 지정할 수 있다. 이 런처는 Linux supervisor에 `--timeout 600`을 명시하여 실행한다.

실행 기록은 `build/integration/<run-id>/`에 저장한다. `motion-server.log`, `axis-panel.log`(창 실행 시), `remote-session.log`, `cleanup.json`, `manual-session.json`을 확인한다.

### 준비 사항

- SSH 별칭 Edge-ubuntu와 키 인증, Linux enp1s0 ↔ Windows 지정 NIC 케이블.
- Windows Python에 pysoem, jsonschema, Tkinter가 사용 가능해야 한다. 검증 환경에는 준비되어 있다.
- C++를 재빌드했다면 Linux에서 capability를 다시 설정한다.

```bash
cd /home/festo/Documents/ethercat-device-simulator
bash scripts/linux/build-cmmt.sh
sudo setcap cap_net_raw,cap_net_admin=ep build/cmmt/cmmt_simulator
```

## 자동 통합 검증

```powershell
python scripts/windows/diagnose-integration.py --source C:\Users\Festo\Documents\motion-server
python scripts/windows/diagnose-integration.py --source C:\Users\Festo\Documents\motion-server --backend mock
```

검증기는 기존 `AxisServerClient`로 TCP에 연결하고 실제 `AxisServerControlPanel` 클래스를 생성한다. Tk 창은 숨긴 채 이벤트 루프, 상태 표시와 버튼 callback을 실행해 검사한다. 사람이 화면을 보고 마우스로 조작한 검증이나 화면 배치의 시각 검수는 아니다.

- Panel 상태 및 mm 단위 metadata, 제어권 획득.
- 초기 Disable → Panel Enable 버튼 → Homing.
- 실제 TCP move_abs 명령으로 10 mm 이동, Panel 위치 표시 확인.
- 100 mm 이동 중 Panel Stop 버튼으로 중단, 속도 0 확인.
- Panel Fault Reset 버튼, 성공 응답 및 Switched On 상태 확인.
- Disable과 정상 프로세스 정리.

Move 명령은 기존 Panel client의 전송 메서드를 사용하며 Enable/Homing/Stop/Fault Reset은 기존 Panel callback을 호출한다. 응답 관측은 시험용 client subclass에 기록하며 제품 client 코드는 수정하지 않는다.

## 실제 결과

| 항목 | PySOEM + 물리 KickCAT | MockMaster |
| --- | --- | --- |
| run ID | 5068d8c5adde44efb16fa4699c4e6a0a | 2d2c4de4d67948d79dc86facdc1aac32 |
| 초기화 | 실제 SDO mapping write/readback, OP, 정상 feedback | 동일 초기화 계약 및 정상 feedback |
| WKC (서버 로그 관측) | 3/3 | 2/2 (Mock 자체 기대값) |
| Enable / Homing | 통과 | 통과 |
| 목표 10 mm 이동 | actual 약 10.0 mm | actual 약 10.0 mm |
| Panel 위치 표시 | 10.000 | 10.000 |
| 100 mm 이동 중 정지 | 23.429 mm에서 정지 | 약 20.0 mm에서 정지 |
| Fault Reset | ok=true, mask 0x23 | ok=true, mask 0x23 |
| 정리 오류 | 없음 | 없음 |

정지 명령을 전송한 시점과 통신 지연이 다르므로 정지 위치의 수치 동등성을 요구하지 않았다. 두 경로 모두 이동 완료, 유효한 feedback, 목표 도달 전 정지 및 정상 상태 전이를 합격 기준으로 비교했다.

Fault Reset은 **정상 상태에서 명령을 보내 성공 응답과 제어 시퀀스를 확인한 시험**이다. 실제 Fault를 주입한 뒤 제거·복구하는 시험은 수행하지 않았다.

추가 검증:

- RF-003 회귀 `f958abe28ad343089ac2310c4bdf66b5`: SDO 쓰기·복원, OP, CiA 402, Homing, 이동 및 PDO 1,000회 통과.
- C++ `fixed_mapping_contract`: 정상 clear/rewrite/restore와 잘못된 값·count·subindex·상태의 거부 통과.
- Windows Python 테스트 11개 통과.
- 수동 런처의 창 없는 시작·자동 종료 `cca1184ec7ff4816b9c00d1dbf7f8a30`: READY 확인, 2초 후 정상 정리.
- Motion Server와 KickCAT upstream 작업 트리의 기존 변경을 보존했다. Node-RED 관련 시험은 수행하지 않았다.

## 완료 범위와 남은 작업

- [x] Axis Panel TCP 연결 및 실제 GUI 클래스의 상태 표시 확인.
- [x] 실제 PySOEM 초기화·기본 PDO 재적용·OP 진입.
- [x] Enable, Homing, 이동, Stop, Fault Reset 명령 경로 검증.
- [x] 명령 결과와 위치/상태 feedback 일치 확인.
- [x] MockMaster와 같은 시나리오 비교 및 RF-003 회귀.
- [x] 수동 실행 방법, 결과 및 제한 기록.
- [ ] 실제 Fault 주입 후 복구 검증.

TD-001 Abort 보정은 계속 보류한다. 임의 PDO 재매핑, 전체 CMMT OD, DC/CSP 실시간 보증, 다축 및 자동 재접속은 검증하지 않았다. 4단계의 기본 기능 경로 완료를 이 후속 범위까지 완료한 것으로 해석하지 않는다. MockMaster는 유지한다.

## 후속 항목 등록 (2026-09-22)

기본 구성 이외의 PDO 재매핑은 [RF-014](RF-014-dynamic-pdo-mapping.md)로 등록했다. 현재 고정 매핑 지원 범위와 RF-004의 완료 판정은 변경하지 않는다.
