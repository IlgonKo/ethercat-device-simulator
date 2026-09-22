# EtherCAT Device Simulator

Software-based EtherCAT device simulation, starting with CMMT drives and reusable CiA 402 models.

The intended architecture connects a PySOEM master over EtherCAT to a software ESC and slave communication stack, with device behavior provided by our existing object dictionary and CiA 402 modules.

KickCAT is the selected implementation direction for the software ESC and slave stack. Basic PySOEM PDO and SDO paths have been validated with a corrected test ESI; CMMT-AS single-axis model integration is validated over a Unix socket; SDO Abort interoperability is deferred as TD-001. The acontis evaluation is on hold.

## 프로젝트 문서

- [작업 일지](Doc/Work_log.md): 진행 결과, 결정 사항 및 후속 작업
- [RF 항목 목록](Doc/RF/README.md): 기본 타당성 검증과 후속 DT 연동 개발
- [TD 항목 목록](Doc/TD/README.md): 보류한 기술 문제와 해결 기준
- [설계 및 진행 계획](Doc/project-plan.md): 목적, 실행 구성 및 모듈 책임

기본 타당성 검증에 사용한 실행 구성은 **Windows PC의 Motion Server/PySOEM ↔ 실제 EtherCAT 케이블 ↔ 별도 Linux PC의 KickCAT 시뮬레이터**입니다. Linux 빌드 및 enp1s0에서 기본 Slave 실행·정상 종료를 검증했습니다. Windows PySOEM과의 물리 PDO 교환 1,000회를 검증했습니다. 테스트용 ESI에 0x1C00 정렬 보정이 필요하며, SDO 시험은 2-1단계로 분리했습니다.

진행 순서 (2026-09-14 합의):

1. Linux에서 KickCAT 빌드 및 기본 Slave 시뮬레이션 실행.
2. Windows PySOEM에서 Slave 검색 → OP 전환 → PDO 왕복 검증. 명시적 SDO 시험은 별도 2-1단계.
3. 기존 `VirtualOdBridge`와 가상 서보 모델을 연결해 CMMT 동작 구현.
4. Motion Server와 Axis Panel로 통합 테스트.

**첫 목표는 물리 케이블을 통한 PySOEM과 KickCAT의 기본 통신 확인**입니다. MockMaster는 비교·회귀 테스트용으로 유지합니다. acontis EC-Simulator 검토는 보류합니다.

2-1단계 기본 SDO 읽기·쓰기·복원 및 PDO 회귀를 검증했습니다. SDO Abort 응답 호환성은 [TD-001](Doc/TD/TD-001-sdo-abort-response.md)로 등록하고 구현을 보류합니다.

RF-003 기본 1축 연결을 검증했습니다: CMMT-AS / 기본 PDO, 별도 Python 모델 + Unix 소켓, SDO·CiA 402·Homing·이동·PDO 1,000회 및 SDO/PDO 위치 일치 확인. [구현 및 실행 방법](Doc/RF/RF-003-cmmt-model-integration.md). Motion Server·Axis Panel 통합은 RF-004입니다.

## Motion Server / Axis Panel 수동 테스트

Windows PowerShell에서:

```powershell
python scripts/windows/run-integration-bench.py --source C:\Users\Festo\Documents\motion-server --panel
```

Linux 시뮬레이터, Windows Motion Server와 Axis Panel을 함께 실행합니다. Panel 접속은 `127.0.0.1:15100`이며 기본 9분 후 자동 종료합니다. Ctrl+C 또는 Panel 종료로도 정리합니다. [RF-004 사용 절차 및 검증 결과](Doc/RF/RF-004-motion-server-axis-panel.md)를 참조하세요. 기본 통합과 MockMaster 비교는 통과했으며 실제 Fault 주입·복구 및 TD-001은 후속 범위입니다.


## Omniverse DT 연동 설계 (2026-09-15)

기본 타당성 검증을 완료하고 다음 구조에 합의했습니다. **Motion Server 1개 / 실제·가상 장치 동일 EtherCAT 버스 / 외부 명령·리드백 라우터 / Omniverse 연결부**입니다. Motion Server는 수정 없는 독립 패키지로 유지합니다. 기본 3 Slave 혼합 버스와 실제·가상 장치 선택 동작은 RF-005에서 검증했습니다. 외부 라우터와 모드 전환은 후속 구현입니다.

- [DT-001 전체 구조](Doc/Design/DT-001-system-architecture.md)
- [DT-002 모드 전환과 상태 동기화](Doc/Design/DT-002-mode-switching.md)
- [DT-003 모델 인터페이스와 FMI 확장 방향](Doc/Design/DT-003-model-interface.md)

실제→가상은 정지한 실제 상태로 모델을 초기화하고, 가상→실제는 실제 장비를 움직이지 않고 현재 실제 상태로 DT를 맞춥니다. 장치 동작은 가상축·가상 IO 모델이 계산하며 FMI는 향후 확장입니다. RF-005는 기본 검증 완료, RF-006~008은 계획 상태로 [RF 목록](Doc/RF/README.md)에서 관리합니다.

양방향 파라미터 동기화와 가상장치 재시작 시 설정 유지 요구를 [DT-004](Doc/Design/DT-004-parameter-sync-persistence.md)에 추가했습니다. RF-009 동기화는 계획 단계이며 RF-010은 기본 저장·복원을 구현하고 후속 검증 중입니다.

[DT-005 독립 장치 구성](Doc/Design/DT-005-device-configuration.md)에 독립 JSON 단일 형식(2026-09-22 변경), 별도 설정 소유권, 실제·가상 Slave 배치 및 번호 매핑을 기록했습니다. Motion Server 설정 자동 읽기는 채택하지 않습니다. 구성 로더와 4축 생성의 초기 구현·오프라인 검증을 완료했습니다. [RF-011](Doc/RF/RF-011-device-configuration.md)의 4축 기본 동작을 확인했으나 8 ms 주기 안정성 문제가 재현되어 개선 중입니다.

[DT-006 Docker 배포](Doc/Design/DT-006-docker-deployment.md): Linux Edge PC의 단일 Simulator 컨테이너, host 네트워크, 외부 설정·영구 저장소를 초기 방향으로 정했습니다. Edge NIC 3개는 Master / Simulator / 엔지니어링·외부 Omniverse 연결에 각각 사용합니다. [RF-012](Doc/RF/RF-012-docker-deployment.md)는 계획/미착수입니다.

현재 구현 범위는 **가상축**입니다. RF-011은 독립 JSON과 다중 CMMT 축을 담당하며 가상 IO·IO-Link는 [RF-013](Doc/RF/RF-013-virtual-io.md)에 Pending으로 분리했습니다. 기존 IO 설계 예시는 현재 구현 계약이 아니며 별도 재논의합니다.

## JSON 4축 구성

[config/four-axes.json](config/four-axes.json)은 직선축 2개와 회전축 2개의 독립 구성 예제입니다. `--config`로 지정하며, 파라미터 저장 경로는 JSON 기준 `storage.directory`입니다. PDO 선택 필드는 없고 기본 고정 매핑으로 시작합니다.

[RF-011 실행 절차](Doc/RF/RF-011-device-configuration.md#수동-실행과-다음-물리-시험)에 신규 빌드 실행·NIC 없는 검증·물리 시험 순서를 기록했습니다. 현재 모델 소스는 명시적 `--model-root`로 재사용하며 독립 모델 패키지 배포는 후속입니다. [RF-015](Doc/RF/RF-015-axis-model-semantics.md)는 위치 제한/회전 동작 개선을 별도 관리합니다.

## 2026-09-22 성능 계측 결과와 다음 작업

2축은 120초 관측에서 정상 동작했으나 4축은 PDO 처리 지연 및 버스 Fault가 재현됐습니다. [프레임·IPC 계측](Doc/RF/RF-011-timing-20260922.md)과 [Python 세부 계측](Doc/RF/RF-011-python-timing-20260922.md)에 시험 조건과 한계를 기록했습니다. IPC 시간의 약 90%가 모델 계산이며, 별도 오프라인 프로파일에서는 OD role 전체 검색이 모델 시간의 약 97.57%를 차지했습니다.

다음 작업은 OD role 조회 인덱스의 일관성과 축별 독립성을 유지하는 최적화 후 동일 2축/4축 조건 재측정입니다. 최적화 및 IPC 묶음 처리는 아직 적용하지 않았으며 RF-011은 완료 상태가 아닙니다.
