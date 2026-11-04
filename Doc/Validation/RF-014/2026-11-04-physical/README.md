# RF-014 변경 매핑 물리 시험 — 2026-11-04

- 상태: 4번 변경 매핑 시험 통과. 장시간 안정성 및 장애 주입 전체 완료를 의미하지 않음.
- 사용자 확인: 새 이미지 적용·Motion Server 초기화·Axis Panel 수동 운전(1~3번) 완료.
- 사전 조건: 사용자가 Motion Server 버스 연결 해제 확인. 별도 Windows PySOEM 1.1.13 Master로 실행.
- 배치: 실제 CMMT(0), 실제 CPX IO(1), F-KR 가상축(2,3), Copley 가상축(4,5).
- 이미지: ethercat-device-simulator 실행 이미지 b2f60c9ebafa80c0ff523034817fbde70d46f9f6d9243652247329e97a56e5ff.
- PP 이동 명령은 가상축에만 전달. 실제 축·IO의 주기 출력은 0으로 유지.

## 변경 구성 및 결과

| 항목 | 시험 구성/결과 |
| --- | --- |
| RxPDO | Padding 8bit → Controlword 16bit, 총 3바이트 |
| TxPDO | Actual Position 32bit → Statusword 16bit → Mode Display 8bit → Actual Velocity 32bit → Padding 8bit, 총 12바이트 |
| 선택 Rx 제외 | Mode·Target Position·Profile Velocity를 PDO에서 제외하고 SDO로 설정 |
| 모드/속도 | PP=1, Profile Velocity raw 100, PDO 운전 후에도 SDO 값 유지 |
| F-KR 기준 설정 | Homing mode 6을 SDO로 설정하고 참조 완료 후 PP mode 1 복귀 |
| 이동 | F-KR 두 축 목표 raw 1000, Copley 두 축 목표 raw 2000에 도달 |
| 주기 교환 | 목표 주기 8ms, OP 이후 427회 WKC 모두 18/18, 불일치 0 |
| 피드백 | 변경한 Tx 위치·SW·Mode·Velocity 해석 및 padding=0 확인 |
| 컨테이너 재생성 | 기존 start.sh로 force-recreate. 4축의 변경 매핑 readback 일치 |
| 복원 후 통신 | 매핑 재설정 없이 config_map/SAFE-OP/OP 성공. 125회 WKC 모두 18/18 |
| 기본 구성 복원 | 기존 Motion Server 매핑 Rx24/Tx14로 4축 재설정·SAFE-OP 적용·저장 후 PRE-OP 복귀 |
| 최종 상태 | 6개 Slave 모두 PRE-OP, AL error 0. 가상축 Controlword=0. Docker healthy |

## 오류 거부

각 가상축에 다음을 실행했으며 총 20건이 정상 pysoem.SdoError로 반환됐다. PacketError로 우회하지 않았다.

- Complete Access 읽기/쓰기: 0x06010000.
- OD 비트 길이 불일치: 0x06040041. 거부 전후 후보 값 동일.
- 동일 OD 중복 매핑 count 확정: 0x06040041.
- SAFE-OP에서 매핑 쓰기: 0x08000022.

거부 이후 유효 구성·OP·PP 운전이 가능했으며 Slave 종료가 없었다.

## 시험 보정 및 복구

첫 시도에서 F-KR은 참조가 설정되지 않아 SDO 목표를 유지하지 않았다. 현재 목표 readback만으로 성공 판정하면 이동하지 않은 것을 놓칠 수 있어, 시험을 수정했다. 가상 F-KR의 Homing 완료 후 새 의도 목표를 별도 기록하고 이동 전후 OD 값 및 실제 위치를 모두 비교한 재시험 결과를 exercise.json에 기록했다. 제품 코드는 수정하지 않았다.

컨테이너 재생성으로 가상 위치/운전 상태는 초기화됐다. 기본 매핑 복원 시 Mode·Profile Velocity는 시험 전 값으로 되돌리고, 목표 위치는 현재 위치로 설정했다. 파라미터 저장 명령은 보내지 않았다. 마지막 조회에서 4축 기본 매핑이 before.json과 일치하고 Controlword=0임을 확인했다. 사용자는 Motion Server에서 버스를 다시 연결·초기화할 수 있다.

## 근거 및 범위

before.json은 시험 전 매핑/값, exercise.json은 변경 매핑·PP/Abort/WKC, verify_restore.json은 재생성 후 복원/OP/WKC, restore_default.json은 기본 매핑 복원 결과다. test_rf014_physical.py는 이번 6-Slave 구성 전용 실행 기록으로 범용 자동 시험 도구가 아니다.

WKC 관측은 짧은 기능 시험이며 장시간 안정성/RT 성능 보장이 아니다. 파일 저장 실패·전원 차단·재매핑 경계 Host 장애 주입 및 2축/4축 성능 비교는 이 시험 범위에 포함하지 않았다.
