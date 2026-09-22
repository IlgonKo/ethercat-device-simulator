# RF-002-1 — SDO 읽기·쓰기 및 복원 검증

- 단계: 2-1 (2단계에서 분리한 하위 항목)
- 상태: 기본 읽기·쓰기·복원 및 PDO 회귀 완료 (2026-09-14)
- 선행 항목: [RF-002](RF-002-windows-pdo-diagnostic.md)
- 미해결 오류 응답: [TD-001](../TD/TD-001-sdo-abort-response.md) — 보류, 미구현
- 완료 범위: 정상 SDO 경로. Abort 오류 경로는 완료에 포함하지 않는다.

2026-09-14. Windows PySOEM과 Linux KickCAT 사이 물리 케이블로 기본 SDO 읽기·쓰기·복원 검증 완료. 오류 응답 호환성은 별도 미해결 항목이다.

## 실행

Windows 저장소 루트에서:

```powershell
python scripts/windows/diagnose-kickcat.py --with-sdo
```

기존 2단계 자동 시작·종료를 재사용한다. Slave identity와 PRE-OP 상태를 확인한 후 SDO를 검사하고, 성공한 경우 PDO 매핑·OP 전환·1,000회 교환을 수행한다. 옵션 없는 실행은 기존 PDO 전용 검증이다.

## 검사 항목과 실제 결과

| 항목 | 결과 |
| --- | --- |
| Device Type `0x1000:0` | `00000000`, 4바이트 |
| `0x1C00:0..4` 개별 읽기 | 각각 `04`, `01`, `02`, `03`, `04` |
| `0x1C00:0` Complete Access | 실제 수신 `04 00 01 02 03 04`, 6바이트 |
| RxPDO assignment `0x1C12:0/1` | count=1, PDO=0x1600 |
| TxPDO assignment `0x1C13:0/1` | count=1, PDO=0x1A00 |
| `0x1C12:0` 쓰기·읽기 | `01 → 00`, 읽어서 `00` 확인 |
| 원래 값 복원 | `00 → 01`, 읽어서 `01` 확인. `0x1C12:1`은 0x1600 유지 |
| 복원 후 PDO 회귀 | OP, 입력 12·출력 3바이트, 1,000/1,000회 WKC=3 |
| 정리 | Master INIT, Simulator 종료 코드 0, 정리 오류 없음 |

성공 run ID: `f47f00895ecf4affb35435b2313d0860`.
결과는 `build/diagnostics/<run-id>/result.json`의 `stages.sdo`에 저장한다.
Complete Access 검사에서는 예약 byte 1의 값 자체를 조건으로 삼지 않고 count, 길이, SM 값의 위치를 검사한다.

기본 Board의 LED 객체는 쓰기 전용이므로 원래 값을 읽어 복원하는 용도에 맞지 않는다. PRE-OP 쓰기가 허용된 assignment count를 잠시 변경하고 원복한다. 이것은 CMMT 파라미터 쓰기나 영구 저장, OP 중 SDO 시험이 아니다.

변경 쓰기가 예외를 발생시켜도 실제 Slave에는 적용됐을 수 있으므로 `finally`에서 복원을 시도한다. 복원 확인이 실패하면 PDO 검증에 진입하지 않는다. 성공 로그만으로 오류 응답 검증까지 완료됐다고 해석하지 않는다.

## 별도 실패: SDO Abort 응답

추가 오류 검증 명령:

```powershell
python scripts/windows/diagnose-kickcat.py --with-sdo --sdo-errors
```

읽기 전용 `0x1000:0`에 쓰기를 요청하면 예상 `SdoError / 0x06010002` 대신 `PacketError(1, 1)`이 발생한다. 현재 이 명령은 실패로 종료한다. PacketError를 정상 Abort로 인정하거나 성공으로 처리하지 않는다.

재현 run ID: `1bc8c0ffd3f74d13a789fbb764b13423`. 정상 SDO 검사는 통과했고 `stages.sdo_errors`에서 실패했다. 정리는 정상 수행됐다.
이 시험에서 뒤따르는 없는 객체 `0x5FFF` 읽기/Abort 검사는 앞선 실패로 아직 실행되지 않았다. 오류 응답 원인 수정과 전체 Abort 검증은 후속 작업이다. upstream 소스는 이번에도 변경하지 않았다.

## 복원 실패 경로 단위 검증

```powershell
python -m unittest discover -s tests -v
```

3개 통과: 쓰기는 적용됐지만 응답이 유실된 경우 복원 후 실패 유지, 복원이 거부된 경우 실패 유지, 예상과 다른 원래 값인 경우 쓰기 금지. 이 테스트는 실제 물리 통신 결과를 대체하지 않는다.
