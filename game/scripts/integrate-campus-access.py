#!/usr/bin/env python3
"""Stage school/gate navigation and precise solid polygons; never edit GLBs.

python -B scripts/integrate-campus-access.py --game-root /path/to/staged-game
Use --dry-run to calculate the report without writing files. Boundary geometry
defaults to source_geometry.json beside the schools overlay. Its absence is
reported; bounds then cover only supplied buildings, fields and road corridors.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OWNER = "campus-access-v1"
EPS = 1e-8
TOLL_APPROACH_M = 20
TOLL_STRAIGHT_M = 7


def cv(p):
    return [p[0], p[2], -p[1]]


def uncv(p):
    return [p[0], -p[2], p[1]]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def finite(p, count):
    return isinstance(p, (list, tuple)) and len(p) == count and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in p)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def mix(a, b, t):
    if t <= EPS:
        return list(a)
    if t >= 1 - EPS:
        return list(b)
    return [x + (y - x) * t for x, y in zip(a, b)]


def area(poly):
    return .5 * sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(poly, poly[1:] + poly[:1]))


def cross(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def point_inside(p, poly):
    result = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (abs(cross(a, b, p)) < EPS and min(a[0], b[0]) - EPS <= p[0] <= max(a[0], b[0]) + EPS
                and min(a[1], b[1]) - EPS <= p[1] <= max(a[1], b[1]) + EPS):
            return True
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]:
            result = not result
    return result


def segment_hits_polygon(a, b, polygon):
    if point_inside(a, polygon) or point_inside(b, polygon):
        return True
    for p, q in zip(polygon, polygon[1:] + polygon[:1]):
        abp, abq, pqa, pqb = cross(a, b, p), cross(a, b, q), cross(p, q, a), cross(p, q, b)
        if abp * abq <= 0 and pqa * pqb <= 0 and not (max(a[0], b[0]) < min(p[0], q[0]) or max(p[0], q[0]) < min(a[0], b[0]) or max(a[1], b[1]) < min(p[1], q[1]) or max(p[1], q[1]) < min(a[1], b[1])):
            return True
    return False


def validate(schools, gates):
    if schools.get("version") != "affiliated_schools_1.1" or gates.get("version") not in ["gates_access_1.1","gates_access_1.2"]:
        raise ValueError("Unsupported schools/gates overlay version")
    ids = []
    for obstacle in schools["obstacles"] + gates["obstacles"]:
        polygon = obstacle["polygon"]
        if (obstacle.get("type") != "solid" or len(polygon) < 3 or not all(finite(p, 2) for p in polygon)
                or abs(area(polygon)) < EPS or not finite([obstacle["min_z"], obstacle["max_z"]], 2)
                or obstacle["min_z"] >= obstacle["max_z"]):
            raise ValueError("Invalid solid obstacle " + str(obstacle.get("id")))
        ids.append(obstacle["id"])
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate obstacle IDs")
    school_ids = {s["school_id"] for s in schools["schools"]}
    for segment in schools["navigation_segments"]:
        if (segment["school_id"] not in school_ids or not finite(segment["from"], 3) or not finite(segment["to"], 3)
                or not math.isfinite(segment["width"]) or segment["width"] <= 0
                or math.dist(segment["from"][:2], segment["to"][:2]) < EPS):
            raise ValueError("Invalid school navigation segment")
    for gate in gates["toll_gates"]:
        if not finite(gate["center_xy"], 2) or not finite(gate["road_tangent"], 2) or gate["canopy_across_m"] <= 0:
            raise ValueError("Invalid toll gate frame")
        for lane in gate["lanes"]:
            if (lane.get("oneway") is not True or not finite(lane["center_xy"], 2) or not finite(lane["direction_xy"], 2)
                    or abs(math.hypot(*lane["direction_xy"]) - 1) > 1e-5
                    or lane["passage_width_m"] <= 0 or not math.isfinite(lane["ground_z"])
                    or not re.fullmatch(r"https://www\.openstreetmap\.org/way/\d+", lane["direction_source"])):
                raise ValueError("Incomplete directed gate lane " + str(lane.get("id")))


def frame(gate):
    norm = math.hypot(*gate["road_tangent"])
    if norm < EPS:
        raise ValueError("Zero gate tangent")
    u = [v / norm for v in gate["road_tangent"]]
    return u, [-u[1], u[0]]


def coordinates(p, gate):
    u, v = frame(gate)
    delta = [p[i] - gate["center_xy"][i] for i in (0, 1)]
    return dot(delta, u), dot(delta, v)


def local_interval(a, b, gate):
    """Clip to the finite gate rectangle, the modeled approach extent along its tangent."""
    pa, pb = coordinates(a, gate), coordinates(b, gate)
    start, end = 0.0, 1.0
    for k, limit in [(0, TOLL_APPROACH_M), (1, gate["canopy_across_m"] / 2)]:
        delta = pb[k] - pa[k]
        if abs(delta) < EPS:
            if abs(pa[k]) > limit + EPS:
                return None
            continue
        t0, t1 = sorted(((-limit - pa[k]) / delta, (limit - pa[k]) / delta))
        start, end = max(start, t0), min(end, t1)
        if end - start <= EPS:
            return None
    return max(0.0, start), min(1.0, end)


def gate_way_ids(gate):
    return {p["direction_source"].rsplit("/", 1)[1] for p in gate["lanes"]}


def road_way(record):
    if record.get("osm_id") is not None:
        return str(record["osm_id"])
    match = re.search(r"CAMPUS_ROAD (\d+)(?:\s|$)", record.get("name", ""))
    return match.group(1) if match else None


def clip_roads(records, gates, is_world):
    result, changes = [], []
    for record in records:
        if record.get("integrationSource") == OWNER:
            continue
        relevant = [g for g in gates if road_way(record) in gate_way_ids(g)]
        if not relevant:
            result.append(record)
            continue
        points = [uncv(p) for p in record["points"]] if is_world else record["points"]
        fragments, current, changed = [], [], False
        for a, b in zip(points, points[1:]):
            pieces = [(a, b)]
            for gate in relevant:
                next_pieces = []
                for p, q in pieces:
                    interval = local_interval(p, q, gate)
                    if interval is None:
                        next_pieces.append((p, q))
                    else:
                        changed = True
                        start, end = interval
                        if start > EPS:
                            next_pieces.append((p, mix(p, q, start)))
                        if end < 1 - EPS:
                            next_pieces.append((mix(p, q, end), q))
                pieces = next_pieces
            if not pieces and current:
                fragments.append(current)
                current = []
            for p, q in pieces:
                if current and math.dist(current[-1], p) > 1e-6:
                    fragments.append(current)
                    current = []
                if not current:
                    current = [p]
                current.append(q)
        if current:
            fragments.append(current)
        if not changed:
            result.append(record)
        else:
            changes.append({"name": record.get("name"), "outsideFragments": len(fragments)})
            for index, fragment in enumerate(fragments):
                item = {**record, "points": [cv(p) for p in fragment] if is_world else fragment}
                if index and "id" in item:
                    item["id"] = str(item["id"]) + "__gate_outside_" + str(index)
                result.append(item)
    return result, changes


class Graph:
    def __init__(self, data):
        self.data = data
        self.nodes = data["nodes"]
        self.edges = [e for e in data["edges"] if e.get("integrationSource") != OWNER and not e.get("campusAccessLocalSplit")]
        self.edges.extend(copy.deepcopy(data.get("campusAccessPreservedGateEdges",[])))
        for edge in data.get("campusAccessPreservedMergeEdges",[]):
            if not any(e["a"]==edge["a"] and e["b"]==edge["b"] and e.get("osm_id")==edge.get("osm_id") for e in self.edges):self.edges.append(copy.deepcopy(edge))
        self.by_xy = {}
        for i, p in enumerate(self.nodes):
            self.by_xy.setdefault(tuple(round(v, 6) for v in p[:2]), []).append(i)
        self.joins = []

    def node(self, point):
        key = tuple(round(v, 6) for v in point[:2])
        candidates = self.by_xy.get(key, [])
        if candidates:
            best = min(candidates, key=lambda i: abs(self.nodes[i][2] - point[2]))
            if abs(self.nodes[best][2] - point[2]) < .25:
                if abs(self.nodes[best][2] - point[2]) > 1e-6:
                    self.joins.append({"node": best, "sourceZ": point[2], "retainedGraphZ": self.nodes[best][2]})
                return best
        index = len(self.nodes)
        self.nodes.append(list(point))
        self.by_xy.setdefault(key, []).append(index)
        return index

    def add(self, a, b, attributes):
        ai, bi = self.node(a), self.node(b)
        if ai != bi:
            self.edges.append({**attributes, "a": ai, "b": bi, "length": math.dist(self.nodes[ai], self.nodes[bi])})

    def anchors(self, gate, way, side):
        candidates = {}
        for edge in self.edges:
            if str(edge.get("osm_id")) != way or edge.get("integrationSource") == OWNER:
                continue
            a, b = self.nodes[edge["a"]], self.nodes[edge["b"]]
            pa, pb = coordinates(a, gate), coordinates(b, gate)
            if abs(pb[0] - pa[0]) < EPS:
                continue
            t = (side * TOLL_APPROACH_M - pa[0]) / (pb[0] - pa[0])
            if -EPS <= t <= 1 + EPS:
                point = mix(a, b, max(0, min(1, t)))
                if abs(coordinates(point, gate)[1]) <= gate["canopy_across_m"] / 2:
                    candidates[tuple(round(x, 6) for x in point)] = (point, edge)
        if len(candidates) != 1:
            raise ValueError(f"Gate {gate['id']} needs one exact OSM {way} intersection at {side * TOLL_APPROACH_M} m; found {len(candidates)}. No remote link was invented.")
        point, edge = next(iter(candidates.values()))
        a, b = self.nodes[edge["a"]], self.nodes[edge["b"]]
        if edge.get("oneway") not in ("yes", True, "1"):
            raise ValueError("Gate lane source is not an explicitly forward-directed graph edge: " + way)
        return point, [b[i] - a[i] for i in (0, 1)]

    def cut_gate(self, gate):
        outside, removed, affected_nodes = [], [], set()
        ways = gate_way_ids(gate)
        for edge in self.edges:
            a, b = self.nodes[edge["a"]], self.nodes[edge["b"]]
            interval = local_interval(a, b, gate) if str(edge.get("osm_id")) in ways else None
            if interval is None:
                outside.append(edge)
                continue
            start, end = interval
            preserved=self.data.setdefault("campusAccessPreservedGateEdges",[])
            if not any(e["a"]==edge["a"] and e["b"]==edge["b"] and e.get("osm_id")==edge.get("osm_id") for e in preserved):preserved.append(copy.deepcopy(edge))
            removed.append({"a": edge["a"], "b": edge["b"], "osm_id": edge["osm_id"]})
            affected_nodes.update([edge["a"], edge["b"]])
            for p, q in ([(a, mix(a, b, start))] if start > EPS else []) + ([(mix(a, b, end), b)] if end < 1 - EPS else []):
                ai, bi = self.node(p), self.node(q)
                outside.append({**edge, "a": ai, "b": bi, "length": math.dist(self.nodes[ai], self.nodes[bi]), "campusAccessLocalSplit": True})
        self.edges = outside
        unresolved = []
        for edge in outside:
            if str(edge.get("osm_id")) in ways or edge.get("integrationSource") == OWNER:
                continue
            for index in (edge["a"], edge["b"]):
                x, y = coordinates(self.nodes[index], gate)
                if abs(x) < TOLL_APPROACH_M - EPS and abs(y) <= gate["canopy_across_m"] / 2:
                    unresolved.append({"node": index, "osm_id": edge.get("osm_id"), "gateId": gate["id"]})
        return removed, unresolved

    def finish(self):
        self.edges.sort(key=lambda e:(e["a"],e["b"],str(e.get("osm_id","")),str(e.get("id",""))))
        self.data["edges"] = self.edges
        adjacency = {}
        for edge in self.edges:
            adjacency.setdefault(edge["a"], set()).add(edge["b"])
            adjacency.setdefault(edge["b"], set()).add(edge["a"])
        seen, components = set(), []
        for node in sorted(adjacency):
            if node in seen:
                continue
            component, stack = [], [node]
            seen.add(node)
            while stack:
                item = stack.pop()
                component.append(item)
                for neighbor in sorted(adjacency[item], reverse=True):
                    if neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
            components.append(component)
        self.data["components"] = components
        self.data["campusAccessDirectionNote"] = "Gate edges are forward a->b with oneway=yes. School segments retain unknown legal direction. Components describe weak connectivity of used nodes."
        return components


def lane_branches(graph, gates, issues):
    records, reports = [], []
    for gate in gates["toll_gates"]:
        anchors = {(way, side): graph.anchors(gate, way, side) for way in sorted(gate_way_ids(gate)) for side in (-1, 1)}
        original_edges = copy.deepcopy(graph.edges)
        removed, unresolved = graph.cut_gate(gate)
        for lane in gate["lanes"]:
            direction, center = lane["direction_xy"], lane["center_xy"]
            u, _ = frame(gate)
            sign = 1 if dot(direction, u) > 0 else -1
            if abs(dot(direction, u)) < .9999 or abs(coordinates(center, gate)[0]) > 1e-5:
                raise ValueError("Lane center/direction does not fit the supplied toll gate frame")
            way = lane["direction_source"].rsplit("/", 1)[1]
            start, start_direction = anchors[way, -sign]
            end, end_direction = anchors[way, sign]
            start, end = graph.nodes[graph.node(start)], graph.nodes[graph.node(end)]
            if dot(start_direction, direction) <= 0 or dot(end_direction, direction) <= 0:
                raise ValueError("Gate lane conflicts with its OSM edge direction: " + lane["id"])
            # Remain straight through the canopy; merge laterally over the
            # outer approach section with zero lateral slope at both ends.
            points = []
            for step in range(2*TOLL_APPROACH_M+1):
                t = step / (2*TOLL_APPROACH_M); along = -TOLL_APPROACH_M + step
                base = mix(start, end, t)
                lane_point = [center[0] + along * direction[0], center[1] + along * direction[1], lane["ground_z"]]
                blend = min(1, max(0, (TOLL_APPROACH_M - abs(along)) / (TOLL_APPROACH_M-TOLL_STRAIGHT_M))); blend = blend * blend * (3 - 2 * blend)
                point = [base[k] * (1 - blend) + lane_point[k] * blend for k in range(3)]
                points.append(point)
            points[0], points[-1], points[TOLL_APPROACH_M] = start, end, [*center, lane["ground_z"]]
            for a, b in zip(points, points[1:]):
                for obstacle in gates["obstacles"]:
                    # Raised beams/arms remain physical GLB geometry; only the
                    # supplied bounded solid polygons are tested here.
                    if (min(a[2], b[2]) < obstacle["max_z"] and max(a[2], b[2]) + 2 > obstacle["min_z"]
                            and segment_hits_polygon(a, b, obstacle["polygon"])):
                        raise ValueError("Gate branch crosses solid " + obstacle["id"] + ": " + lane["id"])
            record = {"id": lane["id"], "name": "GATE_LANE " + lane["id"], "points": points,
                      "width": lane["passage_width_m"], "osm_id": way, "oneway": "yes", "vehicle": True,
                      "direction_xy": direction, "gate_id": gate["id"], "kind": "directed_gate_lane",
                      "source": lane["direction_source"], "direction_basis": lane["direction_basis"],
                      "integrationSource": OWNER, "finalGLBHeightSamplingRequired": True}
            records.append(record)
            for index, (a, b) in enumerate(zip(points, points[1:])):
                graph.add(a, b, {"id": lane["id"] + "_" + str(index), "lane_id": lane["id"], "gate_id": gate["id"],
                               "width": lane["passage_width_m"], "osm_id": way, "oneway": "yes", "highway": "service",
                               "source": lane["direction_source"], "integrationSource": OWNER})
        # Preserve mapped incoming junctions whose shared carriageway node
        # was removed by the four-lane reconstruction. Merge within the same
        # visible carriageway strip; the exact lane allocation is inferred.
        removed_nodes={index for e in removed for index in [e['a'],e['b']]}
        merged=[]
        for edge in original_edges:
            if str(edge.get('osm_id')) in gate_way_ids(gate) or edge['b'] not in removed_nodes or edge.get('oneway') not in ['yes',True,'1']:continue
            start=graph.nodes[edge['a']];end=graph.nodes[edge['b']]
            if max(abs(coordinates(p,gate)[0]) for p in [start,end])>=TOLL_APPROACH_M:continue
            source_edges=[edge]
            predecessors=[e for e in original_edges if e['b']==edge['a'] and str(e.get('osm_id'))==str(edge.get('osm_id')) and e.get('oneway') in ['yes',True,'1']]
            if len(predecessors)==1 and abs(coordinates(graph.nodes[predecessors[0]['a']],gate)[0])<30:
                source_edges=[predecessors[0],edge];start=graph.nodes[predecessors[0]['a']]
            outgoing={str(e.get('osm_id')) for e in original_edges if e['a']==edge['b'] and str(e.get('osm_id')) in gate_way_ids(gate)}
            choices=[]
            for lane_record in records:
                if lane_record.get('gate_id')!=gate['id'] or lane_record.get('kind')!='directed_gate_lane' or lane_record['osm_id'] not in outgoing:continue
                target=lane_record['points'][TOLL_APPROACH_M-10] # align ten metres before the toll center
                direction=lane_record['direction_xy'];forward=dot([target[k]-start[k] for k in [0,1]],direction)
                if forward<=.5:continue
                if any(min(start[2],target[2])<o['max_z'] and max(start[2],target[2])+1.7>o['min_z'] and segment_hits_polygon(start,target,o['polygon']) for o in gates['obstacles']):continue
                choices.append((math.dist(start[:2],target[:2]),lane_record['id'],target))
            if not choices:continue
            _,lane_id,target=min(choices)
            # The correction stays within the 8m mapped incoming pavement;
            # final visible-GLB support/body checks remain mandatory.
            distances=[]
            for original in source_edges:
                p,q=[graph.nodes[original[k]] for k in ['a','b']];dx=q[0]-p[0];dy=q[1]-p[1];t=max(0,min(1,((target[0]-p[0])*dx+(target[1]-p[1])*dy)/(dx*dx+dy*dy or 1)));distances.append(math.hypot(target[0]-p[0]-t*dx,target[1]-p[1]-t*dy))
            lateral=min(distances)
            if lateral>edge['width']/2-1.15:continue
            graph.edges=[e for e in graph.edges if not any(e['a']==old['a'] and e['b']==old['b'] and e.get('osm_id')==old.get('osm_id') for old in source_edges)]
            preserved=graph.data.setdefault('campusAccessPreservedMergeEdges',[])
            for old in source_edges:
                if not any(e['a']==old['a'] and e['b']==old['b'] for e in preserved):preserved.append(copy.deepcopy(old))
            identifier='gate_merge_'+str(edge['osm_id'])+'_'+str(edge['b'])
            record={'id':identifier,'name':'GATE_MERGE '+identifier,'osm_id':str(edge['osm_id']),'points':[start,target],'width':2.7,'vehicle':True,'oneway':'yes','kind':'directed_gate_merge','gate_id':gate['id'],'direction_xy':records[next(i for i,r in enumerate(records) if r['id']==lane_id)]['direction_xy'],'source':edge.get('source'),'integrationSource':OWNER,'originalSegments':[[graph.nodes[e['a']],graph.nodes[e['b']]] for e in source_edges],'mergeLane':lane_id,'accuracy':'Mapped common junction retained; bounded lane merge within existing pavement is reconstructed'}
            records.append(record);graph.add(start,target,{'id':identifier,'width':2.7,'osm_id':str(edge['osm_id']),'oneway':'yes','source':edge.get('source'),'integrationSource':OWNER})
            merged.append({'originalFrom':source_edges[0]['a'],'originalTo':edge['b'],'replacedNodes':sorted({i for e in source_edges for i in [e['a'],e['b']]}),'sourceOsmId':str(edge['osm_id']),'targetLane':lane_id,'target':target,'lateralCorrectionM':lateral})
        resolved_nodes={(i,m['sourceOsmId']) for m in merged for i in m['replacedNodes']}
        unresolved=[u for u in unresolved if (u['node'],str(u['osm_id'])) not in resolved_nodes]
        if unresolved:issues.append({'kind':'gate_junction_unspecified','details':unresolved,'message':'Mapped side links still need a bounded lane-merge contract.'})
        reports.append({"gateId": gate["id"], "removedLocalEdges": removed, "addedLanes": len(gate["lanes"]), "preservedMappedMerges":merged, "alongExtentMeters": [-TOLL_APPROACH_M, TOLL_APPROACH_M]})
    return records, reports


def trim_redirected_segments(roads, lanes, is_world):
    output=[]
    for road in roads:
        points=[uncv(p) for p in road['points']] if is_world else road['points'];matching=[r for r in lanes if r['kind']=='directed_gate_merge' and str(r['osm_id'])==road_way(road)]
        if not matching:output.append(road);continue
        fragments=[];current=[]
        for a,b in zip(points,points[1:]):
            redirected=False
            for merge in [segment for record in matching for segment in record['originalSegments']]:
                p,q=merge;dx=q[0]-p[0];dy=q[1]-p[1]
                def on(v):
                    t=((v[0]-p[0])*dx+(v[1]-p[1])*dy)/(dx*dx+dy*dy or 1)
                    return -.00001<=t<=1.00001 and math.hypot(v[0]-p[0]-t*dx,v[1]-p[1]-t*dy)<.001
                if on(a) and on(b):redirected=True;break
            if redirected:
                if len(current)>1:fragments.append(current)
                current=[]
            else:
                if not current:current=[a]
                current.append(b)
        if len(current)>1:fragments.append(current)
        for i,fragment in enumerate(fragments):output.append({**road,'points':[cv(p) for p in fragment] if is_world else fragment,**({'id':str(road['id'])+'_merge_part'+str(i)} if i and 'id' in road else {})})
    return output


def school_records(schools, graph):
    records = []
    for index, segment in enumerate(schools["navigation_segments"]):
        identifier = f"school_access_{segment['school_id']}_{index:03d}"
        points = segment.get("points", [segment["from"], segment["to"]])
        record = {"id": identifier, "name": "SCHOOL_ACCESS " + identifier, "points": points,
                  "width": segment["width"], "school_id": segment["school_id"], "osm_id": segment["osm_way"],
                  "vehicle": True, "kind": "school_access", "oneway": "unknown", "source": segment["source"],
                  "integrationSource": OWNER, "finalGLBHeightSamplingRequired": True}
        records.append(record)
        for a,b in zip(points,points[1:]):
            graph.add(a, b, {"id": identifier, "width": segment["width"], "school_id": segment["school_id"],
                       "osm_id": segment["osm_way"], "oneway": "unknown", "highway": "service", "source": segment["source"], "integrationSource": OWNER})
    return records


def paved_school_connection(schools, boundaries, graph, issues):
    """A bounded driveway on the visible concrete yard, not an OSM road claim."""
    if not boundaries:
        issues.append({'kind':'school175_paved_connector_unchecked','message':'Exact school boundary is required before adding the reconstructed yard connection.'})
        return []
    school=next(s for s in schools['schools'] if s['school_id']==175)
    boundary=next(s['boundary'] for s in boundaries['schools'] if s['id']==175)
    endpoints=[([781.831,-426.537],'1108554463'),([792.771,-546.844],'1366486348')]
    anchors=[]
    for xy,way in endpoints:
        matches={tuple(p) for s in schools['navigation_segments'] if str(s['osm_way'])==way for p in [s['from'],s['to']] if math.dist(p[:2],xy)<.001}
        if len(matches)!=1:raise ValueError('School paved connection requires its exact mapped endpoint: '+way)
        anchors.append(list(matches.pop()))
    xy=[endpoints[0][0],[763,-486],[764,-488],[795,-517],endpoints[1][0]]
    distances=[math.dist(a,b) for a,b in zip(xy,xy[1:])];total=sum(distances);along=0;points=[]
    for i,p in enumerate(xy):
        if i:along+=distances[i-1]
        points.append([*p,anchors[0][2]+(anchors[1][2]-anchors[0][2])*along/total])
    points[0],points[-1]=anchors
    forbidden=[b['footprint'] for b in school['buildings']]+[school['field']['boundary']]
    for a,b in zip(points,points[1:]):
        if any(segment_hits_polygon(a,b,poly) for poly in forbidden):raise ValueError('School yard connection crosses a building or sports field')
        count=math.ceil(math.dist(a[:2],b[:2])/.5)
        if any(not point_inside(mix(a,b,i/count),boundary) for i in range(count+1)):raise ValueError('School yard connection leaves its mapped paved pad')
    identifier='school175_paved_yard_connection'
    record={'id':identifier,'name':'SCHOOL_YARD '+identifier,'school_id':175,'points':points,'width':4.4,'osm_id':'RV2_SCHOOL175_PAVED_YARD','kind':'school_paved_yard_connection','oneway':'unknown','vehicle':True,'integrationSource':OWNER,'source':'Visible modeled concrete school yard, inside mapped school boundary; inferred driving connection between OSM 1108554463 and 1366486348, not a surveyed or legally verified street','sourceOsmIds':[x[1] for x in endpoints],'finalGLBHeightSamplingRequired':True}
    for a,b in zip(points,points[1:]):graph.add(a,b,{k:record[k] for k in ['id','width','school_id','osm_id','oneway','kind','source','integrationSource']})
    return [record]


def expand_bounds(world, nav, schools, boundaries, issues):
    points = []
    boundary_by_id = {str(s["id"]): s for s in boundaries.get("schools", [])} if boundaries else {}
    for school in schools["schools"]:
        source = boundary_by_id.get(str(school["school_id"]))
        if source:
            if str(source["boundary_osm_id"]) != str(school["boundary_osm_id"]) or not all(finite(p, 2) for p in source["boundary"]):
                raise ValueError("School boundary source does not match overlay")
            points.extend(source["boundary"])
        else:
            issues.append({"kind": "school_boundary_missing", "schoolId": school["school_id"],
                           "message": "Overlay omits the full pad boundary. Bounds include only supplied building footprints, field boundary and road widths; provide --school-boundaries for the full mapped pad."})
        for building in school["buildings"]:
            points.extend(building["footprint"])
        if school.get("field"):
            points.extend(school["field"]["boundary"])
    for segment in schools["navigation_segments"]:
        radius = segment["width"] / 2
        for p in [segment["from"], segment["to"]]:
            points.extend([[p[0] - radius, p[1] - radius], [p[0] + radius, p[1] + radius]])
    minx, maxx, miny, maxy = min(p[0] for p in points), max(p[0] for p in points), min(p[1] for p in points), max(p[1] for p in points)
    before = {"world": copy.deepcopy(world["bounds"]), "navigation": copy.deepcopy(nav["bounds"])}
    w, n = world["bounds"], nav["bounds"]
    w.update(minX=min(w["minX"], minx), maxX=max(w["maxX"], maxx), minZ=min(w["minZ"], -maxy), maxZ=max(w["maxZ"], -miny))
    n["min"][0], n["max"][0] = min(n["min"][0], minx), max(n["max"][0], maxx)
    n["min"][1], n["max"][1] = min(n["min"][1], miny), max(n["max"][1], maxy)
    return {"before": before, "after": {"world": w, "navigation": n}, "method": "Union existing bounds with exact mapped school pads/buildings/fields and supplied road half-widths; no remote rectangle or terrain support generated"}


def encode(value, pretty=False):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2 if pretty else None, separators=None if pretty else (",", ":")) + "\n").encode()


def atomic_write(path, raw):
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(raw)
    try:
        os.chmod(temporary, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def apply_school_road_override(schools, school_raw, overlay):
    if overlay.get('schema')!='final-school-road-ownership-1' or overlay.get('source_sha256')!=digest(school_raw):
        raise ValueError('School road replacement is not bound to this source overlay')
    updated=copy.deepcopy(schools);seen=set()
    for replacement in overlay['segment_replacements']:
        index=replacement['source_segment_index']
        if index in seen or not 0<=index<len(updated['navigation_segments']):raise ValueError('Invalid school source segment index')
        seen.add(index);before=updated['navigation_segments'][index]
        if before!=replacement['source_record']:raise ValueError('School source segment changed before bounded replacement')
        points=replacement['points'];width=replacement['width_m']
        if len(points)<2 or not all(finite(p,3) for p in points) or not 0<width<=before['width']:
            raise ValueError('Invalid supported school road profile')
        start,end=before['from'],before['to'];dx,dy=end[0]-start[0],end[1]-start[1];length=math.hypot(dx,dy)
        for p in points:
            along=((p[0]-start[0])*dx+(p[1]-start[1])*dy)/(length*length)
            lateral=abs((p[0]-start[0])*dy-(p[1]-start[1])*dx)/length
            if not -.00001<=along<=1.00001 or lateral>.001:raise ValueError('School replacement moved the mapped road XY')
        if math.dist(points[0][:2],start[:2])>.001 or math.dist(points[-1][:2],end[:2])>.001:
            raise ValueError('School replacement changed endpoint XY')
        updated['navigation_segments'][index]={**before,'from':points[0],'to':points[-1],'points':points,'width':width,
            'source':replacement['source'],'support_surface_objects':replacement['support_surface_objects']}
    return updated


def integrate(school_source, gate_source, game_root=ROOT, school_boundaries=None, dry_run=False, school_road_source=None):
    game_root, school_source, gate_source = Path(game_root).resolve(), Path(school_source).resolve(), Path(gate_source).resolve()
    boundary_path = Path(school_boundaries).resolve() if school_boundaries else school_source.with_name("source_geometry.json")
    school_raw, gate_raw = school_source.read_bytes(), gate_source.read_bytes()
    boundary_raw = boundary_path.read_bytes() if boundary_path.exists() else None
    if school_boundaries and boundary_raw is None:
        raise ValueError("Explicit school boundary file does not exist: " + str(boundary_path))
    schools, gates = json.loads(school_raw), json.loads(gate_raw)
    road_raw=Path(school_road_source).read_bytes() if school_road_source else None
    if road_raw is not None:schools=apply_school_road_override(schools,school_raw,json.loads(road_raw))
    boundaries = json.loads(boundary_raw) if boundary_raw is not None else None
    validate(schools, gates)
    world_path, nav_path, graph_path = game_root / "dist/world-config.js", game_root / "data/campus-navigation.json", game_root / "data/road-graph-3d.json"
    prefix, payload = world_path.read_text().split("export const WORLD = ", 1)
    world, nav, data = json.loads(payload.rstrip(";\n \t")), json.loads(nav_path.read_bytes()), json.loads(graph_path.read_bytes())
    actor_before = {key: copy.deepcopy(world.get(key)) for key in ("extraNPCs", "extraCars", "shuttles")}
    graph, issues = Graph(data), []
    lanes, gate_report = lane_branches(graph, gates, issues)
    roads = school_records(schools, graph)
    yard_connections=paved_school_connection(schools,boundaries,graph,issues)
    roads.extend(yard_connections)
    components = graph.finish()
    if len(components) > 1:
        issues.append({"kind": "disconnected_source_routes", "componentNodeCounts": [len(c) for c in components],
                       "message": "Supplied mapped segments have separate components; no proximity bridge or remote connection was invented."})
    issues.append({"kind": "school_direction_unspecified", "message": "School segment overlays omit legal direction/access restrictions. Their graph direction remains unknown."})
    issues.append({"kind": "runtime_direction_enforcement", "message": "Directed gate records are preserved. Existing player driving reads road corridors, not one-way graph rules; this metadata script does not change runtime enforcement."})
    bounds = expand_bounds(world, nav, schools, boundaries, issues)
    school_arrivals=[]
    for school in schools['schools']:
        identifier=str(school['school_id']);anchor_xy=school['connection_to_existing_roads']['points'][0]
        candidates=[p for segment in schools['navigation_segments'] if segment['school_id']==school['school_id'] for p in [segment['from'],segment['to']] if math.dist(p[:2],anchor_xy)<1e-6]
        if not candidates:raise ValueError('School arrival must use its exact existing mapped access anchor')
        position=candidates[0]
        destination=next((d for d in world['destinations'] if str(d['id'])==identifier),None)
        if destination is None:
            world['destinations'].append({'id':identifier,'label':school['name']+' 외부 진입로','position':cv(position),'source':'https://www.openstreetmap.org/way/'+str(school['boundary_osm_id']),'accuracy':'Mapped school access road; exterior visualization, not a verified door'})
            nav.setdefault('landmarks',[]).append({'id':school['school_id'],'label':school['name']+' 외부 진입로','position':position})
        school_arrivals.append(identifier)
        for building in school['buildings']:
            key='school_building_'+str(building['osm_id']);poly=building['footprint'];xs=[p[0] for p in poly];zs=[-p[1] for p in poly]
            world['footprints']=[f for f in world.get('footprints',[]) if f.get('id')!=key]+[{'id':key,'x':min(xs),'z':min(zs),'width':max(xs)-min(xs),'depth':max(zs)-min(zs),'label':school['name']}]
    obstacles = schools["obstacles"] + gates["obstacles"]
    obstacle_ids = {p["id"] for p in obstacles}
    road_changes = {}
    for name, target, is_world in [("world", world, True), ("navigation", nav, False)]:
        target["collisionPolygons"] = [p for p in target.get("collisionPolygons", []) if p.get("id") not in obstacle_ids]
        for obstacle in obstacles:
            item = {**copy.deepcopy(obstacle), "label": obstacle["id"], "preciseVehicle": True, "integrationSource": OWNER}
            if is_world:
                item.update(polygon=[[p[0], -p[1]] for p in obstacle["polygon"]], minY=obstacle["min_z"], maxY=obstacle["max_z"])
            target["collisionPolygons"].append(item)
        target["roads"], road_changes[name] = clip_roads(target.get("roads", []), gates["toll_gates"], is_world)
        target["roads"]=trim_redirected_segments(target["roads"],lanes,is_world)
        for record in roads + lanes:
            item = copy.deepcopy(record)
            if is_world:
                item["points"] = [cv(p) for p in item["points"]]
                if "direction_xy" in item:
                    x, y = item.pop("direction_xy")
                    item["direction"] = [x, 0, -y]
            target["roads"].append(item)
        target["pedestrianPaths"] = [p for p in target.get("pedestrianPaths", []) if p.get("integrationSource") != OWNER]
        target["pedestrianPaths"].extend({**copy.deepcopy(r), "points": [cv(p) for p in r["points"]] if is_world else copy.deepcopy(r["points"])} for r in roads)
    if actor_before != {key: world.get(key) for key in actor_before}:
        raise ValueError("Campus access integration changed existing actors")
    report = {"schema": OWNER, "sourceHashes": {"schools": digest(school_raw), "gates": digest(gate_raw)},
              "schoolDestinationIds":school_arrivals,"addedCollisionPolygons": len(obstacles), "addedSchoolSegments": sum(r['kind']=='school_access' for r in roads), "inferredPavedYardConnections":yard_connections, "addedDirectedGateLanes": sum(r["kind"]=="directed_gate_lane" for r in lanes), "addedMappedGateMerges":sum(r["kind"]=="directed_gate_merge" for r in lanes),
              "gateGraph": gate_report, "clippedRoads": road_changes, "bounds": bounds, "graphHeightJoins": graph.joins,
              "actorsPreserved": True, "solidVisualGeometryPreserved": True, "issues": issues,
              "finalGLBHeightSampling": {"required": True, "sampled": False,
                    "scope": "School segment and gate branch support heights; lane centers use supplied ground_z, endpoints interpolate existing graph anchors."}}
    if boundary_raw is not None:
        report["sourceHashes"]["schoolBoundaries"] = digest(boundary_raw)
    if road_raw is not None:report['sourceHashes']['schoolRoadReplacement']=digest(road_raw)
    world_out = prefix.encode() + b"export const WORLD = " + encode(world).rstrip(b"\n") + b";\n"
    report["outputHashes"] = {"world": digest(world_out), "navigation": digest(encode(nav)), "graph": digest(encode(data))}
    if not dry_run:
        outputs = {world_path: world_out, nav_path: encode(nav), graph_path: encode(data),
                   game_root / "data/campus-access-schools.json": school_raw, game_root / "data/campus-access-gates.json": gate_raw,
                   game_root / "data/campus-access-sync-report.json": encode(report, True)}
        if boundary_raw is not None:
            outputs[game_root / "data/campus-access-school-boundaries.json"] = boundary_raw
        if road_raw is not None:outputs[game_root/'data/campus-access-school-road-replacement.json']=road_raw
        if any(p in outputs for p in (school_source, gate_source, boundary_path)):
            raise ValueError("Source paths must differ from output paths")
        for path, raw in outputs.items():
            atomic_write(path, raw)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--school-source", type=Path, default=ROOT.parent / "realism_v2/affiliated_schools/overlay.json")
    parser.add_argument("--gate-source", type=Path, default=ROOT.parent / "realism_v2/gates_access/overlay.json")
    parser.add_argument("--school-boundaries", type=Path, help="Mapped school source_geometry.json; defaults beside school overlay if present")
    parser.add_argument("--school-road-source", type=Path, help="Native-bound actual school road ownership/height replacement")
    parser.add_argument("--game-root", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    report = integrate(args.school_source, args.gate_source, args.game_root, args.school_boundaries, args.dry_run, args.school_road_source)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
