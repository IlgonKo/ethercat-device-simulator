# RF-014 재매핑 중 IPC 지연·장애 검증

- 상태: 오프라인 통합 검증 완료
- 날짜: 2026-11-05

## 구성과 범위

실제 Slave 실행 파일의 응답 처리 pump와 PRE-OP→SAFE-OP 대기 조건을 사용한다. 기존 물리 프레임 루프의 대기 조건을 공통 runRoutine으로 추출하여 시험과 운영 경로가 같은 코드를 실행한다. 제품 정책을 변경하지 않았다.

실제 Python 기능 모델과 Unix 소켓 중계기를 연결했다. 중계기는 응답 지연/식별자 변경을 수행하며, 정지·종료 조건에서는 실제 임시 Model Host에 SIGSTOP/SIGKILL을 보낸다. NIC, 운영 컨테이너, 운영 저장소는 사용하지 않는다. 저장은 임시 디렉터리이며 프로세스별로 격리한다.

F-KR 4축과 Copley 2축+F-KR 2축 각각에서 아래 8조건을 실행했다. 재매핑 대상은 첫 번째 축으로, 두 번째 구성에서는 실제 Copley Linux FMU 축이다. 다른 3개의 ESC도 같은 에뮬레이션 네트워크에서 응답한다.

| 조건 | 주입 | 결과 |
| --- | --- | --- |
| delay | 활성/비활성 응답 각각 25ms 지연, 제한 100ms | 두 응답 처리 후에만 새 매핑 적용 |
| timeout | 이전 활성 응답 200ms 지연 | Host Fault, 새 매핑 차단, 늦은 응답 무시 |
| stop | 활성 요청 시 Model Host 250ms 정지 후 재개 | Host Fault 유지, 자동 복구 없음 |
| terminate | 활성 요청 시 Model Host 강제 종료 | Host Fault, Slave 실행 유지 |
| stale-session | 다른 세션 응답과 식별 가능한 위치값 | 응답 거부, 위치 미반영 |
| stale-request | 이전 요청 번호 응답과 식별 가능한 위치값 | 응답 거부, 위치 미반영 |
| inactive-timeout | 활성 응답 후 비활성 응답 200ms 지연 | 비활성 완료 전 새 매핑 차단 |
| inactive-stop | 비활성 요청 시 Model Host 250ms 정지 | 비활성 완료 전 새 매핑 차단 |

## 확인 내용

- 기존 Tx2바이트와 후보 Tx7바이트를 구분했다. 대기 중에는 PRE-OP, 기존 활성 매핑과 저장 파일을 유지했다.
- 활성 응답 완료를 비활성 완료로 잘못 취급하지 않았다. 정상 지연 조건에서는 비활성 응답까지 처리한 후 SAFE-OP/새 Tx7이 적용됐다.
- 오류 조건에서는 기존 Tx2/저장 파일을 유지하고 Statusword의 Fault를 투영했다. 늦거나 이전 세션/요청의 위치값은 피드백에 반영되지 않았다.
- 각 조건의 350ms 관측 동안 4개 ESC에 BRD AL Status 프레임을 계속 전달했다. 매번 WKC=4를 확인했다. 실제 물리 PDO WKC=18 시험과는 다르다.
- 오류 후 AL 오류 확인과 SAFE-OP 재요청, 출력 버퍼의 Fault Reset 비트로 Host Fault가 해제되지 않았다. PRE-OP에서는 동작 모델에 운전 출력이 전달되지 않는다. 이는 Motion Server/Axis Panel을 통한 전체 Reset 명령 시험을 새로 수행했다는 의미가 아니다. 해당 수동 근거는 RF-018을 따른다.
- NIC-free 시험에서는 후보를 내부 매핑 관리자에 직접 작성하고 이전 활성 exchange를 시험 코드에서 제출한다. SDO 작성 경로는 앞선 RF-014 시험을 따른다. 물리 운전 중 전환 타이밍까지 재현한 시험은 아니다.

## 결과와 재현

16/16 통과. 각 조건에서 324~330개 프레임 처리, WKC 불일치 0. [실행 결과](results.json). CTest 6/6 및 기존 혼합 4축 매핑/저장 복원/시작 오류 통합 시험도 통과했다.

```bash
cmake --build build/timing --target cmmt_simulator -j2
python3 tests/integration/run_remap_ipc.py

docker run --rm --network=none --cap-drop=ALL \
  -v "$PWD:/workspace:ro" -w /workspace \
  --entrypoint python3 ethercat-device-simulator:rf014 \
  tests/integration/run_remap_ipc.py --fmu-dir /model_artifacts
```

기존 이미지에서 최신 소스·호스트 빌드 실행 파일을 읽기 전용 마운트했다. 새 시험은 Dockerfile 빌드 검증에도 추가했으나 이번 작업에서 운영 이미지 재빌드/전환은 하지 않았다. 장시간 안정성 또는 RT 성능 보장 결과가 아니다.
