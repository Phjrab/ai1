조선대학교 재질 / 렌더 프리셋 모듈

범위
기존 형상에 원본 절차적 PBR 재질과 자연광 표현을 적용하는 모듈입니다. 실측·사진측량 재현이 아니며, 저폴리 나무/단순화된 건물 형상 자체는 바뀌지 않습니다. 외부 이미지 텍스처·HDRI·유료 자산 없음. 개별 건물 도색색은 기존 모델을 기반으로 유지합니다. 버스 도색/문자/표지/발광등 재질은 의도적으로 보존합니다.

Blender 품질
World Position 기반으로 미터 단위 미세 표면을 적용합니다. 흰벽 0.8mm, 콘크리트 1.2mm, 벽돌 1.4mm, 아스팔트 1.7mm의 Bump Distance에 강도 0.25입니다. 실루엣이나 메시를 바꾸지 않습니다. 거친 돌/벽돌/도로와 매끈한 금속/유리의 반응을 분리합니다. 먼 항공샷에서 미세 요철이 안 보이는 것은 정상이며, 거대하고 더러운 얼룩으로 과장하지 않습니다.
유리: 내부가 없는 현 모델에서 불필요한 투시를 피하려 opaque tinted dielectric + clear coat로 근사합니다. 실제 투과유리/실내 재현은 아닙니다. 금속은 metallic 0.92, 도장 금속은 0으로 구별합니다.

통합
1. 모든 최종 기하/버스 도색 통합 뒤 Blender에서 campus_materials.apply_materials() 호출.
2. setup_presentation('catalogue')로 렌더 기본값 설정(기존 lights를 제거하고 프리셋 sun/world 적용).
3. procedural 원본 .blend를 먼저 저장.
4. 게임 GLB는 별도 프로세스/사본에서 game_fallback(json_path) 호출 후 export. 원본 procedural .blend를 폴백 상태로 저장하지 않기.
5. validate_glb_fallback.py GLB_PATH JSON_TABLE_PATH 실행.
apply_pbr_copy.py는 위 순서를 따르며 입력 원본 덮어쓰기를 거부하고 메시/변환 checksum 불변도 확인합니다.
밤/노을 조명 스크립트를 쓸 때는 재질 적용 및 원본 저장 후 시간대 조명 스크립트를 적용해야 합니다. emissive room variants를 만든 뒤 apply_materials를 돌리지 마세요.

렌더 비용
현재 Blender 4.3.2 빌드는 OpenImageDenoise를 지원하지 않습니다. 기본 denoise=False. CPU 2스레드 단일 렌더, persistent_data=False로 연속 출력 뒤 메모리 누적을 억제합니다. 60개 이상 카탈로그를 동시에 실행하지 말고 순차 처리하세요.
- test: 1400×875, Cycles 24 samples, adaptive .06
- catalogue: 1600×1000, 48 samples, adaptive .035. 1400폭 override 가능.
- hero: 2400×1500, 128 samples, adaptive .018
- 최대 bounce 5, diffuse/glossy 3, indirect clamp 3. AgX Medium High Contrast.
조명은 원본 절차적 하늘 gradient + 단일 sun이며 실제 날짜·방위·기상 시뮬레이션이 아닙니다.
건물마다 샘플 및 노출을 직접 점검해야 하며 프리셋만으로 전부 최종 QA를 통과했다고 간주하지 않습니다.

게임 폴백
GLB에 Blender noise/ramp/bump node는 전달되지 않습니다. baseColorLinear(선형 sRGB RGBA), roughness, metalness의 명시적 상수 폴백을 제공합니다. 유리는 opaque roughness .16, metalness 0, transmission 0. clear-coat와 procedural bump는 모바일 기본에서 생략됩니다. 모든 값을 표와 GLB JSON에서 비교해 흰재질 회귀를 검사합니다.
Three.js는 GLTFLoader가 색공간을 처리하므로 baseColorLinear를 다시 sRGB->linear 변환하면 안 됩니다. 수동 Color.setRGB는 linear 값 그대로 사용. 게임 담당자는 opaque MeshStandardMaterial과 저해상도 procedural PMREM environment를 사용할 수 있습니다. HemisphereLight만으로 환경 반사는 생기지 않습니다. 새 텍스처/알파블렌드/전송 패스는 추가하지 않습니다.

공식 기술 근거
https://docs.blender.org/manual/en/3.4/addons/import_export/scene_gltf2.html
https://docs.blender.org/manual/ca/4.3/render/color_management.html
https://threejs.org/docs/pages/MeshStandardMaterial.html
현재 실행 테스트는 Blender 4.3.2에서 검증합니다. 최신 영문 Blender 문서 직접 접근은 오류가 있어 검색 색인/위 공식 버전 문서와 로컬 실행 검증을 함께 사용했습니다.

실측 시험 결과(중간 모델 SHA256 5662152700bdce411785bf2b57c704a4b4322a25c2a954775ca76862f824c372)
1400×875 / 24 samples / CPU 2스레드: 전 51.87초, 후 56.36초. 피크 Blender 메모리 751.57MiB. 원본과 사본의 메시+변환 해시 일치, apply 두번째 호출 변경 0 확인. 실제 GLB 사용 재질 67개의 baseColor/roughness/metalness가 JSON과 일치. 사용하지 않는 재질 1개는 정상적으로 GLB에서 제외.
단순 픽셀·샘플 비례로 1600×1000 / 48 samples를 예산 잡으면 2스레드에서 약 150초/장, 60장 약 2.5시간(추정일 뿐, 최종형상과 카메라 따라 다름). 4~6코어 할당을 높이면 빨라질 수 있으나 여러 작업을 동시에 렌더하지 마세요.

새 사진검수 재질
REVIEW {id} • observed facade: 130/137/140/144/153/155/157/160은 brick, 159는 painted masonry, 기타 observed facade는 stone. REVIEW 접두사의 사진 기반 색을 그대로 유지하고 roughness/micro-bump만 처리합니다. observed glazing도 기존 사진 기반 RGB 보존. parking sky blue cladding, chalk stone, warm yellow entrance, ochre stair cladding, pharmacy ochre stone 및 STAIRS granite/metal 계열 처리.

v1.1 식생 보정
foliage 슬롯에 해당하는 면만 smooth shading 처리합니다. 건물·지형·줄기 면의 hard/smooth 상태는 보존합니다. 정점·면 수 및 좌표 변화를 만들지 않습니다. 기존 수관의 다면체 실루엣/실제 잎 부재는 그대로이며, 음영 경계만 부드러워집니다.
개별 Object Random 0.16 기여 + 약 5.6m 공간주기의 world-position noise로 잎 색/거칠기 변화를 작게 줍니다. 약한 sheen 0.14와 subsurface weight 0.025로 잎광 반응을 완화합니다. GLB에는 해당 효과 대신 지정 평균 상수값과 smooth normals만 전달됩니다. 모바일에서 추가 렌더 패스·텍스처가 없습니다.
주요 비교: after.png(v1.0) 대비 after_vegetation_v11.png(v1.1), 동일 카메라/조명. 초기 before.png 대비 최종 after_vegetation_v11.png가 전체 재질 개선 비교입니다. entrance_before/after.png는 v1.0 본관 근접 검수이며 수목 변화는 거의 포함되지 않습니다.
v1.1 추가 실측: 동일 1400×875 / 24sample / CPU 3스레드 38.43초, 피크761.22MiB. 이 수치는 다른 동시작업 부하에 영향을 받습니다. v1.1에서도 원본 mesh+transform checksum 동일, idempotence 및 사진색/버스제외 계약 테스트 통과.
