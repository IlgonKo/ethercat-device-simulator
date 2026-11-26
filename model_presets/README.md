# 동작 모델 프리셋

상태: **형식 채택·기본 프리셋 추가, 제품 로더 미구현**.

재사용할 모델 종류와 모델 특성을 JSON으로 관리한다. 장치 종류/모델 종류별로 분류하고 프리셋 ID로 참조한다. 운전 조건·초기 조건은 `.env`의 `DEVICE_SIMULATOR_MODEL_<id>_INSTANCE_CONFIG`에 둔다.

- JSON 필드: schema_version, id, model, config.
- 프리셋은 Git 관리 대상이며 실행 중 수정하거나 state에 복제하지 않는다.
- 같은 프리셋을 선택한 각 인스턴스의 상태는 독립적이다.
- 기존 축 OD 파라미터 저장 및 AXIS_MODELS를 변경하지 않는다.
- 모델 ID 등록·탐색·패키징은 구현 전이다. 파일 추가만으로 실행 지원이 완료된 것은 아니다.

[RF-013](../Doc/RF/RF-013-virtual-io.md)의 현재 계약을 따른다.
