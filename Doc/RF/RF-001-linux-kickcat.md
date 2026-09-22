# RF-001 — Linux KickCAT 빌드 및 기본 Slave 실행

- 단계: 1
- 상태: 완료 (2026-09-14)
- 다음 항목: [RF-002 — 물리 PDO 검증](RF-002-windows-pdo-diagnostic.md)
- 범위: 기본 통신용 Board Slave. CMMT 모델 구현은 RF-003에서 진행한다.

2026-09-14. 1단계: Linux 빌드 및 기본 Slave 실행. PySOEM 상호운용은 2단계, CMMT 모델 연결은 3단계이다.

## 연결

- Linux: Edge-ubuntu, Ubuntu 24.04.3 LTS x86-64
- 저장소: /home/festo/Documents/ethercat-device-simulator
- Simulator 전용 NIC: enp1s0 (IP 없음, 물리 링크 UP 확인)
- Windows Master NIC GUID: {906A65C9-C606-4B1F-8384-2625829A4D18}
- Npcap 장치 경로는 2단계에서 PySOEM 어댑터 목록으로 정확한 표기를 확인한다.
- 두 전용 NIC는 Ethernet 케이블로 직결되어 있다 (사용자 확인).
- SSH 관리 연결: eno1 / 192.168.0.12. 인터넷 기본 경로: wlp3s0.
- 기존 다른 서비스와 네트워크 설정은 변경하지 않는다.
- acontis 검토는 보류한다. MockMaster는 비교·회귀 테스트용으로 유지한다.

## 준비 및 빌드

저장소 루트에서 실행한다.

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake ninja-build python3-venv libcap2-bin
git submodule update --init --recursive
bash scripts/linux/build-kickcat.sh
```

현재 고정 revision: 43ad3e9ce390f0f6d9548118098bcaafc0d4f1f1.
원본은 수정하지 않고 upstream configure/setup 래퍼를 호출한다.
Conan 2.10.2는 저장소 전용 .venv-kickcat에 설치한다.
빌드 결과는 build/kickcat에 생성하며 기본 병렬 작업 수는 2이다.
simulation, esi_parser, master_examples만 활성화하고 network_simulator와 simulated_bus 타깃을 빌드한다.
최초 실행에는 PyPI와 Conan 패키지 저장소 접근이 필요하다.

## 내부 엔진 확인

```bash
build/kickcat/examples/master/simulated_bus/simulated_bus \
  -f third_party/KickCAT/examples/slave/lan9252/freedom-k64f/nuttx/freedom-k64f.xml -t Board
```

이 예제의 master는 내부 검증 전용이다. Motion Server의 PySOEMMaster를 교체하지 않으며, 성공해도 Windows 물리 통신 검증을 통과한 것은 아니다.

## 물리 NIC에서 실행

Linux Socket 구현은 raw socket과 NIC 플래그 변경을 사용하므로 두 capability가 필요하다.
빌드로 실행 파일이 교체되면 다시 설정한다.

```bash
sudo setcap cap_net_raw,cap_net_admin=ep build/kickcat/simulation/network_simulator
bash scripts/linux/run-simulator.sh
```

기본 NIC는 enp1s0이다. IPv4/IPv6 주소 유무나 종류로 실행을 차단하지 않는다. 현재 SSH 연결에 쓰이는 NIC와 링크가 없는 NIC는 거부하며 네트워크를 자동 재설정하지 않는다. SSH NIC 검사는 SSH_CONNECTION 환경 변수가 있을 때 적용된다.
기본 Slave 설정은 configs/kickcat/basic-slave.json이며 upstream Board ESI를 참조한다.
이 장치는 CMMT가 아니다. 기본 입력 패턴을 사용하는 통신 검증용 장치이다.
Ctrl+C 또는 SIGTERM으로 정상 종료한다. upstream Socket은 NIC를 UP/PROMISC로 설정하며, 종료 시 PROMISC 플래그를 자동 복원하지 않는다.
다른 raw socket 사용자가 없고 필요할 경우 수동으로 `sudo ip link set enp1s0 promisc off` 한다.

## 완료 기준 및 결과

- [x] network_simulator 및 simulated_bus 빌드 성공
- [x] 내부 예제: Slave 1개, SAFE_OP/OPERATIONAL, 입력 12바이트·출력 3바이트, 종료 코드 0
- [x] enp1s0에서 기본 Slave 1개 구성 로드, EtherCAT 0x88A4 raw socket 바인딩 확인
- [x] SIGTERM 정상 종료 코드 0 및 socket 해제 확인
- [x] 실행 재현 절차 및 실제 검증 결과 기록

Windows PySOEM 검색·PDO 매핑·OP 전환·PDO 교환 결과는 [RF-002](RF-002-windows-pdo-diagnostic.md), 명시적 SDO 읽기·쓰기 결과는 [RF-002-1](RF-002-1-sdo-diagnostic.md)에 기록한다.

물리 NIC 실행·종료 검증: `python3 scripts/linux/smoke-simulator.py`. 실행 전후 raw socket 목록을 비교하고 SIGTERM 종료 코드 0 및 socket 해제를 확인한다. Master 통신 성공을 검사하는 테스트는 아니다.

검증 환경: GCC 13.3, CMake 3.28.3, Conan 2.10.2, Release 빌드. KickCAT submodule 원본 변경 없음. 검증 후 Simulator는 종료 상태이다.

사용자 요청에 따라 일반 IP 주소 차단을 제거했다. SSH NIC 보호는 유지한다.
