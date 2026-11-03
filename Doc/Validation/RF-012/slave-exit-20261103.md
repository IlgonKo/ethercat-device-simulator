# RF-012 — Slave 강제 종료 검증 (2026-11-03)

- 문서 유형: **검증 기록**
- 관련: [RF-012](../../RF/RF-012-docker-deployment.md)
- 판정: 완료 — Slave 장애 감지·서비스 종료·모델 정리 및 컨테이너 재기동·Master 재연결 후 통신 복구 확인.

## 방법 및 결과

사용자 준비 완료 후 실제 축·IO + F-KR 2축/Copley 2축 혼합 버스에서 전 축 속도 0, trajectory/homing idle, Fault 없는 정상 진단, WKC 18/18을 조회했다. Motion Server 주기는 4ms다. 이동·Enable 명령은 보내지 않았다.

실행 중 컨테이너 status.json에서 Slave PID 17을 읽고 /proc 명령행이 cmmt_simulator인지 재확인한 뒤 SIGKILL을 Slave에만 보냈다. 모델 PID 8에는 시험 도구가 직접 신호를 보내지 않았다.

- SIGKILL 로그 시각: Linux epoch 1793675675.6031358.
- supervisor failed 로그: 1793675675.6324196, Slave exited: -9. 이 관측에서 약 29.3ms 후 감지했으며 최악 시간 보장은 아니다.
- 최종 failed 로그: 1793675675.6400073, Slave -9 / 모델 -15. supervisor가 모델을 SIGTERM으로 정리한 것을 확인했다.
- Docker 종료: 2026-11-03T03:14:35.658338199Z, exit code 1, Running=false, PID=0, Health=unhealthy. 자동 재시작 없음.
- 신호 직후 첫 inspect 표본은 이전 healthy였고 다음 표본은 exited/unhealthy였다. 즉시 health 전환 보장으로 해석하지 않는다.
- 서비스 코드에서 model.sock unlink 뒤 최종 failed 로그를 출력한다. 최종 로그와 tmpfs 소멸은 확인했으나 unlink 순간 파일 상태를 독립 관측하지는 않았다. 새 컨테이너에서 소켓 생성·ready 성공으로 stale socket에 의한 재기동 방해가 없음을 확인했다.
- state/*.json의 시험 전후 SHA-256 모두 일치. 파일 권한 변경 없이 별도 network-none 읽기 전용 마운트로 비교했다.
- Motion Server API는 계속 응답했고 bus_disconnected / BUS_CONNECTION_LOST를 보고했다. 종료 후 wkc=0, expected_wkc=12였으며 종료 전 18/18과 구분한다. 종료 후 캐시된 statusword를 최신 장치 상태로 해석하지 않는다.

## 복구

기존 이미지로 scripts/docker/start.sh를 실행하여 컨테이너를 재생성했다. healthy 및 새 모델/Slave ready를 확인했다. 사용자가 Motion Server 재연결·초기화를 완료한 후 읽기 전용으로 확인했다. 서버 initialized=true, runtime_state=normal, initialization_failure=null, 진단 normal 및 4ms 주기였다. 약 3초 동안 bus/status 30회 모두 WKC 18/18이고 불일치 0이었다. 전 축 Fault bit 없음, 실제 속도 0, trajectory/homing idle을 확인했다. 가상축 위치는 모두 0이었다. Simulator는 running/healthy, 모델과 Slave는 ready였다. 이번 확인에서 Enable·이동 명령은 보내지 않았으며 이동 재개 시험까지 완료한 것으로 확대하지 않는다. 상태 조회 표본이며 전체 프레임 무손실 인증은 아니다.

이번 시험은 Slave 프로세스 종료를 다룬다. Slave hang, OS/NIC 장애, 정상 종료 지연의 최악 시간 검증은 아니다. 실행 코드는 변경하지 않았다.

## 원본 증거

Linux ignored build/diagnostics/rf012-slave-exit-20261103/의 before.json, result.json, container.log, master-before.json, master-after.json, restart-status.json, recovery.json 및 check-slave-exit.py. 상태 관측은 표본이며 전체 EtherCAT 프레임 캡처가 아니다.
