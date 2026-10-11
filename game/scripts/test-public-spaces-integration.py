#!/usr/bin/env python3
"""Small standard-library fixtures. Never write to the canonical game export."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("public_space_integration", HERE / "integrate-public-spaces.py")
INTEGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INTEGRATION)
REALISM = Path(os.environ.get("CHOSUN_REALISM_ROOT", HERE.parent.parent / "realism_v2"))
SOURCE = REALISM / "public_spaces_review/public_spaces_navigation.json"
TRACK = REALISM / "track_perimeter_review/track_navigation.json"


def read_world(root):
    return json.loads((root / "dist/world-config.js").read_text().split("export const WORLD = ")[1].rstrip(";\n"))


def triangle_area(surface):
    return sum(abs(INTEGRATION.area([surface["polygon"][i] for i in face])) for face in surface["triangles"])


class ClippingTests(unittest.TestCase):
    square = [[0, 0], [1, 0], [1, 1], [0, 1]]
    far = [[100, 100], [101, 100], [101, 101], [100, 101]]

    def test_planar_concave_and_clockwise_triangulation(self):
        xy = [[0, 0], [3, 0], [3, 1], [1, 1], [1, 3], [0, 3]]
        polygon = [[x, y, 2 * x - y + 7] for x, y in xy]
        for ring in (polygon, list(reversed(polygon))):
            triangles = INTEGRATION.triangulate_planar(ring)
            self.assertEqual(len(triangles), 4)
            self.assertAlmostEqual(triangle_area({"polygon": ring, "triangles": triangles}), 5)
            self.assertTrue(all(INTEGRATION.area([ring[i] for i in face]) * INTEGRATION.area(ring) > 0 for face in triangles))

    def test_invalid_supports_rejected(self):
        for ring in ([[0, 0, 0], [1, 0, 0], [1, 1, 1], [0, 1, 0]],
                     [[0, 0, 0], [1, 1, 0], [0, 1, 0], [1, 0, 0]],
                     [[0, 0, 0], [1, 0, 0], [2, 0, 0]]):
            with self.assertRaises(ValueError):
                INTEGRATION.triangulate_planar(ring)

    def test_triangle_subtraction_preserves_outside_area_and_sloped_z(self):
        polygon = [[x, y, 2 * x + 3 * y] for x, y in [[-2, -2], [4, -2], [-2, 4]]]
        surface = {"id": "long_legacy_surface", "polygon": polygon, "triangles": [[0, 1, 2]], "evidence": "keep"}
        clipped, report = INTEGRATION.clip_surface(surface, self.square, self.far)
        self.assertAlmostEqual(triangle_area(clipped), 17)
        self.assertEqual(clipped["id"], surface["id"])
        self.assertEqual(clipped["evidence"], "keep")
        self.assertEqual(report["theatreTrianglesClipped"], 1)
        for x, y, z in clipped["polygon"]:
            self.assertAlmostEqual(z, 2 * x + 3 * y)
        again, change = INTEGRATION.clip_surface(clipped, self.square, self.far)
        self.assertEqual(again, clipped)
        self.assertIsNone(change)

    def test_rose_matches_original_triangle_centroid_suppression(self):
        outside_centroid = {"id": "overlaps_rose", "polygon": [[-3, 0, 4], [1, 0, 4], [1, 1, 4]], "triangles": [[0, 1, 2]]}
        kept, report = INTEGRATION.clip_surface(outside_centroid, self.far, self.square)
        self.assertIs(kept, outside_centroid)
        self.assertIsNone(report)
        inside_centroid = {"id": "old_rose_support", "polygon": [[-.5, 0, 4], [1, 0, 4], [1, 1, 4]], "triangles": [[0, 1, 2]]}
        removed, report = INTEGRATION.clip_surface(inside_centroid, self.far, self.square)
        self.assertIsNone(removed)
        self.assertEqual(report["roseTrianglesRemoved"], 1)

    def test_long_path_clips_both_zones_without_reconnecting_gap(self):
        second = [[3, 0], [4, 0], [4, 1], [3, 1]]
        path = {"id": "long_route", "kind": "walk", "width": 2, "points": [[-5, .5, -10], [5, .5, 10], [6, .5, 12]]}
        paths, report = INTEGRATION.clip_path(path, [self.square, second])
        self.assertEqual(report["remainingFragments"], 3)
        self.assertEqual(paths[0]["id"], "long_route")
        self.assertEqual(paths[0]["points"], [[-5, .5, -10], [0, .5, 0]])
        self.assertEqual(paths[1]["points"], [[1, .5, 2], [3, .5, 6]])
        self.assertEqual(paths[2]["points"], [[4, .5, 8], [5, .5, 10], [6, .5, 12]])
        for fragment in paths:
            again, change = INTEGRATION.clip_path(fragment, [self.square, second])
            self.assertEqual(again, [fragment])
            self.assertIsNone(change)

    def test_concave_mask_and_boundary_paths(self):
        concave = [[0, 0], [3, 0], [3, 3], [2, 3], [2, 1], [1, 1], [1, 3], [0, 3]]
        path = {"id": "through_notch", "points": [[-1, 2, 0], [4, 2, 5]]}
        fragments, _ = INTEGRATION.clip_path(path, [concave])
        self.assertEqual(len(fragments), 3)
        self.assertEqual(fragments[1]["points"], [[1, 2, 2], [2, 2, 3]])
        for points in ([[-1, 0, 0], [2, 0, 0]], [[-1, 1, 0], [1, -1, 0]]):
            path = {"id": "boundary", "points": points}
            kept, report = INTEGRATION.clip_path(path, [self.square])
            self.assertEqual(kept, [path])
            self.assertIsNone(report)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="public-spaces-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "dist").mkdir()
        (self.root / "data").mkdir()
        surfaces = [
            {"id": "unrelated", "kind": "walkway", "polygon": [[800, 800, 11], [801, 800, 12], [800, 801, 13]], "triangles": [[0, 1, 2]], "keep": "unchanged"},
            {"id": "theatre_crossing", "kind": "walkway", "polygon": [[-260, -280, -40], [-100, -280, -32], [-100, -180, -27], [-260, -180, -35]], "triangles": [[0, 1, 2], [0, 2, 3]]},
            {"id": "obsolete_rose", "kind": "walkway", "polygon": [[109, -454, -45], [112, -454, -44], [112, -450, -43]], "triangles": [[0, 1, 2]]},
            {"id": "osm1190387575", "kind": "walkway", "polygon": [[0, -370, -50], [5, -370, -50], [0, -360, -50]], "triangles": [[0, 1, 2]]},
        ]
        paths = [
            {"id": "unrelated_route", "points": [[800, 800, 11], [810, 810, 11]], "width": 2},
            {"id": "long_theatre_route", "points": [[-260, -238.81, -44], [-100, -238.81, -36]], "width": 2},
            {"id": "long_rose_route", "points": [[90, -453, -44], [140, -453, -42]], "width": 2},
        ]
        landmarks = [{"id": "167", "label": "1.8극장(노천극장)", "position": [-170, -280, -40], "yaw": .4, "source": "keep"},
                     {"id": "163", "label": "장미원", "position": [110, -440, -48], "yaw": .5, "source": "keep"},
                     {"id": "outside", "label": "Outside", "position": [800, 800, 11], "yaw": .6}]
        boxes = [{"min": [-210 + i, -250, -42], "max": [-209 + i, -249, -30], "label": INTEGRATION.LEGACY_THEATRE_LABEL} for i in range(11)]
        boxes.append({"min": [800, 800, 1], "max": [801, 801, 2], "label": "outside obstacle"})
        self.nav = {"walkableSurfaces": surfaces, "pedestrianPaths": paths, "collisionBoxes": boxes, "landmarks": landmarks,
                    "roads": [{"id": "vehicle_route", "points": [[0, 0, 0], [1, 1, 1]]}], "unrelated": {"keep": True}}
        self.world = {"walkableSurfaces": [{**s, "polygon": [INTEGRATION.cv(p) for p in s["polygon"]]} for s in surfaces],
                      "pedestrianPaths": [{**p, "points": [INTEGRATION.cv(v) for v in p["points"]]} for p in paths],
                      "collisionBoxes": [{**b, "min": [b["min"][0], b["min"][2], -b["max"][1]], "max": [b["max"][0], b["max"][2], -b["min"][1]]} for b in boxes],
                      "destinations": [{**d, "position": INTEGRATION.cv(d["position"])} for d in landmarks],
                      "extraNPCs": [{"position": [i, 10, 0]} for i in range(19)],
                      "extraCars": [{"position": [i, 10, 0]} for i in range(11)],
                      "shuttles": [{"id": "shuttle_1"}, {"id": "shuttle_2"}],
                      "roads": [{"name": "keep road", "points": [[0, 0, 0], [1, 1, 1]]}], "walkingAccessZones": [], "siteAsset": "campus.glb"}
        (self.root / "dist/world-config.js").write_text("// fixture\nexport const WORLD = " + json.dumps(self.world) + ";\n")
        (self.root / "data/campus-navigation.json").write_text(json.dumps(self.nav))

    def snapshots(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_dry_run_and_wrong_native_source_never_write(self):
        before = self.snapshots()
        report = INTEGRATION.integrate(SOURCE, self.root, dry_run=True, track_source=TRACK)
        self.assertEqual(self.snapshots(), before)
        self.assertEqual(report["changes"]["world"]["removedLegacyCollisionBoxes"], 11)
        bad_module = self.root / "bad-module.py"
        bad_module.write_text("# Not the frozen module\n")
        before = self.snapshots()
        with self.assertRaisesRegex(ValueError, "frozen"):
            INTEGRATION.integrate(SOURCE, self.root, module_path=bad_module)
        self.assertEqual(self.snapshots(), before)

    def test_merge_is_idempotent_and_preserves_unrelated_state(self):
        report = INTEGRATION.integrate(SOURCE, self.root, track_source=TRACK)
        world = read_world(self.root)
        nav = json.loads((self.root / "data/campus-navigation.json").read_text())
        for key in ("extraNPCs", "extraCars", "shuttles", "roads", "walkingAccessZones", "siteAsset"):
            self.assertEqual(world[key], self.world[key])
        for key in ("roads", "unrelated"):
            self.assertEqual(nav[key], self.nav[key])
        self.assertEqual(world["walkableSurfaces"][0], self.world["walkableSurfaces"][0])
        self.assertEqual(world["pedestrianPaths"][0], self.world["pedestrianPaths"][0])
        self.assertEqual(world["destinations"][2], self.world["destinations"][2])
        self.assertFalse(any(s["id"] in ("obsolete_rose", "osm1190387575") for s in nav["walkableSurfaces"]))
        self.assertTrue(any(s["id"] == "theatre_crossing" for s in nav["walkableSurfaces"]))
        self.assertEqual(len(world["collisionBoxes"]), 117)
        self.assertFalse(any(b["label"] == INTEGRATION.LEGACY_THEATRE_LABEL for b in world["collisionBoxes"]))
        for key, expected in (("walkableSurfaces", 20), ("pedestrianPaths", 3)):
            self.assertEqual(sum(str(v["id"]).startswith("public_") for v in nav[key]), expected)
        self.assertEqual(sum(str(v["id"]).startswith("red_track_") for v in nav["walkableSurfaces"]), 743)
        for key in ("walkableSurfaces", "pedestrianPaths"):
            self.assertEqual([v["id"] for v in world[key]], [v["id"] for v in nav[key]])
            coords = "polygon" if key == "walkableSurfaces" else "points"
            for w, n in zip(world[key], nav[key]):
                self.assertEqual(w[coords], [INTEGRATION.cv(p) for p in n[coords]])
        for destination in world["destinations"][:2]:
            original = next(d for d in self.world["destinations"] if d["id"] == destination["id"])
            for key in ("id", "label", "yaw", "source"):
                self.assertEqual(destination[key], original[key])
        self.assertEqual(world["destinations"][0]["position"], [-184.46, -41.35, 238.81])
        self.assertEqual(world["destinations"][1]["position"][::2], [111, 453])
        self.assertFalse(report["finalGLBHeightSampling"]["sampled"])
        self.assertTrue(report["finalGLBHeightSampling"]["required"])
        for copied, original in [("public-spaces.json", SOURCE), ("track-perimeter.json", TRACK)]:
            self.assertEqual((self.root / "data" / copied).read_bytes(), original.read_bytes())
        before = self.snapshots()
        repeated = INTEGRATION.integrate(SOURCE, self.root, track_source=TRACK)
        after = self.snapshots()
        for path in before:
            if path != "data/public-spaces-sync-report.json":
                self.assertEqual(after[path], before[path], path)
        self.assertEqual(repeated["changes"]["world"]["removedLegacyCollisionBoxes"], 0)
        self.assertEqual(repeated["changes"]["world"]["replacedPublicCollisionBoxes"], 116)
        self.assertEqual(repeated["changes"]["world"]["changedLegacySurfaces"], [])
        self.assertEqual(repeated["changes"]["world"]["changedLegacyPaths"], [])

    def test_track_quads_preserve_pitch_hole_and_exact_height(self):
        source = json.loads(TRACK.read_bytes())
        surfaces = INTEGRATION.validate_track(source)
        hole = [[x, y, -50.982] for x, y in source["spatialContract"]["innerPitchHole"]]
        hole_triangles = INTEGRATION.triangulate_planar(hole)
        overlap = 0
        for surface, original in zip(surfaces, source["walkableSurfaces"]):
            self.assertEqual(surface["polygon"], original["polygon"])
            self.assertEqual(len(surface["triangles"]), 2)
            for indices in hole_triangles:
                mask = [hole[i] for i in indices]
                if INTEGRATION.area(mask) < 0:
                    mask.reverse()
                piece = surface["polygon"]
                for a, b in zip(mask, mask[1:] + mask[:1]):
                    piece = INTEGRATION.half(piece, a, b)
                overlap += abs(INTEGRATION.area(piece))
        self.assertLess(overlap, 1e-6)

    def test_similarly_named_unrelated_records_survive(self):
        self.nav["walkableSurfaces"][0]["id"] = "public_unrelated"
        self.nav["pedestrianPaths"][0]["id"] = "public_unrelated_route"
        self.nav["collisionBoxes"][-1]["label"] = "Public spaces | unrelated obstacle"
        (self.root / "data/campus-navigation.json").write_text(json.dumps(self.nav))
        INTEGRATION.integrate(SOURCE, self.root)
        nav = json.loads((self.root / "data/campus-navigation.json").read_text())
        self.assertEqual(nav["walkableSurfaces"][0], self.nav["walkableSurfaces"][0])
        self.assertEqual(nav["pedestrianPaths"][0], self.nav["pedestrianPaths"][0])
        self.assertEqual(nav["collisionBoxes"][0], self.nav["collisionBoxes"][-1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
