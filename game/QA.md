# 검증 범위

실제 Three.js GLB/Meshopt 디코딩과 게임 함수의 Node 통합 회귀입니다. DOM·렌더러는 모의 객체이며 브라우저 화면 검사나 GPU 벤치마크가 아닙니다.

## 현재 확인한 항목

- 최종 자산 SHA256과 원본 대응은 MODEL_PROVENANCE.json에 기록
- 50개 목적지 안전 도착, 19명 NPC, 11대 탐험 차량
- 실제 animate 72개 시점에서 NPC 19명 중첩 0, 차량 11대 각각 탑승·주행·제동·하차 통과
- 본관 진입·복도 벽, NPC 대화, 차량 탑승·운전·제동·하차·복구
- 942개 노드/997개 실제 차량 도로 간선과 본관 앞뒤 주차 포장 2개 사용. 제거된 하단·양끝 옛 도로는 주행 영역에서 제외
- 셔틀 실제 update 함수 1,200초: 두 대 모두 2회 순환, 모든 7개 정류장 방문, 영구 정지 없음
- 전체 노선 약 0.25m 간격 9,501개 표본에서 정적/동적 장애물 중첩 0
- 셔틀 앞뒤 바퀴 접지 기반 pitch/roll. 경로 최대 경사 약 27.75%, 검사한 바퀴 접지 오차 최대 0.078m
- 자동 셔틀 2대는 정적 전시 버스와 중복 표시하지 않음. 게임 전용 통행 정리 내역은 tests/shuttle-live-results.json 참고
- 435개 보행면의 삼각형 지지 높이와 24개 접근 경로 양방향 실제 보행 모두 통과. 겹친 보행면은 전체 명시 면의 위쪽 표면을 삼각형 보간해 기대 높이로 사용

## 재실행

- npm test
- node tests/actors.mjs
- node tests/shuttle.mjs
- node tests/shuttle-live.mjs
- node tests/transit-integration.mjs
- node tests/vehicle-grounding.mjs
- node tests/walkable-paths.mjs

## 미검증

실제 WebGL 렌더링, 데스크톱/모바일 뷰포트의 시각 품질, 마우스 잠금의 브라우저별 동작, 실기기 터치, FPS/GPU 메모리, 브라우저 WebMCP 실행은 검증하지 못했습니다. 현재 환경의 Chromium Unix 소켓 및 브라우저 로컬 미리보기 접근 제한을 우회하지 않았습니다.

모바일 기본값은 pixel ratio 1.15, 실시간 그림자 끄기, 먼 장식 수목/차량 거리 숨김입니다. 실제 iPhone 성능을 보증하지 않습니다.
