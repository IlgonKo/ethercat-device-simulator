# RF-016 — CiA402 Drive 프로파일 및 F-KR Internal 어댑터

- 등록일: 2026-10-26
- 상태: 범위 합의 / 구현 미착수
- 설계: [DT-007](../Design/DT-007-cia402-profile-adapters.md)

## 범위

공통 CiA402 Drive 프로파일, 기존 CMMT-AS 장치 설명 분리, F-KR Internal 어댑터 및 기존 Model Host 연결. 현재 Motion Server 무수정, CMMT identity와 PDO, 기존 모델 계산·상태 전이·파라미터를 유지한다. 폴더 구조는 DT-007로 확정했다. src/ethercat_slave와 src/functional_model로 분리하며, 기능 모델은 profiles/cia402_drive + adapters + models로 구성한다. 실제 이관은 의존성 조사 후 진행한다.

## 완료 기준

- [ ] 확정 폴더 구조로 이관하고 패키지 import·빌드·Docker 경로를 갱신.

- [ ] 공통 OD·제조사 확장·PDO·identity의 책임과 파일 분리.
- [ ] 어댑터 계약과 지원 기능 정의, 미등록 모델·미지원 조합 거부.
- [ ] 기존 가상 모델 상태 머신 중복 실행 없음 및 축별 OD 값 소유권 확인.
- [ ] 기본값과 저장 파라미터 복원·SDO 적용의 동등성 검증.
- [ ] 1축 및 4축 OD/PDO/모델 상태 독립성, 기존 운전 모드 회귀.
- [ ] 2축/4축 계측 비교 및 실제/가상 혼합 버스 검증. 물리 시험 결과와 오프라인 검증을 구분.
- [ ] Docker 빌드·실행 경로와 사용자 문서 갱신.

FMU 실행·Copley 연결·CMMT FMU는 후속. 범용 EtherCAT identity 및 axis:cia402-drive 설정 전환은 별도 합의. 동적 PDO(RF-014), IO(RF-013), 모델 동작 변경(RF-015)은 포함하지 않는다.
