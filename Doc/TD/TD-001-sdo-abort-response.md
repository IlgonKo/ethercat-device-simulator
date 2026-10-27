# TD-001 — KickCAT SDO Abort 응답 호환성

- 상태: 래퍼 구현·비물리 응답/복구 검증 완료 / 물리 PySOEM 재검증 대기
- 등록일: 2026-09-14
- 관련 RF: [RF-002-1](../RF/RF-002-1-sdo-diagnostic.md), [RF-003](../RF/RF-003-cmmt-model-integration.md)
- 영향: 오류 SDO 응답이 PySOEM에서 SdoError 대신 PacketError로 전달됨
- 초기 결정(2026-09-14): 기록 후 보류. 2026-10-27 아래 프로젝트 래퍼를 구현했다.
- 구현 방향: upstream 직접 수정보다 래퍼를 우선 검토하되 세부 방식은 추후 결정한다.

2026-09-14 16:50 KST. KickCAT/PySOEM/래퍼 동작을 수정하지 않고 `--with-sdo --sdo-errors`로 재현했다.
캡처는 Windows 전용 NIC에서 EtherType 0x88A4만 수집했다.

- 캡처: `build/captures/20260914-165011/sdo-abort.pcapng`
- 디코딩: 같은 폴더 `abort-frame444.txt`
- 실행 결과: `build/diagnostics/9a1f1df0c0474672928b2d12c7428aaf/result.json`

## 관측 사실

Frame 439는 Master의 mailbox write 요청이고, frame 444는 Slave mailbox 0x1400을 읽은 FPRD 반환 프레임이다. 후자는 WKC=1이며 아래 응답 데이터를 포함한다. 원래 EtherCAT 프레임이 반환되므로 source MAC으로 방향을 추론하지 않는다.

```text
                  CoE   SDO  Index Sub  Data / Abort code
요청(frame 439):   00 20 23   00 10 00   00 00 00 00
응답(frame 444):   00 20 83   00 10 00   02 00 01 06
```

- Mailbox payload length: 10, type CoE=3, counter=4
- CoE header: 0x2000, service=2 (SDO Request)
- SDO command byte: **0x83**
- Index/subindex: **0x1000:0**
- Abort code: **0x06010002**, read-only object write rejection
- PySOEM result: **PacketError(1, 1)**

Wireshark는 command 상위 3비트가 4이므로 Abort Transfer로 표시하지만, 실제 command 전체 바이트는 0x80이 아닌 0x83이다.

## 코드와 대응

KickCAT `ServiceData`의 command는 전체 바이트가 아닌 상위 3비트 필드이다. `SDOMessage::abort()`가 command만 4로 바꾸면서 요청 0x23의 하위 비트(size_indicator=1, transfer_type=1)를 지우지 않아 0x83이 된다. 해당 함수는 CoE service를 SDO_REQUEST로 지정하고 Abort code를 복사한다.

공개 SOEM v1.4.0 `ecx_SDOwrite()` expedited 경로는 정상 응답 조건에서 벗어나면 command 전체가 ECT_SDO_ABORT(0x80)인지 비교한다. 0x83은 이 비교에 맞지 않아 Unexpected frame 오류 경로에 들어간다. 설치된 PySOEM 1.1.13에서도 실제 PacketError가 재현됐다. 공개 SOEM 코드 참조는 설치 바이너리의 정확한 소스 revision을 확인한 것과는 구분한다.

CoE service=2는 올바르다. 앞선 'SDO_RESPONSE로 바꿔야 할 수도 있다'는 추정은 철회한다. 명령 바이트의 하위 비트 잔존이 문제이며, Abort code는 올바르다. 패치/래퍼 보정은 적용하지 않았다.

참조: https://github.com/OpenEtherCATsociety/SOEM/blob/v1.4.0/soem/ethercatcoe.c#L337-L382

## 공개 자료 교차 확인 (2026-09-14)

ETG 규격 원문 전체를 직접 열람한 것은 아니다. TR-Electronic 공식 문서의 Abort SDO Transfer Request Protocol 표와 SOES/IgH 구현을 교차 확인했다.

- Abort는 Slave → Master 방향에서도 CoE Service `0x02` (SDO Request)를 사용한다.
- 명령의 상위 3비트는 `100`, 하위 5비트는 모두 0이므로 전체 바이트는 `0x80`이다.
- SOES는 응답 생성 시 CoE SDO Request와 명령 `0x80`을 설정한다.
- IgH Master는 서비스 2 및 `(command >> 5) == 4`로 Abort를 판별한다. 상위 3비트만 확인하는 수신 구현도 실제 존재하지만, 송신 형식의 하위 비트 잔존을 정당화하지 않는다.

```text
                CoE    명령  Index  Sub  Abort code
캡처:           00 20   83    00 10  00   02 00 01 06
기대:           00 20   80    00 10  00   02 00 01 06
```

Mailbox 헤더를 제외한 데이터이다. 보정한다면 검증된 Abort의 명령 바이트만 정규화하며 CoE 서비스, Index/Subindex 및 Abort code는 보존한다. 임의 위치의 0x83을 무조건 치환하지 않는다.

참고 자료:

- [TR-Electronic 공식 문서 — 11.3 Abort SDO Transfer Request Protocol](https://www.tr-electronic.de/produktselektor?cHash=12ca4b847d9086324b3087186e12e1a1&tx_mtmtrproductselector_productselector%5Baction%5D=getAggregateManualPdf&tx_mtmtrproductselector_productselector%5Bcontroller%5D=Selektor&tx_mtmtrproductselector_productselector%5Bid%5D=COH110M-00001&type=41459404)
- [SOES Abort 생성](https://github.com/OpenEtherCATsociety/SOES/blob/master/soes/esc_coe.c#L240)
- [SOES 상수 정의](https://github.com/OpenEtherCATsociety/SOES/blob/master/soes/esc.h#L204)
- [IgH Master Abort 판별](https://docs.etherlab.org/ethercat/1.6/doxygen/fsm__coe_8c_source.html)

## 추후 구현 검토

시뮬레이터 송신 경계인 `network.route(frame)` 이후, `out->write()` 이전을 후킹 후보로 검토했다. `AbstractSocket::write()`를 감싸는 소켓 데코레이터와 프로젝트 자체 실행 파일 구성이 후보이다. 실제 메일박스 데이터 경계, 길이, 서비스 및 Abort 명령을 확인할 수 있는 파서와 다중 datagram 처리가 필요하다. 기본 Board의 mailbox 주소 0x1400을 모든 장치에 고정하지 않는다.

이 내용은 후보 설계이며 구현 확정 또는 동작 검증 결과가 아니다. PySOEM에서 PacketError를 정상 Abort로 간주하는 처리는 넣지 않는다.

## 해결 완료 기준

- [ ] 후킹 및 보정 방식을 결정하고 구현한다.
- [ ] RO 객체 쓰기에서 캡처 명령 `0x80`, 서비스 2, Abort `0x06010002`를 확인한다.
- [ ] PySOEM이 PacketError가 아닌 SdoError와 실제 Abort code를 전달하는지 확인한다.
- [ ] 아직 실행하지 못한 없는 객체 `0x5FFF` 읽기의 Abort `0x06020000`을 검증한다.
- [ ] 정상 SDO 읽기·쓰기·복원 및 PDO 1,000회 회귀를 통과한다.
- [ ] 불완전 프레임과 비대상 메시지를 잘못 보정하지 않는지 검증한다.
- [ ] 수정 전후 캡처·실행 결과를 기록한 뒤 TD를 완료 처리한다.

캡처와 실행 로그는 `build/` 아래 로컬 증거이며 Git에서 제외된다. 저장소 클론만으로 원본 pcap을 받을 수 없으므로 필요 시 별도 보관한다.

## 관련 RF 추가 (2026-09-22)

[RF-014 동적 PDO 매핑](../RF/RF-014-dynamic-pdo-mapping.md)의 잘못된 설정 거부에도 정상 SDO Abort가 필요하다. TD-001의 응답 형식 보정과 RF-014의 매핑 검증·오류 생성은 별개다. 등록만으로 본 TD를 해결 처리하지 않는다.


## 2026-10-27 구현 및 검증

- KickCAT submodule 및 PySOEM/SOEM 원본은 수정하지 않았다. GNU linker `--wrap`으로 CoE 메시지 팩토리를 프로젝트 gateway로 감싼다.
- 모델 소유 OD는 직접 IPC 검증 후 성공 응답을 만든다. 기존 KickCAT after-write hook의 성공 응답 선발행 문제를 피한다.
- 미지원 SDO는 Python 서비스에서 구조화된 error 응답을 반환한다. C++ gateway는 0x80/CoE service 2/length 10의 Abort로 변환하고 다음 요청을 계속 처리한다.
- KickCAT이 처리하는 기타 OD의 Abort도 명령 바이트 전체를 0x80으로 정규화한다.
- 실제 Copley FMU + Python IPC + C++ mailbox 시험에서 restart=0 성공, restart=1/미지원 mode/RO 쓰기/없는 객체·subindex/잘못된 길이 Abort, 실패 후 OD 값 보존, 정상 SDO 읽기 및 PDO Operation Enabled 도달을 검증했다.
- 실행: `PYTHONPATH=src:. build/fmi-venv/bin/python scripts/linux/validate-sdo.py --binary build/timing/test_sdo_gateway` (Copley가 포함된 .env 필요, 임시 저장소 사용, NIC 미사용).
- 물리 PySOEM의 SdoError 수신과 캡처는 아직 재검증하지 않았다. native FMU crash/hang·IPC timeout 시 Slave 유지 정책은 별도 작업이다.

### 2026-10-27 — 메일박스 응답 길이 후속 수정

물리 재시험의 초기화 OD Communication failed 원인은 FMU 변수 누락이 아니라 래퍼가 응답 backing buffer를 16바이트로 축소한 것이었다. EmulatedESC는 SM 마지막 바이트가 기록되어야 mailbox-full을 설정한다. 원래 메일박스 버퍼 크기는 보존하고 헤더 payload length만 10으로 설정하도록 수정했다.

실제 Copley FMU + IPC에서 0x2194:1~4, 0x607D:1~2, 0x6081/6083/6084, 0x60A4:1, 0x607F, 0x2183:12, 0x60C5/C6 조회를 검증했다. 추가로 모든 응답을 실제 EmulatedESC의 128바이트 mailbox SM에 기록하여 mailbox-full 표시를 확인했다. 기존 Abort 및 후속 PDO 시험도 통과했다. Linux binary/Docker 이미지 갱신, 실행 중 컨테이너는 자동 재시작하지 않았다.
