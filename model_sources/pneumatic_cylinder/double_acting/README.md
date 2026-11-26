# 복동 실린더 FMU — 소스·Export·오프라인 시험

상태: **Linux FMI 3.0 FMU 재사용 채택·오프라인 검증 완료**(2026-11-25).
Windows FMI 2.0 시험도 완료했다. Soft ESC의 Remote I/O 실행부에는 아직 연결하지 않았다.

`SoftESCDoubleActingCylinder.mo`는 공개 Modelica 라이브러리의 부품을 조합한
복동 실린더 동작 모델이다. Windows에서 FMI 2.0 Co-Simulation FMU로 만들고
FMPy로 직접 실행한다. 모델 내부 적분은 CVODE가 담당한다.

현재 IO 연결 대상으로 선택한 산출물은 Playground에서 Export한 FMI 3.0
`SoftESCDoubleActingCylinder-fmi3-web.fmu`이다. 아래 Windows 빌드와는 별개이며,
Linux에서 8ms 직접 호출을 포함한 5개 시험을 통과했다. 원본 모델의 OFF/OFF 방향
유지를 사용하며, 이전 단순 실린더의 OFF/OFF 정지·일정 이동 시간 계약을 적용하지 않는다.

## 구성과 신호

```text
extend_command  → 3/2 파일럿 밸브 → 파일럿 14 ┐
                                             ├→ 5/2 메모리 밸브 → 복동 실린더
retract_command → 3/2 파일럿 밸브 → 파일럿 12 ┘                    │
                                                    위치·속도·압력·끝단 센서
```

Boolean 입력은 공개 모델의 파일럿 밸브를 구동한다. 전기 코일의 전류나
전자기력까지 모델링한 솔레노이드 밸브는 아니다.

| 구분 | 이름 | 의미 / 단위 |
|---|---|---|
| 입력 | `extend_command` | 전진 파일럿 구동 Boolean |
| 입력 | `retract_command` | 후진 파일럿 구동 Boolean |
| 출력 | `position`, `velocity` | 위치 m, 속도 m/s |
| 출력 | `pressure_cap`, `pressure_rod` | 양쪽 챔버 **절대압** Pa |
| 출력 | `pneumatic_force` | 마찰·부하·끝단 접촉력을 빼기 전의 순 공압력 N |
| 출력 | `retracted_sensor`, `extended_sensor` | 후진·전진 끝단 Boolean |
| 출력 | `valve_extended` | 밸브의 기억된 방향. 위치 도달 여부와 구분 |

기본값은 스트로크 100 mm, 피스톤 지름 20 mm, 로드 지름 8 mm, 이동 질량
0.15 kg, 공급 게이지압 6 bar이다. 초기 위치는 0 m, 밸브는 후진 방향,
챔버와 배관은 대기압으로 시작한다. 초기화 이후 압력이 형성된다.

- 두 입력 OFF: 밸브 방향 유지. **실린더 정지 명령이 아니다.**
- 한쪽 입력 펄스: 파일럿 압력이 전환 기준에 도달하면 방향을 기억한다.
  검증 펄스 폭은 120 ms이다.
- 양쪽 입력 ON: 공개 모델의 파일럿 압력·이력에 따른다. 우선순위·Fault
  정책을 추가하지 않았고 기존 오프라인 시험의 제어 입력으로 사용하지 않았다.
  IO 어댑터도 두 입력을 그대로 전달하며 상충 판단·진단은 상위 애플리케이션 책임이다.
- 센서는 끝단에서 1 mm 이내일 때 켜진다. 히스테리시스는 없다.
- 끝단은 탄성 접촉 모델이므로 위치에 작은 초과량이 생길 수 있다.
- `opposing_force`는 초기화 시 지정하는 일정한 외력이다. 시간에 따라
  변경하는 외력 입력이나 DT와의 힘 교환 인터페이스는 아직 없다.

## Soft ESC IO 연결 범위 — 2026-11-26 확정

실린더 인스턴스의 전진/후진 명령은 DO 2개, 끝단 센서는 DI 2개에 각각 1:1로 연결한다. 같은 채널 또는 같은 인스턴스 신호를 중복 연결하지 않는다. 현재 FMU의 위치·속도·압력·힘 출력은 오프라인 검증에서 사용할 수 있지만 Soft ESC의 실린더 AI 채널로 노출하지 않는다. 실린더 AO 연결도 지원하지 않는다. RF-013의 일반 AI/AO 지원은 별도 아날로그 순수 지연 동작 모델로 검증한다. 이 절은 합의 범위이며 IO 런타임 구현 완료를 뜻하지 않는다.

## 정격 유량 후속 개선

정격 유량은 유로 특성을 정하는 동작 모델 설정이다. 현재는 소스 내부에 있으며 FMU 외부 parameter로 노출되지 않는다. 실제 질량 유량은 내부 계산 결과이며 외부 입출력으로 노출되지 않는다. 외부 정격 유량 설정 지원과 재Export는 [RF-021](../../../Doc/RF/RF-021-pneumatic-cylinder-fmu-improvements.md)로 분리했다. 현재 RF-013 IO 연동은 기존 FMU 그대로 진행한다.

공급압·외력은 외부 운전 조건으로 구분한다. XML에는 tunable parameter로 표시되지만 현재는 초기화 적용만 검증했으며 실행 중 변경은 미검증이다.

## 출처와 재현성

- [PneumaticCircuits 원본](https://github.com/Samarth030312/pneumatic-circuits-openmodelica)
- 버전: [upstream.json](upstream.json)에 고정한 커밋과 ZIP SHA256
- 원본 라이선스: MIT. 생성 FMU의 `documentation/`에 라이선스와 출처를 포함
- 공식 제조사 FMU가 아닌 공개 교육용 모델이다. 마찰·유량·질량 등의
  추정 파라미터가 포함되며 실제 장비에 대한 정확도 검증을 의미하지 않는다.

원본 라이브러리는 `build/pneumatic-fmu-windows/upstream/`에 내려받는다.
기존 축 모델, `.env`, Linux 실행 중 컨테이너는 변경하지 않는다.

## Windows 실행

PowerShell에서 저장소 루트로 이동한다.

```powershell
Set-Location C:\Users\Festo\Documents\ethercat-device-simulator
python -m pip install "fmpy==0.3.26" matplotlib
```

FMU가 이미 생성되어 있으면 다음 명령만 실행한다. OpenModelica는 FMU 실행에
필요하지 않고, Modelica 소스로부터 다시 빌드할 때 필요하다.

```powershell
python scripts/validation/test-pneumatic-fmi2.py
```

재빌드는 [OpenModelica 1.27.1 Windows 배포본](https://openmodelica.org/download/download-windows/)의
`bin/omc.exe`를 지정한다. 이 PC에서는 아래 시험 도구 경로를 사용할 수 있다.

```powershell
python scripts/models/build-pneumatic-fmu.py --omc .cache/toolchains/OpenModelica/bin/omc.exe
python scripts/validation/test-pneumatic-fmi2.py
```

빌드 시 공개 소스 ZIP의 SHA256을 확인한다. FMU, 원본 커밋, 모델 소스 해시,
컴파일러 버전은 다음 산출물로 남는다.

- `model_artifacts/SoftESCDoubleActingCylinder-win64.fmu`
- `model_artifacts/SoftESCDoubleActingCylinder-win64.provenance.json`
- `build/pneumatic-fmu-windows/build.log`

시험 결과는 `results/pneumatic-cylinder/fmi2/<UTC-run-id>/`의 `summary.json`, 각 시험의
CSV, `roundtrip.png`에 저장한다. 기본 결과 경로는 UTC 실행 ID로 구분한다.
이전 결과를 보존하려면 `--output build/pneumatic-fmu-windows/results-new`를 지정한다.

## 검증 범위

1. FMU 구조·입출력·초기 위치·센서 확인.
2. 100 mm 실린더 2회 왕복, 입력 OFF 이후 밸브 기억과 끝단 센서 확인.
3. 제어 구간 8 ms를 0.1 ms FMU 호출 80회로 나누어 계산하고,
   0.05 ms FMU 호출 기준 결과와 위치를 비교한다. CVODE의 내부 적분 간격은 별도이다.
4. 스트로크 50 mm로 초기화해 왕복 확인.
5. 공급압 0 Pa(gauge)에서 명령을 보내도 움직이지 않는지 확인.

여기서 FMU 호출 간격은 FMPy가 `doStep()`에 넘기는 **시뮬레이션 시간 간격**이다.
실제 시간을 기다리는 EtherCAT 주기 시험이나 실시간 성능 보증은 아니다.
생성된 FMU에는 Windows x64 바이너리만 포함한다. Linux 배포는 별도 빌드·검증이
필요하며, CPX-AP-I DO/DI 연결도 후속 작업이다.

## 이번 시험에서 확인된 실행 조건

- 이 OpenModelica 1.27.1 FMI 2.0 CS 런타임은 상태 이벤트를 FMU 호출 경계에서
  처리한다. `doStep(8 ms)` 한 번으로 진행하면 끝단 접촉 처리가 늦어져
  100 mm 시험의 0.52 s 지점에서 계산에 실패했다.
- 1 ms 호출은 100 mm 왕복을 통과했으나 50 mm 시험에서 과도한 끝단 침투가
  관측됐다. 최종 시험기는 두 스트로크 모두 검증된 **0.1 ms 호출**을 사용한다.
  FMU가 스스로 8 ms를 안전하게 분할하도록 수정한 것은 아니다.
- OpenModelica Windows 배포본은 UCRT를 사용한다. 현재 FMU의 CVODE 종료 코드는
  콜백으로 할당한 구조체를 직접 `free()`한다. FMPy 기본 MSVCRT 콜백에서는
  `freeInstance()` 중 heap 오류가 재현됐다. 시험기에서만 UCRT 할당·해제 콜백을
  지정해 해결했으며, 다른 FMU 실행기에서도 종료 호환성을 확인해야 한다.
- 4개 시험 모두 FMU 생성·초기화·계산·종료·해제까지 성공했다.

수치와 한계는 [Windows 검증 보고서](../../../Doc/Validation/Pneumatic-Cylinder-Windows-20261125.md)를 참조한다.

## OpenModelica Playground에서 확인

[Playground FMI](https://playground.openmodelica.org/latest/#fmi)는
`binaries/wasm32-wasip2`를 포함하는 **FMI 3.0 WebAssembly FMU**를 요구한다.
위 Windows FMI 2.0 파일은 이 화면에 직접 넣어 실행할 수 없다.

대신 빌드 스크립트가 아래 **단일 Modelica 소스**도 생성한다. 원본 라이브러리의
필요 부품, 래퍼, 전진·후진 펄스가 포함된 자동 왕복 시험 모델을 함께 담았다.

```text
build/pneumatic-fmu-windows/web/SoftESCPneumaticDemo.mo
```

Windows/Linux에서 컴파일러 설치 없이 웹용 소스만 생성할 수 있다. 아래 파일은
Windows FMU 빌드도 담당하므로 `scripts/models`에 있으며 이 옵션은 양쪽 OS에서 동작한다.

```bash
python3 scripts/models/build-pneumatic-fmu.py --browser-only
```

Windows에서는 `python3` 대신 `python`을 사용한다. 고정한 공개 원본을 내려받고
체크섬을 확인한다. 데모와 외부 명령용 실린더의 단일 소스를 각각 생성한다.

1. Windows의 VS Code 또는 메모장에서 위 `.mo` 파일을 열어 전체 내용을 복사한다.
2. Playground에서 **Simulator**로 이동하고, 왼쪽 **MODELICA MODEL** 코드 편집기를
   클릭한 뒤 `Ctrl+A`, `Ctrl+V`로 기존 예제 전체를 교체한다. Simulator에는 파일
   열기 버튼이 없다. 위쪽 드롭다운은 예제 선택용이며 실행 모델 선택 메뉴가 아니다.
   파일의 첫 선언을 `SoftESCPneumaticDemo`로 배치해 실행 대상으로 인식되게 했다.
3. 오른쪽 위 톱니바퀴에서 Stop time 4 s, Integration method `dassl`을 확인하고
   창을 닫은 뒤 **Run**을 누른다. 결과에서 `position`, `extended_sensor`,
   `retracted_sensor`를 확인한다. 자동으로 두 번 왕복하도록 구성했다.
4. 웹용 FMU가 필요하면 Simulator의 **Export FMU**에서 생성한다.

단일 소스는 Windows OpenModelica에서 구조 검사(85 equations / 85 variables)를
통과했다. 2026-11-25 Playground Simulator에서도 `SoftESCPneumaticDemo`의
**0~4 s 실행 완료와 4,060개 결과 지점 생성**을 확인했다. 이후 사용자가 내보낸
실린더 단독 FMI 3.0 FMU는 Linux x86-64 실행 검증을 통과했다. WebAssembly에서의
FMU 실행은 아직 검증하지 않았다.

웹용 파일은 계산에 필요한 부품만 포함하고 그림·HTML 설명 annotation을 제거했다.
문자열 내부 줄바꿈은 이스케이프했다. 원본 계산식과 Windows FMU는 변경하지 않았다.
기존 파일에서 보고된 `unterminated string literal`의 정확한 원인은 재현하지 못했으며,
여러 줄 설명문 자체가 잘못된 Modelica 문법이라는 의미는 아니다. 같은 파일명으로
다시 생성했으므로, 이전 내용을 붙여넣었다면 파일을 다시 열어 편집기 전체를 교체한다.

2026-11-25 실제 UI에서 코드 편집기, Simulation settings, Run을 확인해 안내를
정정했다. Files의 Add files는 브라우저 `/persist`에 파일을 보관하는 별도 기능이다.

### 외부 명령을 받는 실린더를 Linux FMU로 내보내기

자동 왕복 시나리오를 포함하는 `SoftESCPneumaticDemo` 대신 아래 단일 소스를 쓴다.
원본 폴더의 래퍼와 달리 필요한 PneumaticCircuits 부품도 함께 포함한 파일이다.

```text
build/pneumatic-fmu-windows/web/SoftESCDoubleActingCylinder.mo
```

1. Playground의 컴파일러 로딩이 끝난 뒤, 위 파일 전체를 Simulator 편집기에 붙여넣는다.
   첫 줄은 `model SoftESCDoubleActingCylinder`이다. 예제 드롭다운은 바꾸지 않는다.
2. Run을 누르고 상단 결과 이름이 `SoftESCDoubleActingCylinder`인지 확인한다.
   자동 왕복 명령이 없으므로 입력 OFF인 상태에서 위치가 유지되는 것이 정상이다.
3. Export FMU에서 Model Exchange 해제, Co-Simulation 체크, CS solver `auto`,
   DAE mode 해제, Linux x86-64 체크로 설정한다. ARM 장치라면 Linux ARM64를 선택한다.
4. Export를 누르고 다운로드된 `.fmu`를 보관한다. 출력은 FMI 3.0이며 기존 Windows
   FMI 2.0 파일과 별도 산출물이다. 입력은 `extend_command`, `retract_command`이다.

2026-11-25 이 단일 소스의 로컬 구조 검사(80 equations / 80 variables), 웹 Run,
Linux x86-64 / Co-Simulation 옵션 선택을 확인했다. 이후 사용자가 내보낸 FMU의
Linux 실행 시험 5개도 통과했다. 결과와 Event Mode 호출 조건은
[Linux 검증 보고서](../../../Doc/Validation/Pneumatic-Cylinder-Web-FMU-20261125.md)에 기록했다.

### Linux 오프라인 재검증

FMU 바이너리는 저장소의 기존 정책대로 Git에 넣지 않는다. 웹에서 생성한 전체
`.fmu` 파일을 `model_artifacts/SoftESCDoubleActingCylinder-fmi3-web.fmu`에 보관한다.
이번 검증 파일의 SHA256은 `34b14a7967042fe3abaabab4de6086e8a29324faeb3a2ab29f569c590e2cac42`다.
재Export한 FMU는 생성기·토큰·시간 등에 따라 해시가 달라질 수 있으므로 다시 시험한다.

```bash
python3 -m venv build/fmi-venv
build/fmi-venv/bin/python -m pip install 'fmpy==0.3.26'
build/fmi-venv/bin/python scripts/validation/test-pneumatic-fmi3.py \
  --output build/pneumatic-fmu-web-20261125/results-repeat
```

기존 `build/fmi-venv`에 FMPy 0.3.26이 준비되어 있으면 마지막 명령만 실행한다.
일반 Co-Simulation에서는 FMU가 내부 이벤트를 처리한다. 명시적 Event Mode를
선택하면 Boolean 입력 갱신 시 상태 전이와 Early Return 처리가 필요하다.
이 시험기는 EtherCAT Slave·운영 Docker를 시작하거나 정지하지 않는다.
