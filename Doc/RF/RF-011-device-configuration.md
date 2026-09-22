# RF-011 — 독립 JSON 구성 및 다중 가상축

- 등록일: 2026-09-15
- 상태: 구현 진행 / 초기 구현 및 오프라인 검증 완료, 4축 기본 동작 확인, 8 ms 안정성 문제 재현 / 개선 필요
- 설계: [DT-005](../Design/DT-005-device-configuration.md)
- 연계: RF-005 혼합 버스, RF-006 ID 매핑, RF-010 영구 파라미터

## 현재 작업 범위

가상축만 구현한다. JSON 로더, 필수 slave_index와 영구 id, 장치 type, model.type·mode, parameter_set 연결을 구현한다. 우선 CMMT-AS 4축의 독립 모델·OD·PDO 동작을 검증한다. Motion Server 파일/소스/로더 의존과 .env 병행 지원은 없다.

파라미터 공간 신규 생성·기존 복원은 RF-010과 연계한다. role·counts_per_unit·initial_parameters는 현 합의 형식에 포함하지 않는다. 상세 규칙은 DT-005를 따른다.

## 완료 기준

- [x] 자체 JSON 문법·스키마 버전·중복 키·필드 타입 검증.
- [x] slave_index 연속 정수·고유 id 및 배열 순서와 독립된 생성 순서 검증.
- [ ] CMMT-AS 4축의 개별 identity·OD·PDO·모델 및 명령/리드백 분리 검증.
- [x] 타입·기본 PDO·모델·mode 호환성 및 미지원 구성 시작 전 거부.
- [ ] parameter_set 참조·중복 참조 거부, RF-010 저장/복원 경계 검증.
- [ ] 로컬 Slave 번호·전체 버스 번호·서버 Axis 번호 매핑 및 순서 변경 시 장치 식별 유지.
- [ ] 정지 후 재구성·Master 설정 정합성 절차 문서화.
- [x] IO 구성을 미지원 오류로 보고하고 축으로 대체하거나 무시하지 않음.

## 범위 이관

가상 IO·CPX 모듈·IO-Link·센서 모델·센서 저장·IO를 포함한 12 Slave 확장은 [RF-013](RF-013-virtual-io.md)으로 보류한다. 이전 RF-005 이관 중 다중 가상축은 여기서 수행하고 IO는 RF-013에서 재논의한다. 기존 실제 CPX가 포함된 혼합 버스 사용을 금지하는 의미는 아니다.

## 검증 기록

초기 구현과 오프라인 검증을 완료했고 사용자가 수동 실행 후 동작 테스트 완료를 보고했다. 세부 시험 항목과 계측 수치는 아래 사용자 확인 기록을 따른다. RF-005의 기본 혼합 성공을 다중 가상축 또는 가상 IO 구현 완료로 해석하지 않는다.

## 4축 검증 및 회전축 사전 점검 (2026-09-22)

사용자 요청으로 검증 목표를 CMMT-AS 4축으로 변경한다. 축별 모델·OD·PDO 독립성과 지원 운전 모드별 통신을 검증한다. 4축 구성은 이후 합의에 따라 linear 2개 + rotary 2개로 확정했다. 이 절의 사전 점검은 물리 4축 시험이 아니다.

현재 VirtualCiA402Servo는 공통 위치·속도 수치로 계산하며, OD 파라미터가 단위와 스케일을 결정한다. 별도의 회전축 전용 각도 누적 로직은 없다. rotary_deg 기본 설정은 위치 단위 0x4100, 위치 지수 6, 속도/가속도 지수 3이며, Position_limit(0x607D:01/02)의 초기값은 ±180000000(±180°)이다. 이 값은 변경 가능한 파라미터이지 모델에 고정된 회전 범위가 아니다. modulo/360도 wrap 및 최단 회전 경로 처리는 없다. Homing은 약 0.1초 후 위치 0으로 설정하는 단순 모델이다.

오프라인 모델 확인: PP에서 181000000 목표는 당시 Position_limit 상한 +180000000을 초과해 거부됐고, +170000000에서 -170000000 목표는 음의 방향으로 움직이기 시작했다. PV는 위치 179999999에서 양의 속도로 300회(10 ms) 계산 후 760999999까지 진행했고 속도 200000을 유지했다. 즉 PV 위치 한계 초과는 상태 비트 표시가 있지만 이 경로에 한계 도달 자동 정지 처리는 없다. 이전의 ‘제한 위치축’ 설명을 모든 모드의 강제 제한 보장으로 해석하지 않는다.

이는 로컬 모델만 실행한 사전 점검이며 실제 장비·EtherCAT 4축 통신 시험은 하지 않았다. 회전축 modulo/연속 회전 정책과 운전 모드별 위치 제한 일관성 개선은 RF-015로 분리하고 RF-011에서는 기존 모델 동작을 유지한다.

## 위치 제한 해석 정정 및 코드 재확인 (2026-09-22)

- PP 181° 거부는 기본 Position_limit 설정의 결과다. 상한을 +720°로 변경하면 181°는 위치 제한 검사를 통과한다. 이는 코드 조건에 따른 판단이며 +720° 설정의 별도 통신 시험을 수행한 것은 아니다.
- ‘각도 단위 누적 위치’는 공통 수치 계산에 각도 단위/스케일을 적용한다는 의미로 한정한다. 회전축 전용 누적 알고리즘 또는 고정 ±180° 모델 한계를 뜻하지 않는다.
- 현재 구현의 제한 적용은 경로별로 다르다. PP/CSP 목표 위치 입력은 0x607D 범위 밖 목표를 거부한다. PV는 속도로 위치를 갱신하며 위치 한계에 따른 자동 정지 코드가 없다. Jog는 한계에 도달한 상태에서 바깥 방향의 목표 속도를 0으로 변경해 감속한다. 공통 상태 처리는 실제 위치 한계 초과를 상태 비트로 표시한다. 목표 거부와 실제 위치의 강제 클램프는 구분한다.
- 이 차이는 공통 가상축 코드의 현재 동작이며, 회전축 고유 특성이나 실제 CMMT의 사양으로 확정하지 않는다. 제한 처리 변경 여부는 별도 결정한다.
- 확인 소스: Motion Server의 device/cmmt/non_pdo_configuration.py(rotary_deg), device/virtual_servo_drive/servo_model.py(set_target_position, process_pv, _limit_jog_velocity_at_software_limit, process_cycle).

## 확정 범위와 초기 구현 (2026-09-22)

- 사용자 합의: linear 2축 + rotary 2축, 축별 독립 parameter_set. 모델 동작 개선은 RF-015. JSON PDO 필드 제거, --config, storage.directory, 시작 시 적용·오류 시 전체 중단·재시작 시 초기 정지 상태를 확정했다.
- configuration.py: 엄격 JSON·중복 키·필수/미지원 필드·연속 정수 Slave 번호·중복 ID/저장 공간·축 타입/model/mode 검증과 상대 경로 해석.
- model_service.py: 축별 모델·OD·브리지·cycle counter, slave_index를 필수로 받는 다축 IPC, 축별 ESI/계약 생성.
- cmmt_simulator.cc: 다중 ESC·OD 콜백·고정 PDO 재설정 상태를 축별 보관하고 EmulatedNetwork에 순서대로 연결. FMMU에 해당하는 축만 PDO 모델을 진행한다. 현재 고정 byte-aligned 24-byte RxPDO가 한 datagram에 모두 포함되는 구성이 지원 범위다.
- parameter_store.py: RF-010 기본 저장/복원 경계, 기존 공간 호환성 확인, 원자적 교체·체크섬·단독 잠금. 영구화 범위와 미완료 사항은 DT-005/RF-010 참조.

## 검증 결과

- Python: Windows 전체 27개, Linux 변경 관련 24개 테스트 통과. JSON 오류 거부, 4축 OD·PDO·모델 분리, 각 축의 기존 PP/PV/CSP/Jog 및 단순 Homing, 저장/미저장 재시작, 순서 재배치, mode 불일치·손상 데이터 거부, 저장 실패 원본 보존·중복 실행 잠금 검증.
- Linux C++: 빌드 성공. 고정 PDO 재설정 및 4 ESC 브로드캐스트 WKC=4·축별/통합 PDO 대상 판별 테스트 통과. 이는 메모리 내 프레임 시험이며 물리 WKC 관측이 아니다.
- 실제 C++ 프로세스와 Python Unix socket 연결에서 4개 Slave ESI·OD 계약 검증 통과(--validate, NIC 미사용).
- 구현 시점에는 물리 시험을 수행하지 않았다. 이후 사용자가 동작 테스트 완료를 보고했다. 개별 identity·SDO·모드별 시험·축 간 독립성·WKC·주기·혼합 구성의 상세 결과는 아직 수집하지 않았으므로 포괄적인 완료 기준은 유지한다.
- Linux 전체 Python discovery는 Windows SDO 진단 테스트의 pysoem 미설치로 실패했다. 변경 관련 configuration/model_service 테스트는 별도 실행해 통과했다. Windows 전체 Python 테스트는 통과했다.

## 수동 실행과 다음 물리 시험

기존 Motion Server와 Simulator를 정지하고 Master 버스 설정을 새 가상축 수량/순서에 맞춘 뒤 실행한다. 기존 실행 중인 세션에는 이번 설정이 자동 적용되지 않는다. 현재 검증 빌드는 기존 실행 파일과 분리된 build/rf011에 있다.

```bash
cd /home/festo/Documents/ethercat-device-simulator
sudo setcap cap_net_raw,cap_net_admin=ep build/rf011/cmmt_simulator
python3 scripts/linux/cmmt-session.py --run-id fouraxis01 \
  --model-root build/model-source-da0b0a3 \
  --config config/four-axes.json --binary build/rf011/cmmt_simulator
```

run-id는 영문/숫자로 지정한다. 같은 이름의 로그 폴더가 있으면 -2, -3 등의 접미사를 붙여 새 폴더를 만들고 시작 출력에 실제 경로를 표시한다. 이전 로그는 유지한다. 기본 실행 시간 제한은 없고 stop 입력 또는 Ctrl+C로 종료한다. 저장 파일은 예제 기준 state/parameters에 생성된다. --config 사용 시 NIC는 JSON에서 읽고 --nic 중복 지정을 거부한다. Master의 실제 장치 수에 따라 전체 버스 번호는 달라지며 JSON slave_index는 가상 구간의 0~3이다.

NIC 없이 계약을 검증하려면:

```bash
python3 scripts/linux/validate-fleet.py --model-root build/model-source-da0b0a3 \
  --binary build/rf011/cmmt_simulator
```

물리 시험은 각 축의 identity·단위·위치 한계 확인 → PRE-OP SDO 독립성 → OP/PDO → 한 축 명령 시 다른 축 유지 → 지원 모드별 동작 → 4축 성공 세션 WKC·주기·시험 시간 기록 → 저장 후 프로세스 재시작 복원 순서다. 실제 장비에 연결된 상태에서는 기존 물리축과 가상축 번호를 먼저 확인한다.

## 사용자 수동 동작 시험 확인 (2026-09-22)

four-axes.json을 사용하는 수동 실행과 run-id 충돌 수정 안내 후 사용자가 “동작 테스트 완료”를 보고했다. 해당 4축 구성의 사용자 동작 시험 완료로 기록한다. 개별 축/운전 모드, 혼합 버스 구성, WKC·주기·시험 시간, SDO 저장 후 프로세스 재시작 복원 및 순서 재배치의 세부 결과까지 확인한 것으로 확장하지 않는다. RF-011 전체 완료 판정은 남은 기준을 점검한 후 수행한다.

## 2축·4축 처리 시간 비교 (2026-09-22)

[계측 보고서](RF-011-timing-20260922.md)에 실제 8 ms/120초 비교 결과를 기록했다. 2축은 WKC Fault 없이 종료했고 4축은 BUS_PROCESS_DATA_INCOMPLETE를 재현했다. 4축 PDO 처리 최대 11.509 ms, 8 ms 초과 16회이며 연결 상실은 이번에는 없었다. 기본 동작 확인과 안정성 완료를 구분하고 RF-011을 완료 처리하지 않는다. IPC 묶음 최적화와 timeout 변경은 적용하지 않았다.

## Python 계산 비용 분리 계측 (2026-09-22)

[분리 계측 보고서](RF-011-python-timing-20260922.md): 모델 계산이 IPC 왕복의 약 90%이며, 별도 오프라인 프로파일에서 7,400개 OD 항목을 주기당 4회 검색하는 definition_by_role가 모델 시간의 약 97.6%를 차지했다. 2축은 120초 정상, 4축은 약 103초에 BUS_CONNECTION_LOST가 재현됐다. role 조회 인덱스가 우선 개선 후보이며 최적화는 아직 하지 않았다.
