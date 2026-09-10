# EtherCAT Device Simulator

Software-based EtherCAT device simulation, starting with CMMT drives and reusable CiA 402 models.

The intended architecture connects a PySOEM master over EtherCAT to a software ESC and slave communication stack, with device behavior provided by our existing object dictionary and CiA 402 modules.

KickCAT is the initial candidate for the software ESC and slave stack. Integration and PySOEM interoperability are pending validation.

## 프로젝트 문서

- [설계 및 진행 계획](docs/project-plan.md): 목적, 합의한 구성, 책임 경계, 검증 단계, 후보 조사 결과

현재 합의한 실행 구성은 **Ubuntu Docker의 Motion Server/PySOEM ↔ 실제 EtherCAT 케이블 ↔ Windows의 KickCAT 기반 시뮬레이터**입니다. 아직 빌드 및 통신 검증 전입니다.
