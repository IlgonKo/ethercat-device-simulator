# RF-013 — 가상 IO 및 IO-Link 시뮬레이션

- 등록일: 2026-09-22
- 상태: **Pending / 보류 — 사용자와 별도 재논의 후 착수**
- 등록 사유: 현재 구현 범위를 가상축으로 한정. RF-011의 가상 IO 항목을 분리한다.
- 관련: [DT-005](../Design/DT-005-device-configuration.md), [RF-011](RF-011-device-configuration.md)

## 향후 논의·구현 후보

- 기존 가상 IO 모델 재사용 및 CPX-AP-I-EC 가상 Slave의 identity·OD·PDO·모듈 구성.
- DI/DO/DIO/AI/AO/AIO의 슬롯·채널 정의와 입력 설정·출력 조회.
- IO-Link 모듈·포트, IODD·ProcessData profile, 미연결 포트 표현.
- 센서 동작 모델, ISDU 파라미터, CPX 본체/센서의 영구 저장 및 저장 명령 의미.
- 라우터·DT 연결·실제/가상 IO 대응 및 확장 혼합 버스 시험.

## 이전 논의 보존 — 확정 스키마 아님

기존 대화에서는 slot/port 명시, device:null로 미연결 표현, IODD 및 process_data_profile 지정, 최초 입력값 설정·출력 조회부터 구현하는 초안에 동의했다. 이후 사용자가 IO 전체를 별도 논의로 보류했으므로 이 내용을 현재 구현 계약으로 사용하지 않는다.

IO-Link 센서별 id·parameter_set은 제안만 있었으며 확정되지 않았다. 구체적인 JSON 필드·모듈 범위·식별 정보·모델·센서 저장 규칙은 재논의한다. IODD가 센서 동작 모델 자체는 아니라는 경계도 검토한다.

## 착수 및 완료 기준

- [ ] 사용자와 IO 범위 및 JSON 스키마 재합의.
- [ ] 지원 모듈·IODD·PDO/SDO·모델 및 파라미터 저장 계약 정의.
- [ ] 합의한 범위의 가상 IO 구현 및 개별 채널/포트 검증.
- [ ] 실제·가상 IO 혼합 통신 및 라우터/DT 연동 범위별 검증.

RF-011 완료의 선행 조건이 아니다. 기존 RF-005의 실제 CPX IO 읽기 성공은 보존하며 가상 IO 구현 완료로 해석하지 않는다. 이 RF 등록만으로 IO 구현을 시작하지 않는다.
