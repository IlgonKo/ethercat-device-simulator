# RF-017 — Copley FMU 초기 연동

- 현재 상태: **진행 중**
- 상태 상세: Linux FMU·Docker·저장·혼합 물리 PP·Fault/Reset·장애 격리 확인. 물리 세부 이동/파라미터 효과와 혼합 정량 성능만 잔여 (2026-10-28).

## 현재 구현 및 지원 범위

별도 Functional Model 프로세스에서 FMPy 기반 FMI3 Co-Simulation FMU를 라이브러리로 호출한다. 모델 ID는 `copley_drive_sim`, BUS는 `cia402-drive`다. EtherCAT identity/PDO는 CMMT-AS 호환이며 축마다 독립 FMU 인스턴스를 생성한다.

- PP 절대/상대 이동, Enable/Disable, 피드백, Fault/Reset 및 지원 파라미터 적용.
- referenced bit15는 항상 설정하며 실제 Homing은 제공하지 않음.
- Halt bit8은 FMU 전달 시 마스킹. Stop/Halt 정지 기능과 PV/PT 어댑터 연결은 범위 밖.
- 모델 오류·지연 시 Slave 유지 및 정상 SDO Abort는 RF-018 검증 완료. 초기화 호환 OD는 어댑터가 처리.
- FMU는 2ms 단위로 진행. 8ms 입력은 4회 실행하고 잔여 시간은 누적. 2ms보다 짧은 입력 에지 보존은 보장하지 않음.
- 위치는 OD raw count와 FMU count 대응, 속도/가속도는 단위 지수로 변환. 가속·감속이 같고 속도·가속도가 양수여야 함.
- 저장은 단위 메타데이터 5개 + 0x6081/0x6083/0x6084 총 8개. 위치·속도 피드백·Controlword·Fault는 저장하지 않음.

## 완료 기준 대조

| 항목 | 상태 | 기존 근거와 한계 |
| --- | --- | --- |
| Linux 실제 FMU 로드·입출력·단위·시간 진행 | 완료 | 고정 소스 Linux 빌드 및 실제 FMU 시험 |
| PP 절대/상대·Enable/Disable·Fault/Reset | 오프라인 완료 / 물리 일부 확인 | 오프라인 2000 절대 이동, -750 상대 이동 후 1250 도달. 물리 기본 PP 및 사용자 Fault Reset 복귀 확인. 물리 절대/상대 각각의 목표/최종값 기록은 없음 |
| 파라미터 적용·저장/복원 | 저장/복원 완료 / 물리 동작 효과 미검증 | 오프라인 속도 변화에 따른 도달 시간 차이, RF-010 실제 SDO 저장/복원 완료. 물리 이동 응답 효과의 정량 근거는 없음 |
| 초기화 OD·미지원 Abort·Halt 마스킹 | 완료 | 초기화·후속 SDO/PDO 및 실제 FMU/IPC 회귀 |
| .env·Docker artifact·다축 독립성 | 완료 | 운영 F-KR 2축 + Copley 2축 및 별도 인스턴스 검증 |
| crash/hang/IPC timeout 격리 | 완료 | RF-018 SIGSTOP/SIGKILL·SDO·축 Reset·Docker 수동 복구 |
| 혼합 4축 장시간 이동 성능 | 미검증 | 혼합 운전은 확인됐지만 시간·부하·주기별 지연을 정한 정량 보고 없음 |

## 실제 남은 항목

1. 물리 EtherCAT 경로에서 Copley PP 절대·상대 이동 각각의 목표값/최종 위치 확인 기록.
2. 지원 속도·가감속 파라미터 변경이 물리 연동 이동 응답에 반영되는지 확인. SDO 저장/복원 재시험과 구분한다.
3. 혼합 4축 이동 부하의 시간·주기·지연/WKC 근거 확보. RF-016 계측과 통합 가능하며 시간/합격 조건은 별도 확정한다.

사용자의 지속 혼합 운전 확인은 유효하다. 미연동 상태로 되돌리지 않으며 위 세부 수치를 측정한 것으로 확대하지도 않는다. RF-017은 진행 중으로 유지한다.

## 모델 한계

외부 부하·힘·관성·마찰·중력 모델이 없어 PP 이동에 필요한 토크를 계산하지 않는다. upstream PT는 목표 토크의 단순 1차 지연 추종이며 현재 어댑터에 연결하지 않았다. 소프트웨어 위치 제한·실제 Homing·Stop 구현은 이번 범위에 추가하지 않는다. FMI2, Model Exchange, 이벤트 모드, early return, FMU 상태 저장/복원은 공통 runner의 현재 지원 범위가 아니다.

## 실행·재현 및 근거

운영은 [Docker 스크립트](../../scripts/README.md)를 따른다. `DEVICE_SIMULATOR_FMU_DIR` 기본 `./model_artifacts`의 `CopleyDriveSim-linux.fmu`를 `/model_artifacts`에 읽기 전용 마운트한다. FMU 전용 `/run/fmu` tmpfs에서 라이브러리를 로드한다.

고정 revision/hash, Linux 빌드·오프라인 재현 명령 및 시험 수치는 [이전 기록](../Validation/RF-017/history-through-20261028.md)에 보존했다. 운영 미반영·장애 격리 미구현 문구는 당시 이력이다.

관련: [RF-010](RF-010-parameter-persistence.md), [RF-018](RF-018-diagnostic-fault.md), [DT-008](../Design/DT-008-diagnostic-fault.md). 이번 정리는 새 물리 시험이나 실행 환경 변경을 포함하지 않는다.
