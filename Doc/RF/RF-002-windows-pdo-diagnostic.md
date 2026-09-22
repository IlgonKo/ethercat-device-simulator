# RF-002 — Windows PySOEM 물리 PDO 통신 검증

- 단계: 2
- 상태: 완료 (2026-09-14), 테스트 ESI 보정 적용 기준
- 선행 항목: [RF-001](RF-001-linux-kickcat.md)
- 별도 SDO 검증: [RF-002-1](RF-002-1-sdo-diagnostic.md)
- 다음 단계: [RF-003](RF-003-cmmt-model-integration.md)

2026-09-14 검증 완료. 명시적 SDO 읽기·쓰기 시험은 사용자 결정으로 **2-1단계**에 분리한다. PySOEM의 PDO 자동 매핑 과정에서 사용하는 CoE 조회는 그대로 수행한다.

## 구성 및 실행

- Windows 네이티브 Python 3.14 / PySOEM 1.1.13 / Npcap
- Windows NIC: `\Device\NPF_{906A65C9-C606-4B1F-8384-2625829A4D18}` (실제 PySOEM 목록으로 확인)
- SSH: `Edge-ubuntu`, Linux 저장소 `/home/festo/Documents/ethercat-device-simulator`
- Linux 전용 NIC: `enp1s0`, Windows NIC와 물리 케이블 직결
- KickCAT: `43ad3e9ce390f0f6d9548118098bcaafc0d4f1f1`, 기본 Board Slave 1개

Linux에서 1단계 빌드 및 capability 설정을 먼저 완료한다. 양쪽 저장소에 이번 스크립트들이 있어야 한다. Windows 저장소 루트에서:

```powershell
python scripts/windows/diagnose-kickcat.py
```

필요 시 PySOEM 설치: `python -m pip install pysoem==1.1.13`.
SSH 공개키 인증과 ssh-agent 설정이 필요하며 비밀번호를 스크립트에 저장하지 않는다.
기본 1,000회, 10ms 목표 주기, DC 비활성화. 옵션은 `--help`로 확인한다.

프로그램은 Linux Simulator를 직접 시작하고 종료한다. 수동 Simulator가 이미 실행 중이면 종료 후 실행한다. 기존 EtherCAT socket이 있는 NIC는 자동 세션이 차지하지 않으며, 실행 중인 다른 프로세스를 강제로 종료하지 않는다.

## 검증 범위

1. 어댑터 GUID로 Windows NIC를 선택한다.
2. SSH supervisor가 전용 NIC 사용 가능 여부를 확인하고, 자신의 Simulator 프로세스만 시작한다.
3. Slave 1개와 Vendor/Product/Revision을 확인한 뒤 PRE-OP에 진입한다.
4. 기본 PDO를 매핑하고 입력 12바이트·출력 3바이트를 확인한다.
5. SAFE-OP에서 출력 데이터를 공급하며 OP로 전환한다.
6. 매회 출력 3바이트를 전송하고 입력 12바이트를 수신한다. WKC가 예상값 3과 매번 일치하고 기본 입력 패턴이 변화해야 통과한다.
7. 종료 시 Master를 INIT로 내리고 NIC를 닫는다. supervisor가 자신이 시작한 Simulator에 SIGTERM을 전달하고 종료 코드와 socket 해제를 확인한다.

SSH 표준입력 종료 시에도 supervisor는 자신의 프로세스를 정리한다. 세션은 최대 600초로 제한한다. 예외/사용자 중단 시 결과와 정리 오류를 기록하며 정리에 실패하면 성공 처리하지 않는다.

이 검증은 출력 echo 시험이 아니다. 기본 Simulator가 생성하는 입력 패턴과 WKC로 PDO 통신을 검증한다. CMMT 동작, 명시적 SDO API 시험, 실시간 성능 보장은 포함하지 않는다. MockMaster와 Motion Server는 변경하지 않았다.

## 발견한 상호운용 문제와 테스트용 ESI

원본 Board ESI를 사용한 첫 실행은 Slave 검색에 성공했지만 매핑이 입력 3·출력 0바이트로 잘못 계산됐다.

KickCAT의 `ESI/Parser.cc`는 누락된 `0x1C00`을 자동 생성하면서 첫 SM 항목을 bit offset 8에 배치한다. Complete Access를 사용하는 SOEM이 기대하는 subindex 0 뒤의 16비트 정렬과 맞지 않아 SM 종류가 밀려 해석됐다. `uploadComplete()`는 OD의 bit offset 그대로 데이터를 구성한다.

`prepare-board-fixture.py`는 upstream ESI에서 테스트용 `build/fixtures/board.xml`을 생성한다. 여기에 `0x1C00`을 명시하고 offset을 0/16/24/32/40으로 정의한다. SM 값은 count=4, MailboxOut=1, MailboxIn=2, Output=3, Input=4이다. Slave identity와 PDO 항목, Complete Access 설정은 유지한다. 원본 submodule 코드는 수정하지 않는다.

이 구성으로 예상 PDO 크기와 WKC가 정상화됐다. **검증 성공은 이 명시적 0x1C00 정의가 포함된 테스트 구성 기준**이다. upstream 기본 ESI 그대로의 PySOEM 상호운용 성공을 의미하지 않는다. 향후 upstream 갱신 시 이 보정의 필요성을 재검토한다.

2단계 자동 supervisor는 이 fixture를 생성·선택한다. 수동으로 같은 구성을 실행하려면 Linux 저장소 루트에서:

```bash
python3 scripts/linux/prepare-board-fixture.py
KICKCAT_SLAVE_CONFIG="$PWD/build/fixtures/board.json" bash scripts/linux/run-simulator.sh
```

일반 `run-simulator.sh`의 기본 설정은 1단계의 원본 Board ESI이다.

## 실제 결과

최종 run ID: `75fb1be43b9e4b1ca4597d83eab8f033`

| 항목 | 결과 |
| --- | --- |
| Slave | Board 1개, Vendor 0x6A5 / Product 0xDEFEDE / Revision 0x5A01 |
| PDO | 입력 12바이트 / 출력 3바이트 |
| 상태 | OP, AL 오류 0 |
| 반복 교환 | 1,000/1,000회 WKC=3 |
| 입력 패턴 | 0x11 반복 833회 → 0x22 반복 167회 |
| 측정 송신 간격 | 평균 10.0003ms, 최소 9.1460ms, 최대 11.1637ms |
| 정리 | Master INIT, Simulator 종료 코드 0, 정리 오류 없음 |

직전 실행에서도 1,000회 교환을 통과했다. 주기 측정은 Windows 프로그램의 송신 호출 간격이며 NIC 하드웨어 타임스탬프나 실시간 보증이 아니다.

Windows 결과: `build/diagnostics/<run-id>/result.json`, `diagnostic.log`, `remote-session.log`. 실패 시 `exception.txt`도 저장한다. JSON에는 실패 단계, AL 상태, 모든 PDO/WKC 샘플 및 정리 결과가 포함된다. Linux Simulator 로그는 `build/diagnostics/<run-id>/simulator.log`에 남는다. 결과 파일은 Git에서 제외한다.

2-1단계 기본 SDO 검증은 별도 [SDO 진단](RF-002-1-sdo-diagnostic.md)에 기록했다. `--with-sdo` 옵션으로 SDO 검사 및 PDO 회귀를 실행한다.
