# RF-014 저장 실패·복원 경계 검증

- 상태: 오프라인 검증 완료
- 날짜: 2026-11-04
- 제품 저장/오류 처리 로직 변경 없음. 시험 코드와 빌드 검증 대상 추가.

## 저장 경계

`test_mapping_store_failures` 전용 실행 파일에서 write/fsync/rename을 linker wrap하여 오류를 주입한다. 운영 실행 파일에는 이 주입 기능이 없다. 각 시험은 임시 저장소에서 기존 매핑을 저장한 다음 다른 길이의 매핑 저장을 시도한다.

| 조건 | 확인한 결과 |
| --- | --- |
| write ENOSPC | 예외, 이전 파일 바이트 보존, 이전 매핑 복원 |
| 파일 fsync EIO | 예외, 이전 파일 보존·복원 |
| rename EIO | 예외, 이전 파일 보존·복원 |
| rename 후 디렉터리 fsync EIO | 저장 성공으로 처리하지 않음, 활성 매핑 유지, 현재 파일시스템에서 새 매핑 복원 |
| 파일 fsync 후/rename 전 프로세스 종료 | 이전 매핑 복원, 남은 임시 파일을 저장본으로 취급하지 않음 |
| 디렉터리 fsync 직후/활성화 전 프로세스 종료 | 새 매핑 복원 |
| save 반환 후 호출자 활성화 단계에서 예외 주입 | 활성 매핑 유지, 재시작 시 새 매핑 복원 |

7/7 통과. 프로세스 종료는 자식 프로세스의 `_exit`로 수행한다. 전원 차단 시험이 아니며 디렉터리 fsync 실패 이후 정전 시 새 파일의 생존을 보장하지 않는다. 마지막 조건은 호출자 경계 모의 예외이며 실제 activate()의 메모리 할당 실패를 재현한 것은 아니다.

스키마 비호환·체크섬 손상·체크섬이 유효하지만 필수 Controlword가 없는 저장 내용도 검사했다. 3/3 통과. 오류 분류, 원본 보존, 부분 후보/활성 매핑 미적용을 확인했다.

## Slave 상태 전환 및 시작 통합 시험

기존 NIC 없는 self-test에서 현재 장치의 임시 파일 경로에 디렉터리를 만들어 실제 파일 open 실패를 유발했다. 새 후보 Rx4바이트, 기존 활성 Rx3바이트를 사용했다.

- SAFE-OP 거부, PRE-OP+AL 오류와 PDO_MAPPING_SAVE_FAILED 진단.
- 후보 readback 유지, 기존 활성 매핑 및 저장 파일 유지, 기능 모델 응답 유지.
- 오류 원인 제거 및 AL 오류 확인 후 SAFE-OP 진입, 새 Rx4 적용, 진단 해제.
- 시험 후 Rx3로 복원. 운영 파일/컨테이너는 사용하지 않는다.
- F-KR 2축 + Copley Linux FMU 2축, 재시작 전후 8/8 통과.

`run_dynamic_mapping.py --storage-startup`은 별도 Model Host 세션마다 실제 Slave 초기화 경로를 실행한다. 스키마/체크섬 오류는 시작 실패 및 원본 보존, 유효 형식의 부적합 매핑은 PDO_MAPPING_RESTORE_INVALID 진단과 미설정 상태 확인 후 PRE-OP 재설정/SAFE-OP 복구를 검사한다. 3/3 통과. Model Host가 한 Slave 연결만 처리하므로 각 시작 시험에 새 Host를 실행한다.

저장 시스템 호출별 예외는 저장 계층 시험에서, 저장 예외에 대한 AL 상태/진단은 실제 open 실패 통합 시험에서 확인했다. 모든 시스템 호출 오류를 물리 버스에서 각각 반복한 것은 아니다.

## 실행과 결과

```bash
cmake -S . -B build/timing
cmake --build build/timing --target cmmt_simulator test_mapping_store_failures -j2
ctest --test-dir build/timing --output-on-failure

docker run --rm --network=none --cap-drop=ALL \
  -v "$PWD:/workspace:ro" -w /workspace \
  --entrypoint python3 ethercat-device-simulator:rf014 \
  tests/integration/run_dynamic_mapping.py --axes 4 \
  --fmu-dir /model_artifacts --storage-startup
```

CTest 6/6 통과. 혼합 4축 재시작·변경 매핑·SDO 유지 기존 검사도 통과. [결과 요약](results.json).

Dockerfile의 명시적 빌드 대상에 새 저장 실패 시험을 추가했다. 기존 이미지를 실행 환경으로 사용하고 최신 소스/호스트 빌드 바이너리를 읽기 전용 마운트하여 검증했다. 운영 이미지 재빌드/전환, 물리 버스 조작, 기존 장치 저장 파일 변경은 하지 않았다.
