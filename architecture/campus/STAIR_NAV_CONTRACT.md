# Stair, entrance and rendering contracts

- Coordinates in all JSON files are Blender Z-up metres. Convert to glTF/Three using `[x,z,-y]`.
- `navigation.json.walkableSurfaces` contains original-mesh top surfaces. Every polygon is upward-wound; `triangles` indexes the polygon. `kind` is stairs, landing, ramp, or walkway.
- `pedestrianPaths` contains centerlines, width, step count and maximum absolute riser. These are traversal/regression samples. `smoothTraversal` permits foot-elevation interpolation while individual treads remain visible.
- Building collision boxes use a 2m grid whose four corners lie inside the mapped polygon. Courtyards, the gap between separately mapped buildings, and the space between solar-test huts remain open. Stair tops do not receive solid obstacle boxes.
- Interior access is not claimed. Facade meshes and collision boxes still enclose buildings.
- The final terrain mesh is cut under building volumes and only under approach polygons where a terrain triangle would intersect the walk surface. Retaining skirts close exposed terrain/base edges. These integration walls are unsurveyed construction, explicitly marked as such.
- A photographed stair's exact count is unknown unless stated. The central staircase has 108 individual treads; its width and distribution between landings are estimates. Other approach counts adapt to final modeled grade. The Hwanggeumchu ramp is photo-backed, but its exact gradient is estimated.
- The workshop metal staircase is distinct from the central granite stair and has its own supports and upper connecting landing.
- Original 47 destination IDs remain. Dental hospital, nursery and funeral facility are additional destinations. The solar compound's destination already existed.
- `building_render_catalog.json` has exactly one row per campus coverage record and per building collection (67 at this revision); each includes actual emitted bbox, recommended camera/target, source, uncertainty and approximate entrance coordinate.
- `main_building_catalog.json` describes the separately preserved main-building asset. `professor_annex_catalog.json` is an optional additional crop of its west rounded annex, not another campus-coverage record.

Run `python verify_remaining.py <output-folder>` for original-record preservation, catalog parity, upward winding, stair-height sanity, collision-center checks and the dental split area-conservation test. Geometry/renders and end-to-end game navigation still require visual/runtime QA.
