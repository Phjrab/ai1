#!/usr/bin/env python3
"""Merge the frozen public-space contract into a game export, without Blender.

Usage: python3 scripts/integrate-public-spaces.py NAVIGATION --game-root GAME
       python3 scripts/integrate-public-spaces.py NAVIGATION --dry-run

Run after the final terrain-v5 navigation/export is staged. This is a metadata
merge, not final-GLB height verification. The report deliberately leaves that
verification pending. No actors, render assets, roads, or terrain are generated.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
MODULE_SHA256 = "c656c7cf2e30f152644a83c67b3143a7a9cf38a7cf3fbda48d3facf632586153"
LEGACY_THEATRE_LABEL = "1.8극장(노천극장)"
PUBLIC_BOX_PREFIX = "Public spaces | "
EPS = 1e-9
MIN_AREA = 1e-7  # public_spaces.coordinate_paths uses this projected area cutoff.


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def cv(point):
    """Blender XYZ -> glTF/Three XYZ; this rotation preserves handedness."""
    return [point[0], point[2], -point[1]]


def uncv(point):
    return [point[0], -point[2], point[1]]


def area(poly):
    return .5 * sum(a[0] * b[1] - b[0] * a[1]
                    for a, b in zip(poly, poly[1:] + poly[:1]))


def cross(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def inside(point, poly):
    """Same ray-crossing convention as the frozen native public_spaces.inside."""
    x, y = point[:2]
    result = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if ((a[1] > y) != (b[1] > y)
                and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]):
            result = not result
    return result


def on_segment(p, a, b):
    return (abs(cross(a, b, p)) <= EPS * max(1, math.dist(a[:2], b[:2]))
            and min(a[0], b[0]) - EPS <= p[0] <= max(a[0], b[0]) + EPS
            and min(a[1], b[1]) - EPS <= p[1] <= max(a[1], b[1]) + EPS)


def strictly_inside(point, poly):
    return (not any(on_segment(point, a, b) for a, b in zip(poly, poly[1:] + poly[:1]))
            and inside(point, poly))


def half(poly, a, b, keep_inside=True):
    """Native _half, carrying Z by edge interpolation instead of dropping it."""
    result = []
    for p, q in zip(poly, poly[1:] + poly[:1]):
        sp, sq = cross(a, b, p), cross(a, b, q)
        ip = sp >= -EPS if keep_inside else sp <= EPS
        iq = sq >= -EPS if keep_inside else sq <= EPS
        if ip:
            result.append(p)
        if ip != iq:
            t = sp / (sp - sq)
            result.append([p[k] + t * (q[k] - p[k]) for k in range(len(p))])
    return result


def subtract_convex(poly, mask):
    """Disjoint outside pieces, with the native half-plane clipping tolerance."""
    if area(mask) < 0:
        mask = list(reversed(mask))
    pieces, left = [], poly
    for a, b in zip(mask, mask[1:] + mask[:1]):
        if len(left) < 3:
            break
        outside = half(left, a, b, False)
        if len(outside) >= 3 and abs(area(outside)) > MIN_AREA:
            pieces.append(outside)
        left = half(left, a, b, True)
    # Keep disjoint triangles byte-for-byte, including ones touching the boundary.
    if len(left) < 3 or abs(area(left)) <= MIN_AREA:
        return [poly], 0.0
    return pieces, abs(area(left))


def finite_point(point, dimensions=3):
    return (isinstance(point, (list, tuple)) and len(point) == dimensions
            and all(isinstance(x, (float, int)) and not isinstance(x, bool)
                    and math.isfinite(x) for x in point))


def segments_intersect(a, b, c, d):
    turns = cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b)
    if turns[0] * turns[1] < 0 and turns[2] * turns[3] < 0:
        return True
    return any((abs(turn) <= EPS and on_segment(p, u, v)) for turn, p, u, v in
               [(turns[0], c, a, b), (turns[1], d, a, b),
                (turns[2], a, c, d), (turns[3], b, c, d)])


def validate_ring(poly, dimensions):
    if len(poly) < 3 or not all(finite_point(p, dimensions) for p in poly):
        raise ValueError("Polygon requires at least three finite vertices")
    if abs(area(poly)) <= MIN_AREA:
        raise ValueError("Polygon has no projected support area")
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        if math.dist(a[:2], b[:2]) <= EPS:
            raise ValueError("Polygon contains a repeated boundary vertex")
        for j in range(i + 1, len(poly)):
            if j == i + 1 or (i == 0 and j == len(poly) - 1):
                continue
            if segments_intersect(a, b, poly[j], poly[(j + 1) % len(poly)]):
                raise ValueError("Polygon boundary self-intersects")


def triangulate_planar(poly):
    """Ear-clip a simple planar ring; keep its vertices and original winding."""
    validate_ring(poly, 3)
    origin = poly[0]
    plane = None
    for i in range(1, len(poly) - 1):
        b, c = poly[i], poly[i + 1]
        determinant = cross(origin, b, c)
        if abs(determinant) > MIN_AREA:
            u = [(b[k] - origin[k]) for k in range(3)]
            v = [(c[k] - origin[k]) for k in range(3)]
            plane = ((u[2] * v[1] - u[1] * v[2]) / determinant,
                     (u[0] * v[2] - u[2] * v[0]) / determinant)
            break
    if plane is None or any(abs(p[2] - origin[2] - plane[0] * (p[0] - origin[0])
                               - plane[1] * (p[1] - origin[1])) > 1e-6 for p in poly):
        raise ValueError("Public support polygon is not planar")
    direction = 1 if area(poly) > 0 else -1
    indices, triangles = list(range(len(poly))), []
    while len(indices) > 3:
        for index, b in enumerate(indices):
            a, c = indices[index - 1], indices[(index + 1) % len(indices)]
            if direction * cross(poly[a], poly[b], poly[c]) <= EPS:
                continue
            if any(all(direction * cross(poly[u], poly[v], poly[p]) >= -EPS
                       for u, v in [(a, b), (b, c), (c, a)])
                   for p in indices if p not in (a, b, c)):
                continue
            triangles.append([a, b, c])
            indices.pop(index)
            break
        else:
            # Collinear boundary points are valid, but cannot form an ear.
            for index, b in enumerate(indices):
                a, c = indices[index - 1], indices[(index + 1) % len(indices)]
                if abs(cross(poly[a], poly[b], poly[c])) <= EPS:
                    indices.pop(index)
                    break
            else:
                raise ValueError("Cannot triangulate support polygon")
    if abs(area([poly[i] for i in indices])) > EPS:
        triangles.append(indices)
    actual = sum(abs(area([poly[i] for i in t])) for t in triangles)
    if abs(actual - abs(area(poly))) > max(1e-7, abs(area(poly)) * 1e-10):
        raise ValueError("Triangulation does not conserve polygon area")
    return triangles


def bbox(poly):
    return min(p[0] for p in poly), min(p[1] for p in poly), max(p[0] for p in poly), max(p[1] for p in poly)


def overlaps(a, b):
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def clip_surface(surface, theatre, rose):
    """Rose suppression uses each original triangle's centroid, as in Blender."""
    poly = surface["polygon"]
    if not any(overlaps(bbox(poly), bbox(mask)) for mask in (theatre, rose)):
        return surface, None
    triangles = surface.get("triangles")
    if triangles is None:
        triangles = triangulate_planar(poly)
    pieces, rose_removed, theatre_changed, removed_area = [], 0, 0, 0.0
    for face in triangles:
        if (len(face) != 3 or any(not isinstance(i, int) or i < 0 or i >= len(poly) for i in face)):
            raise ValueError("Invalid legacy support triangle: " + str(surface["id"]))
        triangle = [poly[i] for i in face]
        centroid = [sum(p[k] for p in triangle) / 3 for k in (0, 1)]
        if inside(centroid, rose):
            rose_removed += 1
            removed_area += abs(area(triangle))
            continue
        if overlaps(bbox(triangle), bbox(theatre)):
            outside, removed = subtract_convex(triangle, theatre)
            if removed > 0:
                theatre_changed += 1
                removed_area += removed
            pieces.extend(outside)
        else:
            pieces.append(triangle)
    if not rose_removed and not theatre_changed:
        return surface, None
    vertices, faces, keys = [], [], {}
    for piece in pieces:
        ids = []
        for point in piece:
            # Same vertex reuse precision as coordinate_paths; keep original Z.
            key = tuple(round(float(v), 6) for v in point)
            if key not in keys:
                keys[key] = len(vertices)
                vertices.append(list(point))
            ids.append(keys[key])
        for j in range(1, len(ids) - 1):
            face = [ids[0], ids[j], ids[j + 1]]
            if len(set(face)) == 3 and abs(area([vertices[i] for i in face])) > EPS:
                faces.append(face)
    before = sum(abs(area([poly[i] for i in face])) for face in triangles)
    after = sum(abs(area([vertices[i] for i in face])) for face in faces)
    if abs(before - removed_area - after) > max(1e-5, before * 1e-9):
        raise ValueError("Legacy triangle clipping lost outside area: " + str(surface["id"]))
    report = {"id": surface["id"], "roseTrianglesRemoved": rose_removed,
              "theatreTrianglesClipped": theatre_changed,
              "beforeTriangles": len(triangles), "afterTriangles": len(faces)}
    return ({**surface, "polygon": vertices, "triangles": faces} if faces else None), report


def segment_intersections(a, b, poly):
    """Segment parameters at a possibly concave polygon's boundary."""
    result = [0.0, 1.0]
    dx, dy = b[0] - a[0], b[1] - a[1]
    length_squared = dx * dx + dy * dy
    if length_squared <= EPS * EPS:
        return result
    for p, q in zip(poly, poly[1:] + poly[:1]):
        ex, ey = q[0] - p[0], q[1] - p[1]
        denominator = dx * ey - dy * ex
        px, py = p[0] - a[0], p[1] - a[1]
        if abs(denominator) > EPS:
            t, u = (px * ey - py * ex) / denominator, (px * dy - py * dx) / denominator
            if -EPS <= t <= 1 + EPS and -EPS <= u <= 1 + EPS:
                result.append(max(0.0, min(1.0, t)))
        elif abs(px * dy - py * dx) <= EPS:
            for p in (p, q):
                t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length_squared
                if 0 < t < 1:
                    result.append(t)
    return result


def interpolate(a, b, t):
    if t == 0:
        return list(a)
    if t == 1:
        return list(b)
    return [a[k] + t * (b[k] - a[k]) for k in range(3)]


def clip_path(path, masks):
    fragments, current, changed = [], [], False
    for a, b in zip(path["points"], path["points"][1:]):
        ts = sorted(t for mask in masks for t in segment_intersections(a, b, mask))
        unique = []
        for t in ts:
            if not unique or t - unique[-1] > EPS:
                unique.append(t)
        for start, end in zip(unique, unique[1:]):
            if any(strictly_inside(interpolate(a, b, (start + end) / 2), mask) for mask in masks):
                changed = True
                if len(current) >= 2:
                    fragments.append(current)
                current = []
                continue
            p, q = interpolate(a, b, start), interpolate(a, b, end)
            if current and math.dist(current[-1], p) > 1e-7:
                if len(current) >= 2:
                    fragments.append(current)
                current = []
            if not current:
                current.append(p)
            if math.dist(current[-1], q) > EPS:
                current.append(q)
    if not changed:
        return [path], None
    if len(current) >= 2:
        fragments.append(current)
    result = []
    for i, points in enumerate(fragments):
        result.append({**path, "id": path["id"] if i == 0 else str(path["id"]) + "__public_spaces_part_" + str(i),
                       "points": points, "publicSpacesSourcePathId": path.get("publicSpacesSourcePathId", path["id"])})
    return result, {"id": path["id"], "remainingFragments": len(result)}


def validate_source(source, contract):
    if source.get("schema") != "public-spaces-v1" or source.get("coordinateSystem") != "Blender Z-up metres":
        raise ValueError("Unsupported public-space navigation schema/coordinates")
    if contract.get("module_sha256") != MODULE_SHA256:
        raise ValueError("Integration contract does not reference the frozen public-space module")
    if contract.get("removeLegacyCollisionLabels") != [LEGACY_THEATRE_LABEL] or contract.get("legacyTheatreColliderCount") != 11:
        raise ValueError("Unexpected legacy theatre removal contract")
    for key, expected in [("walkableSurfaces", 20), ("pedestrianPaths", 3), ("collisionBoxes", 116)]:
        if len(source[key]) != expected:
            raise ValueError(f"Expected {expected} {key}, got {len(source[key])}")
    if source.get("roseSharedPrototypes") != 4 or source.get("roseShrubInstances") != 1477:
        raise ValueError("Unexpected native/game shared rose instance contract")
    masks = source["suppressLegacyWalkSurfacesWithin"]
    if len(masks) != 2:
        raise ValueError("Expected theatre and rose suppression polygons")
    for mask in masks:
        validate_ring(mask, 2)
    theatre = masks[0] if area(masks[0]) > 0 else list(reversed(masks[0]))
    if any(cross(theatre[i - 1], theatre[i], theatre[(i + 1) % len(theatre)]) < -EPS for i in range(len(theatre))):
        raise ValueError("Theatre suppression polygon must be convex")
    if source.get("theatreTerrainCut", {}).get("polygon") != masks[0]:
        raise ValueError("Theatre surface suppression differs from terrain cut")
    surfaces = []
    for surface in source["walkableSurfaces"]:
        surfaces.append({**surface, "triangles": triangulate_planar(surface["polygon"])})
    for key, records in [("surfaces", surfaces), ("paths", source["pedestrianPaths"])]:
        ids = [item["id"] for item in records]
        if len(set(ids)) != len(ids) or any(not str(i).startswith("public_") for i in ids):
            raise ValueError("Invalid public-space " + key + " IDs")
    for path in source["pedestrianPaths"]:
        if len(path["points"]) < 2 or not all(finite_point(p) for p in path["points"]):
            raise ValueError("Invalid public-space path")
    for box in source["collisionBoxes"]:
        if (not finite_point(box["min"]) or not finite_point(box["max"])
                or not all(a < b for a, b in zip(box["min"], box["max"]))
                or not box.get("label", "").startswith(PUBLIC_BOX_PREFIX)):
            raise ValueError("Invalid bounded public-space collision box")
    return surfaces, theatre, masks[1]


def validate_track(track):
    if track.get("schema") != "track-perimeter-navigation-v1" or track.get("coordinateSystem") != "Blender Z-up metres":
        raise ValueError("Unsupported track navigation schema/coordinates")
    if (len(track["walkableSurfaces"]) != 743 or len(track["pedestrianPaths"]) != 1
            or track["collisionBoxes"] or track["spatialContract"].get("surfaceZ") != -50.982):
        raise ValueError("Expected 743 track quads, one pedestrian loop and no collision boxes")
    if track.get("removeLegacyWalkSurfaceIds") != ["osm1190387575", "1190387575"]:
        raise ValueError("Unexpected legacy track surface removal IDs")
    surfaces = []
    for surface in track["walkableSurfaces"]:
        if (len(surface["polygon"]) != 4 or surface.get("kind") != "running_track"
                or not str(surface["id"]).startswith("red_track_")
                or any(abs(p[2] + 50.982) > 1e-8 for p in surface["polygon"])):
            raise ValueError("Invalid fixed-height track support quad")
        surfaces.append({**surface, "triangles": triangulate_planar(surface["polygon"])})
    if len({s["id"] for s in surfaces}) != len(surfaces):
        raise ValueError("Duplicate track support IDs")
    path = track["pedestrianPaths"][0]
    if (path.get("id") != "red_track_perimeter_loop" or path.get("kind") != "running_track"
            or len(path["points"]) < 4 or not all(finite_point(p) for p in path["points"])
            or path["points"][0] != path["points"][-1]
            or any(abs(p[2] + 50.982) > 1e-8 for p in path["points"])):
        raise ValueError("Track must supply a closed pedestrian loop at its fixed height")
    return surfaces


def merge_target(target, is_world, source, surfaces, theatre, rose, track=None, track_surfaces=None):
    to_native, from_native = (uncv, cv) if is_world else (list, list)
    public_surface_ids = {s["id"] for s in surfaces}
    public_path_ids = {p["id"] for p in source["pedestrianPaths"]}
    public_box_labels = {b["label"] for b in source["collisionBoxes"]}
    track_ids = {s["id"] for s in track_surfaces} if track else {f"red_track_{i:04d}" for i in range(743)}
    report = {"removedLegacyCollisionBoxes": 0, "replacedPublicCollisionBoxes": 0,
              "removedLegacySurfaces": 0, "changedLegacySurfaces": [], "changedLegacyPaths": [],
              "replacedPublicSurfaces": 0, "replacedPublicPaths": 0}
    if track:
        report["track"] = {"removedLegacySurfaceIds": [], "replacedSurfaces": 0, "replacedPaths": 0,
                           "addedSurfaces": len(track_surfaces), "addedPedestrianPaths": 1,
                           "addedCollisionBoxes": 0, "addedVehicleRoads": 0}
    result = []
    for surface in target.get("walkableSurfaces", []):
        if track and str(surface["id"]) in track["removeLegacyWalkSurfaceIds"]:
            report["track"]["removedLegacySurfaceIds"].append(surface["id"])
            continue
        if surface["id"] in track_ids:
            if track:
                report["track"]["replacedSurfaces"] += 1
            else:
                result.append(surface)
            continue
        if surface["id"] in public_surface_ids:
            report["replacedPublicSurfaces"] += 1
            continue
        native = {**surface, "polygon": [to_native(p) for p in surface["polygon"]]}
        clipped, change = clip_surface(native, theatre, rose)
        if change is None:
            result.append(surface)
        else:
            report["changedLegacySurfaces"].append(change)
            if clipped:
                result.append({**clipped, "polygon": [from_native(p) for p in clipped["polygon"]]})
            else:
                report["removedLegacySurfaces"] += 1
    target["walkableSurfaces"] = result + [{**s, "polygon": [from_native(p) for p in s["polygon"]]} for s in surfaces]
    if track:
        target["walkableSurfaces"].extend({**s, "polygon": [from_native(p) for p in s["polygon"]]} for s in track_surfaces)
    result = []
    for path in target.get("pedestrianPaths", []):
        if path["id"] == "red_track_perimeter_loop":
            if track:
                report["track"]["replacedPaths"] += 1
            else:
                result.append(path)
            continue
        if path["id"] in public_path_ids:
            report["replacedPublicPaths"] += 1
            continue
        native = {**path, "points": [to_native(p) for p in path["points"]]}
        clipped, change = clip_path(native, [theatre, rose])
        if change is None:
            result.append(path)
        else:
            report["changedLegacyPaths"].append(change)
            result.extend({**p, "points": [from_native(v) for v in p["points"]]} for p in clipped)
    target["pedestrianPaths"] = result + [{**p, "points": [from_native(v) for v in p["points"]]} for p in source["pedestrianPaths"]]
    if track:
        target["pedestrianPaths"].extend({**p, "points": [from_native(v) for v in p["points"]]} for p in track["pedestrianPaths"])
    for key in ("walkableSurfaces", "pedestrianPaths"):
        ids = [str(item["id"]) for item in target[key]]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate IDs after merging " + key)
    boxes = []
    for box in target.get("collisionBoxes", []):
        if box.get("label") == LEGACY_THEATRE_LABEL:
            report["removedLegacyCollisionBoxes"] += 1
        elif box.get("label") in public_box_labels:
            report["replacedPublicCollisionBoxes"] += 1
        else:
            boxes.append(box)
    if report["removedLegacyCollisionBoxes"] not in (0, 11):
        raise ValueError("Expected 11 obsolete theatre collision boxes, or zero on a rerun")
    for box in source["collisionBoxes"]:
        boxes.append({**box, "min": [box["min"][0], box["min"][2], -box["max"][1]],
                      "max": [box["max"][0], box["max"][2], -box["min"][1]]} if is_world else copy.deepcopy(box))
    target["collisionBoxes"] = boxes
    report["added"] = {"walkableSurfaces": len(surfaces), "supportTriangles": sum(len(s["triangles"]) for s in surfaces),
                       "pedestrianPaths": len(source["pedestrianPaths"]), "collisionBoxes": len(source["collisionBoxes"])}
    return report


def update_destinations(world, nav, source):
    spine = next(p for p in source["pedestrianPaths"] if p["id"] == "public_rose_spine")
    rose = next((list(p) for p in spine["points"] if math.dist(p[:2], [111, -453]) < 1e-7), None)
    if rose is None:
        raise ValueError("Rose arrival XY [111, -453] has no source spine vertex")
    targets = {"167": [-184.46, -238.81, -41.35], "163": rose}
    changes = []
    for identifier, position in targets.items():
        destinations = [d for d in world["destinations"] if str(d["id"]) == identifier]
        landmarks = [d for d in nav["landmarks"] if str(d["id"]) == identifier]
        if len(destinations) > 1 or len(landmarks) > 1 or not destinations and not landmarks:
            raise ValueError("Missing or ambiguous existing public-space destination " + identifier)
        if not destinations:
            landmark = landmarks[0]
            destinations = [{k: copy.deepcopy(landmark[k]) for k in ("id", "label", "yaw", "source") if k in landmark}]
            world["destinations"].extend(destinations)
        if not landmarks:
            destination = destinations[0]
            landmarks = [{k: copy.deepcopy(destination[k]) for k in ("id", "label", "yaw", "source") if k in destination}]
            nav["landmarks"].extend(landmarks)
        destinations[0]["position"] = cv(position)
        landmarks[0]["position"] = list(position)
        changes.append({"id": identifier, "label": destinations[0]["label"], "blenderPosition": position,
                        "heightSource": "source public_theatre_court" if identifier == "167" else "source public_rose_spine vertex",
                        "finalGLBResamplingRequired": True})
    return changes


def encode(value, pretty=False):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2 if pretty else None,
                       separators=None if pretty else (",", ":")) + "\n").encode()


def atomic_write(path, raw):
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(raw)
    try:
        os.chmod(temporary, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def integrate(source_path, game_root=ROOT, contract_path=None, module_path=None, dry_run=False, track_source=None):
    source_path, game_root = Path(source_path).resolve(), Path(game_root).resolve()
    contract_path = Path(contract_path).resolve() if contract_path else source_path.with_name("INTEGRATION_CONTRACT.json")
    module_path = Path(module_path).resolve() if module_path else source_path.parent.parent / "public_spaces.py"
    raw, contract_raw, module_raw = source_path.read_bytes(), contract_path.read_bytes(), module_path.read_bytes()
    if sha256(module_raw) != MODULE_SHA256:
        raise ValueError("Native public-space module differs from the frozen integration contract")
    source, contract = json.loads(raw), json.loads(contract_raw)
    surfaces, theatre, rose = validate_source(source, contract)
    track_raw = Path(track_source).read_bytes() if track_source else None
    track = json.loads(track_raw) if track_raw is not None else None
    track_surfaces = validate_track(track) if track is not None else None
    world_path, nav_path = game_root / "dist/world-config.js", game_root / "data/campus-navigation.json"
    world_raw, nav_raw = world_path.read_bytes(), nav_path.read_bytes()
    prefix, payload = world_raw.decode().split("export const WORLD = ", 1)
    world, nav = json.loads(payload.rstrip(";\n \t")), json.loads(nav_raw)
    actor_snapshot = {key: copy.deepcopy(world.get(key)) for key in ("extraNPCs", "extraCars")}
    changes = {"world": merge_target(world, True, source, surfaces, theatre, rose, track, track_surfaces),
               "navigation": merge_target(nav, False, source, surfaces, theatre, rose, track, track_surfaces)}
    destinations = update_destinations(world, nav, source)
    if actor_snapshot != {key: world.get(key) for key in actor_snapshot}:
        raise ValueError("Actor data changed during public-space integration")
    output_world = prefix.encode() + b"export const WORLD = " + encode(world).rstrip(b"\n") + b";\n"
    output_nav = encode(nav)
    report = {"schema": "public-spaces-game-integration-v1",
              "sourceHashes": {"navigation": sha256(raw), "integrationContract": sha256(contract_raw), "nativeModule": sha256(module_raw)},
              "outputHashes": {"world": sha256(output_world), "navigation": sha256(output_nav)},
              "coordinateSystem": "Source Blender XYZ; world Three XYZ = (x,z,-y)",
              "changes": changes, "destinations": destinations,
              "legacySurfaceMethod": "Original-triangle rose centroid suppression; convex theatre subtraction with linearly interpolated source Z",
              "legacyPathMethod": "Clip segments to the outside of both polygons; preserve first fragment ID and unrelated route portions",
              "finalGLBHeightSampling": {"status": "pending", "required": True, "sampled": False,
                  "destinationIds": ["167", "163"],
                  "requirement": "Use final exported visible support triangles after terrain v5 for destination/actor contact and surviving legacy surface/path heights; source metadata heights are not final GLB verification"},
              "preserved": {"extraNPCs": len(world.get("extraNPCs", [])), "extraCars": len(world.get("extraCars", [])),
                  "actorArraysUnchanged": True, "transitAndRenderAssetsUntouched": True,
                  "nativeActorContract": {"NPCs": 19, "cars": 11, "shuttles": 2},
                  "roseRenderingContract": {"sharedPrototypes": 4, "placements": 1477, "visualOnly": True, "rendered": "Required in final GLB; not verified by metadata integration"}}}
    if track:
        report["sourceHashes"]["trackNavigation"] = sha256(track_raw)
        report["trackSupport"] = {"surfaceZ": -50.982, "quadCount": len(track_surfaces),
                                  "triangleCount": sum(len(s["triangles"]) for s in track_surfaces),
                                  "method": "Supplied annular quads only; no filled outer polygon", "vehicleRoad": False}
    if not dry_run:
        outputs = {world_path: output_world, nav_path: output_nav,
                   game_root / "data/public-spaces.json": raw,
                   game_root / "data/public-spaces-integration-contract.json": contract_raw,
                   game_root / "data/public-spaces-sync-report.json": encode(report, pretty=True)}
        if track:
            outputs[game_root / "data/track-perimeter.json"] = track_raw
        if source_path in outputs or contract_path in outputs or module_path in outputs or (track_source and Path(track_source).resolve() in outputs):
            raise ValueError("Input and integration output paths must be distinct")
        for path, content in outputs.items():
            atomic_write(path, content)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=ROOT.parent / "realism_v2/public_spaces_review/public_spaces_navigation.json")
    parser.add_argument("--game-root", type=Path, default=ROOT, help="Game root containing dist/ and data/; use a temporary fixture for tests")
    parser.add_argument("--contract", type=Path, help="Defaults to INTEGRATION_CONTRACT.json beside source")
    parser.add_argument("--module-source", type=Path, help="Frozen public_spaces.py to verify against the contract")
    parser.add_argument("--track-source", type=Path, help="Optional track_navigation.json; merges its annular quads and pedestrian loop only")
    parser.add_argument("--dry-run", action="store_true", help="Validate and calculate changes without writing any output")
    args = parser.parse_args()
    report = integrate(args.source, args.game_root, args.contract, args.module_source, args.dry_run, args.track_source)
    print(json.dumps({"dryRun": args.dry_run, "sourceHashes": report["sourceHashes"], "changes": report["changes"],
                      "finalGLBHeightSampling": "pending"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
