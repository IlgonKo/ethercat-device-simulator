# CPX ESI·Motion Server 진단 읽기 경로 조사

- 현재 상태: **조사 기록 / 코드 정적 확인** (2026-11-26)
- 대상: Linux Motion Server commit `ba1bab8`, 작업 트리 변경 없음. Soft ESC [RF-013](../RF/RF-013-virtual-io.md) 설계 근거.
- 최신 결정: 모델 오류는 내부 진단으로 유지하며 CPX 전달에서 제외한다. 아래 이전 조사 중 모델 오류 투영 제안은 철회했고 CPX 자체 진단 근거만 유지한다.
- 이번 조사에서 실제 SDO/PDO 요청·운전 시험·Motion Server 수정은 수행하지 않았다.

## ESI 근거

Motion Server `device/cpx_ap_i_ec/esi/festo_cpx_ap_i_ec.xml` SHA256:
`b11d95f0922884584a8500c0a96c4dddbcfa8e65b87b46882a66699cbbe03b32`.
`esi_module_catalog.find_device()`와 동일하게 CPX-AP-I-EC-M12 중 0x27F0이 있는 Device를 선택했다. ProductCode=8086609, RevisionNo=0x00000002. 다른 ESI revision 전체를 검증한 것은 아니다.

| OD | 의미 | 형식 | 진단 PDO 내 바이트 위치 |
| --- | --- | --- | --- |
| 0x6102:01 | Category Status | DWORD, 32bit | 0..3 |
| 0x6102:02 | Count Active Diagnosis | UINT, 16bit | 4..5 |
| 0x6102:03 | Module With Latest Diagnosis | UINT, 16bit | 6..7 |
| 0x6102:04 | Latest Diagnosis Code | UDINT, 32bit | 8..11 |

모두 읽기 전용이며 TxPDO mapping 가능하다. ESI의 0x1AF1 Diag PDO는 위 4개를 매핑한 12바이트다. ESI TxPdo에 기본 Sm 지정이 없고 Motion Server DEC-020/RF-012도 선택형으로 명시한다. 0x6102 OD 구조의 112bit(SubIndex 0·정렬 포함)를 PDO 12바이트와 혼동하지 않는다.

0x1001은 8bit Error register다. 0x10F3은 Diagnosis History이며 0x1AF0은 새 메시지 플래그와 padding을 매핑하는 별도 PDO다. 0x6102만으로 활성 진단 전체·채널별 유효성을 전달할 수 있다고 가정하지 않는다. Category 비트 의미/진단 코드의 합법적인 매핑은 ESI 이름만으로 확정하지 않았으며 제조사 계약 대조가 필요하다.

## 현재 Motion Server 읽기 경로

1. **주기 IO 값**: `device/cpx_ap_i_ec/pdo_codec.py::CPXPdoCodec.decode_txpdo` → 모듈 DI/AI 디코드 → `motion_server/api/encoder.py::io_device_snapshot` → `handlers/status/io_status.py::io_status_message` → `system/io/status`.
   - 모듈 값만 디코드하며 0x6102 진단 변환은 없다.
   - 일반 DI/AI는 값 목록만 반환한다. `process_data_valid`는 서버 세션 상태 기반이며 이 경로에서 IO-Link 쪽에 전달될 뿐 일반 DI/AI의 모델 데이터 신선도/유효성을 표현하지 않는다.
   - `diagnostic_status_snapshot`은 이미 등록된 Diagnostic을 직렬화할 뿐 장치 OD를 읽는 함수가 아니다.
2. **명시적 개별 SDO 조회**: `system/io/param_read` → `handlers/status/registry.py::handle_io_parameter_read` → `handlers/parameter_access/ethercat.py::_read_io_parameter` → `runtime.sdo.io` → EtherCAT SDO transport.
   - uint8/uint16/uint32 읽기 경로가 있다. 장치가 제공하면 0x1001, 0x6102의 개별 subindex를 조회할 수 있는 코드 경로다. 자동 polling/Alarm·Fault 등록은 아니다.
   - `system/io/ethercat/param_catalog`은 ESI 기반 객체 목록을 제공하며 값의 실시간 진단 수집이 아니다.
3. **매핑 검증**: `device/cpx_ap_i_ec/pdo_configuration.py::validate_process_image_mapping`은 모듈 또는 고정 block layout의 정확한 일치를 요구한다. TxPDO 진단 추가를 허용하지 않는다. `tests/test_cpx_process_image.py::test_rejects_input_truncation_extra_diagnostic_and_wrong_slot`에도 추가 진단 항목 거부가 있다.
4. **기존 의사결정**: `docs/decisions.md` DEC-020은 health source가 보장되지 않는 현재 구성에서 CPX IO 진단을 생성하지 않는다고 명시한다. `docs/tasks/rf/RF-012-cpx-ap-optional-diagnostic.md`가 선택형 0x1AF1 활성화·12byte offset·station 진단 변환의 기존 후속 항목이다. 주기 SDO polling도 아직 채택되지 않았다.

## 현재 책임 분리 — 2026-11-26 확정

- 모델 계산 실패·잘못된 출력·Host 종료/IPC timeout은 내부 Diagnostic/로그로 검출·기록한다. 마지막 정상 IO 값 유지·장애 격리·Slave 유지·수동 재시작 정책은 RF-013을 따른다.
- 모델 오류를 CPX Category(Software/Misc 포함)·1001·6102·모듈 진단·10F3·Emergency로 변환하지 않는다. 모델 오류용 CPX 진단 코드 제안은 철회한다. 채널 식별자는 내부 영향 정보일 뿐 채널 하드웨어 오류로 분류하지 않는다.
- CPX는 기본 오류 상태 OD(1001/6102 기준)의 개별 읽기만 1차 지원한다. 진단 PDO·10F3 이력·Emergency 전송은 제외한다. 이 문서의 ESI 기능 설명은 제조사 기능 조사이며 Soft ESC 전체 구현 선언이 아니다.
- WKC/OP·CPX health와 모델 계산 정상 여부는 독립적이다. 별도 전달 경로 전에는 내부 로그로 확인하고 향후 상위 애플리케이션이 모델 상태를 별도 경로로 수집한다. Omniverse 통합·관리 인터페이스는 이번 구현 범위가 아니다.
- Host가 중단된 경우에도 살아 있는 감시 경로에서 내부 진단을 기록한다. 기존 축의 RF-018 Fault 표현/Reset 정책에는 이번 IO 결정을 소급 적용하지 않는다.

## Motion Server 개선 항목 — 별도 TD 등록용

범위: 아래는 CPX 자체 장치 진단을 수집하기 위한 Motion Server 별도 개선 항목이다. 모델 오류 전달은 포함하지 않는다. CPX 진단 수집을 구현해도 동작 모델의 계산 중단·출력 신선도를 보증하지 않는다.

1. **선택형 CPX 진단 PDO 지원(서버 후속 범위, Soft ESC 1차에는 미적용)**: 명시적 설정으로 0x1AF1 assignment·mapping readback을 검증하고 12byte diagnosis 영역과 모듈 데이터 offset을 정의한다. 기존 모듈/고정 layout과 비활성 구성을 회귀한다. 기존 RF-012와 연계하고 중복 과제로 만들지 않는다.
2. **진단 수집·변환**: 0x6102 4개 필드를 디코드해 station 단위 IO Diagnostic으로 전달한다. Category는 원인 분류이므로 그것만으로 Alarm/Fault를 판정하지 않는다. 진단 코드/심각도 근거와 발생·해제·latching·acknowledge 규칙을 명세한다. module/code는 상세정보로 보관하고 latest 항목을 전체 활성 목록으로 오인하지 않는다. 상세정보의 API 직렬화 범위도 확인한다.
3. **CPX 장치 데이터 유효성 계약**: 값 보관과 갱신 정상 여부를 분리한다. 버스 연결/OP/WKC, 진단 수집 사용 여부·신선도, 장치 health를 함께 고려해 유효성/불명 상태를 공개 API에서 표현한다. 진단 소스가 비활성·미지원·오래됐다는 이유로 정상으로 간주하지 않는다. 세부 enum/필드 이름은 Motion Server에서 결정한다.
4. **공식 클라이언트 표시와 회귀**: IO status/진단 화면에서 유지된 값과 오류·유효성 상태를 구분한다. 정상·장치 장애 중 WKC 정상·버스 이탈·복구·다중 IO·진단 비활성 및 실장치/Soft ESC 동일 계약을 검증한다. CPX 진단이 없는 버스 WKC 실패를 특정 IO 고장으로 추정하지 않는다.

Motion Server 개선은 이 저장소에서 구현하지 않는다. 사용자 요청에 따라 별도 TD로 등록할 내용만 분리한다. Soft ESC RF-013 완료 판정에는 확정된 CPX 자체 진단 제공 범위만 적용하며, Master 표시 개선 및 별도 모델 상태 전달을 모델 장애 격리 검증의 선행 조건으로 두지 않는다.

## 추가 OD·제조사 의미 대조 — 2026-11-26 정적 조사

근거: 같은 Linux Motion Server의 `Reference/CPX-AP-I-EC-M12.pdf`(2025-05d), 22쪽 표19/21 및 26쪽 표31. ESI/서버 코드를 함께 대조했으며 실장치 응답을 새로 확인한 것은 아니다.

- 서버 prepare_process_image는 Identity 확인 → IO-Link가 있을 때 variant 설정 → F050 조회/F030 쓰기·재조회 → 1C12/1C13 매핑 조회·검증 순서다. 이번 DI/DO/AIO 범위에는 IO-Link variant 설정이 필요 없다.
- F030 쓰기는 각 ident를 :01부터 쓴 다음 :00에 개수를 쓴다. 개수 clear 선행을 강제하면 현재 서버 절차와 충돌한다. F050에는 interface를 포함한 구성 목록을 제공한다.
- pdo_configuration.py의 REQUIRED_STATION_OD는 ESI 카탈로그 존재 검사다. 여기에 27F0이 포함됐다는 이유만으로 초기화 때 모든 AP 파라미터를 SDO로 읽고 쓴다고 해석하지 않는다.
- Category Status는 오류 심각도가 아닌 원인 분류다. bit6=Configuration/Parameter, bit8=Communication, bit11=Software다. 예를 들어 Software category만으로 제조사 모든 코드의 Fault/Alarm 심각도를 확정할 수 없다.
- 27F1:01의 제조사 의미는 0=파라미터 값 변경 없이 저장분 삭제, 1=저장/갱신, 2=저장분 삭제와 기본값 복원이다. 현재 서버의 volatile=0/non_volatile=1 이름을 단순 영구 저장 모드 스위치로 복제하면 안 된다. 이 API 의미 정합성은 사용자 등록 Motion Server TD-044(`docs/tasks/td/TD-044-cpx-parameter-storage-semantics.md`)로 추적한다.
- F030은 선택 ESI에서 rw이고 현재 서버가 쓰지만 매뉴얼의 접근 표기는 ro다. 선택 revision/ESI와 현재 서버 호환 동작을 기준으로 구현 계약을 명시하고, 이를 모든 실장치 revision의 동작으로 일반화하지 않는다.

## CPX OD 1차 지원 범위 — 고정 PDO·설정 최소화·기본 오류 상태 읽기 확정

| 그룹 | 제안 |
| --- | --- |
| 식별 | 1000/1008/1009/100A/1018, station·모듈 식별정보를 선택 ESI 형식으로 읽기 제공 |
| Modular Device Profile | F000, F050 읽기, F030 PRE-OP 쓰기/읽기. .env가 실제 가상 모듈 구성을 정하며 F030 쓰기로 모듈을 생성·삭제하지 않음. 요청 목록과 구성의 일치 검증 |
| 주기 IO | 선택 모듈의 6000/7000 영역, 1C00/1C12/1C13 및 해당 mapping 객체. ESI 슬롯 stride·bit 정렬·부가 공급 출력 비트를 포함해 Motion Server가 해석하는 전체 layout과 일치시킴. 모듈 구성에서 고정 생성하고 mapping/assignment 개별 읽기만 지원. 쓰기·CPX 매핑 저장/복원은 제외. 축 RF-014 계약은 유지 |
| 현재 장치 진단 | 기본 오류 상태 OD(1001/6102 기준)의 개별 읽기만 제공. 실제 지원하는 CPX 자체 상태·자료형은 구현 지원표에 명시. 모델/Host 오류는 포함하지 않음. 진단 PDO·이력·Emergency 전송 제외 |
| AP·모듈 설정 | 1차 DI/DO/AIO 초기화에 불필요한 2000 영역 설정·27F0 AP 접근은 제외. 미지원 SDO 요청은 정상 Abort, 성공/적용/기본값을 가장하지 않음 |
| 저장·이력 | 27F1 저장, 10F3 이력 및 1AF0은 1차 범위에서 제외 확정. 지원 전 명령 성공/저장 완료/정상 이력을 가장하지 않음. CPX 매핑은 저장하지 않으며 시작 때 모듈 구성에서 생성. 축 매핑 저장 및 동작 모델 프리셋은 유지 |

지원하지 않는 OD·subindex·접근·Complete Access에는 정상 SDO Abort를 반환하고 Slave/Host를 종료하지 않는다. ESI에 항목이 있다는 이유만으로 기능 구현 완료를 선언하지 않는다. 이번 제안으로 기존 RF-014의 매핑 정책을 변경하지 않는다.

## 철회한 모델 진단 매핑과 남은 사항

- 모델 계산 오류를 Software 또는 Misc category 및 CPX 진단 코드로 투영하는 제안은 철회했다. 해당 모델과 연결 station/모듈/채널 목록은 내부 Diagnostic에만 남긴다.
- CPX Category/오류 수/latest-module/latest-code는 CPX 자체 진단 사건으로만 구성한다. 모델 오류로 이 값을 채우거나 정상 채널/모듈을 하드웨어 고장으로 표시하지 않는다.
- CPX 고정 PDO·매핑 읽기 전용·모듈/AP 파라미터와 27F1 제외는 확정했다. CPX 기본 오류 상태 OD 읽기만 지원하고 진단 PDO·이력·Emergency 전송은 제외하기로 확정했다. 모델 상태 외부 전달 API/프로토콜은 후속 논의이며, 이번에 코드나 컨테이너를 변경하지 않았다.
