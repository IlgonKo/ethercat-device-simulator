# RF-017 — Copley 물리 PP·파라미터 효과 검증 (2026-11-03)

- 문서 유형: **검증 기록**
- 판정: Copley 1축의 물리 PP 절대/상대 이동, 속도·동일 가감속 설정 효과 및 다른 가상축 유지 확인.
- 관련: [RF-017](../../RF/RF-017-copley-fmu.md)

## 구성·범위

Windows Motion Server basic/PP 4ms, 실제 축·IO + F-KR 2축/Copley 2축 혼합 버스. Master Axis 3 = virtual-axis-2 = Simulator local 2의 Copley에만 명령을 보냈다. 전 축 속도 0·trajectory/homing idle·WKC 18/18 확인 후 사용자가 Panel 조작권을 해제했다. 시험 클라이언트가 조작권을 얻어 수행했다. 실제 축에 이동/Reset/Enable/파라미터 명령을 보내지 않았다.

최초 Enable 단독 요청은 API success였으나 Statusword 0x8250에서 Operation Enabled로 전환되지 않았다. manualCW는 basic 모드 advanced_only로 거부됐다. 두 사전 시도 모두 이동 없이 설정을 복원하고 조작권을 반환했다. 이후 기존 axis/fault_reset(Shutdown→Switch On 포함) → Enable 경로로 정상 전환하여 시험했다. Enable 단독 성공으로 기록하지 않는다. 실행 코드/서버 설정은 바꾸지 않았다.

## 결과

위치는 mm, 속도 mm/s, 가감속 mm/s²의 API 단위다. 도달 시간은 요청 직전부터 위치 오차 ≤0.002mm·속도 ≤0.01을 연속 3회 확인한 구간의 첫 표본까지의 호스트 시간이다. API 왕복·샘플링 지연을 포함하며 정밀 제어주기 계측은 아니다.

| 시험 | 시작→목표 | 속도 | 가속=감속 | 최종 위치 | 도달 시간 | 관측 최고 속도 |
| --- | --- | --- | --- | --- | --- | --- |
| absolute_10 | 0→10 | 10 | 500 | 10.000 | 1.041s | 10.0 |
| relative_minus_4 | 10→6 | 10 | 500 | 6.000 | 0.452s | 10.0 |
| velocity_20 | 0→10 | 20 | 500 | 10.000 | 0.566s | 20.0 |
| acceleration_20 | 0→10 | 20 | 20 | 10.000 | 1.465s | 14.0 |
| acceleration_100 | 0→10 | 20 | 100 | 10.000 | 0.741s | 20.0 |

상대 이동은 Motion Server move_rel API로 요청했으며 서버가 절대 목표값으로 계산해 PP에 전달한다. 따라서 FMU의 relative Controlword bit 자체를 물리 wire에서 시험한 결과는 아니다. 해당 bit의 기존 오프라인 시험과 구분한다.

- 복귀 포함 9회 이동, 486개 상태 표본에서 WKC 불일치 0, 이동 중 축 Fault 없음.
- 비대상 가상축 Axis 1/2/4의 위치 변화는 모두 0. 실제 축 Axis 0 피드백 변동은 최대 약 0.001mm였으며 실제 축 명령을 보낸 것은 아니다.
- 속도 10→20에서 동일 10mm 이동이 1.041→0.566초. 가감속 20→100에서 1.465→0.741초로 바뀌었다. 독립적인 감속만 변경한 시험은 아니며 Copley의 동일 가감속 계약을 따른다.
- 순차 SDO 가감속 갱신 후 상태 표본에서 Fault는 관측되지 않았다. 전수 프레임 캡처나 트랜잭션 원자성 보장은 아니다.

## 복원·종료

위치 0으로 복귀하고 Profile Velocity 100, 가속/감속 500으로 복원했다. 실제 SDO 0x6081/0x6083/0x6084 readback = 100/500/500 확인. 영구 저장 명령은 보내지 않았다. 목표축은 Disable 후 Statusword 0x8233(Operation Enabled 해제), 전 축 속도 0·Fault 없음, 버스 normal/WKC 18/18이었다. 조작권 owner=null 확인.

초기의 Switch On Disabled와 종료의 Switched On은 같은 상태는 아니며, 종료 시 Operation Enabled가 해제된 것을 확인했다. 다른 축의 제어 상태 복원을 위해 추가 명령을 보내지 않았다.

## 증거 및 잔여

Linux ignored build/diagnostics/rf017-motion-20261103의 before.json, original.json, motion-results.json, after.json, summary.json, enable-precheck.json, manual-controlword-precheck.json, rf017-motion.py.

이 시험은 Copley 1축의 기능 검증이다. 혼합 4축 동시 이동·장시간 성능 및 현 구조 2축/4축 계측은 아직 남는다. 두 번째 Copley 축 전체 반복 시험이나 다른 주기/모드의 결과로 확대하지 않는다.
