# Chosun campus transit: original geometry assets

## Files
- `build_transit.py`: deterministic Blender generator. Run `blender -b --python build_transit.py`.
- `transit_assets.blend`: editable source asset scene, roots separated for inspection.
- `shuttle_bus.glb`: conventional white coach, four independent wheel pivots and front steering pivots.
- `shelter_reference.glb`: curved green roof, blue beams, salmon columns, double-sided green moulded bench seats.
- `shelter_education.glb`: second flat-blue-roof type, tall orange rear portal and wooden benches.
- `bus_stop_sign.glb`: photographed monument stop label.
- `bus_stop_generic.glb`: generic campus circulation label; does not falsely repeat the monument name.
- `asset_contract.json`: axes, origins, dimensions, wheel animation, collision shapes, and reconstruction limits.
- `asset_qa.json`: exported mesh/triangle counts. All five assets have zero images/textures.
- `append_transit.py`: append fixed facilities and optional display coach to a campus using a terrain height callback. Awaits a `transit_placements.json` from repaired game graph; deliberately refuses to fabricate fallback coordinates.

## Source and accuracy
1. Monument shelter photograph, official Chosun article, 2021-03-24: https://www3.chosun.ac.kr/bbs/chosun/72/224908/artclView.do . Directly inspected image `shelter_campaign.jpg` establishes canopy shape/colors, columns, seats and circular BUS sign. Approximate dimensions and rear unseen detail are reconstructed.
2. White coach, Ilyosisa news photograph, 2015-04-15: https://www.ilyosisa.co.kr/news/article.html?no=80155 . Directly inspected `bus_library_2015.jpg`. White coach/large dark front glass/rectangular headlights/black mirrors/campus name supported; exact vehicle model, side/rear treatment, dimensions and present-day fleet are unverified. Geometry is a representative historical reconstruction, never a claim of the current fleet.
3. Education shelter, official College of Education photograph dated 2021-03-08: https://edutrain.chosun.ac.kr/atchmnfl/sites/edutrain/atchmnfl/bbs/420/20210308_100310380_31426.jpg . Directly inspected. Blue flat canopy, tall orange portal and wooden benches supported. Approximate dimensions.
4. Official route sequence: https://mall.chosun.ac.kr/chosun/160/subview.do and dated 2023 notice https://csu.chosun.ac.kr/bbs/global/417/250328/artclView.do . Directly inspected route illustration. Monument → Art → Central Library → Engineering 2 → Law/Business → Main north end → Student Union → Monument. Route polyline and curb positions require game-world reconstruction.

These reference photographs are research-only and are not embedded in model materials. 2025 blue autonomous demonstration shuttle was intentionally not treated as the ordinary fleet. Timetable graphics contain schematic lines, not invented operating times. All placement coordinates are representations on the reconstructed terrain, not site-survey positions.

## Integration
Coordinate convention is Blender Z-up, +Y forward. glTF is Y-up, -Z forward. Static furniture fronts face Blender -Y. Import GLBs via Blender glTF importer for correct conversion. Source blend roots are separated for preview, so use the GLBs or reset source root transforms before placement.

Game must remove the `TRANSIT_DISPLAY_BUS` subtree from the static campus before adding moving shuttles. Use the supplied dynamic bus collision dimensions, with slowing/stopping for pedestrians. Furniture must remain outside the drivable lane and existing destination approaches. Do not use the full shelter footprint as a solid collision box: only columns and benches should block movement, retaining the waiting aisle.


## 2026-10-08 livery revision
2025-10-15 민주조선 77쪽 전면/좌측 사진과 2026-05-11 조대신문 6면 후방 사진을 직접 확인해 파란 후방 상승 곡선/흰 상부/학교 슬로건을 재구성. 우측은 대칭 추정이며 세부 차종·실측 치수는 미확인. 새 자료가 이전 2015 도색 설명을 대체한다. 원점·바퀴 피벗·충돌 치수·정류장 배치 계약은 유지.
