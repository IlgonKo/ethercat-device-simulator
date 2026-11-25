# Playground 실린더 FMU — Linux 실행 검증

상태: **완료 — Linux x86-64 오프라인 FMU 검증 통과**

검증일: 2026-11-25 (Asia/Seoul)

## 대상

사용자가 OpenModelica Playground에서 Export한 `SoftESCDoubleActingCylinder.fmu`를
수정하지 않고 Linux PC `Edge-ubuntu`에서 실행했다. 기존 Windows FMI 2.0 FMU와는
다른 산출물이다. 실린더 단독 모델이며 자동 왕복 입력은 시험기에서 외부 신호로 제공했다.

- 사용자 원본: `C:/Users/Festo/Downloads/SoftESCDoubleActingCylinder.fmu`
- Linux 보관: `/home/festo/Documents/ethercat-device-simulator/model_artifacts/SoftESCDoubleActingCylinder-fmi3-web.fmu`
- SHA256: `34b14a7967042fe3abaabab4de6086e8a29324faeb3a2ab29f569c590e2cac42`
- FMI 3.0 Co-Simulation, solver 설정 `auto`.
- 생성기: `OpenModelica Compiler v1.28.0-dev.2122+ga67a2b8d1e.rust`.
- 포함 플랫폼: Linux x86-64, Windows x86-64, wasm32-wasip2.
- 실제 실행 환경: Ubuntu 24.04.3, Linux 6.8.1-1015-realtime x86_64, glibc 2.39,
  Python 3.12.3, FMPy 0.3.26. Windows 및 WebAssembly 바이너리는 이번 시험에서 실행하지 않았다.

## 구조·입출력

FMPy `validate_fmu()`의 오류 목록은 비어 있다. Linux 바이너리는 x86-64 ELF 공유
라이브러리이며 로드·인스턴스 생성·계산·종료·해제를 모두 통과했다. 전체 FMU를
압축 해제해 사용했으며 `.so`만 떼어 배포하는 방식은 시험하지 않았다.

| 구분 | 이름 | 자료형 / 단위 |
|---|---|---|
| 입력 | `extend_command`, `retract_command` | Boolean |
| 출력 | `position`, `velocity` | Float64, m / m/s |
| 출력 | `pressure_cap`, `pressure_rod` | Float64, 절대압 Pa |
| 출력 | `pneumatic_force` | Float64, N |
| 출력 | `retracted_sensor`, `extended_sensor`, `valve_extended` | Boolean |

## 실행 결과

각 시험은 시뮬레이션 시간 4초이며 별도 프로세스에서 수행했다. 전진 펄스는
0.4~0.52초와 2.0~2.12초, 후진 펄스는 1.2~1.32초와 2.8~2.92초에 제공했다.

| 시험 | 조건 | 결과 |
|---|---|---|
| 기본 왕복 | 스트로크 100mm, 공급 6bar(gauge), 8ms 직접 호출 | 두 번 왕복, 끝단 센서 정상 |
| 호출 간격 비교 | 같은 입력으로 1ms 호출 | 통과, 8ms 표본에서 최대 위치 차이 약 3.13×10⁻¹³m |
| 스트로크 변경 | 초기화 시 50mm, 8ms 호출 | 두 번 왕복, 변경된 끝단에서 센서 ON |
| 무공압 | 공급 0Pa(gauge), 동일 입력 | 위치 0 유지, 전진 센서 OFF |
| 명시적 이벤트 모드 | 8ms 제어 간격, Event Mode와 Early Return 처리 | 통과, doStep 525회 / Early Return 25회 |

기본 8ms 시험은 501개 표본에서 위치 -0.015834~100.018850mm를 관측했다.
약 0.019mm의 끝단 초과는 모델의 탄성 접촉에 따른 것이며, 시험 허용 범위 ±2mm
이내이다. 모든 실수 출력이 유한하고 절대압은 양수였으며, 두 끝단 센서가 동시에
ON인 표본은 없었다. 입력 OFF 이후 밸브 방향을 유지하는 것도 확인했다.

8ms와 1ms의 위 차이는 공통 관측 시점에서의 두 실행 결과 차이이다. 별도의
고정밀 물리 기준 해와 비교한 정확도 수치가 아니다.

기본 시험은 `eventModeUsed=false`, `earlyReturnAllowed=false`로 FMU가 내부에서
이벤트를 처리한다. 기존 Windows FMI 2.0 시험과 달리 외부 시험기에서 8ms를
0.1ms로 분할하지 않아도 이 FMI 3.0 산출물은 해당 시나리오를 통과했다.

## 이벤트 모드에서 확인한 호출 조건

FMPy 0.3.26의 고수준 `simulate_fmu(use_event_mode=True)` 경로는 Step Mode에서
Boolean 입력을 다시 쓰며 `fmi3SetBoolean` 오류가 발생했다. FMU 파일은 수정하지 않았다.
시험기의 명시적 FMI 호출을 다음 순서로 구성하자 통과했다.

1. 초기화 중 입력 설정 → 초기화 종료 → 이산 상태 갱신 → Step Mode.
2. 입력 변경 시 Event Mode 진입 → Boolean 입력 설정 → 이산 상태 갱신 → Step Mode.
3. doStep의 이벤트·Early Return을 확인하고 `lastSuccessfulTime`부터 남은 시간을 계산.

이는 FMI 3.0의 [Event Mode와 입력 이벤트 처리](https://fmi-standard.org/docs/3.0.2/#state-event-mode)에
따른다. 당장 사용할 기본 경로는 FMU 내부 이벤트 처리를 이용한 일반 Co-Simulation이다.
명시적 이벤트 처리가 필요한 실행기는 위 순서와 Early Return 처리를 구현해야 한다.
초기 진단 실패 로그는 `build/pneumatic-fmu-web-20261125/results/`에 보존했다.

## 재실행과 근거 파일

Linux 저장소에서 실행한다. 실행 중인 Soft ESC 컨테이너나 EtherCAT NIC를 사용하지 않는다.

```bash
cd /home/festo/Documents/ethercat-device-simulator
build/fmi-venv/bin/python scripts/linux/test-pneumatic-fmi3.py \
  --output build/pneumatic-fmu-web-20261125/results-repeat
```

- 시험기: `scripts/linux/test-pneumatic-fmi3.py`
- 원본 결과·CSV·로그: `build/pneumatic-fmu-web-20261125/results-validated/`
- 결과 사본: [Pneumatic-Cylinder-Web-FMU-20261125.json](Pneumatic-Cylinder-Web-FMU-20261125.json)

이번 검증은 오프라인 FMU 실행 호환성과 해당 조건의 동작을 확인한 것이다.
실시간 주기 보장, 실제 실린더에 대한 정량 정확도, Soft ESC 어댑터·CPX-AP-I IO
연결은 포함하지 않는다. 두 입력 OFF는 정지가 아니라 밸브 방향 유지이며, 이 동작을
기존 단순 실린더 모델의 OFF/OFF 정지 계약과 혼동하면 안 된다.
