# 복동 실린더 FMU Windows 오프라인 검증

상태: **완료 — 아래 실행 조건에서 오프라인 동작 확인**

검증일: 2026-11-25 (Asia/Seoul)

## 대상과 결과

공개 MIT 라이브러리 PneumaticCircuits의 복동 실린더·5/2 메모리 밸브·3/2
파일럿 밸브를 조합했다. 전진/후진 Boolean 입력과 끝단 센서 2개, 위치·속도·압력·
공압력을 노출한다. 물리 EtherCAT, CPX-AP-I, DT, Linux 컨테이너는 이번 시험에 포함하지 않았다.

| 시험 | 조건 | 결과 |
|---|---|---|
| 기본 왕복 | 스트로크 100 mm, 공급 6 bar(gauge), 전진·후진 각 2회 | 통과 |
| 계산 간격 비교 | FMU 호출 0.1 ms와 0.05 ms 비교 | 최대 위치 차이 0.0683 mm |
| 파라미터 반영 | 초기화 시 스트로크 50 mm로 변경, 2회 왕복 | 통과 |
| 공급 공기 없음 | 공급 0 Pa(gauge), 동일 입력 | 위치 0 유지, 전진 센서 OFF |

초기 후진 센서 ON, 이동 중 두 끝단 센서 OFF, 전진/후진 도달 시 해당 센서 ON을
확인했다. 두 센서가 동시에 ON인 표본은 없었다. 입력 펄스가 끝나도 밸브 방향을
유지하는 동작을 확인했다. 이는 정지 기능이 아니다.

각 시험은 시뮬레이션 시간 4 s이며 `instantiate → initialize → doStep → terminate
→ freeInstance`를 모두 수행했다. `summary.json`의 네 시험 모두 성공했다.

## 실행 환경과 수치

- Windows 11 x64 (10.0.26100), Python 3.14.3, FMPy 0.3.26.
- 공식 OpenModelica 1.27.1 Windows x64 배포본, FMI 2.0 Co-Simulation, CVODE.
- 배포본 SHA256: `b7479c752e11648e7859341f986aa981a400ef3071e8e718101a8375037eaa8d`.
- 원본 소스 커밋: `9aaa71e837333ab4964ebd40426b1f89a3c099e0`.
- FMU SHA256: `17e86295eb735f2fb5f20f18a51d507dbe81f6e58f43d412f08e27f3553889c4`.

최종 시험기의 제어/관측 간격은 8 ms, FMU `doStep()` 간격은 0.1 ms이다.
한 제어 구간에서 같은 입력을 유지한 채 80회 계산한 후 결과를 읽는다. CVODE가
선택하는 내부 적분 간격과 구분한다. 기준 계산은 `doStep()` 0.05 ms를 사용했다.

100 mm 시험에서 한 8 ms 구간을 계산하는 데 평균 0.320 ms, p95 0.545 ms,
최대 1.974 ms가 소요됐다. 이는 Python 호출 루프와 FMU 계산을 포함한 한 번의
오프라인 관측값이며 실시간 스케줄링·EtherCAT 지연·다중 장치 성능 검증은 아니다.
위치 범위 등의 통계는 각 제어 구간 종료 시 읽은 표본 기준이다.

## 발견된 제약과 처리

1. **큰 FMU 호출 간격에서 접촉 이벤트 지연.** 직접 `doStep(8 ms)`를 호출한
   최초 시험은 0.52 s에서 위치 106.965 mm를 관측한 후 FMI Fatal로 실패했다.
   런타임 소스에서 상태 이벤트를 통신 구간 종료 후 확인하는 경로를 확인했다.
   1 ms는 100 mm 왕복을 통과했으나 50 mm에서 후진 끝단 침투가 약 3.75 mm로
   나타났다. 시험기 호출 간격을 0.1 ms로 줄여 검증했다. 원본 물성값, 접촉식,
   OpenModelica 적분 코드는 수정하지 않았다. 다른 파라미터 조합에는 추가 검증이 필요하다.
2. **Windows 메모리 할당자 불일치.** FMPy 기본 MSVCRT 콜백으로 초기화·계산 후
   `freeInstance()`를 호출하면 `0xc0000374` 오류가 재현됐다. 생성 FMU의
   `fmu_read_flags.c`가 콜백으로 할당한 CVODE 구조체를 `cvode_solver_deinitial()`이
   직접 `free()`하는 경로가 있다. 시험기의 콜백을 Windows UCRT로 지정하자
   정상 해제됐다. 다른 실행기로 배포할 때 확인해야 할 호환성 항목이다.
3. **제조사 정밀 모델 아님.** 교육용 공개 모델의 마찰·유량·이동 질량 등에는
   추정값이 있다. 실제 Festo 실린더의 정량 정확도를 입증한 시험이 아니다.
4. **웹 실행 형식 차이.** Playground FMI 페이지는 FMI 3.0 + wasm32-wasip2를
   요구한다. 이 FMU는 Windows x64/FMI 2.0이다. 웹용 단일 `.mo` 소스는 구조 검사와
   Playground Simulator의 0~4 s 실행을 통과했다. 이후 사용자가 Export한 FMI 3.0
   산출물의 Linux 실행도 [별도 보고서](Pneumatic-Cylinder-Web-FMU-20261125.md)에서
   검증했다. 그 산출물의 WebAssembly FMU 실행은 미검증이다.

## Playground 소스 실행 확인

2026-11-25 웹 편집기에 단일 소스 전체를 넣고 Run을 실행했다. 결과 제목은
`SoftESCPneumaticDemo`, 시간 범위는 `[0, 4]`, 결과 지점 수는 4,060이었다.
이 확인은 웹 Simulator의 Modelica 소스 실행이며 Windows FMU를 웹에서 실행한 것이 아니다.

- 입력 파일: `build/pneumatic-fmu-windows/web/SoftESCPneumaticDemo.mo`.
- 검증 파일 길이: 17,870자. 브라우저 입력과 로컬 파일의 FNV-1a는 `defbd9cd`로 일치.
- 필요한 부품만 남기고 그림·HTML 설명 annotation을 제외했으며 문자열 줄바꿈을
  이스케이프했다. 부품 계산식과 기존 Windows FMU는 변경하지 않았다.
- 사용자가 보고한 96행의 `unterminated string literal`은 수정본에서 발생하지 않았다.
  기존 설명문을 단독 시험했을 때도 오류가 재현되지 않아 최초 오류의 원인은 확정하지 않았다.

## 파일과 재실행

저장소: `C:\Users\Festo\Documents\ethercat-device-simulator`

- Windows FMU: `model_artifacts/SoftESCDoubleActingCylinder-win64.fmu`
- 출처/해시: 같은 위치의 `.provenance.json`
- Modelica 원본: `model_sources/pneumatic_cylinder/`
- 웹용 단일 소스: `build/pneumatic-fmu-windows/web/SoftESCPneumaticDemo.mo`
- 결과 JSON/CSV/그래프: `build/pneumatic-fmu-windows/results/`
- 수치 사본: [Pneumatic-Cylinder-Windows-20261125.json](Pneumatic-Cylinder-Windows-20261125.json)

```powershell
Set-Location C:\Users\Festo\Documents\ethercat-device-simulator
python scripts/windows/test-pneumatic-fmu.py
```

재빌드·Playground 사용 방법은 [모델 README](../../model_sources/pneumatic_cylinder/double_acting/README.md)에 기록했다.
기존 Windows 체크아웃의 미커밋 문서 변경과 Linux 실행 환경은 수정하지 않았다.

## 근거

- [사용한 공개 모델](https://github.com/Samarth030312/pneumatic-circuits-openmodelica/tree/9aaa71e837333ab4964ebd40426b1f89a3c099e0)
- [OpenModelica 1.27.1 FMU export와 CVODE](https://openmodelica.org/doc/OpenModelicaUsersGuide/v1.27.1/fmitlm.html)
- [Playground 브라우저 실행 설명](https://openmodelica.org/doc/OpenModelicaUsersGuide/1.28/webbrowser.html)
- [Playground FMI 화면](https://playground.openmodelica.org/latest/#fmi)
