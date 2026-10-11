"""Record input/output hashes after model integration; does not alter model files."""
import pathlib, hashlib, json, os
root = pathlib.Path(__file__).resolve().parents[1]
model = pathlib.Path(os.environ.get('CHOSUN_MODEL_ROOT', root.parent / 'architecture'))
def meta(path):
    return {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
export_root = os.environ.get('CHOSUN_GAME_EXPORT_ROOT')
export_root = pathlib.Path(export_root) if export_root else None
def source_label(path):
    for base in [root.parent, export_root.parent.parent if export_root else root.parent]:
        try: return str(path.resolve().relative_to(base.resolve()))
        except ValueError: pass
    return path.name
assets = {}
for name, source in [('building.glb', 'building/chosun_main_building.glb'), ('campus.glb', 'campus/campus.glb'), ('shuttle_bus.glb', 'transit/shuttle_bus.glb')]:
    assets[name] = meta(root / 'dist/assets' / name)
    source_path = export_root / name if export_root and (export_root / name).exists() else model / source
    assets[name].update({'source_' + k: v for k, v in meta(source_path).items()})
    assets[name]['source_path'] = source_label(source_path)
nav = json.loads((model / 'campus/navigation.json').read_text())
report = json.loads((root / 'MODEL_PROVENANCE.json').read_text())
report['assets'] = assets
for name, source in [('navigation', 'navigation.json'), ('road_graph', 'road_graph_3d.json'), ('transit_placements', 'transit_placements.json'), ('ground_elevation', 'ground_elevation.json')]:
    report[name] = meta(model / 'campus' / source)
if export_root:
    graded = export_root.parent / 'verification'
    report['baseline_metadata'] = {key: report[key] for key in ['navigation', 'road_graph', 'transit_placements', 'ground_elevation']}
    for key, filename in [('navigation','navigation_graded.json'), ('road_graph','road_graph_3d_graded.json'), ('transit_placements','transit_placements_graded.json'), ('ground_elevation','ground_elevation_graded.json')]:
        source_path = graded / filename
        if source_path.exists():
            report[key] = meta(source_path)
            report[key]['source_path'] = source_label(source_path)
report['material_table'] = meta(root / 'data/game-materials.json')
report['web_compression'] = {name: json.loads((root / 'data' / (name + '-material-application.json')).read_text())['compression'] for name in ['building','campus','shuttle']}
report['web_texture_materials'] = {name: json.loads((root / 'data' / (name + '-material-application.json')).read_text()).get('texturedMaterials', []) for name in ['building','campus','shuttle']}
report['compression'] = 'Meshopt buffer compression. Selected architectural and vegetation geometry uses16-bit position quantization; explicitly listed ground, road, stair, deck and walk-support meshes retain Float32 positions. Source triangle coordinates are preserved for physical support.'
report['full_precision_support_meshes'] = json.loads((root / 'data/campus-material-application.json').read_text()).get('fullPrecisionMeshes', [])
report['material_revision'] = json.loads((root / 'data/game-materials.json').read_text()).get('version')
if export_root:
    report['model_revision'] = 'realism_v2'
    report['materials'] = 'Name-matched final Blender baseColor/roughness/metalness fallback; explicitly tagged image PBR materials retain their image bindings and authored neutral factors. Original instanced tree geometry uses realism-v2 chlorophyll palette and smooth normals. Dense foliage and other procedural render shaders are native-Blender only.'
for key, filename in [('runtime_navigation', 'campus-navigation.json'), ('runtime_vehicle_graph', 'road-graph-3d.json'), ('runtime_walking_graph', 'walking-road-graph-3d.json'), ('runtime_transit_placements', 'transit-placements.json')]:
    if (root / 'data' / filename).exists(): report[key] = meta(root / 'data' / filename)
if (root / 'data/grade-sync-report.json').exists():
    report['grading_sync'] = meta(root / 'data/grade-sync-report.json')
    report['grading_baseline'] = meta(root / 'data/grade-sync-baseline.json')
    report['grading_source_inputs'] = json.loads((root / 'data/grade-sync-report.json').read_text())['source_files']
report['runtime_game_code'] = {name: meta(root / 'dist' / name) for name in ['game.js', 'revision-colliders.js', 'parking-system.js', 'polygon-colliders.js', 'water-constraints.js', 'vehicle-steering.js', 'vehicle-surfaces.js', 'wheel-suspension.js', 'walking-floor.js', 'parking-config.js', 'shuttle-system.js']}
report['game_integration_code'] = {str(p.relative_to(root)):meta(p) for p in sorted((root/'scripts').glob('*')) if p.is_file() and p.suffix in ['.py','.mjs'] and not p.name.startswith('test-')}
report['runtime_world_config'] = meta(root / 'dist/world-config.js')
report['runtime_transit_config'] = meta(root / 'dist/transit-config.js')
if export_root and (export_root / 'manifest.json').exists():
    export_manifest = json.loads((export_root / 'manifest.json').read_text())
    report['native_scene'] = {'source_path': export_manifest['source'], 'sha256': export_manifest['source_sha256']}
    report['source_export_manifest'] = meta(export_root / 'manifest.json')
    report['authoring_phases'] = {key:export_manifest.get(key) for key in ['integration_plan_sha256','bounded_repair_plan_sha256','bounded_repair_base_native_sha256','bounded_repair_status']}
    (root/'data/native-export-manifest.json').write_bytes((export_root/'manifest.json').read_bytes())
    for exported in export_manifest['exports']:
        if exported.get('object_inventory_file'):
            inventory=export_root/pathlib.Path(exported['object_inventory_file']).name
            assert meta(inventory)['sha256']==exported['object_inventory_sha256']
            (root/'data'/('native-export-'+pathlib.Path(exported['file']).stem+'-inventory.json')).write_bytes(inventory.read_bytes())
    report['grounding'] = 'Runtime ground height comes from final exported terrain and foundation triangle raycasts. The coarse elevation grid is reference data only.'
graded_grid = os.environ.get('CHOSUN_GROUND_ELEVATION_PATH')
if graded_grid:
    report['revised_ground_elevation_reference'] = meta(pathlib.Path(graded_grid))
    report['revised_ground_elevation_reference']['source_path'] = source_label(pathlib.Path(graded_grid))
world = json.loads((root / 'dist/world-config.js').read_text().split('export const WORLD = ')[1].rstrip(';\n'))
report['walkable_surface_count'] = len(world.get('walkableSurfaces', []))
report['destination_count'] = len(world['destinations'])
report['controllable_car_count'] = 2 + len(world['extraCars'])
report['npc_count'] = 6 + len(world['extraNPCs'])
for key, filename in [('rose_endpoint_metadata','rose-endpoint-sync-report.json'),('pond_entry_metadata','pond-entry-sync-report.json'),('terrace_driving_alignment_metadata','terrace-drive-alignment-report.json'),('exported_inferred_support_metadata','exported-inferred-support.json'),('it_lower_paving_retirement_metadata','it-lower-paving-retirement-report.json'),('garage_exterior_navigation_metadata','garage-exterior-navigation.json'),('garage_exterior_integration_metadata','garage-exterior-sync-report.json'),('garage_road_boundary_metadata','garage-road-boundary.json'),('final_walking_metadata','walk-alignments-sync-report.json'),('actor_grounding_metadata','actor-grounding-report.json'),('parking_terraces_metadata','parking-terraces-sync-report.json'),('haeoreum_metadata','haeoreum-stair-sync-report.json'),('parking_metadata','parking-gameplay.json'),('rooftop_bridge_metadata','it-rooftop-bridge.json'),('lounge_metadata','it-lounge.json'),('entrance_metadata','entrance-sync-report.json'),('transit_overlay_metadata','transit-alignment-overlay.json'),('public_space_metadata','public-spaces-sync-report.json'),('pharmacy_metadata','pharmacy-sync-report.json'),('hospital_metadata','hospital-sync-report.json'),('campus_access_metadata','campus-access-sync-report.json'),('pond_metadata','pond-sync-report.json'),('football_goal_metadata','football-goals-sync-report.json'),('greenery_metadata','greenery-sync-report.json'),('static_vehicle_metadata','static-vehicle-sync-report.json'),('stop_walkway_metadata','hospital-stop-walkways-sync-report.json')]:
    if (root / 'data' / filename).exists(): report[key] = meta(root / 'data' / filename)
    else: report.pop(key,None)
parking = json.loads((root / 'dist/parking-config.js').read_text().split('export const PARKING = ')[1].rstrip(';\n'))
report['parking'] = {'enabled':parking['enabled'], 'levels':len(parking.get('levelTops', [])), 'decorative_cars':len(parking.get('parkedCars', [])), 'ramps':len(parking.get('rampConnections', []))}
transit = json.loads((root/'dist/transit-config.js').read_text().split('export const TRANSIT = ')[1].rstrip(';\n'))
report['runtime_transit_policy'] = {'notice':transit.get('notice'),'terminalNotice':transit.get('terminalNotice'),'routes':[{'id':r['id'],'terminalStopId':r.get('terminalStopId'),'repeatCirculation':r.get('repeatCirculation',True),'headingSpanMeters':r.get('headingSpanMeters',0)} for r in transit.get('routes',[])]}
(root / 'MODEL_PROVENANCE.json').write_text(json.dumps(report, indent=2) + '\n')
print('Recorded final source and web-asset hashes.')
