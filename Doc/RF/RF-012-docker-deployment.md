# RF-012 — Simulator Docker 패키징 및 실행 검증

- 현재 상태: **진행 중**
- 상태 상세: 독립 Docker 운영·혼합 물리 통신·저장 복원·모델 장애 격리 확인. Slave 자체 장애 정리·재연결 복구도 확인. 배포 재현성·성능 비교·배치 조건 잔여 (2026-11-03).

## 현재 구현

Linux 단일 컨테이너에서 EtherCAT Slave와 Functional Model을 별도 프로세스로 실행한다. Simulator 자체 `.env`, host 네트워크, 지정 NIC, `/state` bind 저장소, 임시 소켓을 사용한다. Motion Server 소스·설정·외부 모델 스냅샷을 마운트하지 않는다.

이미지는 `ethercat-device-simulator:dev`, 운영은 [scripts/docker](../../scripts/README.md)를 따른다. Dockerfile은 현재 `build/timing/cmmt_simulator`를 패키징한다. `start.sh --build`는 C++ 소스 빌드까지 수행하지 않으며 사전 native 빌드가 필요하다. 모델은 `src/functional_model`에서 포함한다.

## 완료 기준 대조

| 기준 | 상태 | 기존 근거 / 실제 남은 범위 |
| --- | --- | --- |
| Linux/CPU 이미지 빌드·배포 조건 | 부분 확인 | Edge x86_64 빌드·운영 성공. 깨끗한 checkout에서 전체 의존성까지 재현하는 검증은 남음 |
| Motion Server와 독립 실행 | 완료 | RF-016 자체 모델 이관 및 운영 Docker |
| 비대화식 지속 실행·정상 stop·자식 정리 | 완료 | Docker 시험에서 stdin 없이 실행, stop 코드 0 및 자식 종료 확인 |
| 모델 실패 시 Slave 유지·장애 표시 | 완료 | RF-018 SIGSTOP/SIGKILL, WKC 표본·축 Fault·수동 복구 |
| Slave 자체 실패 시 서비스 정리·readiness | 완료 | 2026-11-03 Slave SIGKILL, 모델 -15 정리, 컨테이너 exit 1/unhealthy, 새 소켓·ready 확인. Master 재연결 후 WKC 18/18·정상 진단 확인 |
| NIC 선택·중복 거부·기본 경로 보호 | 부분 확인 | 기존 보호 검사·중복 사용 거부 시험. 실제 권한 필요성과 NIC 플래그 변경/종료 후 상태 기록은 남음 |
| 물리 검색·SDO·OP·PDO 및 혼합 통신 | 완료 | Windows Master + Linux Docker, 실제 축/IO + 가상 4축. RF-010/018 4ms·WKC 18/18 관측 |
| 비컨테이너 대비 주기 지연 | 미검증 | 동일 조건 비교 기록 없음. RF-016과 함께 계측 가능 |
| .env 다축 구성 전달 | 완료 | .env 전환 회귀와 운영 4축 생성 |
| 저장·컨테이너 재생성·새 이미지 적용 | 완료 | RF-010 스키마 이관/새 이미지, SDO 111/123 저장·재생성 복원, 58개 전체 대조·저장 오류 시험 |
| 외부 DT/엔지니어링 경로 분리 | 부분 확인 | 관리 연결 운영과 별개로 Omniverse 별도 PC 동시 통신 근거는 없음. RF-008 연계 |
| Master/Simulator 동일 Edge 배치 | 미검증 | Windows Master + Linux Simulator 시험으로 대체하지 않음 |
| 운영·업데이트·백업·복구 절차 | 완료 | scripts, RF-010 백업/이관, RF-018 수동 복구. 임의 구버전 rollback 호환성 보장은 아님 |

모델 장애 시 통신 유지가 미구현이라는 과거 문구는 RF-018 완료로 대체한다. healthcheck는 OP/PDO/WKC 정상의 보장이 아니다. 모델 재시작은 진행 동작 복원이 아니며 Master 초기화의 Enable과 구분한다.

## 실제 남은 항목

1. 깨끗한 Linux checkout 기준 C++·Python·FMU 준비와 전체 배포 재현성 검증.
2. NIC 권한·플래그 영향 기록 및 Docker/native 동일 조건 지연 비교.
3. 동일 Edge의 Master/Simulator 동시 배치, 별도 Omniverse PC와 외부 통신 경로 검증. 현재 구성의 실패가 아니라 아직 시험하지 않은 배치 조건이다.

일반 혼합 연결·SDO/PDO·저장 복원·모델 종료 시험을 다시 요구하지 않는다. 위 기존 완료 기준이 남아 RF 전체는 진행 중이다. 신규 시험 시간·합격 수치는 이번 정리에서 정하지 않는다.

## 근거

- [RF-010](RF-010-parameter-persistence.md), [RF-018](RF-018-diagnostic-fault.md).
- [과거 Docker 구현·검증 기록](../Validation/RF-012/history-through-20261028.md): 당시 JSON·미구현 표시는 현재 판정이 아니다.
- [DT-006](../Design/DT-006-docker-deployment.md), [운영 스크립트](../../scripts/README.md).

## 2026-11-03 Slave 장애 시험

[검증 기록](../Validation/RF-012/slave-exit-20261103.md). Slave SIGKILL 감지, 모델 정리, 컨테이너 비정상 종료 및 재생성 ready 확인. 저장 파라미터 불변. 사용자 Master 재연결 후 30회 모두 WKC 18/18, 정상 진단·전 축 Fault 없음 확인. Slave 종료·정리·수동 복구 항목을 완료 처리했다.
