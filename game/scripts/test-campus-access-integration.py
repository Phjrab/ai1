#!/usr/bin/env python3
"""Isolated metadata/graph fixtures; no Blender, Node, or live export writes."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SPEC = importlib.util.spec_from_file_location("campus_access", HERE / "integrate-campus-access.py")
ACCESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ACCESS)
REALISM = Path(os.environ.get("CHOSUN_REALISM_ROOT", ROOT.parent / "realism_v2"))
SCHOOLS = REALISM / "affiliated_schools/overlay.json"
GATES = REALISM / "gates_access/overlay.json"
BOUNDARIES = SCHOOLS.with_name("source_geometry.json")


def read_world(root):
    return json.loads((root / "dist/world-config.js").read_text().split("export const WORLD = ")[1].rstrip(";\n"))


class CampusAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="campus-access-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "dist").mkdir()
        (self.root / "data").mkdir()
        self.gates = json.loads(GATES.read_bytes())
        self.schools = json.loads(SCHOOLS.read_bytes())
        self.graph = json.loads((REALISM / "verification/road_graph_3d_graded.json").read_bytes())["vehicle"]
        # Preserve real IDs/coordinates for the toll and its unspecified side
        # junction, plus school route endpoint nodes. Exclude unrelated edges.
        ways = {p["direction_source"].rsplit("/", 1)[1] for g in self.gates["toll_gates"] for p in g["lanes"]}
        self.graph["edges"] = [e for e in self.graph["edges"] if str(e.get("osm_id")) in ways | {"399365553"}]
        roads = [{"name": "CAMPUS_ROAD " + e["osm_id"], "osm_id": e["osm_id"], "width": e["width"],
                  "points": [self.graph["nodes"][e["a"]], self.graph["nodes"][e["b"]]]} for e in self.graph["edges"]]
        roads.insert(0, {"id": "unchanged_road", "name": "Elsewhere", "width": 5, "points": [[400, 100, 10], [450, 100, 10]]})
        self.nav = {"bounds": {"min": [-490, -1120, -80], "max": [660, 240, 110]}, "roads": copy.deepcopy(roads),
                    "pedestrianPaths": [{"id": "unrelated_walk", "points": [[500, 0, 0], [550, 0, 0]]}],
                    "walkableSurfaces": [{"id": "existing_support", "keep": "exact"}],
                    "collisionPolygons": [{"id": "unrelated_obstacle", "polygon": [[1, 1], [2, 1], [1, 2]], "min_z": 0, "max_z": 2}],
                    "landmarks": [{"id": "174", "label": "Keep arrival", "position": [-500, -150, -36]}]}
        self.world = {"bounds": {"minX": -487, "maxX": 657, "minZ": -237, "maxZ": 1117},
                      "roads": [{**r, "points": [ACCESS.cv(p) for p in r["points"]]} for r in roads],
                      "pedestrianPaths": [{"id": "unrelated_walk", "points": [[500, 0, 0], [550, 0, 0]]}],
                      "walkableSurfaces": copy.deepcopy(self.nav["walkableSurfaces"]),
                      "extraNPCs": [{"position": [i, 0, 0], "label": str(i)} for i in range(19)],
                      "extraCars": [{"position": [i, 0, 2], "yaw": .3} for i in range(11)],
                      "shuttles": [{"id": "s1"}, {"id": "s2"}],
                      "collisionBoxes": [{"min": [1, 0, 1], "max": [2, 2, 2], "label": "Keep existing collision"}],
                      "destinations": [{"id": "174", "label": "Keep arrival", "position": [-500, -36, 150]}],
                      "siteAsset": "campus.glb", "walkingAccessZones": [{"id": "keep"}]}
        self.write_inputs()

    def write_inputs(self):
        (self.root / "dist/world-config.js").write_text("// isolated fixture\nexport const WORLD = " + json.dumps(self.world) + ";\n")
        (self.root / "data/campus-navigation.json").write_text(json.dumps(self.nav))
        (self.root / "data/road-graph-3d.json").write_text(json.dumps(self.graph))

    def run_integration(self, **kwargs):
        return ACCESS.integrate(SCHOOLS, GATES, self.root, **kwargs)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_dry_run_has_no_filesystem_effect(self):
        before = self.snapshot()
        report = self.run_integration(dry_run=True)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(report["addedCollisionPolygons"], 30)
        self.assertEqual(report["addedSchoolSegments"], 52)
        self.assertEqual(report["addedDirectedGateLanes"], 4)

    def test_actor_preservation_and_idempotent_game_navigation_graph(self):
        first = self.run_integration()
        world = read_world(self.root)
        nav = json.loads((self.root / "data/campus-navigation.json").read_bytes())
        graph = json.loads((self.root / "data/road-graph-3d.json").read_bytes())
        for key in ("extraNPCs", "extraCars", "shuttles", "collisionBoxes", "siteAsset", "walkingAccessZones", "walkableSurfaces"):
            self.assertEqual(world[key], self.world[key], key)
        self.assertEqual(nav["landmarks"][:len(self.nav["landmarks"])], self.nav["landmarks"])
        self.assertEqual(world["destinations"][:len(self.world["destinations"])], self.world["destinations"])
        self.assertTrue(any(str(d["id"])=="175" for d in world["destinations"]))
        self.assertEqual(world["roads"][0], self.world["roads"][0])
        self.assertEqual(nav["collisionPolygons"][0], self.nav["collisionPolygons"][0])
        self.assertEqual(graph["nodes"][:len(self.graph["nodes"])], self.graph["nodes"])
        before = self.snapshot()
        repeated = self.run_integration()
        after = self.snapshot()
        for key in before:
            if key != "data/campus-access-sync-report.json":
                self.assertEqual(after[key], before[key], key)
        self.assertEqual(repeated["addedMappedGateMerges"],1)
        self.assertNotIn("gate_junction_unspecified", [i["kind"] for i in repeated["issues"]])
        self.assertFalse(first["finalGLBHeightSampling"]["sampled"])

    def test_collision_polygon_coordinates_and_heights_remain_exact(self):
        self.run_integration()
        world = read_world(self.root)
        polygons = {p["id"]: p for p in world["collisionPolygons"]}
        for original in self.schools["obstacles"] + self.gates["obstacles"]:
            collider = polygons[original["id"]]
            self.assertEqual(collider["polygon"], [[x, -y] for x, y in original["polygon"]])
            self.assertEqual(collider["minY"], original["min_z"])
            self.assertEqual(collider["maxY"], original["max_z"])
            self.assertTrue(collider["preciseVehicle"])
            self.assertEqual(collider["type"], "solid")

    def test_school_extents_and_only_supplied_segments_are_added(self):
        self.run_integration()
        world = read_world(self.root)
        nav = json.loads((self.root / "data/campus-navigation.json").read_bytes())
        boundaries = json.loads(BOUNDARIES.read_bytes())
        points = [p for school in boundaries["schools"] for p in school["boundary"]]
        for segment in self.schools["navigation_segments"]:
            radius = segment["width"] / 2
            for x, y, _ in (segment["from"], segment["to"]):
                points.extend([[x - radius, y - radius], [x + radius, y + radius]])
        b = world["bounds"]
        self.assertLess(b["minX"], self.world["bounds"]["minX"])
        self.assertGreater(b["maxX"], self.world["bounds"]["maxX"])
        self.assertEqual(b["minZ"], self.world["bounds"]["minZ"])
        self.assertEqual(b["maxZ"], self.world["bounds"]["maxZ"])
        for x, y in points:
            self.assertLessEqual(b["minX"], x)
            self.assertGreaterEqual(b["maxX"], x)
            self.assertLessEqual(b["minZ"], -y)
            self.assertGreaterEqual(b["maxZ"], -y)
        self.assertGreater(b["minX"], -600)
        self.assertLess(b["maxX"], 860)
        self.assertEqual(nav["bounds"]["min"][0], b["minX"])
        self.assertEqual(nav["bounds"]["max"][0], b["maxX"])
        records = [r for r in nav["roads"] if r.get("kind") == "school_access"]
        self.assertEqual(len(records), len(self.schools["navigation_segments"]))
        for record, source in zip(records, self.schools["navigation_segments"]):
            self.assertEqual(record["points"], [source["from"], source["to"]])
            self.assertEqual(record["width"], source["width"])
            self.assertEqual(record["oneway"], "unknown")

    def test_gate_branches_obey_directions_and_avoid_solid_booths(self):
        self.run_integration()
        nav = json.loads((self.root / "data/campus-navigation.json").read_bytes())
        graph = json.loads((self.root / "data/road-graph-3d.json").read_bytes())
        lanes = {lane["id"]: lane for gate in self.gates["toll_gates"] for lane in gate["lanes"]}
        gates = {gate["id"]: gate for gate in self.gates["toll_gates"]}
        records = [r for r in nav["roads"] if r.get("kind") == "directed_gate_lane"]
        self.assertEqual(len(records), 4)
        for road in records:
            source, gate = lanes[road["id"]], gates[road["gate_id"]]
            self.assertEqual(road["oneway"], "yes")
            self.assertEqual(road["points"][ACCESS.TOLL_APPROACH_M], [*source["center_xy"], source["ground_z"]])
            self.assertEqual(len(road["points"]),2*ACCESS.TOLL_APPROACH_M+1)
            self.assertLess(math_distance(road["points"][1][:2],road["points"][0][:2]),1.3)
            for a, b in zip(road["points"], road["points"][1:]):
                self.assertGreaterEqual(ACCESS.dot([b[k] - a[k] for k in (0, 1)], source["direction_xy"]), -1e-7)
                for obstacle in self.gates["obstacles"]:
                    self.assertFalse(ACCESS.segment_hits_polygon(a, b, obstacle["polygon"]), (road["id"], obstacle["id"]))
            for p in road["points"]:
                self.assertLessEqual(abs(ACCESS.coordinates(p, gate)[0]), ACCESS.TOLL_APPROACH_M + 1e-7)
        owned = [e for e in graph["edges"] if e.get("lane_id")]
        self.assertEqual(len(owned), 8*ACCESS.TOLL_APPROACH_M)
        for edge in owned:
            a, b = graph["nodes"][edge["a"]], graph["nodes"][edge["b"]]
            self.assertEqual(edge["oneway"], "yes")
            self.assertGreaterEqual(ACCESS.dot([b[k] - a[k] for k in (0, 1)], lanes[edge["lane_id"]]["direction_xy"]), -1e-7)
        # Original selected carriageway edges no longer cross the toll strip.
        for edge in graph["edges"]:
            if edge.get("integrationSource") == ACCESS.OWNER:
                continue
            for gate in self.gates["toll_gates"]:
                if str(edge.get("osm_id")) in ACCESS.gate_way_ids(gate):
                    self.assertIsNone(ACCESS.local_interval(graph["nodes"][edge["a"]], graph["nodes"][edge["b"]], gate))

    def test_paved_yard_connection_joins_only_exact_mapped_school_endpoints(self):
        report=self.run_integration()
        self.assertEqual(len(report['inferredPavedYardConnections']),1)
        road=report['inferredPavedYardConnections'][0]
        self.assertEqual(road['sourceOsmIds'],['1108554463','1366486348'])
        self.assertEqual(road['oneway'],'unknown')
        graph=json.loads((self.root/'data/road-graph-3d.json').read_bytes())
        nodes=[]
        for point,way in zip([road['points'][0],road['points'][-1]],road['sourceOsmIds']):
            matches=[i for i,p in enumerate(graph['nodes']) if math_distance(p,point)<1e-6]
            self.assertEqual(len(matches),1);nodes.append(matches[0])
            self.assertTrue(any(str(e.get('osm_id'))==way and matches[0] in [e['a'],e['b']] for e in graph['edges']))
        self.assertTrue(any(all(n in component for n in nodes) for component in graph['components']))
        self.assertEqual(read_world(self.root)['walkableSurfaces'],self.world['walkableSurfaces'],'The yard connection creates no invisible paving or support')

    def test_missing_gate_anchor_fails_before_writes(self):
        self.graph["edges"] = [e for e in self.graph["edges"] if e.get("osm_id") != "1485914582"]
        self.write_inputs()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "No remote link was invented"):
            self.run_integration()
        self.assertEqual(self.snapshot(), before)

    def test_conflicting_oneway_fails_before_writes(self):
        for edge in self.graph["edges"]:
            if edge.get("osm_id") == "1485914582":
                edge["oneway"] = "no"
        self.write_inputs()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "explicitly forward-directed"):
            self.run_integration()
        self.assertEqual(self.snapshot(), before)

    def test_missing_boundary_and_mapped_merge_are_reported(self):
        isolated_source = self.root / "schools-overlay.json"
        isolated_source.write_bytes(SCHOOLS.read_bytes())
        report = ACCESS.integrate(isolated_source, GATES, self.root, dry_run=True)
        kinds = [i["kind"] for i in report["issues"]]
        self.assertEqual(kinds.count("school_boundary_missing"), 2)
        self.assertEqual(report["addedMappedGateMerges"],1)
        self.assertNotIn("gate_junction_unspecified", kinds)
        self.assertIn("disconnected_source_routes", kinds)
        self.assertIn("runtime_direction_enforcement", kinds)


class SchoolRoadOverrideTests(unittest.TestCase):
    def fixture(self):
        row={'school_id':175,'osm_way':'mapped_connection','from':[0,0,1],'to':[10,0,2],'width':5.5,'source':'source XY'}
        schools={'navigation_segments':[row,{'untouched':True}]};raw=json.dumps(schools).encode()
        overlay={'schema':'final-school-road-ownership-1','source_sha256':ACCESS.digest(raw),'segment_replacements':[{'source_segment_index':0,'source_record':copy.deepcopy(row),'points':[[0,0,1.1],[5,0,1.7],[10,0,2.2]],'width_m':4.6,'source':'Actual surviving visible support','support_surface_objects':['asphalt']} ]}
        return schools,raw,overlay

    def test_exact_profile_preserves_source_and_unrelated_indices(self):
        schools,raw,overlay=self.fixture();result=ACCESS.apply_school_road_override(schools,raw,overlay)
        self.assertEqual(result['navigation_segments'][1],schools['navigation_segments'][1]);self.assertNotIn('points',schools['navigation_segments'][0])
        self.assertEqual(result['navigation_segments'][0]['points'],overlay['segment_replacements'][0]['points']);self.assertEqual(result['navigation_segments'][0]['width'],4.6)

    def test_source_mismatch_and_xy_departure_rejected(self):
        schools,raw,overlay=self.fixture();overlay['source_sha256']='stale'
        with self.assertRaisesRegex(ValueError,'not bound'):ACCESS.apply_school_road_override(schools,raw,overlay)
        schools,raw,overlay=self.fixture();overlay['segment_replacements'][0]['points'][1][1]=.1
        with self.assertRaisesRegex(ValueError,'moved the mapped road XY'):ACCESS.apply_school_road_override(schools,raw,overlay)


def math_distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** .5


if __name__ == "__main__":
    unittest.main(verbosity=2)
