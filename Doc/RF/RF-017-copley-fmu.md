# RF-017 — Copley FMU 초기 연동

- 현재 상태: **완료**
- 상태 상세: 초기 연동 범위 완료 — 세부 물리 이동·파라미터 효과와 혼합 4축 4ms 설정/10분 반복 운전 확인. 엄격한 주기 보장은 제외 (2026-11-03).

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
| 혼합 4축 반복 운전·처리 시간 | 완료(관측 조건 한정) | 4ms 설정/600.912초/271왕복, 상태 표본 WKC 정상·Fault 없음. rx_gap 최대 21.998ms이므로 주기 준수 보장은 아님 |

## 실제 남은 항목

현재 초기 연동 범위의 미완료 항목은 없다. [혼합 4축 계측](../Validation/RF-017/mixed-endurance-20261103.md)으로 10분 조건의 반복 운전·처리 시간을 확인했다. 모든 4ms 주기 준수나 최대 부하 성능을 합격 처리한 것은 아니다. 현 구조 2축/4축 비교와 수신 간격 지터 원인 분리는 RF-016에 남긴다.

## 2026-11-03 물리 세부 검증 완료

[시험 기록](../Validation/RF-017/physical-motion-20261103.md): Master Axis 3(Copley) 절대 10mm·상대 -4mm→6mm 도달, 속도 10/20 및 동일 가감속 20/100 변경에 따른 응답 차이 확인. 복귀 포함 9회 이동, 486개 표본 WKC 정상·다른 가상축 위치 유지. 위치 0·설정 100/500/500 복원 후 Disable·조작권 반환.

이는 위 표의 물리 세부값/동작 효과 미검증 상태를 대체한다. 상대 이동은 서버가 절대 목표로 변환하는 move_rel API 경로이며 FMU relative bit 자체 물리 시험은 아니다. 최초 Enable 단독 전이는 실패했고 기존 Fault Reset→Enable로 진행했다. 이후 혼합 4축 10분 계측까지 수행했으며 결과와 한계는 위 보고서를 따른다.

## 모델 한계

외부 부하·힘·관성·마찰·중력 모델이 없어 PP 이동에 필요한 토크를 계산하지 않는다. upstream PT는 목표 토크의 단순 1차 지연 추종이며 현재 어댑터에 연결하지 않았다. 소프트웨어 위치 제한·실제 Homing·Stop 구현은 이번 범위에 추가하지 않는다. FMI2, Model Exchange, 이벤트 모드, early return, FMU 상태 저장/복원은 공통 runner의 현재 지원 범위가 아니다.

## 실행·재현 및 근거

운영은 [Docker 스크립트](../../scripts/README.md)를 따른다. `DEVICE_SIMULATOR_FMU_DIR` 기본 `./model_artifacts`의 `CopleyDriveSim-linux.fmu`를 `/model_artifacts`에 읽기 전용 마운트한다. FMU 전용 `/run/fmu` tmpfs에서 라이브러리를 로드한다.

고정 revision/hash, Linux 빌드·오프라인 재현 명령 및 시험 수치는 [이전 기록](../Validation/RF-017/history-through-20261028.md)에 보존했다. 운영 미반영·장애 격리 미구현 문구는 당시 이력이다.

관련: [RF-010](RF-010-parameter-persistence.md), [RF-018](RF-018-diagnostic-fault.md), [DT-008](../Design/DT-008-diagnostic-fault.md). 이번 정리는 새 물리 시험이나 실행 환경 변경을 포함하지 않는다.
