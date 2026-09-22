# DT-006 — Linux Edge PC의 Docker 배포

- 결정일: 2026-09-15
- 상태: 초기 배포 방향 합의, 이미지·서비스 진입점 및 컨테이너 통신 검증 전

## 배포 기준

Linux Edge PC의 Docker Engine에서 Simulator 단일 컨테이너를 실행한다. KickCAT C++ 통신 프로세스와 Python 가상축·가상 IO 모델을 함께 배포하고 현재 Unix 소켓 경계를 유지한다. Motion Server는 별도 독립 패키지이며 Simulator 이미지에 포함하거나 해당 소스 체크아웃을 실행 시 요구하지 않는 것이 목표다. 재사용 모델의 배포 의존성·라이선스·버전 고정 방식은 구현 시 명세한다. 향후 FMI 모델 연결을 위한 경계는 DT-003을 따른다.

이 구성은 Linux Docker Engine을 기준으로 한다. Windows Docker Desktop 또는 VM에서 물리 EtherCAT NIC를 동일하게 사용할 수 있다고 가정하지 않는다. Motion Server의 Linux 실행 및 Edge 동시 배치는 별도 검증 대상이며 기존 Windows Master 시험 결과를 그대로 전용하지 않는다.

## Edge PC와 NIC 역할

사용자는 Edge PC에 추가 LAN 카드를 설치하고 Omniverse를 별도 PC에서 실행할 예정이다. 다음 세 인터페이스를 분리한다. NIC 1/2/3은 역할 이름이며 실제 OS 인터페이스 이름은 설정으로 지정한다.

```text
Edge PC / Linux
  Motion Server ↔ NIC 1 ↔ 실제 장비 체인 ↔ NIC 2 ↔ Simulator 컨테이너
  라우터 / DT Bridge ↔ NIC 3 ↔ 일반 Ethernet 스위치
                                  ├─ Omniverse PC
                                  └─ 엔지니어링 PC
```

- NIC 1: EtherCAT Master.
- NIC 2: EtherCAT Simulator. 실제 장비 체인 끝에 연결하는 초기 범위.
- NIC 3: 일반 TCP/IP, 엔지니어링·관리·DT 연결.

Master가 보낸 프레임은 실제 장비들을 지나 Simulator에 도달하고, Simulator가 같은 NIC 2로 반환하면 같은 실제 장비들을 반환 경로로 지나 Master NIC 1로 돌아간다. 뒤에 별도의 실제 장비를 추가하는 의미가 아니다. Simulator는 NIC 하나로 다수 가상 Slave를 생성하는 것이 목표다.

중간 삽입을 위한 IN/OUT 두 포트 및 하류 전달·반환 처리는 초기 범위에서 제외한다. 실제 체인 뒤에서의 다장치 프레임 경로·OP·PDO 동작은 RF-005에서 검증한다. 위 배치는 시험 완료 결과가 아니다.

## Docker 네트워크와 권한

초기 네트워크는 Linux `network_mode: host`를 사용한다. 호스트 네트워크 네임스페이스를 공유하고 Simulator 설정이 NIC 2를 명시적으로 선택한다. host 모드는 NIC 하나만 컨테이너에 독점 할당하는 기능이 아니다. 중복 Simulator·동일 NIC 사용자 및 관리 NIC 오선택 검사를 유지한다.

현재 코드의 raw Ethernet 및 NIC 설정에 맞춰 NET_RAW·NET_ADMIN 권한을 검증한다. 전체 privileged 모드를 기본으로 하지 않는다. 실행 UID, 이미지 파일 capability 및 실제 프로세스 권한의 조합을 구현 시 확인한다. NET_ADMIN과 host 네트워크는 호스트 NIC에 영향을 줄 수 있으므로 초기화·종료 시 변경하는 플래그와 복원 범위를 명시한다.

EtherCAT은 포트 publish 또는 일반 bridge/NAT 연결로 대체하지 않는다. 관리 서비스는 정한 관리 IP 또는 로컬 주소에 바인딩하고 NIC 3을 통한 접근 경로를 정의한다. 구체적인 API·포트·인증 방식은 미결정이다. 네트워크 공유만으로 실시간 성능이나 NIC 독점이 보장되는 것은 아니다.

## 이미지·설정·데이터 경계

| 항목 | 위치 및 정책 |
| --- | --- |
| C++ 실행 파일·Python 의존성·장치 기본 프로파일 | 버전이 고정된 이미지 |
| Simulator 구성 JSON | 호스트 파일을 읽기 전용 마운트 |
| 장치 영구 파라미터·설정 revision·백업 | 호스트 데이터 디렉터리 또는 named volume |
| Unix 소켓·임시 데이터 | 컨테이너 임시 영역, 영구 저장 제외 |
| 실행 로그 | 표준 출력과 필요한 영구 시험/변경 기록 |

2026-09-22 결정에 따라 장치 구성은 표준 JSON 하나로 관리하며 Simulator 자체 로더가 읽는다. Compose 배포 환경 설정과 제품 장치 구성 JSON을 구분하며 .env 장치 구성은 지원하지 않는다. Motion Server .env 자동 읽기 옵션은 없다.

컨테이너 재생성·이미지 교체 이후에도 같은 저장소를 연결해 파라미터를 복원한다. 데이터 볼륨을 삭제하는 운영 명령은 일반 재시작 절차에 포함하지 않는다. 데이터 경로·볼륨 방식·저장 형식은 상세 설계에서 확정한다. DT-004의 스키마 검증·이관·손상 처리·실행 상태 제외 원칙을 따른다.

## 서비스 수명 주기

현재 cmmt-session.py는 진단용이며 stdin EOF로 종료한다. 이를 그대로 백그라운드 컨테이너의 진입점으로 사용하지 않는다. 서비스용 관리자가 다음을 담당한다.

1. 설정 검증 및 영구 파라미터 복원.
2. Python 모델 및 C++ 프로세스 시작, Unix 소켓 연결·NIC 초기화 확인.
3. 준비 상태 제공. 프로세스 존재만으로 EtherCAT OP 또는 운전 준비를 주장하지 않는다.
4. 터미널 입력과 무관하게 지속 실행. 수동 서비스의 실행 시간 제한 없음.
5. docker stop의 종료 신호를 전달하고 두 프로세스 및 소켓을 정리, 종료 상태 기록.
6. 어느 한 프로세스가 실패하면 다른 프로세스도 정리하고 서비스 실패로 보고.

컨테이너 재시작과 실제 장비 운전 재개는 별도다. 자동 재시작 정책·정리 제한 시간·health/readiness 계약은 구현 전에 정한다. 재시작된 Simulator가 이전 이동 명령을 자동 재생하지 않으며 서버의 재연결·오류 복구 가능 범위도 따로 확인한다.

## 검증과 미결정 항목

[RF-012](../RF/RF-012-docker-deployment.md)에서 이미지 빌드·서비스 수명 주기·raw NIC 접근·물리 PDO·영구 데이터 복원을 검증한다. 최초 단축 컨테이너 검증은 기존 RF-003/004 구성을 재사용할 수 있다. 다장치·혼합 버스·장치 구성·파라미터 저장 완료는 RF-005/010/011과 연계해 구분한다.

기본 이미지, CPU 아키텍처, 실행 UID, 데이터 경로, 이미지 배포처, 재시작 정책과 리소스 설정은 미결정이다. Docker 도입만으로 DC/CSP 실시간성 또는 지연 목표를 충족했다고 보지 않는다.

## 근거 및 관련 문서

- [Docker host 네트워크](https://docs.docker.com/engine/network/drivers/host/)
- [Docker 실행 권한](https://docs.docker.com/engine/containers/run/)
- [Docker 영구 볼륨](https://docs.docker.com/engine/storage/volumes/)
- [전체 구조](DT-001-system-architecture.md), [파라미터 저장](DT-004-parameter-sync-persistence.md), [독립 구성](DT-005-device-configuration.md)

Docker 문서는 배포 기술 선택의 근거이며 이 프로젝트의 컨테이너 실행 검증 결과를 대신하지 않는다.
