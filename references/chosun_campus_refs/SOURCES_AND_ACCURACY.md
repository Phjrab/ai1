# Chosun University main-campus spatial data

Retrieved 2026-10-08 UTC.

## Official landmarks
54 named location entries were extracted from https://www3.chosun.ac.kr/campusMap/chosun/view.do (saved official_geo.html). The illustrated map at https://www3.chosun.ac.kr/campusMap/chosun/view2.do provides visual relationships and names, but its illustration is NOT a metric footprint survey. Current official names include IT융합대학, 사회과학ㆍ사범대학, 미술대학(미술관), 학생회관(동아리연합회), 서석홀(평생교육원,박물관), 공과대학 제1공학관/제2공학관, 글로벌하우스/백학학사, 중앙도서관.

## OpenStreetMap
© OpenStreetMap contributors. ODbL 1.0: https://www.openstreetmap.org/copyright and https://opendatacommons.org/licenses/odbl/1-0/
Source: https://api.openstreetmap.org/api/0.6/map?bbox=126.924,35.134,126.938,35.148
Raw response: osm_map.xml. University outline: https://www.openstreetmap.org/way/468689587 .
Exported 537 spatial features, including 66 building geometries (some associated facilities flagged excluded), 286 highway/path geometries, 185 other areas. OSM mapped buildings remain incomplete for several official pins, including parking building and Green Village.

## Transform and limits
The main official pin is latitude35.142722 longitude126.934734, not the earlier AKS coordinates near the rose garden. Existing main model is preserved. The unscaled local frame is anchored at (0,8.5), with positive x toward south-southeast and positive y toward east-northeast. Axis vectors in east/north coordinates are x=(0.19870281,-0.98005979), y=(0.98005979,0.19870281). Directions derive from PCA of the OSM main footprint. Metric planar approximation, navigation pins, traced footprints and illustrative heights must not be presented as survey-grade.

No elevation survey or measured building heights were obtained. Footprints are factual map geometries; exterior colors, facade massing and levels may be supported separately by photographs; terrain heights are inferred. Preserve attribution when distributing the site and comply with ODbL for distributed derived database. University photographs/maps are reference-only copyrighted material and were not relicensed by this extraction.

## Main-model overlap
Do not extrude main way190176334; the existing main model is authoritative for this task. Professor-research round tower190176326 and south round tower471778461 correspond to terminal components already modeled. Flags preserved_main_model_component identify these.

## Multi-part buildings
Baekhak dormitory comprises north/male472263773 and south/female472263774. Aerospace and naval engineering use468704892 and468704895. Natural sciences relation13257660 has an inner courtyard hole. Official medical research building 의성관 remains part of university massing even though its OSM centroid overlaps hospital land.
