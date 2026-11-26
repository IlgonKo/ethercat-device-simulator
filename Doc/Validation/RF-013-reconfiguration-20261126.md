# RF-013 CPX 재구성·재검색·원복 — 2026-11-26

- 현재 상태: **통과**. 합의한 RF-013 잔여 검증 완료.
- 수행 시각: 2026-11-26 16:53:00~16:53:24 KST. 종료 후 별도로 모든 축 Disable·조작권 해제를 확인했다.
- 대상: 기존 혼합 Slave 8개 중 가상 io1(Master Slave 6). io2(Slave 7) 및 축 구성은 유지했다.

## 절차와 결과

| 단계 | 설정/검증 | 결과 |
| --- | --- | --- |
| 기존 구성 확인 | io1=1:DI:8,2:DO:8,3:AIO:4:4, 입력 9 / 출력 10바이트 | 합격 |
| 구성 변경 | io1 슬롯4 DO8 추가, Simulator 재생성 및 일치하는 Motion Server 설정으로 재기동·재검색 | 합격 |
| 새 배치 | 입력 9 / 출력 11바이트, io2는 입력 9 / 출력 10바이트 유지 | 합격 |
| F030/F050 | count 4→5, ident=[0x2084,0x2007,0x2139,0x2134,0x2139] | 일치 |
| Rx assignment 0x1C12 | [0x1602,0x1603]→[0x1602,0x1603,0x1604] | 일치 |
| Tx assignment 0x1C13 | [0x1A01,0x1A03] 유지 | 일치 |
| 추가 DO mapping | 0x1604의 8개 항목이 0x7040:01~08, 각 1bit | 일치 |
| PDO 출력/OD 대응 | 슬롯4 DO0·DO7 ON, 나머지 OFF; SDO 0x7040:01~08 값 [1,0,0,0,0,0,0,1] | 일치 |
| 변경 구성 통신 | 약 3초 WKC 상태 조회 69회 | 모두 24/24 |
| 원복 | 추가 DO OFF → Master 종료 → 원본 Simulator .env 복원·재생성 → 원래 Master 설정으로 재기동·재검색 | 합격 |
| 원복 배치/OD | 입력 9 / 출력 10바이트, F030/F050 count=4와 원래 idents·assignment | 일치 |
| 최종 상태 | Slave 8개, WKC 24/24, Fault 없음, 모든 축 정지·Disable, 조작권 없음 | 정상 |

Simulator .env는 백업 후 수정하고 원본 바이트로 복원했으며 시험 전후 SHA-256이 같다. Motion Server .env 파일은 수정하지 않았다. 기존 Windows 프로세스의 실행 인자·작업 경로·환경변수를 메모리에 보존하고, 변경 시험에서는 MOTION_SERVER_IO_IO1_MODULES 한 항목만 임시 변경했다. 원복 시 원래 환경으로 다시 시작했다.

Motion Server는 설정 파일보다 프로세스 환경변수를 우선하므로 기존 프로세스를 재시작했다. 시험 종료 후 원래 실행 설정의 서버가 백그라운드에서 실행 중이다. 현재 PID 17268은 시험 기록이며 고정 운영 식별자가 아니다. 표준 출력은 Windows 임시 진단 폴더의 run01/restored-master.stdout.log로 연결되어 있다.

Master 초기화 뒤 Enable 상태가 확인되어 종료 단계에서 실제 축을 포함한 5축에 Disable을 보냈다. 이동 명령은 보내지 않았다. 최종 실축 위치는 약 147.841mm, 가상축 위치는 모두 0이다. 이번 재구성 시험에서는 실축 Fault Reset이 필요하지 않았다.

## 저장·정책 확인

- CPX 전용 파라미터/매핑 JSON은 생성되지 않았다. state에는 기존 축 파라미터 4개와 축 PDO mapping 4개만 존재한다.
- 모듈 구성에서 고정 PDO를 다시 생성했으며 CPX 런타임 SDO 재매핑을 추가하지 않았다. 지원하지 않는 AP 파라미터·27F1 Abort 및 mapping 쓰기 거부는 기존 1~3단계/경계 시험 근거를 사용한다.
- WKC는 상태 조회 표본이며 전수 패킷 캡처나 장시간 RT 성능 시험이 아니다.
- 기존 실린더 binding은 변경하지 않았다. 이번 추가 DO8은 미연결 채널이며 수신 PDO/OD 값만 확인했다.

## 증거 및 완료 판정

Linux build/diagnostics/rf013-reconfigure-20261126/에 simulator.env.before, run01/result.json, 요청·피드백 로그, Master 시작 로그, final-park/result.json 및 재현용 probe.py를 보관했다. build 산출물은 Git 추적 대상이 아니다. 원복과 정지 단계까지 failure/cleanup 오류는 없었다.

RF-013은 합의 범위 완료다. 실린더 수동·혼합 운전, 실제 FMU 자동 시험, Host 장애/복구, CPX 재구성/재검색 근거를 함께 사용한다. 아날로그 수동/물리 AO→FMU→AI 왕복은 사용자 결정으로 생략했으며 미검증 한계를 유지한다. IO-Link·진단 PDO/이력/Emergency·상위 공정 타임아웃·외부 DT 연동은 이번 완료 범위에 포함하지 않는다.
