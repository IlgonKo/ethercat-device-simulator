# RF-013 혼합 Host 장애·복구 시험 — 2026-11-26

- 현재 상태: **Host 장애 격리·재시작 복구 항목 통과**. RF-013 전체는 진행 중이다.
- 기준: [RF-013](../RF/RF-013-virtual-io.md), [정상 혼합 운전](RF-013-mixed-operation-20261126.md).
- 대상: 기존 실제 CMMT/CPX + 가상 F-KR 2축·Copley 2축·CPX 2 station, Slave 8개·기대 WKC 24. Motion Server 설정 주기 4ms.
- 모델 프로세스 전체를 SIGSTOP/SIGKILL했다. 특정 FMU 계산 함수의 내부 오류 주입과 구분한다. 실제 축에 이동/Enable 명령은 보내지 않았다.

## 수행 및 결과

각 시험 전에 모든 축의 정지를 확인하고 가상축을 Disable했다. 두 실린더를 전진 끝단으로 보내 초기화 상태와 다른 DI를 확보했다. 한 클라이언트가 조작권을 소유하고 정상/장애/복구 상태를 수집했다.

| 항목 | SIGSTOP 응답 지연 | SIGKILL 강제 종료 |
| --- | --- | --- |
| 장애 구간 | 약 5초 | 약 5초 |
| 버스 상태 표본 | 97개 모두 WKC 24/24 | 97개 모두 WKC 24/24 |
| 전체 가상축 Host Fault 최초 관측 | 신호 전송 후 약 116ms | 약 11ms |
| EtherCAT Slave | 동일 PID 유지, 종료 없음 | 동일 PID 유지, 종료 없음 |
| DI/AI | 마지막 전진 센서 값·AI 값 유지 | 동일 |
| 장애 후 DO 방향 전환 | RxPDO 값은 변경, DI는 유지 | 동일 |
| CPX 기본 진단 SDO | 두 station의 0x1001 및 0x6102:0~4 읽기 가능, 정상 구간과 동일 | 동일 |
| 축 Fault 상태 SDO | Axis 3의 0x6041에서 Fault 확인 | 동일 |
| 축 Fault Reset | API 처리 응답 후에도 4개 가상축 Host Fault 유지 | 동일 |
| 복구 | Docker 재시작 + 버스 재연결 + 실축 통신 Fault Reset | 동일 |

SIGSTOP 후 SIGCONT로 Host를 재개해도 가상축 Fault와 기존 IO 값이 유지됐다. 늦은 계산 결과는 반영되지 않았다. 재개한 Python Host는 긴 PDO 간격 오류와 닫힌 IPC 소켓의 BrokenPipe로 종료했지만 EtherCAT Slave는 계속 생존했다. 이를 Host 자동 복구로 해석하지 않으며 수동 재시작 정책을 유지한다.

SIGKILL에서는 supervisor의 model exit_code=-9 및 model-failed 상태를 확인했다. 이 상태에서 Slave는 유지되고 SDO/PDO 응답을 계속 제공했다. 모델 오류를 CPX 진단으로 전달하지 않는 기존 경계도 유지했다.

## 복구 결과

- 두 경우 모두 Docker restart 후 Motion Server의 system/bus/reconnect로 초기화했다.
- 가상축 4개는 Fault 없이 초기 위치 0, Disable 상태로 복구했다. 이전 위치·Enable·원점 참조 상태를 운전 재개 상태로 자동 복원하지 않는다.
- 실린더는 지정한 초기 위치 0의 센서 조합으로 복구했다: io1 DI[0:2]=[False,True], io2 DI[0:2]=[True,False]. DO는 OFF, AI/AO는 0이다.
- 최종 재검증에서 실린더 2개 전진/후진 왕복 성공, 버스 24/24·Fault 없음 확인 후 DO OFF로 복원했다. 조작권 해제 완료.
- 최종 실제 축 위치는 약 147.841mm로 유지됐다. 재연결 후 실제 축의 0x603F=0x8188을 관측했다. 로컬 CMMT ESI의 설명은 Monitoring - Communication이다. 실제 축 Fault Reset으로 해제했고 이동/Enable은 하지 않았다.
- 따라서 혼합 실제 버스에서 Docker 재시작은 실제 드라이브의 통신 감시 Fault를 만들 수 있으며, 전체 복구 절차에는 버스 재연결 뒤 실축 Fault 확인/Reset도 포함한다. Host만 멈춘 5초 관측 구간에는 실제 축 Fault가 없었다.

## 저장·매핑 복원

축 파라미터 파일 4개의 SHA-256은 시험 전후 동일했다. 최종 실제 SDO 0x6081 읽기는 논리 Axis 1~4에서 각각 raw 300/100/100/100으로 저장값과 일치했다.

첫 시험 전 Axis 1의 실행 중 profile velocity는 API 표시값 200이었으며 재시작 후 저장값 300으로 돌아왔다. 저장되지 않은 실행 중 변경을 영구 값으로 복원하지 않는 정상 동작이다. 두 번째 시험에서는 profile 배열이 전후 동일했다.

Motion Server는 재연결 초기화에서 PDO 매핑을 다시 설정한다. 네 축 mapping 파일은 revision 17→18→19, 이에 따른 checksum만 바뀌었다. 현재 JSON의 revision을 이전 값으로 되돌리고 동일 CRC32/checksum·직렬화 규칙으로 계산한 SHA-256이 시험 전 파일 해시와 정확히 일치함을 확인했다. identity/schema/rx/tx 내용은 변경되지 않았다. 원본 파일은 수정하지 않고 메모리에서 검증했다.

## 시험 도구 판정 보정과 한계

첫 자동 실행은 '재연결 직후 실축을 포함해 Fault가 전혀 없어야 한다'는 검사에서 중단됐다. 이후 실축 코드 확인·Reset으로 정상 복구를 확인했다. 두 번째 실행은 'mapping 파일 바이트도 동일해야 한다'는 과도한 검사에서 중단됐다. mapping 재설정에 따른 revision/checksum 갱신을 분리 검증하여 내용 보존을 확인했다. 원시 실패 결과를 삭제/성공으로 덮어쓰지 않았고 후속 검증 기록으로 최종 판정을 남겼다.

97+97회 WKC는 API 상태 표본이며 모든 프레임의 무손실 증명이 아니다. 지연 관측 116ms/11ms는 클라이언트 표본 시점이며 내부 검출 지연의 정밀 계측값이 아니다. DI는 초기값과 다른 전진 센서 값을 사용했으며 AI는 기존 0 값을 유지했다. 비영점 AI 장애 유지의 물리 검증으로 확대하지 않는다. 아날로그 물리 FMU 왕복 생략 결정은 유지한다.

## 증거 및 남은 항목

Linux build/diagnostics/rf013-host-20261126/에 run01/result.json, kill-run/result.json, real-axis-recovery.json, stores-after.json, persistence-verification.json, final-verification/result.json, 요청/피드백 원시 로그 및 docker.log를 보관했다. build 산출물은 Git 추적 대상이 아니다.

Host 장애·재시작 복구·저장/현재 매핑 초기화 회귀 근거를 확보했다. RF-013에 남은 것은 지원 CPX 모듈 구성 변경 → 고정 PDO 재생성 → Master 설정 일치·재검색 → 원래 구성 복원이다.
