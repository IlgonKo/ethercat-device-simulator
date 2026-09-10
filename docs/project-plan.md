# EtherCAT Device Simulator 설계 및 진행 계획

정리 기준: 2026-09-10

상태: 방향과 실행 구성을 합의한 단계. KickCAT 빌드, PySOEM 상호운용 및 CMMT 통합은 아직 검증하지 않았다.

## 1. 목적

실제 CMMT 드라이브 없이도 우리가 개발 중인 Motion Server의 PySOEM 경로를 실제 EtherCAT 프레임으로 검증하는 소프트웨어 장치 시뮬레이터를 만든다.

- 첫 대상은 CMMT이며, 기존 OD Model과 CiA 402 가상 장치 모듈을 재사용한다.
- 소프트웨어 ESC 및 EtherCAT 슬레이브 통신 계층은 외부 구현을 활용한다.
- 장치의 명령 의미, 상태 전이 및 모션 동작은 우리가 만든 모듈이 담당한다.
- 별도 저장소와 실행 패키지로 구성한다. 다른 장치로 확장할 수 있는 이름을 사용하지만, 추가 장치 구현을 현재 범위에 포함하지 않는다.

저장소: https://github.com/IlgonKo/ethercat-device-simulator

Windows 로컬 경로: `C:\Users\Festo\Documents\ethercat-device-simulator`

기존 Motion Server 저장소의 현재 Windows 로컬 경로: `C:\Users\Festo\Documents\motion-server`

## 2. 합의한 방향

| 항목 | 합의 내용 |
| --- | --- |
| 마스터 | 기존 PySOEMMaster를 유지한다. KickCAT 마스터로 교체하지 않는다. |
| 통신 | 실제 NIC와 EtherCAT 케이블을 통해 마스터와 시뮬레이터를 연결한다. |
| 시뮬레이션 엔진 | KickCAT을 우선 검증한다. 채택 확정이나 호환성 검증 완료를 의미하지 않는다. |
| 장치 동작 | 기존 OD·CiA 402 모듈을 연결한다. 외부 제품의 내장 드라이브 모델로 대체하지 않는다. |
| 최종 마스터 구성 | 충분한 검증 후 PySOEMMaster 하나로 통일하는 것을 목표로 한다. |
| 전환 기간 | MockMaster를 유지해 개발과 회귀 테스트에 사용한다. 지금 제거하거나 축소하지 않는다. |
| 운영체제 | Windows에서 시뮬레이터, Ubuntu에서 Docker 기반 Motion Server를 실행한다. |

## 3. 실행 구성

```text
Ubuntu PC
└─ Docker: Motion Server / PySOEMMaster
                 │
        Ubuntu 전용 Ethernet NIC
                 │
          실제 EtherCAT 케이블
                 │
        Windows 노트북 Ethernet NIC
                 │
               Npcap
                 │
     KickCAT 소프트웨어 ESC·슬레이브 스택
                 │
            장치 연결 어댑터
                 │
      VirtualOdBridge ↔ OD Model
                         ↕
               VirtualCiA402Servo
```

- 각 PC에 EtherCAT용 NIC 하나씩을 사용한다. 현재 Windows 노트북의 NIC 하나로 시뮬레이터를 연결할 수 있다.
- 인터넷 및 GitHub 접속은 Wi-Fi 또는 별도 관리용 인터페이스로 분리할 수 있다.
- Docker의 네트워크 구성과 Raw Socket 권한을 설정해 PySOEM이 호스트의 EtherCAT NIC에 접근하도록 해야 한다. 구체적인 옵션은 검증 후 확정한다.
- PC 분리는 프로토콜상 필수 조건은 아니다. 이번에는 두 PC에 역할을 나누는 구성을 선택했다.
- Windows의 응답 지연이 전체 통신 주기에 영향을 준다. 기능 검증과 목표 CSP 주기의 성능 검증을 구분한다.

## 4. 모듈 책임과 연결 경계

### 외부 통신 계층

KickCAT의 소프트웨어 ESC 및 슬레이브 스택이 EtherCAT 프레임, ESC 레지스터, SII/EEPROM, SyncManager, FMMU, EtherCAT 상태 전이 및 CoE 메일박스 처리를 담당하는 방향이다.

KickCAT의 `LAN9252 (SPI), XMC4800` 지원 표기는 실제 장치용 ESC 하드웨어 지원 목록이다. 이번 소프트웨어 시뮬레이션은 `EmulatedESC`를 사용하므로 해당 칩을 필요로 하는 구성이 아니다.

### 기존 장치 계층

기존 Motion Server의 `docs/tasks/td/TD-029-virtual-od-bridge-pdo-sdo-routing.md`에서 확인한 책임 경계를 재사용 기준으로 삼는다.

- `PDO_Configuration`: PDO mapping의 index, sub-index, 순서 및 타입 정의.
- `VirtualOdBridge`: SDO read/write와 raw PDO payload를 OD Model에 연결.
- `OD Model`: 장치 값의 기준 저장소.
- `VirtualCiA402Servo`: `Model_Update` 시점에 OD를 읽고 장치 명령, 상태 전이, 시간 진행 및 모션 동작을 계산한 뒤 OD에 결과 기록.

의도하는 데이터 흐름:

```text
SDO 요청 → 메일박스 처리 → 어댑터 → VirtualOdBridge → OD
SDO 응답 ← 메일박스 처리 ← 어댑터 ← 값 또는 오류

raw RxPDO → VirtualOdBridge → OD
                                  ↓ Model_Update
                           VirtualCiA402Servo
                                  ↓
raw TxPDO ← VirtualOdBridge ← OD
```

### 구현 전 확정할 부분

- KickCAT 내부 OD 저장소와 우리 OD의 연결 방식. 장치 값이 서로 독립적으로 변경되는 이중 기준을 만들지 않는다.
- SDO 접근 권한, 타입·길이 오류 및 Abort의 반환 방법.
- PDO assignment/mapping의 SDO 설정과 실제 process image 반영 방법.
- C++ 통신 계층과 기존 Python 모듈의 결합 방식 및 실행 프로세스 구성.
- 프레임 수신, PDO 반영, 모델 갱신, TxPDO 제공의 정확한 순서.
- 모델 시간의 기준과 `Model_Update` 호출 주기. 모든 수신 프레임을 모션 주기 하나로 취급하지 않는다.

기존 장치 모듈을 두 저장소에 단순 복제하지 않고 공통 패키지로 재사용하는 방안을 제안했다. 패키지 분리 위치와 의존성 구조는 아직 확정하지 않았다.

## 5. 후보 조사 결과

| 후보 | 확인한 사항 | 현재 판단 |
| --- | --- | --- |
| acontis EC-Simulator | 소프트웨어 네트워크·슬레이브 모사, 물리 NIC 기반 HiL 및 장치 통합 API 제공 | 상용 대안으로 유지. PySOEM 호환성, 우리 OD 연결 및 재배포 조건 확인 필요. |
| KickCAT | 소프트웨어 ESC·네트워크, 실제 NIC 및 Linux 가상 Ethernet 연결 문서, 프레임 송수신 및 장치 동작 호출 코드 확인 | 우선 검증 대상. 완제품 대체 가능성은 아직 미확인. |
| Beckhoff TE1111 | TwinCAT 환경에서 EtherCAT 네트워크 시뮬레이션 | 별도 패키지 구성과 런타임 의존성 때문에 후순위. |
| IBV icECAT Network Simulator | ENI, ESC RAM, PDO 및 SDO 콜백 제공. 공개 구성은 자사 마스터 Link Layer에 연결하는 SiL 라이브러리 | 외부 PySOEM 프레임을 처리하는 독립 실행 방식 미확인. |
| sid2baker/ethercat Simulator | Elixir 기반 Raw Ethernet 시뮬레이션, 상태·PDO·CoE 모사 | 추가 실행 환경과 통합 부담, 단순화된 DC 및 프로젝트 성숙도를 고려해 후순위. |
| ISG-virtuos | 실제 필드버스 연결도 제공하는 기계 시뮬레이션 플랫폼 | 독립적인 소프트웨어 ESC 엔진으로 사용할 근거를 확인하지 못해 직접 후보에서 제외. |
| SOES | ESC 접근 HAL을 갖는 슬레이브 스택 | 자체 소프트웨어 ESC 에뮬레이터는 아니므로 단독 대체품에서 제외. |
| IgH FakeEtherCAT | 마스터 API 대체 및 공유 메모리 기반 process data 모사 | PySOEM의 실제 프레임 경로 검증 조건과 다름. |
| OPAL-RT EtherCAT Slave | Hilscher 전용 통신 카드 사용 | 소프트웨어 ESC 기반 패키지 조건과 다름. |

acontis의 케이블 없는 SiL 구성은 EC-Master에 직접 연결하는 방식으로 설명돼 있다. 이를 PySOEM에 그대로 적용할 수 있다고 가정하지 않는다.

## 6. KickCAT 확인 사항과 제한

조사 시 확인한 upstream revision: `43ad3e9ce390f0f6d9548118098bcaafc0d4f1f1` (2026-08-05). 이는 조사 기준이며, 프로젝트 의존성으로 아직 고정하지 않았다.

- Windows 빌드 문서는 CMake, Conan, Windows GCC(w64devkit), Npcap 드라이버 및 SDK를 안내한다.
- Windows Ethernet 송수신 구현이 존재한다. 현재 시뮬레이터 전체의 Windows 빌드 성공은 아직 확인하지 않았다.
- Windows 지원 범위는 도구·테스트이며 실시간 동작을 보장하지 않는다.
- 에뮬레이터에는 DC 시계, 드리프트 및 SYNC0 모델이 있으나, 우리 PySOEM/DC/CSP 요구를 충족하는지는 별도 검증한다.
- 기능표는 방향별 복수 PDO SyncManager를 지원하지 않는다고 명시한다. 대상 CMMT 설정과 비교해야 한다.
- 기본 `network_simulator`는 수신 프레임 처리 후 슬레이브 루틴 및 장치 `step()`을 호출한다. 우리 모델 갱신 순서를 맞추는 어댑터 검토가 필요하다.
- 라이선스는 CeCILL-C이다. 실제 배포 시 포함 코드·수정분·의존성의 배포 조건을 반영한다.
- 자체 마스터 예제의 성공이나 실제 ESC 하드웨어에 대한 검증 이력을 PySOEM과 소프트웨어 시뮬레이터의 검증 완료로 해석하지 않는다.

## 7. 단계별 진행 계획

| 단계 | 작업 | 완료 기준 | 상태 |
| --- | --- | --- | --- |
| 1 | Windows 빌드 환경 구성, KickCAT 버전 선택·고정, 내부 기본 예제와 시뮬레이터 빌드·실행 | 기본 소프트웨어 슬레이브 실행 및 재현 절차 기록 | 미착수 |
| 2 | Ubuntu Docker의 PySOEM과 Windows 시뮬레이터를 실제 케이블로 연결 | 검색·식별, PRE-OP, SDO, PDO 매핑, OP 및 반복 PDO 통신 성공 | 미착수 |
| 3 | 통신 계층과 기존 OD·장치 모듈의 연결 경계 설계 | SDO/PDO·오류·모델 시간·실행 순서 계약 확정 | 미착수 |
| 4 | 기존 모듈을 활용해 CMMT 1축 통합 | 기존 Motion Server의 초기화·Enable·이동·정지 성공 | 미착수 |
| 5 | Mock 경로 비교 및 오류·복구 검증 | Fault reset, 잘못된 SDO, 통신 누락, 재접속 시 기대 동작 확인 | 미착수 |
| 6 | 목표 주기에서 DC·CSP·다축 검증 | 합의한 주기·축 수에서 지연, 지터, WKC 및 모델 시간 진행 검증 | 미착수 |
| 7 | 독립 패키징 및 재현 가능한 설치 구성 | 새 PC에서 설치·실행 재현, 의존성·라이선스 및 사용 문서 정리 | 미착수 |

1단계 내부 예제에서는 KickCAT 예제 마스터를 사용할 수 있다. 이는 엔진 확인용이며 제품의 마스터 변경을 뜻하지 않는다.

2단계가 첫 채택 판단 지점이다. PySOEM을 수정하지 않고 통신할 수 있는지 확인하고, 필수 기능에 큰 보완이 필요하면 acontis 등과 개발 부담을 비교한 뒤 진행 여부를 판단한다.

MockMaster 제거는 별도 후속 판단이다. 실제 통신 경로와 자동 테스트 대체가 충분히 검증되기 전에는 제거하지 않는다.

## 8. 현재 완료한 작업과 다음 작업

완료:

- 로컬 저장소 생성 및 GitHub `origin` 연결.
- `main` 브랜치와 `origin/main` 추적 설정.
- 프로젝트 README 작성 및 초기 커밋 업로드.
- 후보의 공식 문서와 KickCAT 주요 코드 조사.
- Windows 시뮬레이터 / Ubuntu Docker Motion Server 구성 합의.

다음 작업은 Windows의 개발 도구와 Npcap 설치 상태를 확인하고, KickCAT 기본 예제 및 시뮬레이터 빌드 가능성을 검증하는 것이다. 목표 주기, 축 수, 사용할 NIC, CMMT identity/ESI 및 PDO 구성은 검증 준비 과정에서 확정한다.

## 9. 참고 자료

- [KickCAT 저장소](https://github.com/leducp/KickCAT)
- [시뮬레이션 구조](https://github.com/leducp/KickCAT/blob/master/docs/SIMULATION.md)
- [빌드 및 Windows 요구사항](https://github.com/leducp/KickCAT/blob/master/docs/BUILDING.md)
- [기능 및 제한](https://github.com/leducp/KickCAT/blob/master/docs/FEATURES.md)
- [시뮬레이터 실행 루프](https://github.com/leducp/KickCAT/blob/master/simulation/network_simulator.cc)
- [Windows NIC 구현](https://github.com/leducp/KickCAT/blob/master/lib/src/OS/Windows/Socket.cc)
- [장치 동작 확장 지점](https://github.com/leducp/KickCAT/blob/master/lib/simulation/include/kickcat/simulation/DeviceApp.h)
- [OD 접근 구조](https://github.com/leducp/KickCAT/blob/master/lib/include/kickcat/CoE/OD.h)
- [KickCAT 라이선스](https://github.com/leducp/KickCAT/blob/master/LICENSE)
- [acontis EC-Simulator](https://www.acontis.com/en/ethercat-simulation.html)
- [Beckhoff TE1111](https://www.beckhoff.com/en-us/products/automation/twincat/texxxx-twincat-3-engineering/te1111.html)
- [IBV icECAT Network Simulator](https://www.ibv-augsburg.de/en/products/icnet/ethercat-network-simulation/)
- [Elixir EtherCAT Simulator](https://ethercat.hexdocs.pm/EtherCAT.Simulator.html)
- [ISG 필드버스 연결 설명](https://www.isg-stuttgart.de/en/products/softwareproducts/isg-virtuos/connection-hardware-controls)
- [SOES](https://github.com/OpenEtherCATsociety/SOES)
- [IgH FakeEtherCAT](https://docs.etherlab.org/ethercat/1.7/doxygen/libfakeethercat.html)
- [OPAL-RT EtherCAT Slave](https://www.opal-rt.com/software/software-communication-protocols/ethercat-slave/)

참고 링크의 upstream 내용은 변경될 수 있다. 빌드 검증 시 실제 사용 revision과 결과를 함께 기록한다.
