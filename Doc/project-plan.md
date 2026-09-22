# EtherCAT Device Simulator 설계 및 진행 계획

정리 기준: 2026-09-15

상태: KickCAT 기본 타당성 검증(RF-001~004 및 RF-002-1)을 완료하고 Omniverse DT 연동 설계를 합의했다. 혼합 버스·라우터·모드 전환·DT 연동은 RF-005~008의 신규 계획이며 미검증이다. TD-001, 실제 Fault 주입·복구와 성능 검증은 계속 후속 범위다.

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
| 시뮬레이션 엔진 | KickCAT으로 진행한다. acontis 검토는 보류하며, 기본 빌드·PDO 및 정상 SDO 경로는 검증했고, Abort 호환성은 TD-001로 보류한다. |
| 장치 동작 | 기존 OD·CiA 402 모듈을 연결한다. 외부 제품의 내장 드라이브 모델로 대체하지 않는다. |
| 최종 마스터 구성 | 충분한 검증 후 PySOEMMaster 하나로 통일하는 것을 목표로 한다. |
| 전환 기간 | MockMaster를 유지해 개발과 회귀 테스트에 사용한다. 지금 제거하거나 축소하지 않는다. |
| 운영체제 | Windows PC가 Motion Server/PySOEM 마스터 역할을 하고, 별도 Linux PC에서 KickCAT 시뮬레이터를 실행한다. |

## 3. 타당성 검증 벤치 구성 (RF-001~004)

```text
Windows PC                         별도 Linux PC
Axis Control Panel                 KickCAT Simulator
        ↕ TCP                              ↕
Motion Server / PySOEMMaster        소프트웨어 ESC·슬레이브 스택
        ↕                                  ↕
EtherCAT 전용 NIC ── 실제 케이블 ── EtherCAT 전용 NIC
                                           │
                                    장치 연결 어댑터
                                           │
                                VirtualOdBridge ↔ OD Model
                                                   ↕
                                         VirtualCiA402Servo
```

- 각 PC에 EtherCAT용 NIC 하나씩을 사용해 물리 케이블로 직결한다.
- 인터넷, GitHub 및 SSH 접속은 Wi-Fi 또는 별도 관리용 인터페이스로 분리한다.
- Windows PySOEM의 NIC 접근 환경과 Linux 시뮬레이터의 NIC 접근 권한을 검증 준비 시 확인한다.
- Windows PC 내부의 네이티브/VM 실행 방식은 실제 Master 실행 환경을 확인해 기록한다. 이전 Hyper-V Docker 설정을 이번 구성에 자동 적용하지 않는다.
- 한 VM 안의 veth 구성은 현재 테스트 벤치 기준이 아니다.
- 초기에는 기능 검증을 수행하고, 목표 CSP 주기의 성능 검증은 후속 단계로 구분한다.

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

### 타당성 검증 당시 검토 항목 (현재 결과는 RF-003/004 참조)

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
| acontis EC-Simulator | 소프트웨어 네트워크·슬레이브 모사, 물리 NIC 기반 HiL 및 장치 통합 API 제공 | 2026-09-14 합의로 검토 보류. 현재 진행 대상에서 제외. |
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

조사 시 확인한 upstream revision: `43ad3e9ce390f0f6d9548118098bcaafc0d4f1f1` (2026-08-05). Linux 저장소의 submodule은 이 revision으로 고정했으며 RF-001에서 빌드·실행을 검증했다.

- Windows 빌드 문서는 CMake, Conan, Windows GCC(w64devkit), Npcap 드라이버 및 SDK를 안내한다.
- Windows Ethernet 송수신 구현이 존재한다. 현재 시뮬레이터 전체의 Windows 빌드 성공은 아직 확인하지 않았다.
- Windows 지원 범위는 도구·테스트이며 실시간 동작을 보장하지 않는다.
- 에뮬레이터에는 DC 시계, 드리프트 및 SYNC0 모델이 있으나, 우리 PySOEM/DC/CSP 요구를 충족하는지는 별도 검증한다.
- 기능표는 방향별 복수 PDO SyncManager를 지원하지 않는다고 명시한다. 대상 CMMT 설정과 비교해야 한다.
- 기본 `network_simulator`는 수신 프레임 처리 후 슬레이브 루틴 및 장치 `step()`을 호출한다. 우리 모델 갱신 순서를 맞추는 어댑터 검토가 필요하다.
- 라이선스는 CeCILL-C이다. 실제 배포 시 포함 코드·수정분·의존성의 배포 조건을 반영한다.
- 자체 마스터 예제의 성공이나 실제 ESC 하드웨어에 대한 검증 이력을 PySOEM과 소프트웨어 시뮬레이터의 검증 완료로 해석하지 않는다.

## 7. 단계별 진행 계획

각 단계의 실행·검증 기록은 [RF 목록](RF/README.md), 미해결 보류 항목은 [TD 목록](TD/README.md), 작업 이력은 [작업 일지](Work_log.md)에서 관리한다.

| 단계 | 작업 | 완료 기준 | 상태 |
| --- | --- | --- | --- |
| 1 | Linux에서 KickCAT 버전 선택·고정, 빌드 및 기본 Slave 시뮬레이션 실행 | 기본 소프트웨어 Slave 실행, 사용 revision과 재현 절차 기록 | 완료 (2026-09-14) |
| 2 | Windows PySOEM과 Linux KickCAT을 물리 케이블로 연결 | Slave 검색·식별 → PDO 매핑 및 SAFE-OP/OP 전환 → 1,000회 PDO 왕복 WKC=3, 테스트 ESI 보정 포함 | 완료 (2026-09-14) |
| 2-1 | 명시적 SDO 읽기·쓰기 검증 | PRE-OP 읽기·쓰기·복원 및 PDO 회귀 통과. Abort 응답 호환성 미해결 | 기본 경로 완료 (2026-09-14) |
| 3 | 기존 VirtualOdBridge와 가상 서보 모델 연결, CMMT 동작 구현 | SDO/PDO·모델 시간 연결 및 CMMT 1축 동작 검증. 오류 응답 TD-001 보류 | 기본 경로 완료 (2026-09-14) |
| 4 | Motion Server와 Axis Panel로 통합 테스트 | 초기화·Enable·이동·정지·Fault Reset 명령 확인 및 MockMaster 비교·회귀. 실제 Fault 주입은 후속 | 기본 경로 완료 (2026-09-14) |

**첫 목표는 물리 케이블을 통해 PySOEM과 KickCAT의 기본 통신을 확인하는 것이다.** KickCAT 자체 예제 마스터의 성공만으로 2단계 통과를 판단하지 않는다. 제품의 마스터는 기존 PySOEMMaster를 유지한다.

MockMaster는 비교·회귀 테스트용으로 유지한다. 현재 제거하거나 축소하지 않으며, 최종 제거 여부는 실제 통신 경로와 자동 테스트 대체가 충분히 검증된 뒤 별도로 판단한다.

목표 주기의 DC·CSP·다축 성능 검증, 통신 누락·재접속 등 오류 복구 확장, 독립 패키징은 기본 통신 및 통합 테스트 이후의 후속 작업이다.

## 8. 현재 완료한 작업과 다음 작업

완료:

- 로컬 저장소 생성 및 GitHub `origin` 연결.
- `main` 브랜치와 `origin/main` 추적 설정.
- 프로젝트 README 작성 및 초기 커밋 업로드.
- 후보의 공식 문서와 KickCAT 주요 코드 조사.
- Windows Master / 별도 Linux KickCAT Simulator의 물리 케이블 연결 구성 합의 (2026-09-14).
- Linux에서 프로젝트 저장소 클론 완료 (사용자 보고). SSH 접속, 저장소 쓰기 권한, main/origin/main 및 KickCAT submodule을 확인했다.
- KickCAT 기준 4단계 진행 순서와 MockMaster 유지 방침 확정.

1단계 구현 및 검증 결과는 [Linux 빌드·실행 안내](RF/RF-001-linux-kickcat.md)에 기록했다. 2단계 결과와 ESI 보정은 [Windows PDO 통신 진단](RF/RF-002-windows-pdo-diagnostic.md)에 기록했다. 2-1단계 기본 SDO 검증 결과는 [SDO 진단](RF/RF-002-1-sdo-diagnostic.md)에 기록했다. Abort 응답의 PacketError 문제는 [TD-001](TD/TD-001-sdo-abort-response.md)에 등록하고 구현을 보류한다. 목표 주기, 축 수, 사용할 NIC, CMMT identity/ESI 및 PDO 구성은 검증 준비 과정에서 확정한다.

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

RF-003의 CMMT-AS 1축 / 기본 PDO 및 Unix 소켓 기반 모델 연결 결과는 [RF-003](RF/RF-003-cmmt-model-integration.md)에 기록한다. RF-004 기본 통합까지 완료했으며 TD-001은 보류 상태를 유지한다.

RF-004 기본 통합을 완료했다. [수동 런처와 검증 결과](RF/RF-004-motion-server-axis-panel.md)를 참조한다. TD-001, 실제 Fault 주입·복구 및 성능/재접속 확장은 후속 작업으로 남긴다.


## 10. DT 연동 개발 결정 (2026-09-15)

기본 타당성 검증에서 DT 연동 개발로 진행한다. 기존 1축 직결 벤치는 검증 이력으로 유지한다. 제품 목표는 Motion Server 한 인스턴스와 동일 버스의 실제·가상 장치 그룹, 외부 명령·리드백 라우터 및 Omniverse 연결부다. Motion Server는 수정 없는 독립 패키지로 유지한다.

- [DT-001 전체 구조](Design/DT-001-system-architecture.md): 그룹별 장치 ID 매핑과 선택 리드백. 기본 3 Slave 혼합 버스와 서버 호환성은 RF-005에서 검증 완료.
- [DT-002 전환 정책](Design/DT-002-mode-switching.md): 정지 전환, 실제→가상 모델 초기화, 가상→실제 현재 실제 상태 수용. 실제 장비 자동 이동 없음.
- [DT-003 모델 경계](Design/DT-003-model-interface.md): 기존 가상축·가상 IO 재사용, 향후 FMI 어댑터. 장치 동작은 모델이 계산.

| 후속 항목 | 순서 및 완료 판단 |
| --- | --- |
| [RF-005](RF/RF-005-mixed-bus-feasibility.md) | 혼합 버스·기존 서버 지원 여부를 먼저 검증. 불충족 시 구조 재논의 |
| [RF-006](RF/RF-006-command-feedback-router.md) | 논리 장치 매핑과 선택 명령·리드백 중계 |
| [RF-007](RF/RF-007-mode-switching.md) | 모델 초기화 및 정지 상태 전환·실패 처리 |
| [RF-008](RF/RF-008-omniverse-sync.md) | Omniverse 축·IO 표시와 전환 동기화 |

RF-005 기본 검증은 완료했으며 RF-006~008은 계획/미착수다. FMI 버전·실행 방식, Omniverse 전송 방식, 상세 상태 스키마는 미결정이며 임의로 확정하지 않는다. MockMaster 유지 및 TD-001 보류 방침은 변경하지 않는다. 독립 패키징의 후속 Docker 결정은 13절을 참조한다.

## 11. 파라미터 동기화 및 영구 저장 (2026-09-15)

[DT-004](Design/DT-004-parameter-sync-persistence.md)에 실제↔가상 파라미터 비교·선택 적용과 가상장치 영구 저장 요구를 기록했다. 모드 전환 상태 동기화와 분리한다. [RF-009](RF/RF-009-parameter-sync.md)는 양방향 적용·검증, [RF-010](RF/RF-010-parameter-persistence.md)은 안정적인 장치 ID 기반 저장·재시작 복원을 담당한다. RF-009는 미착수이며 RF-010은 RF-011 연계 기본 저장/복원을 구현하고 후속 검증 중이다. 저장소는 build·임시 폴더와 분리하며 기본값·영구 파라미터·실행 상태를 구분한다. 현재 저장 계약은 DT-005/RF-010의 schema 1 JSON, storage.directory, fsync 후 원자적 교체를 따른다.

## 12. 독립 설정과 혼합 장치 구성 (2026-09-15)

[DT-005](Design/DT-005-device-configuration.md): 최초에는 같은 .env 문법을 선택했으나 2026-09-22 결정으로 Simulator는 독립 JSON 단일 형식, Motion Server는 기존 .env를 유지한다. Motion Server 설정 자동 읽기·1:1 생성 옵션은 채택하지 않는다. 전체 버스에 실제 축 Slave 0~4·IO 5, 가상 축 6~10·IO 11을 배치하는 예시를 확정했다. Simulator는 로컬 0~5만 생성하고 라우터가 번호 공간을 매핑한다. 기본 3 Slave 혼합 통신은 RF-005에서 완료했으며 12 Slave 확장은 후속이다. [RF-011](RF/RF-011-device-configuration.md)에 독립 JSON 로더·4축 생성 초기 구현과 오프라인 검증을 완료했으며 4축 기본 동작 확인 후 8 ms 주기 안정성 문제가 재현되어 개선이 필요하다.

## 13. Docker 및 Edge 네트워크 배포 (2026-09-15)

[DT-006](Design/DT-006-docker-deployment.md)에 Linux Docker Engine·단일 Simulator 컨테이너·host 네트워크·외부 설정/영구 저장소를 초기 배포 방향으로 기록했다. Edge에 LAN 카드를 추가해 Master·Simulator·일반 엔지니어링/DT용 NIC 3개를 사용하며 Omniverse는 별도 PC에서 실행한다. Simulator는 실제 장비 체인 끝에 연결하고 같은 NIC로 프레임을 반환한다. 중간 IN/OUT 전달 기능은 초기 범위에서 제외한다.

[RF-012](RF/RF-012-docker-deployment.md)에 서비스 진입점, 종료·오류 처리, 컨테이너 물리 통신 및 파라미터 복원 검증을 미착수로 등록했다. 기존 서버의 Linux Edge 동시 배치는 검증 전이며, Windows Master와 별도 Linux Simulator의 기본 혼합 버스 검증은 RF-005에서 완료했다. 모델 배포 의존성, 이미지·볼륨 상세와 재시작 정책은 후속 확정한다.

## 14. Simulator JSON 단일 형식 결정 (2026-09-22)

장치별 ID·모델·초기 설정·IO 모듈을 묶어 관리하기 위해 [DT-005](Design/DT-005-device-configuration.md)를 JSON으로 변경했다. 각 장치의 필수 slave_index가 가상 Slave 순서를 결정하며 배열 나열 순서는 무관하다. 번호는 0부터 연속이고 영구 id는 별도다. Motion Server .env 자동 읽기와 두 형식 병행은 제외한다. 영구 파라미터는 별도 저장소를 유지한다. 현재 가상축 schema 1 로더를 구현했으며 확정 필드·검증 규칙은 DT-005와 RF-011을 따른다.

## 15. 현재 구현은 가상축으로 제한 (2026-09-22)

[RF-011](RF/RF-011-device-configuration.md)은 CMMT-AS 다중 가상축과 독립 JSON에 집중한다. [RF-013](RF/RF-013-virtual-io.md)에 가상 IO·CPX 모듈·IO-Link·센서 파라미터 저장을 Pending으로 등록하고 별도 재논의한다. 장기 IO 목표와 실제 IO 혼합 검증 이력은 유지한다. 축은 model.type/mode 및 parameter_set을 사용하며 단위·스케일은 장치 파라미터를 기준으로 한다. 쓰기와 영구 저장은 분리한다.

## 16. 동적 PDO 매핑 후속 등록 (2026-09-22)

[RF-014](RF/RF-014-dynamic-pdo-mapping.md)에 Master SDO 기반 지원 PDO 재매핑, process image·모델 배치 동시 갱신 및 정상 오류 응답 검증을 계획/미착수로 등록했다. RF-004의 동일 기본 구성 재설정과 구분하며 TD-001에 연계한다. 현재 대상은 가상축이고 IO는 RF-013 보류를 유지한다.

## RF-011 초기 구현 (2026-09-22)

직선축 2개·회전축 2개, 축별 parameter_set, JSON --config와 storage.directory를 확정·구현했다. 초기 정지 상태에서 마지막 저장 파라미터를 복원한다. PDO 선택 필드는 없고 동적 재매핑은 RF-014, 기존 모델 제한/회전 정책 개선은 RF-015로 분리한다. 실행·검증 결과와 남은 물리 시험은 RF-011을 기준으로 한다. IO 구현은 RF-013 보류를 유지한다.

## 성능 개선 우선순위 (2026-09-22)

[Python 세부 측정](RF/RF-011-python-timing-20260922.md)에서 IPC 왕복 중 모델 계산이 약 90%를 차지했다. 오프라인 프로파일의 주요 병목은 OD role 전체 검색이다. 다음 작업은 조회 인덱스 개선 후 동일 2축/4축 물리 시험이며, define/overlay 변경 시 인덱스 일관성·누락/중복 오류·축별 OD 독립성을 보존한다. 최적화는 미적용이다. 묶음 IPC는 이후 판단하며 연결 상실의 모든 원인을 이 병목으로 단정하지 않는다.
