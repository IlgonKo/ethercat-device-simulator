# RF-011 — 독립 장치 구성 및 다중 가상축

- 현재 상태: **완료**
- 상태 상세: .env 구성·4축 독립성·혼합 운전·저장 공간 연결을 기존 검증 근거로 완료 판정 (2026-10-28).

## 현재 범위와 판정

Simulator 자체 `.env`에서 명시적 로컬 Slave 번호, 장치 ID, 모델, linear/rotary, parameter_set을 구성한다. BUS 타입은 `cia402-drive`, 모델은 `f_kr_cmmt` 또는 `copley_drive_sim`이다. Motion Server 설정을 읽거나 공유하지 않는다. 가상 IO는 RF-013, 동적 PDO는 RF-014, 위치 제한·회전 경로 변경은 RF-015 범위다.

사용자 확인대로 실제 축·IO + F-KR 2축 + Copley 2축 혼합 환경에서 이미 계속 검증했다. 혼합 환경 구축이나 기본 통신을 신규 시험으로 요구하지 않는다. 구성·독립성의 오프라인 검증과 물리 운전·SDO 관측을 결합하여 아래 기준을 판정했다. 장시간 성능·현 구조 2축/4축 정량 비교는 RF-016/017에서 계속 추적하며 완료했다고 주장하지 않는다.

## 완료 기준 및 기존 근거

| 기준 | 판정 | 근거와 검증 범위 |
| --- | --- | --- |
| 독립 .env 문법·중복 키·필드·타입 검증 | 완료 | .env 전환 회귀 22개 및 configuration 테스트. 과거 JSON 사용자 구성 계약 대체 |
| 명시적 연속 Slave 번호·고유 ID·입력 순서와 독립된 생성 | 완료 | order/relative_storage, env round trip 및 잘못된 번호·ID 거부 시험 |
| 4축 OD·PDO·모델·명령/리드백 분리 | 완료 | four_distinct_models_od_and_pdo, each_axis_moves_independently, fixture identity/계약 검사. 사용자 4축 동작 및 혼합 물리 운전 확인 |
| 프로파일·모델·mode 호환성 및 미지원 구성 거부 | 완료 | 구성 회귀 및 Copley/F-KR registry 검증 |
| parameter_set 참조·중복 거부·저장/복원 경계 | 완료 | 구성 회귀 및 RF-010 물리 저장·재생성·58개 SDO 대조 |
| 번호 공간 매핑·순서 변경 시 ID/저장 공간 유지 | 완료 | 아래 운영 매핑과 index_reorder_keeps_parameter_space 시험. 물리 케이블 재배열 시험을 했다는 뜻은 아님 |
| 정지 후 재구성과 Master 정합성 절차 | 완료 | 아래 현행 Docker 절차 및 기존 재생성·Master 재연결 기록 |
| 가상 IO 미지원 구성 거부 | 완료 | 구성 검증; IO를 축으로 대체하거나 무시하지 않음 |

구성 시험 소스: [test_configuration.py](../../tests/integration/test_configuration.py). 기존 통과 기록은 [과거 기록](../Validation/RF-011/history-through-20261028.md), 물리 근거는 [RF-010](RF-010-parameter-persistence.md)·[RF-018](RF-018-diagnostic-fault.md). 이번 문서 정리에서 시험을 새로 실행하지 않았다.

## 확인된 혼합 구성의 번호 대응

| 대상 | 전체 Slave 번호 | Simulator 로컬 번호 | Motion Server Axis 번호 |
| --- | --- | --- | --- |
| 실제 축 | 0 | 해당 없음 | 0 |
| 실제 IO | 1 | 해당 없음 | 해당 없음 |
| F-KR virtual-axis-0 / cmmt-0 | 2 | 0 | 1 |
| F-KR virtual-axis-1 / cmmt-1 | 3 | 1 | 2 |
| Copley virtual-axis-2 / copley-2 | 4 | 2 | 3 |
| Copley virtual-axis-3 / copley-3 | 5 | 3 | 4 |

이는 검증된 해당 구성의 매핑이다. 다른 버스에 그대로 적용하지 않는다. EtherCAT identity는 CMMT 호환값으로 같을 수 있으며 영구 장치 ID와 구별한다.

## 정지 후 재구성 절차

1. Motion Server 동작·버스 통신을 정지하고 `bash scripts/docker/stop.sh`로 Simulator를 정지한다.
2. `.env`와 state를 백업한다. BUS와 네 AXIS 목록을 함께 수정한다. 순서만 바꿀 때 장치별 ID와 PARAMETER_SET 연결은 유지한다.
3. Motion Server 자체 설정의 전체 버스 순서·타입을 별도로 맞춘다. 설정 자동 공유는 없다.
4. `bash scripts/docker/validate.sh`로 확인하고 `bash scripts/docker/start.sh`로 재생성한다. 코드 이미지 변경 시 `--build`를 사용한다. C++ 빌드는 별도다.
5. Master 재검색·초기화 후 identity, Slave/Axis 번호, 파라미터 readback 및 WKC를 확인한 뒤 운전한다. 모델은 현재 위치·진행 명령을 복원하지 않는다. Master 초기화의 Enable 처리는 별도다.

현행 실행은 [scripts](../../scripts/README.md), 저장 백업/복원은 [RF-010](RF-010-parameter-persistence.md)을 따른다.

## 남은 항목과 검증 기록

현재 RF-011 기능 범위의 미완료 항목은 없다. 성능 계측은 RF-016/017, Docker 배포 조건은 RF-012에 남긴다. 12 Slave·가상 IO·핫플러그 검증 완료로 확대하지 않는다.

- [과거 구현·검증 기록](../Validation/RF-011/history-through-20261028.md): JSON/native 명령은 당시 이력이다.
- [프레임·IPC](../Validation/RF-011/RF-011-timing-20260922.md), [Python 계산 비용](../Validation/RF-011/RF-011-python-timing-20260922.md).
- [최적화 후 2축/4축](../Validation/RF-011/RF-011-role-index-20261020.md): 8ms·각 120초 정지 시험. 현재 Copley 혼합 장시간 이동 성능으로 확대하지 않는다.
