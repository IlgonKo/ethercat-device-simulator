# RF-014 전체 매핑 적용 거부와 수정 재시도 검증

- 상태: 완료 (격리된 오프라인 통합 시험)
- 날짜: 2026-11-04
- 기준 커밋: 0a24ad3 이후 self-test 확장. 제품 처리 로직 변경 없음.

## 방법

실제 Slave 실행 파일의 `--self-test`를 확장했다. KickCAT mailbox로 개별 SDO를 쓰고 ESC AL Control 레지스터에 SAFE-OP을 요청하여 실제 ESM과 매핑 활성화 hook을 통과시킨다. prepare() 함수만 직접 검사하는 단위 시험이 아니다. Python 기능 모델과 Unix 소켓을 연결하며 저장소는 실행별 임시 폴더다.

정상 Rx3/Tx7 매핑을 먼저 적용한 다음 아래 오류를 각각 만들었다.

| case | 후보 오류 | 결과 |
| --- | --- | --- |
| 0 | Rx Controlword를 같은 길이 padding으로 대체 | PRE-OP + AL error |
| 1 | Tx Statusword를 같은 길이 padding으로 대체 | PRE-OP + AL error |
| 2 | Rx assignment count=0 | PRE-OP + AL error |
| 3 | Tx assignment count=0 | PRE-OP + AL error |

각 조건에서 AL Status=0x12, AL Status Code=INVALID_OUTPUT_MAPPING, PDO_MAPPING_INVALID 진단을 확인했다. 후보 SDO upload는 작성한 값을 유지했고, 활성 Rx/Tx와 모든 축의 저장 JSON 내용은 거부 전과 동일했다. 모델 OD 교환이 계속 응답했다. AL 오류 확인 없이 SAFE-OP을 재요청하면 차단이 유지됐다.

PRE-OP|ERROR_ACK로 오류를 확인하고 후보를 수정한 뒤 SAFE-OP=0x04/AL code=0, assignment readback=1, 진단 resolved를 확인했다. 프로세스 재시작 없이 다음 시험을 이어갔다.

## 결과

- F-KR 4축 × 4조건 × 재시작 전후 2회: 32/32 통과.
- F-KR 2축 + 실제 Linux Copley FMU 2축 × 4조건 × 2회: 32/32 통과.
- 기존 CTest: 5/5 통과.
- 변경 매핑의 정상 IPC 교환과 재시작 저장 복원 기존 검사도 통과.
- [조건별 결과](results.json)

## 재현

저장소 루트에서 테스트 실행 파일을 빌드한 뒤:

```bash
cmake --build build/timing --target cmmt_simulator -j2
python3 tests/integration/run_dynamic_mapping.py --axes 4
```

혼합 모델 시험은 기존 RF-014 이미지에 최신 호스트 소스/시험 바이너리를 읽기 전용 마운트했다. 이미지를 재빌드하거나 운영 컨테이너를 전환하지 않았다.

```bash
docker run --rm --network=none --cap-drop=ALL \
  -v "$PWD:/workspace:ro" -w /workspace \
  --entrypoint python3 ethercat-device-simulator:rf014 \
  tests/integration/run_dynamic_mapping.py --axes 4 --fmu-dir /model_artifacts
ctest --test-dir build/timing --output-on-failure
```

## 범위와 한계

NIC 없는 ESM/mailbox/IPC 통합 시험이다. 물리 프레임 전송, WKC, 운전 중 재매핑·저장 I/O 장애·IPC 지연 주입은 이번 시험 범위가 아니다. 기존 물리 시험 근거와 구분한다. 제품 오류 처리 수정은 필요하지 않았으며 실행 중인 Simulator, 운영 저장 파일, Motion Server 연결에는 영향을 주지 않았다.
