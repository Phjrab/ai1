# Chosun campus roads and pedestrian crossings

Inspected 2026-10-08 using the assistant's cloud browser and the official public Kakao Map and Naver Map user interfaces. No bulk tile collection, private API or access-control bypass.

## Direct visual evidence

- Kakao Map, search 조선대학교, Skyview latest layer: https://map.kakao.com/?q=%EC%A1%B0%EC%84%A0%EB%8C%80%ED%95%99%EA%B5%90
  - `kakao_campus_latest.png`: main building, student hall, central library, stadium, rose garden and main connecting loops. Satellite/orthophoto attribution visibly Kakao and National Geographic Information Institute.
  - `kakao_main_latest.png`: 30 m scale detail of main-building front, central-library eastern frontage, triangular circulation loop, northern road junction, parking aisles and painted pedestrian crossings. The current mapped centerline shape is broadly consistent in this view, so no unsupported arbitrary realignment or artificial shortcut was added.
  - The layer was labelled latest; a capture month/year was not exposed. The year picker includes 2025 etc., but no dated older layer was successfully selected. Do not call this 2025 photography.
  - Kakao Roadview produced the same temporary-unavailable alert before and after its requested refresh. Not used as street-level evidence.
- Naver streetview: https://map.naver.com/p/search/%EC%A1%B0%EC%84%A0%EB%8C%80%ED%95%99%EA%B5%90?c=15.00,0,0,2,adh&p=x3_CNBBFh-lxLQV8wY0CCg,15.7,-6.3,80,Float
  - Capture date visibly **2026년 03월(최신)**, road label **조선대5길**.
  - `naver_library_crossing_202603.png` and `naver_library_curb_202603.png`: actual zebra crossing at central-library frontage; road, white crossing markings, yellow roadside stripes, granite edge/kerb, red-grey unit paving and longitudinal yellow tactile strip all visible. A crossing landing is visible, but precise kerb rise/run cannot be measured reliably from the panorama.
  - `naver_library_sidewalk_202603.png`: library frontage and raised unit-paved sidewalk. Same date and road label.
  - Previous panorama: https://map.naver.com/p/search/%EC%A1%B0%EC%84%A0%EB%8C%80%ED%95%99%EA%B5%90?c=15.00,0,0,2,adh&p=FWW2uJE5nlYZHRjeCm7yLw,49,10,80,Float

## Source geometry

- Original OpenStreetMap XML: `/workspace/shared/chosun_campus_refs/osm_map.xml`, attributed © OpenStreetMap contributors, ODbL 1.0. Existing campus metric transform retained exactly.
- 41 crossing nodes are linked to included mapped roads. 39 explicitly marked crossings are reconstructed; 2 lacking evidence of markings are retained as skipped records, not given invented zebra stripes.
- `crossings_inventory.json` contains every rendered source node URL, lat/lon, model XY, OSM last-edit timestamp, source roadway ID, derived local crossing direction, width assumptions and tactile tags. An edit date is not a photo or field-survey date.
- Crossing position is sourced. Crossing direction is perpendicular to the local mapped carriageway tangent. The nominal pedestrian crossing width (3.5 m), stripe pitch (~0.95 m), and road widths without a source width tag are estimates. They are not measured dimensions.
- Existing vehicle graph remains 942 nodes / 997 edges with identical XY, widths, connectivity and one-way metadata. No new shortcut, artificial junction or road widening was inferred just to connect the model.

## Implemented

- `road_continuity.py` retains original `roadfeatures` and height callable contracts. Every 3D vertex, nav point and graph elevation is regenerated from the final terrain callback.
- `prepare_road_details.py` creates `road_details_cache.json` (XY only).
- `road_details.py` adds 39 source-positioned white zebra crossings, mapped pedestrian paving 0.06 m above carriageway, and 75 local transition pieces where crossing ends intersect existing mapped pedestrian surfaces. No full new sidewalks are invented. These curb transitions are deliberately tagged schematic/unverified rather than claiming actual accessibility compliance.
- Tactile pads rendered only at source `tactile_paving=yes` crossings with mapped pedestrian surface at the ends (5 source crossings tagged yes). Their exact footprint is approximate.
- Yellow center/edge lines added only on the library road section between its two mapped crossing nodes, visually supported by the 2026-03 streetview; paint width and exact extent remain approximate.
- All paint and pavement are clipped on exactly the existing 5 m terrain triangles. Pavement boundary skirts extend to height minus 0.215 m, enclosing the 0.295 m visual gap above terrain (terrain is height minus 0.20 m). They are neutral paving closures, not verified retaining walls or drive-blocking obstacles.
- New `navigation.json` receives `crossings` with position/metadata and `crossing_limits`; vehicle roads are unchanged in XY. Graph 3D elevations regenerate at the final build.
- Model owner instructed to remove road-overlapping older trees, parking cars and the original arbitrary near-main zebra markings before final integrated export.

## Verification

Standalone Blender 4.3.2 test `test_road_details.py` on prior campus terrain:
- 163,164 surface samples, 0 below terrain.
- 0 degenerate faces after excluding sub-0.1 mm boundary fragments.
- 39 crossing records, 157 added objects including edge closures.
- Minimum surface clearance 0.294878 m; maximum 0.355122 m.
- Skirt bottoms intentionally penetrate terrain by 0.015 m; excluded from roadway-surface clearance test.
- Independent XY audit: painted area outside carriageway 0 m²; pedestrian coverage difference 0.00000491 m²; ramp/pavement overlap 0.000000067 m²; 0 detail faces cross terrain triangle partitions.
- Final modified DSM/roadbed terrain must be verified separately in the model owner's integrated build. Standalone QA is not a claim that the final exported game scene has passed.

Stable XY files:
- road_graph.json SHA-256: 62dcb92d2948a45d1f027f28bb6a8c40d61825ab25319c3e51d353b099c1b4f6
- road_surface_cache.json SHA-256: 99f28bd3ae50a565582e267c47633dddc43676b4617fd37318289068033e407d

## Explicit limits

This is a photo-informed visual reconstruction, not a surveyed road, traffic-control or accessibility model. Satellite views do not establish current legal bus access, widths, slopes, exact lowered kerbs, parking availability or that all markings remain unchanged. The Naver panorama verifies a library-road sample, not all 39 crossings. Unseen crossing geometry remains OSM-derived plus documented modeling assumptions.

## Final central-stair ownership correction (2026-10-08 07:53 UTC)

The model owner's authored 108 stair treads/landings now exclusively own their footprint: four explicit XY rectangles from `road_surface_masks.py` are removed from rendered pedestrian paving only. This removes 97.630 m² from the base pedestrian layer and 97.549 m² from the detailed pedestrian layer, with the remainder in local ramp pieces. Mask/pavement remaining overlap is zero. Vehicle paving, source widths, original paths, source steps IDs and the complete routing graph are unchanged. Both preparation scripts reproduce the exclusion; `apply_stair_surface_mask.py` provides an idempotent local cache update. The base surface hash above describes the pre-exclusion baseline, not the final pedestrian cache. Final independent audits remain passed: paint outside carriageway 0 m², terrain-partition violations 0, pedestrian coverage error <0.000005 m².
