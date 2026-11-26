# 동작 모델 프리셋

상태: **실린더·아날로그 지연 프리셋 로더 및 실제 FMU 연결 구현**.

재사용할 모델 종류와 모델 특성을 JSON으로 관리한다. 장치 종류/모델 종류별로 분류하고 프리셋 ID로 참조한다. 운전 조건·초기 조건은 `.env`의 `DEVICE_SIMULATOR_IO_MODEL_INSTANCES`에 둔다.

- JSON 필드: schema_version, id, model, config.
- 프리셋은 Git 관리 대상이며 실행 중 수정하거나 state에 복제하지 않는다.
- 같은 프리셋을 선택한 각 인스턴스의 상태는 독립적이다.
- 기존 축 OD 파라미터 저장 및 AXIS_MODELS를 변경하지 않는다.
- 등록 모델: pneumatic_double_acting, analog_delay. 프리셋 ID: cylinder_100mm, analog_delay_16ms.
- 새 모델 종류에는 어댑터·변수 계약·검증된 FMU가 필요하다. JSON 추가만으로 임의 모델이 실행되지는 않는다.

[RF-013](../Doc/RF/RF-013-virtual-io.md)의 현재 계약을 따른다.
