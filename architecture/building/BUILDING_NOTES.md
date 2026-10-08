# Chosun University Main Building — original parametric model

## Files
- `chosun_main_building.blend`: editable architectural model, metres, Blender 4.3.2.
- `chosun_main_building.glb`: material-preserving glTF binary export for reuse.
- `build_building.py`: complete deterministic recreation script. Run `blender -b --python build_building.py`.
- `building_contract.json`: bay-by-bay dimensions and geometry statistics.
- `geometry.json`: deliberately simplified collision proxies and representative corridor walk surface for the separate game project.

## Scale and orientation
Blender X follows the facade; front faces negative Y. The bar extends X=-166 to166m, Y=0 to17m. Rounded annexes reach X=±187.5m for the documented375m overall span. Three principal entrances are at X=-135,0,135m. Ground-floor slab top Z=.15m; exterior paving datum Z=0m. Vertical estimates use3.6m typical floor intervals. Tall outer gables peak32.35m, central gable28.15m. These heights are visual estimates, not survey measurements.

## Evidence and limitations
The defining19-gable rhythm is photograph-based: medium/large/medium + five small + medium/central/medium + five small + medium/large/medium. The central historical core is visibly lower than the two tall outer peaks. Rounded terminal pavilions, narrow white-framed windows, pointed attic windows, extra rectangular attic rows at the three major gables, projecting white roof edges and three columned flat entrance canopies are based on exterior photographs.

This is an architectural interpretation, not a surveyed BIM, CAD plan, construction drawing or certified reconstruction. Exact window counts, wall thicknesses, heights, footprint depth, services and rear elevations are approximate. No third-party 3D model or texture was incorporated. The model consists of original procedural geometry and native procedural materials.

Interiors are explicitly separate. Collection03 contains CONCEPTUAL floor slabs and unsurveyed corridor/classroom partitions. Collection04 contains a24m representative corridor with publicly pictured finishes: grey lower walls, terrazzo-style floor, reddish wooden glazed classroom partitions, white window frames and linear ceiling lights. The exemplar location, room arrangement and dimensions are illustrative. No complete verified interior floor plan or upper-floor stair system was available. Ground-floor corridor is continuous; classroom partitions are not a verified accessible floor plan.

## Collections
01 EXTERIOR: photo-informed envelope and fenestration.
02 ROOFS: pitched roofs, seam details, simplified drainage and roof services.
03 INTERIOR: conceptual floor slabs and partitions; independently togglable.
04 CORRIDOR EXEMPLAR: photo-informed finish sample; independently togglable.
05 ENTRANCES: canopies, columns, threshold steps and open central paired door passages.

## References inspected
- Chosun University official main-building history/photos: https://www3.chosun.ac.kr/fund/2217/subview.do
- Academy of Korean Studies / Gwangju cultural platform production-reference photographs: https://dh.aks.ac.kr/~gwangju/wiki/index.php/제작기록:3d-광주조선대학교본관
- University public filming-location booklet corridor photographs, supplied by the research task.

Reference photos are retained only as working research and are not textures in the deliverable. Existing public reconstruction screenshot was used only for comparison; actual photo evidence superseded it where its equal-height major peaks differed.

## Validation
Recreated successfully in Blender4.3.2; saved native file and re-opened in a separate Blender process. All mesh face normals recalculated outward.64 grouped mesh objects, 144,856 vertices, 107,258 polygons. Exterior test render inspected; corrected upper sidewall closures and major attic fenestration. Final scene integration/lighting by parent task.

Representative corridor camera: position(-10,1.6,1.72), target(11,2.1,1.7), approximately24mm lens. Add soft ceiling-area lights around Z=3.2m for interior visualization.

## Independent render review update
Rear ground-floor service elevation revised against the official filming-location booklet rear photo: dark red-brown brickwork, pale blue service doors, dark metal window frames and continuous white slab overhang. Door/window spacing remains estimated. Procedural brick joints are native Blender detail; glTF preserves the base brick color. Front sill projection beyond the wall is approximately105mm, with75mm thickness, avoiding exaggerated slab-like sill shadows. Coordinate contract and accessible front entries are unchanged.
