# RF-015 — 1~4단계 구현·오프라인 검증

- 현재 상태: **1~4단계 완료 / RF-015 전체 진행 중**
- 일자: 2026-11-26
- 기준: [RF-015](../../RF/RF-015-axis-model-semantics.md)
- 기준 커밋: 76c94a0 + 이번 작업 트리 변경
- 환경: Linux Edge-ubuntu, build/fmi-venv/bin/python, PYTHONPATH=src:.

## 구현

- F-KR 동작 모델에 불변 PPExecution/StopExecution을 도입했다. 공개 OD는 그대로 하나이며 실행 중 목표·프로파일·감속·한계는 별도 실행 상태로 확보한다.
- PP 이동 중 OD 변경은 현재 이동에 영향을 주지 않는다. 이동/감속 중 새 edge를 무시하고 정지 후 재생하지 않는다.
- 0x6060 요청과 0x6061 적용 모드를 분리했다. 이동 중 요청은 유지하되 정지 후 적용한다.
- PV/Jog의 방향 반전은 감속→0→반대 가속 순서다. 한계는 운전별로 확보하며 차단 후 중립 입력과 새 명령으로 재개한다.
- Stop/Halt는 감속값을 확보하고 이전 운전을 취소한다. Quick Stop 옵션 2는 감속 후 Switch On Disabled, Disable Operation은 즉시 정지 후 Switched On이다.
- Homing은 누적 시뮬레이션 시간 0.1초 후 좌표 0/참조 완료다. 중단은 완료로 처리하지 않으며 완료된 참조는 일반 Fault Reset/Disable에서 유지한다.
- F-KR 어댑터에서 역전된 위치 범위와 Quick Stop 미지원 옵션/0 감속값을 거부한다. 저장·복원 시에도 위치 범위 유효성을 검사한다.
- 0x605A/0x6085를 모델 OD 공개 목록에 추가했다. 기본 PDO나 IPC 메시지 형식을 변경하지 않았다.
- Copley, Motion Server, RF-014 및 실행 중 세션은 변경하지 않았다.

## 시험 결과

| 시험 | 결과 |
| --- | --- |
| tests/unit/test_axis_semantics.py | 34개 통과 |
| tests/unit 전체 | 123개 실행, 122개 통과, 1개 건너뜀 |
| 혼합 4축 동적 매핑·시작/재시작 저장 복원 | 통과 |
| 혼합 4축 PP·재매핑·축 독립성 | 통과 |
| IPC 지연/timeout/정지/종료/오래된 session·request/비활성 상태 timeout·정지 | 8개 통과 |
| git diff --check | 통과 |

건너뛴 항목은 test_sdo_restore의 Windows PySOEM 진단 시험이다. 물리 SDO 시험을 통과한 것으로 계산하지 않았다.

34개 신규 시험은 PP 목표/프로파일 고정·다음 명령 반영·중복 요청·범위 밖 요청, 한계 경계/복귀, PV/Jog 반전과 정지, 동일/지연 모드 적용, Stop 감속 고정, Quick Stop 우선순위, Disable/Reset 후 재실행 방지, Homing 완료/취소·참조 보존, 3축 독립성, CSP 기존 추종/범위 거부, 신규 OD 공개를 검증한다. 시험에서 가상 시간만 진행하며 물리 이동은 없다.

재현 명령(저장소 루트):

```bash
PYTHONPATH=src:. build/fmi-venv/bin/python -m unittest tests.unit.test_axis_semantics
PYTHONPATH=src:. build/fmi-venv/bin/python -m unittest discover -s tests/unit
PYTHONPATH=src:. build/fmi-venv/bin/python tests/integration/run_dynamic_mapping.py --axes 4 --fmu-dir model_artifacts --storage-startup
PYTHONPATH=src:. build/fmi-venv/bin/python tests/integration/run_dynamic_mapping.py --axes 4 --fmu-dir model_artifacts --motion
PYTHONPATH=src:. build/fmi-venv/bin/python tests/integration/run_remap_ipc.py --fmu-dir model_artifacts
```

통합 시험은 기존 build/timing/cmmt_simulator의 NIC 없는 self-test 경로와 현재 Python 코드를 사용한다. 실제 NIC, 실행 중 Docker, 기존 state 저장소를 사용하지 않고 임시 저장소를 생성한다. 물리 WKC·주기 성능 검증을 대체하지 않는다.

## 남은 범위와 제한

- 새 Docker 이미지 빌드/적용 및 Motion Server 물리 통합은 아직 수행하지 않았다.
- 원시값 계산과 기존 단위 스케일링은 유지했다. 어댑터 SI 변환 경계 정리는 5단계다.
- Quick Stop 0x605A/0x6085는 현재 영구 저장하지 않는다. 0x605A는 옵션 2만, 0x6085는 프로파일 기본 감속값으로 생성되며 SDO 변경값은 모델 재생성 시 소멸한다. 기존 파라미터 스키마/파일은 변경하지 않았다. 저장 계약은 5단계에서 마무리한다.
- F-KR 3축 시험은 실행 상태 독립성 기본 검증이며 전체 물리 운전 조합의 완료 근거가 아니다.
- Copley의 운전 중 B8 OFF/Halt 미지원 차이는 기존 검토대로 남아 있다.
- RF-022 FMU 제작은 수행하지 않았다.
