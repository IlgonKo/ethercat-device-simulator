# 폴더 재구조화·정리 검증 — 2026-11-26

상태: **완료 — 경로 이관 및 오프라인 회귀 통과**

## 변경

- [ADR-010](../Design/ADR-010-project-layout.md)에 폴더별 역할·Git 관리·보관 정책을 기록했다.
- 모델 원본을 motor_controller/copley 및 pneumatic_cylinder/double_acting으로 분류했다.
- 빌드는 scripts/models, 재사용 검증은 scripts/validation으로 이동했다.
- Copley upstream.json 분리와 Docker COPY/빌드 참조를 반영했다.
- Windows의 과거 체크아웃은 Git·미커밋 파일·실패 결과까지 외부 보관하고 Linux 기준으로 다시 구성했다.
- OpenModelica는 .cache/toolchains, 다운로드는 .cache/downloads, 검증 결과는 results로 옮겼다.
- acontis 평가판과 Git 전달 bundle·일회성 이관 스크립트는 활성 프로젝트에서 제외하고 외부 보존했다.
- Linux의 기존 native build·개발 가상환경과 운영 state/.env는 유지했다. 작업 전부터 있던 미추적 파일 3개는 수정하지 않았다.

## 검증 결과

| 항목 | 결과 |
|---|---|
| Python 단위 시험 | 57개 실행, 56개 통과 / Windows SDO 의존 시험 1개 제외 |
| Docker C++ CTest | 6개 통과 |
| Docker Copley FMU | 8개 통과, 새 metadata 경로로 원본 재빌드 성공 |
| Docker 동적 PDO·저장/재시작·IPC 지연/종료·4축 motion | Dockerfile의 통합 검사 통과 |
| Linux 실린더 FMI3 | 5개 통과 |
| Windows 실린더 FMI2 | 4개 통과 |
| 웹용 Modelica 소스 생성 | Windows/Linux 새 경로에서 성공 |
| 활성 문서 상대 링크·변경분 공백 검사 | 통과 |

검증 이미지: `ethercat-device-simulator:layout-20261126`. 운영 이미지를 교체하거나
컨테이너를 재시작하지 않았다. 운영 컨테이너 시작 시각은 시험 전후
`2026-11-05T07:48:38.710870571Z`로 동일하다. NIC 물리 시험은 수행하지 않았다.

원본 로그는 Linux `results/layout/20261126`, Windows 결과는 같은 상대 경로에 보관한다.
FMU 요약은 각각 `pneumatic/summary.json`, `windows-fmi2/summary.json`이다.
계산 로직은 유지했고 기본 결과 경로에는 UTC 실행 ID를 추가했다.

## 외부 보관 및 복원 근거

- Windows: `C:/Users/Festo/Documents/ethercat-device-simulator-archive/20261126-layout/`.
  `windows-checkout/`에 이전 Git 및 작업 파일을 보존했다. 선택한 도구/결과의 이동은
  `cache-result-moves.json`, 전체 정리 기준은 `cleanup-manifest.json`에 기록했다.
  `acontis-reference-latest/`에는 최신 Git에 남아 있던 과거 acontis 자료가 있다.
- Linux: `/home/festo/Documents/ethercat-device-simulator-archive/20261126-layout/`.
  `baseline.tar`, `status-before.txt`, `moves.json`, `acontis-reference/`를 보관한다.

실패 결과를 일괄 폐기하지 않았다. 추가 보관 기간/삭제 정책은 별도 결정한다.
검증 완료한 재구조화 변경을 저장소 이력으로 관리한다.
