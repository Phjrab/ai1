# Chosun campus terrain evidence and modeling decision

Access date: 2026-10-08. The model now uses the broad elevation trend from a public digital surface model (DSM), with known mapped roofs masked and interpolated. It is **not a surveyed bare-earth model**. No individual stair riser, retaining wall, entrance sill or floor elevation was measured by this dataset.

## Source and rights
- Source tile: https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N35_00_E126_00_DEM/Copernicus_DSM_COG_10_N35_00_E126_00_DEM.tif
- Dataset publisher listing: https://registry.opendata.aws/copernicus-dem/
- Data specification: https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM
- License: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf
- Public GLO-30 AWS 2021 release, GeoTIFF Float32, 3600 × 3600, 1 arcsecond: approximately 25.3m east-west × 30.9m north-south at this site.
- Horizontal: WGS84 geographic coordinates. Vertical: EGM2008 orthometric meters. Pixel-is-point.
- Original measurements primarily TanDEM-X 2011–2015; historical surface and canopy changes are possible.
- The public downloadable tile did not require a login or explicit legal-acceptance click. Distribution/use follows the linked license and attribution requirement.

Required adapted-data credit:
produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved

Mapped footprint masks use OpenStreetMap contributors' geometry under ODbL 1.0; see the existing campus footprint attribution.

## Reproducible processing
1. Preserve the source tile and SHA-256 in terrain_source_samples.json / campus/source_data/terrain/elevation_grid.json.
2. Read a 72×93 source-pixel campus crop.
3. Mask every mapped building footprint plus an 18m margin, including the original main building. This removes 429 source pixels. Fill these cells by inverse-distance weighting of 8 unmasked neighbors.
4. Smooth with a 1-source-pixel Gaussian. This suppresses structure-scale effects but cannot guarantee removal of unmapped buildings or tree canopy.
5. Reproject/sample in the existing rotated campus frame on a 10m storage grid. This finer grid adds no source resolution.
6. Use the median masked/smoothed DSM height at five front-apron samples (x=-80,-40,0,40,80; y=-25) as the relative datum: 109.84023m EGM2008. This is a model normalization choice, **not a surveyed floor height**. Never anchor the model floor to the raw DSM roof sample at the main building (120.0767m).
7. Keep the existing detailed main site exact inside x±235m,y[-128,123]. Blend to the source-backed trend over 150m with smoothstep. This deliberate constraint preserves the main model, original 108-stair route, and surrounding authored objects.
8. Building pads flatten to independently derived building bases and blend with surrounding terrain over 12–65m depending on footprint relief. Footprints, not bounding boxes, determine the distance. The blend is order-independent. Roof/floor heights are added separately, never interpreted from DSM elevation.
9. Final build retains the existing 5m triangular ground sampling. Roads, paint, navigation, objects and transit must use this FINAL padded/triangulated surface, not the unpadded DSM trend.

## Representative source and model values
See terrain_source_samples.json for all included buildings. Raw DSM values are surface elevations, not measured ground.
- Main building: raw DSM 120.077m; model floor remains 0.
- Main athletic field: raw DSM 59.161m; approximate model terrain -51.511m.
- First engineering building: raw DSM 58.558m; approximate base before pads -50.659m.
- University hospital: raw DSM 88.075m; approximate base before pads -31.959m.
- Dentistry education building: raw DSM 64.246m; approximate base before pads -50.943m.
- Dentistry research building: raw DSM 62.016m; approximate base before pads -52.749m.
Building footprint centers used by the final massing builder can differ slightly from official pin centers listed above.

## Files / regeneration
- campus/prepare_terrain_elevation.py: run /usr/bin/python3; needs system GDAL, NumPy, SciPy and the downloaded source tile at this folder's N35E126.tif.
- campus/terrain_elevation.py: pure Python runtime sampler, pad API and final ground exporter.
- campus/source_data/terrain/elevation_grid.json: portable sampled trend and provenance, no GDAL dependency at build/runtime.
- campus/audit_terrain_elevation.py: standalone and final-ground consistency audit.
- terrain_validation.json: current audit status. Final integration road, entrance and transit checks must be rerun after final build.

Validation before integration: 0 non-finite samples; exact core preservation (max error 0m); no core seam discontinuity (2mm crossing gives <0.001m difference); reverse pad order changes result by 0m. These checks are numerical consistency tests, not assertions of survey accuracy.

## Road-corridor corrections and foundations
The DSM trend plus preservation transition and building pads initially produced >45% road slopes. These are not accepted as actual road grades. `campus/terrain_roadbeds.py` subdivides the existing vehicle graph at ≤4m, projects adjacent-node height differences toward a 14% modeling target outside the retained core, and adds local compatibility constraints between road samples within 12m. No centerline XY, width or road connectivity is changed. The detailed core is fixed, with a 29% interface allowance because its original approach is already steep. It then blends the adjusted roadbeds into surrounding terrain over 20–60m beyond the full road corridor. This is explicit game/model earthwork, not a claim about surveyed road construction.

Corrections by OSM road ID and maximum vertical adjustment are recorded in roadbed_corrections.json. A pre-integration test using the builder's actual footprint/pad assembly, 2m road samples and the final 5m triangular sampler yields maximum vehicle grade 27.6816%, entirely in the preserved main-site approach; no sampled segment exceeds 30%. Changes to footprints require this test to be rerun. The result is continuity/traversability QA, not driving-safety certification.

Road grading takes priority near building boundaries; otherwise the 5m mesh would create sharp steps where road and building edge are only 3m apart. Building floors stay separate and retain their assigned relative elevation. Foundation offsets are recorded in foundation_terrain_offsets.json. The renderer uses `terrain_cutouts.py` to subtract exact building footprints from each terrain triangle so hills do not pass through interiors. Building perimeter retaining/foundation skirts must bridge both exposed downhill foundations and uphill abutments. These are inferred/model-designed closures; their exact wall heights are not surveyed.

## Final pedestrian refinement
A second `Roadbeds` layer on the walking graph uses a 32% target, with the detailed main site and vehicle road-support strip locked. In the 67-building test this preserves the vehicle maximum 27.6816% while reducing the worst source footpath gradient from 131% to 66.2%. A graph/terrain modeling target is not an accessibility or safety certification.

`terrain_walksteps.py` adds explicitly inferred game-terrain connectors to the remaining >35% pedestrian segments, outside the detailed main site. They are **not photographs or surveys of real stairs**, and are kept in a separate named object and metadata from photo-backed stairs. The pre-integration test creates 17 connectors with 181 treads and 34 approach surfaces. All 215 walkable polygons have upward winding and finite vertices. Tread corners clear the underlying modeled ground by at least 0.1469m. Source centerlines, original destinations and vehicle connectivity are not changed. The final builder cuts these walk surfaces out of terrain and adds retaining side closures.

Courtyard preservation was separately tested: building mask = outer footprint minus holes. Blender's full-campus footprint subtraction agrees with independent Shapely area to 0.005m² (Float32 triangulation tolerance). Degenerate mask triangles are explicitly rejected to avoid duplicated courtyard terrain faces.

Freeze validation of inferred connectors: maximum adjacent centerline vertical step 0.1666402m; maximum XY centerline gap 1.42e-14m (floating-point zero). The builder must place inferred connectors in their own `CAMPUS 07 | INFERRED GAME terrain connectors` collection, separated from photo-backed stairs. Frozen source modules: terrain_elevation.py, terrain_roadbeds.py, terrain_cutouts.py and terrain_walksteps.py. Final exported asset validation remains a separate integration step.

## Final integrated candidate audit
The latest integrated `review_build` export has been checked (ground SHA-256 `4cf2273a7a9711ff52bade91dbb38444c08d213864f8925e3d1102465ce1840a`). `final_integrated_terrain_validation.json` records 7,654 vehicle segments, none >30%; all 50 destinations above their corresponding final ground; 0 out-of-bounds road samples; 0 non-finite walkable vertices; and all 17 inferred connectors present with the same validated maximum riser and ground clearance. The actual saved Blender scene was opened and its separate inferred-connector collection, explicit evidence disclaimer, 1,720 vertices and 1,290 faces were verified. Runtime shuttle/wheel support and full player traversal are the game integration team's separate checks.
