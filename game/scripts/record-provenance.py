"""Record input/output hashes after model integration; does not alter model files."""
import pathlib, hashlib, json, os
root = pathlib.Path(__file__).resolve().parents[1]
model = pathlib.Path(os.environ.get('CHOSUN_MODEL_ROOT', root.parent / 'architecture'))
def meta(path):
    return {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
assets = {}
for name, source in [('building.glb', 'building/chosun_main_building.glb'), ('campus.glb', 'campus/campus.glb'), ('shuttle_bus.glb', 'transit/shuttle_bus.glb')]:
    assets[name] = meta(root / 'dist/assets' / name)
    assets[name].update({'source_' + k: v for k, v in meta(model / source).items()})
nav = json.loads((model / 'campus/navigation.json').read_text())
report = json.loads((root / 'MODEL_PROVENANCE.json').read_text())
report['assets'] = assets
for name, source in [('navigation', 'navigation.json'), ('road_graph', 'road_graph_3d.json'), ('transit_placements', 'transit_placements.json'), ('ground_elevation', 'ground_elevation.json')]:
    report[name] = meta(model / 'campus' / source)
report['material_table'] = meta(root / 'data/game-materials.json')
report['walkable_surface_count'] = len(nav.get('walkableSurfaces', []))
(root / 'MODEL_PROVENANCE.json').write_text(json.dumps(report, indent=2) + '\n')
print('Recorded final source and web-asset hashes.')
