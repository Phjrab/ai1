# Hospital, sports and science coverage audit
Verified 2026-10-08. Research outputs only; model and source_data unchanged.

## Add versus keep
- ADD Chosun University Hospital, official campus ID162, OSM way488165875. Existing footprint is source-verified but include=false, absent from campus_coverage.json and actual campus.glb nodes. Official pin lat35.138609 lon126.926673; world(301.433,-801.326). Footprint centroid(287.926,-795.923). Reuse exact existing multi-wing polygon, not a new rectangular substitute.
- KEEP 체육대학 ID132, OSM way468704877. Actual GLB mesh431–434 exists, not merely a coverage claim. Improve facade/massing rather than adding duplicate.
- KEEP 자연과학관 ID130, OSM relation13257660. Actual GLB mesh603–606 exists. Keep inner courtyard hole and original OSM outline. Improve brick facade/height only if needed.
- KEEP 의성관 ID154 way488165874, already present. It is adjacent hospital/research context, not missing main hospital.
- Dental hospital ID166 way493566726 is separate; do not mistake it for requested main hospital. Funeral hall ID171 is also separate and outside the minimal main hospital scope.

## Spatial contract and site
Use original main-building origin35.142722,126.934734, original axes and offsetY8.5 verbatim from hospital_spatial_research.json. Meter scale1.0. No recentering or scaling. Hospital building fits current x[-490,660],y[-1020,240] bounds. Full hospital campus area way485036232 reaches y=-1093.902: if including full polygon, extend world/navigation bounds modestly rather than clipping. Local hospital service roads already modeled/include=true: ways468673479,468673480,479887403,481110610,481110611,481110612,1388264528,1388264530,1388264531,1388264532,1388264533,1443949792. Sidewalks944569953–955 exist. Preserve connections and no duplicate road meshes. Parking areas468689591,468635680,468635682 already included. Official hospital access address is 광주 동구 필문대로365.

## Main hospital exterior guide
Downloaded and visually inspected official photos hospital_intro.jpg and hospital.jpg. Hospital_intro is university's main hospital introduction image, filename2021_photo.jpg (historic image, not assertion of 2026 facade survey). It shows long segmented/curving multi-wing white midrise with green/turquoise glazing, deep blue/cyan horizontal accent bands, white vertical piers, a higher central entrance bay with rooftop hospital sign, broad low translucent greenish glazed entrance canopy, forecourt roadway with islands and adjacent parking. Other campus-map photo shows lower white rectangular annex face with large blue hospital lettering, stepped site and landscaped bank. Do not extrude entire complex to one generic four-storey height. Use lower podium/annex plus taller main wings, approx7–9tiers as photo-based representative massing; exact wing heights remain unverified. Campus-map detail162 only lists1–7; hospital public pages reference8th and west9th floors. Directory is incomplete and not safe evidence that all wings are precisely7storeys. Tag heights approximate and avoid interior layout/patient information.

## Sports exterior guide
Official sports.jpg shows very large rectangular volume, strong white full-height exterior piers and grid, recessed dark green/gray glazing, pale horizontal spandrels, a large light roof/upper hall, and rooftop glazed lantern. Front lower entry colonnade and green-roof low annex visible. Directory132 lists1–11, but photo does not read as eleven conventional identical floors; likely complex floor conventions. Preserve original footprint and avoid blind11x3.6m block. Existing generic4-storey mesh can be visually improved with characteristic tall piers, dark glazing, hall roof, roof lantern and entry columns; mark height approximate pending verified elevations.

## Natural sciences exterior guide
Official science.jpg shows red-brown brick, pale roof coping, regular small dark windows and vertical glazed entry/stair bays with pale frames. Directory130 lists1–5. Existing generic4-floor treatment can be updated to5 with approximate per-floor height, retaining previously verified courtyard topology. Photo cropped perspective does not show every listed level.

## Verified official source URLs
- https://csu.chosun.ac.kr/campusMap/chosun/162/detailView.do (downloaded hospital.html)
- https://csu.chosun.ac.kr/sites/chosun/atchmnfl/building/temp_1555050063752100.jpg (hospital.jpg)
- https://csu.chosun.ac.kr/chosun/245/subview.do (hospital_intro.html)
- https://csu.chosun.ac.kr/sites/chosun/images/contents/2021_photo.jpg (hospital_intro.jpg)
- https://csu.chosun.ac.kr/campusMap/chosun/132/detailView.do (sports.html)
- https://csu.chosun.ac.kr/sites/chosun/atchmnfl/building/temp_1554802746163100.jpg (sports.jpg)
- https://csu.chosun.ac.kr/campusMap/chosun/130/detailView.do (science.html)
- https://csu.chosun.ac.kr/sites/chosun/atchmnfl/building/temp_1554801300432100.jpg (science.jpg)
- https://hosp.chosun.ac.kr/subpage/?mn=367&site=hospital_m (official public access location)
- https://hosp.chosun.ac.kr/bbs/?b_id=hospitalization&mn=182&site=hospital (public west9th-floor reference; no interior detail needed)
- https://hosp.chosun.ac.kr/bbs/?b_id=recruit&mn=224&site=hospital&type=view&w_id=1872 (official8th-floor reference)
- https://www3.chosun.ac.kr/campusMap/chosun/view.do (official site plan and GPS pin provenance)

## OSM provenance
Main footprint https://www.openstreetmap.org/way/488165875 ; hospital site https://www.openstreetmap.org/way/485036232 . Original cached XML and exact converted geometry from /workspace/shared/chosun_campus_refs. ©OpenStreetMap contributors, ODbL1.0, https://www.openstreetmap.org/copyright. Coordinates/community footprints are not surveys. Hospital website menu direct fetch returned502; official university exterior photos and campus-map pages succeeded. No new hospital interior research needed.
