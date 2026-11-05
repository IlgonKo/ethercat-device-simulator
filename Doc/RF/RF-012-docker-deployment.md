# RF-012 — Simulator Docker 패키징 및 실행 검증

- 현재 상태: **진행 중**
- 상태 상세: 독립 Docker 운영·혼합 물리 통신·저장 복원·모델 장애 격리 확인. Slave 자체 장애 정리·재연결 복구도 확인. 다단계 빌드 새 이미지의 사용자 수동 정상 동작 확인; NIC 추가 검증 보류(필요 시 별도 RF), Omniverse 연동은 추후 진행. 2026-11-05 Docker/native 동일 조건 비교 완료. 새 PC 확인·동일 Edge 배치 조건 잔여.

## 현재 구현

Linux 단일 컨테이너에서 EtherCAT Slave와 Functional Model을 별도 프로세스로 실행한다. Simulator 자체 `.env`, host 네트워크, 지정 NIC, `/state` bind 저장소, 임시 소켓을 사용한다. Motion Server 소스·설정·외부 모델 스냅샷을 마운트하지 않는다.

이미지는 `ethercat-device-simulator:dev`, 운영은 [scripts/docker](../../scripts/README.md)를 따른다. Docker 다단계 빌드에서 C++ 의존성·KickCAT·Simulator·Linux Copley FMU를 빌드한다. `start.sh --build`에 호스트 native 사전 빌드가 필요하지 않다. 고정 Builder/base 이미지와 소스/wheel 입력은 먼저 준비한다. 기본 FMU는 이미지에 포함하며 기존 외부 경로 설정은 선택적 override로 유지한다.

## 완료 기준 대조

| 기준 | 상태 | 기존 근거 / 실제 남은 범위 |
| --- | --- | --- |
| Linux/CPU 이미지 빌드·배포 조건 | 부분 확인 | Edge x86_64 빌드·운영 성공. 별도 checkout에서 C++·FMU 재빌드와 새 이미지 오프라인 검증 완료. 기존 의존성 묶음 사용; wheel/C++ 소스/base/Builder 고정 및 export·restore·rebuild 도구 구현. 새 PC/OS 확인은 남음 |
| Motion Server와 독립 실행 | 완료 | RF-016 자체 모델 이관 및 운영 Docker |
| 비대화식 지속 실행·정상 stop·자식 정리 | 완료 | Docker 시험에서 stdin 없이 실행, stop 코드 0 및 자식 종료 확인 |
| 모델 실패 시 Slave 유지·장애 표시 | 완료 | RF-018 SIGSTOP/SIGKILL, WKC 표본·축 Fault·수동 복구 |
| Slave 자체 실패 시 서비스 정리·readiness | 완료 | 2026-11-03 Slave SIGKILL, 모델 -15 정리, 컨테이너 exit 1/unhealthy, 새 소켓·ready 확인. Master 재연결 후 WKC 18/18·정상 진단 확인 |
| NIC 선택·중복 거부·기본 경로 보호 | 기존 확인 / 추가 검증 보류 | 기존 보호 검사·중복 사용 거부 근거 유지. 권한·플래그 추가 검증은 사용자 결정으로 보류하며 필요 시 별도 RF로 분리 |
| 물리 검색·SDO·OP·PDO 및 혼합 통신 | 완료 | Windows Master + Linux Docker, 실제 축/IO + 가상 4축. RF-010/018 4ms·WKC 18/18 관측 |
| 비컨테이너 대비 주기 지연 | 완료 | 2026-11-05 동일 모델 조합·PDO·4ms 설정, 2축/4축 정지/PP 반복 비교. Python/컴파일러 환경 차이가 있어 순수 컨테이너 오버헤드 수치로 해석하지 않음 |
| .env 다축 구성 전달 | 완료 | .env 전환 회귀와 운영 4축 생성 |
| 저장·컨테이너 재생성·새 이미지 적용 | 완료 | RF-010 스키마 이관/새 이미지, SDO 111/123 저장·재생성 복원, 58개 전체 대조·저장 오류 시험 |
| 외부 DT/엔지니어링 경로 분리 | 후속 작업 | 관리 연결 운영 근거 유지. Omniverse DT 연동 및 별도 PC 경로 검증은 사용자 결정에 따라 추후 진행. RF-008 연계 |
| Master/Simulator 동일 Edge 배치 | 미검증 | Windows Master + Linux Simulator 시험으로 대체하지 않음 |
| 운영·업데이트·백업·복구 절차 | 완료 | scripts, RF-010 백업/이관, RF-018 수동 복구. 임의 구버전 rollback 호환성 보장은 아님 |

모델 장애 시 통신 유지가 미구현이라는 과거 문구는 RF-018 완료로 대체한다. healthcheck는 OP/PDO/WKC 정상의 보장이 아니다. 모델 재시작은 진행 동작 복원이 아니며 Master 초기화의 Enable과 구분한다.

## 실제 남은 항목

1. 배포 묶음을 실제 새 Linux PC/OS에서 확인. 의존성 고정·묶음 생성·복원·재빌드 절차는 구현했다. 호스트 compiler는 필요 없다. OS·Docker 설치 패키지는 묶음에 포함하지 않는다.
2. 동일 Edge의 Master/Simulator 동시 배치 확인. 현재 구성의 실패가 아니라 아직 시험하지 않은 배치 조건이다.

NIC 권한·플래그 추가 검증은 보류하며 필요성이 생길 때 별도 RF로 분리한다. 지금 새 RF를 발행하거나 시험을 시작하지 않는다. Omniverse DT 연동 및 외부 PC 경로 검증도 추후 작업으로 두며 현재 다음 단계로 추진하지 않는다.

일반 혼합 연결·SDO/PDO·저장 복원·모델 종료 시험을 다시 요구하지 않는다. 위 기존 완료 기준이 남아 RF 전체는 진행 중이다. 신규 시험 시간·합격 수치는 이번 정리에서 정하지 않는다.

## 근거

- [RF-010](RF-010-parameter-persistence.md), [RF-018](RF-018-diagnostic-fault.md).
- [과거 Docker 구현·검증 기록](../Validation/RF-012/history-through-20261028.md): 당시 JSON·미구현 표시는 현재 판정이 아니다.
- [DT-006](../Design/DT-006-docker-deployment.md), [운영 스크립트](../../scripts/README.md).

## 2026-11-03 Slave 장애 시험

[검증 기록](../Validation/RF-012/slave-exit-20261103.md). Slave SIGKILL 감지, 모델 정리, 컨테이너 비정상 종료 및 재생성 ready 확인. 저장 파라미터 불변. 사용자 Master 재연결 후 30회 모두 WKC 18/18, 정상 진단·전 축 Fault 없음 확인. Slave 종료·정리·수동 복구 항목을 완료 처리했다.

## 2026-11-03 별도 checkout 빌드 검증

[검증 기록](../Validation/RF-012/build-repro-20261103.md). KickCAT·Simulator·Linux FMU 재빌드, 별도 이미지, 혼합 4축 저장 복원·SDO gateway·실제 FMU 7개 테스트 통과. 운영 컨테이너는 유지했다. 외부 의존성 일부와 기본 이미지는 기존 오프라인 자료를 사용했으므로 새 OS부터의 전체 재현성 완료로 확대하지 않는다.

## 오프라인 배포 도구

[운영 매뉴얼](../../scripts/deployment/README.md). Python wheel은 전이 의존성까지 버전/해시 고정, Docker base/Builder digest 고정, C++ 의존성은 소스 archive 해시 고정이다. Conan cache는 Docker 배포 경로에 사용하지 않는다. `offline.py`로 운영 설정/파라미터를 제외한 배포 묶음을 생성·검증하고 별도 경로에 복원 또는 재빌드한다. 컨테이너 시작·운영 :dev 태그 전환은 수동이다.

[배포 도구 검증 결과](../Validation/RF-012/offline-deployment-20261103.md): export/verify/load/restore/전체 rebuild 및 새 이미지 혼합 4축·SDO·FMU 검증 통과. 현재 Edge의 격리 경로 범위이며 실제 새 PC 검증은 남는다.

## Docker 다단계 빌드 전환

기존 호스트 GCC/Conan archive 기반 절차는 native 개발용으로 남기고 Docker 배포 경로에서 제거했다. 컴파일러는 Builder 이미지에 포함하며 C++ 의존성도 소스로 빌드한다. schema 2 오프라인 묶음에는 Builder 이미지를 포함한다. [현재 매뉴얼](../../scripts/deployment/README.md)을 우선 적용하며 이전 검증 문서의 host compiler 조건은 당시 방식의 이력이다.

[다단계 빌드 검증 결과](../Validation/RF-012/multistage-build-20261103.md): 컨테이너 내 소스 빌드·schema 2 offline rebuild·최종 이미지 내장 FMU 혼합 4축/SDO 검증 완료. 자동 검증 당시에는 운영 컨테이너를 교체하지 않았으며, 이후 사용자가 새 이미지로 수동 테스트를 완료하고 정상 동작을 확인했다 (2026-11-03).

## 2026-11-03 사용자 수동 전환 검증

사용자가 새 다단계 빌드 이미지로 수동 테스트를 완료하고 정상 동작을 확인했다. 새 이미지의 수동 적용·동작 확인을 완료로 기록한다. 상세 WKC 수치·시험 시간·개별 시험 항목별 로그는 추가 제출되지 않았으므로 새 정량 결과로 기록하지 않는다. 새 PC/OS·동일 Edge 배치 및 성능 비교 등 별도 잔여 기준이 있어 RF-012 전체는 진행 중을 유지한다.

## 2026-11-05 Docker/native 비교 완료

[RF-016 공통 보고서](../Validation/RF-016/runtime-comparison-20261105/README.md). 혼합 2축/4축의 정지·PP를 각각 두 번 측정했다. C++ 평균 처리 시간은 두 방식에서 유사했고 모든 측정 PDO에서 WKC 정상·Fault0을 확인했다. 동일 FMU 파일을 사용했으나 Python/GCC 버전 차이를 포함한다. 새 PC/OS 배포 및 동일 Edge Master/Simulator 배치는 계속 미검증이므로 RF-012 전체는 진행 중이다. NIC 추가 검증 보류·Omniverse 추후 결정은 유지한다.
