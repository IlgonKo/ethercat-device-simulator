# RF-014 PP 재개 및 축별 매핑 독립성

- 날짜: 2026-11-05
- 범위: 격리된 오프라인 ESM/mailbox/기능 모델 IPC 통합 시험

## 시험

F-KR 2축 + 실제 Copley Linux FMU 2축에서 각 축을 순차 시험하고 전체 프로세스를 재시작하여 반복한다. 실제 KickCAT AL 상태를 OP→PRE-OP→SAFE-OP→OP으로 전환하며 매핑은 mailbox 개별 SDO로 작성한다. 동작 계산은 Unix 소켓의 OD exchange로 구동한다. 실제 NIC 프레임 기반 이동 시험은 아니다.

1. F-KR은 Homing 참조를 완료한다. PP 목표 +10000, 속도 raw 1로 실제 위치가 증가하고 아직 목표에 도달하지 않은 것을 확인한다.
2. 이동 중 SDO로 목표를 -10000으로 변경한다. 새 시작 없이 진행 중 이동이 양의 방향으로 계속되고 OD 목표는 -10000을 유지하는지 확인한다.
3. PRE-OP에서 비활성 처리를 완료하고 Tx 매핑을 수정한다. 먼저 필수 Statusword 누락으로 SAFE-OP 거부를 확인한 다음 올바른 매핑으로 수정한다.
4. 재활성화 동안 시작 비트가 1인 0x16/0x17/0x3F를 전송하고 20회 유지한다. 위치 변화가 없어야 한다.
5. 0x0F로 시작 비트 0을 확인한 뒤 0x3F를 전송한다. 새 목표 방향으로 위치가 감소해야 한다.
6. 각 축의 변경·실패·이동 전후 다른 축의 목표 위치, Profile Velocity, 실제 위치, Statusword, AL 상태, 활성 매핑, 저장 파일을 비교한다.

Tx 매핑은 축별 padding 1/2/3/4바이트 + Statusword 2바이트 + Actual Position 4바이트로 구성하여 전체 길이 7/8/9/10바이트를 동시에 유지한다. 재시작 시 각 축에 맞는 서로 다른 매핑이 실제 활성 구성으로 복원됐는지, 저장 파일의 각 항목 값도 확인한다. 파라미터 파일은 매핑 시험 전후 바이트가 동일한지 검사한다.

## 발견 및 수정

F-KR 어댑터는 비활성화 시 목표 OD를 보존했지만 내부 CiA402 상태 머신은 Operation Enabled로 남아 있었다. 다음 Enable 절차의 6 명령이 뒤늦게 Disable 전환을 일으켜 stop_at_current_position()이 목표 OD를 현재 위치로 덮어썼다. 그 결과 새 시작 요청에도 원래 저장한 목표로 이동하지 않았다.

FKrCmmtAdapter.deactivate()에서 Controlword=0의 내부 상태 전환을 완료한 뒤 보존한 목표를 복원하도록 수정했다. 비활성화와 다음 Enable을 하나의 시나리오로 검증하는 회귀 테스트를 추가했다. Copley 어댑터는 변경하지 않았다.

## 재현

```bash
cmake --build build/timing --target cmmt_simulator -j2
docker run --rm --network=none --cap-drop=ALL \
  -v "$PWD:/workspace:ro" -w /workspace \
  --entrypoint python3 ethercat-device-simulator:rf014 \
  tests/integration/run_dynamic_mapping.py --axes 4 \
  --fmu-dir /model_artifacts --motion
```

최종 결과와 이미지 식별자는 아래 빌드 검증 기록을 따른다. 운영 컨테이너/버스/저장 파일은 이 시험에서 변경하지 않는다. 새 수정 이미지의 Motion Server·Axis Panel 수동 회귀는 별도 적용 확인이다.

## 최종 Docker 빌드 검증 결과

- PP 재매핑·독립성 4축 × 재시작 전후 = 8/8 통과. 축별 Tx7/8/9/10 복원 확인.
- CTest 6/6, Python 57개 중 56 통과·1 플랫폼 skip, 실제 Copley FMU 8/8.
- 전체 매핑 오류/저장 경계/시작 오류와 IPC 장애 8조건 회귀도 빌드 내 통과.
- 이미지: `ethercat-device-simulator:rf014-verified`
- 이미지 ID: `sha256:e98e42e25076a556dedcf282298565fe2bb27383560e2a6c28e36431138177b6`
- [기계 판독 결과](results.json)

운영 이미지 태그와 컨테이너는 그대로다. RF-014 기능 검증은 완료했으며, 새 F-KR 수정 이미지 적용 후 기존 Motion Server 연결/PP 운전/비활성화 후 재개 수동 회귀를 최종 적용 확인으로 남긴다.

## 최종 운영 적용 확인 (2026-11-05)

사용자가 새 이미지 적용과 안내한 수동 테스트를 완료하고 정상 동작을 확인했다. 앞선 “적용 확인 대기” 기록은 이 결과로 해소됐다. Motion Server/Axis Panel 사용자 회귀 확인을 반영하여 RF-014를 완료 처리한다. 추가 운전 시간/WKC 수치를 계측한 것으로 기록하지 않는다.
