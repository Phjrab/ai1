"""Read-only native Blender preservation checks for additive scene revisions.

Run inside the SAME Blender major/minor version for baseline and verification.
This module never calls an operator, evaluates a dependency graph, updates a mesh,
changes selection, changes an ID, saves a .blend, or writes into the source file.

Builder::
    baseline = capture_baseline(
        expected_sha256=EXPECTED_INPUT_SHA256,
        expected_object_count=7923,
        source_paths=[__file__, preservation.__file__],
    )
    save_manifest(baseline, "qa/original_preservation.json")
    # Add new mesh objects, new materials and new lights here.
    report = compare_baseline(baseline, allowed_scene_customprops={"RV6_audit"})
    # Save the new native under a DIFFERENT path.

Fresh Blender process after opening the SAVED native::
    baseline = load_manifest("qa/original_preservation.json")
    report = compare_baseline(baseline, allowed_scene_customprops={"RV6_audit"})
    save_manifest(report, "qa/saved_native_preservation.json")

Every original datablock is addressed by its captured identity (RNA ID type,
name and linked-library path), never by a naming-prefix exemption. New datablocks
are reported separately; new objects are restricted to MESH/LIGHT by default.
Collection membership and view-layer trees permit additive links to new IDs only.
Original custom properties remain immutable. Explicitly named scene custom-property
ADDITIONS are allowed; this never authorizes changing an existing property's value.

This helper deliberately rejects inputs with any declared vertex groups or raw
MDeformVert/MDeformWeight blocks. The actual source has neither. The loaded
native is streamed independently on capture and comparison to prove absence,
including after saved-native reopen. No MeshVertex.groups getter is invoked.

Digests cover stored/native data. Selection, editor active items, dependency-graph
caches, generated tessellation/normals, ID user counts and image GPU caches are
excluded because these may change during a read, export or save/reopen. Custom
normals are checked when present. Source files are hashed as bytes. No chat, tool
configuration, environment variables, credentials or private conversation is read.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import time
from collections.abc import Mapping
from functools import lru_cache
from audit_blend_blocks import inventory as _native_block_inventory

SCHEMA = "blender-native-preservation-v2-raw-deform-guard"
EXPECTED_INPUT_SHA256 = "a65c2ae19f02c59f655e0c7eedb2482a5c2f6a9c53bb94f2425769dbd4417fbd"
EXPECTED_INPUT_OBJECTS = 7923

# Stored scene/geometry/shading/animation datablocks. UI workspaces/screens,
# window managers and brushes do not form part of native model preservation.
ID_COLLECTIONS = (
    "objects", "meshes", "materials", "node_groups", "worlds", "lights",
    "cameras", "collections", "scenes", "curves", "hair_curves", "pointclouds",
    "volumes", "metaballs", "armatures", "lattices", "shape_keys", "actions",
    "images", "textures", "fonts", "grease_pencils", "grease_pencils_v3",
    "masks", "movieclips", "sounds", "speakers", "texts", "linestyles",
    "cache_files", "particles", "palettes", "paint_curves", "libraries",
)
DEFAULT_ALLOWED_NEW_DATABLOCKS = frozenset((
    "objects", "meshes", "materials", "lights", "collections", "node_groups",
))
DEFAULT_ALLOWED_NEW_OBJECT_TYPES = frozenset(("MESH", "LIGHT"))

# Only native stored properties are hashed. Read-only scalar RNA fields are
# omitted except selected identity/type metadata; read-only pointer/collection
# properties are traversed because they contain modifiers, nodes, sockets, etc.
_BASE_SKIP = frozenset((
    "rna_type", "bl_rna", "id_data", "original", "preview", "override_library",
    "library", "users", "use_extra_user", "tag", "session_uid", "is_evaluated",
    "is_updated", "is_updated_data", "is_updated_transform", "is_library_indirect",
    "is_runtime_data", "is_editable", "is_missing", "name_full",
    "select", "is_selected", "active", "active_index", "active_node",
    "show_expanded", "is_active", "is_valid", "execution_time", "persistent_uid",
))
_READONLY_IDENTITY = frozenset((
    "type", "bl_idname", "identifier", "data_type", "domain", "is_output",
    "is_multi_input", "is_embedded_data", "has_custom_normals",
))
_OBJECT_SKIP = frozenset((
    "data", "material_slots", "modifiers", "constraints", "vertex_groups",
    "pose", "rigid_body", "rigid_body_constraint", "particle_systems",
    "matrix_world", "matrix_local", "matrix_basis", "dimensions", "bound_box",
    "mode", "users_scene", "users_collection", "children", "children_recursive",
    "face_maps", "animation_data",
))
_MESH_SKIP = frozenset((
    "vertices", "edges", "loops", "polygons", "attributes", "color_attributes",
    "uv_layers", "uv_layer_clone", "uv_layer_stencil", "vertex_colors", "materials", "loop_triangles", "loop_triangle_polygons",
    "vertex_normals", "polygon_normals", "corner_normals", "skin_vertices",
    "vertex_creases", "edge_creases", "vertex_paint_masks", "is_editmode",
    "total_vert_sel", "total_edge_sel", "total_face_sel",
))
_SCENE_SKIP = frozenset((
    "collection", "objects", "view_layers", "tool_settings", "transform_orientation_slots",
    "statistics", "sequence_editor", "node_tree", "animation_data",
))
_IMAGE_SKIP = frozenset((
    "pixels", "packed_file", "packed_files", "size", "channels", "depth",
    "has_data", "is_float", "is_dirty", "bindcode", "render_slots",
))
_NODETREE_SKIP = frozenset(("nodes", "links", "interface", "view_center", "active_input", "active_output"))
_NODE_SKIP = frozenset(("inputs", "outputs", "internal_links", "dimensions", "parent"))
_SOCKET_SKIP = frozenset(("node", "links", "is_linked", "is_unavailable"))
_COLLECTION_SKIP = frozenset(("objects", "all_objects", "children", "children_recursive", "collection_objects", "collection_children"))


class PreservationError(RuntimeError):
    """A missing/changed original, unexpected addition, or capture failure."""

    def __init__(self, message, report=None):
        super().__init__(message)
        self.report = report


def _blender():
    try:
        import bpy
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Run this preservation module inside Blender Python") from exc
    return bpy, np


def file_sha256(path, chunk_bytes=4 * 1024 * 1024):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_bytes), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_digests(paths):
    """Byte digests of explicitly supplied source files, with portable basenames."""
    result = {}
    for source in sorted({str(Path(p).resolve()) for p in paths}):
        path = Path(source)
        if not path.is_file():
            raise PreservationError(f"Missing script source: {source}")
        result[source] = {"filename": path.name, "sha256": file_sha256(path), "bytes": path.stat().st_size}
    return result


def _id_ref(value):
    if value is None:
        return None
    library = value.library.filepath if getattr(value, "library", None) else ""
    return {"id_type": value.bl_rna.identifier, "name": value.name, "library": library}


def _id_key(value):
    ref = _id_ref(value)
    return json.dumps([ref["id_type"], ref["name"], ref["library"]], ensure_ascii=True, separators=(",", ":"))


class _Hash:
    """Typed canonical streaming hash; large values need not become JSON."""

    def __init__(self):
        self._hash = hashlib.sha256()

    def raw(self, kind, data):
        self._hash.update(kind)
        self._hash.update(struct.pack("<Q", len(data)))
        self._hash.update(data)

    def add(self, value):
        if value is None:
            self.raw(b"N", b"")
        elif isinstance(value, bool):
            self.raw(b"B", b"1" if value else b"0")
        elif isinstance(value, int):
            self.raw(b"I", str(value).encode("ascii"))
        elif isinstance(value, float):
            # Preserve native floating-point values, including signed zero.
            self.raw(b"F", struct.pack("<d", value))
        elif isinstance(value, str):
            self.raw(b"S", value.encode("utf8", "surrogatepass"))
        elif isinstance(value, (bytes, bytearray, memoryview)):
            self.raw(b"Y", value)
        elif isinstance(value, Mapping) or hasattr(value, "keys"):
            keys = sorted(value.keys())
            self.add(("mapping", len(keys)))
            for key in keys:
                self.add(key)
                self.add(value[key])
        elif isinstance(value, (set, frozenset)):
            self.add(sorted(value))
        else:
            try:
                values = iter(value)
                count = len(value)
            except (TypeError, AttributeError) as exc:
                raise PreservationError(f"Unsupported value type in digest: {type(value).__name__}") from exc
            self.raw(b"L", struct.pack("<Q", count))
            for item in values:
                self.add(item)
        return self

    def hexdigest(self):
        return self._hash.hexdigest()


def _digest(value):
    return _Hash().add(value).hexdigest()


def _customprops(value):
    """Only hashes leave this function; custom values are never written to QA."""
    result = {}
    try:
        keys = value.keys()
    except (AttributeError, TypeError):
        return result
    bpy, _ = _blender()
    for key in sorted(keys):
        item = value[key]
        result[key] = _digest(_id_ref(item) if isinstance(item, bpy.types.ID) else item)
    return result


def _rna_hash(value, *, skip=(), customprops=True):
    """Hash stored RNA recursively; ID pointers become stable identity references.

    Read failures are fatal. They never become silently skipped preservation data.
    """
    sink = _Hash()
    _rna_into(sink, value, frozenset(skip), customprops=customprops, depth=0)
    return sink.hexdigest()


def _rna_into(sink, value, skip=frozenset(), *, customprops=True, depth=0, ancestry=()):
    bpy, _ = _blender()
    if value is None:
        sink.add(None)
        return
    pointer = value.as_pointer()
    if pointer in ancestry:
        sink.add(("RNA cycle to ancestor", ancestry.index(pointer), value.bl_rna.identifier))
        return
    ancestry = (*ancestry, pointer)
    if depth > 32:
        raise PreservationError(f"Unexpected recursive RNA at {type(value).__name__}")
    sink.add(value.bl_rna.identifier)
    for prop in sorted(value.bl_rna.properties, key=lambda p: p.identifier):
        name = prop.identifier
        if name in _BASE_SKIP or name in skip:
            continue
        kind = prop.type
        if prop.is_readonly and kind not in {"POINTER", "COLLECTION"} and name not in _READONLY_IDENTITY:
            continue
        # Reading an unset Python-registered PropertyGroup/collection can create
        # its IDProperty backing storage. Preserve the unset state BEFORE the
        # getter runs; initialized groups remain fully traversed and hashed.
        if kind in {"POINTER", "COLLECTION"} and prop.is_runtime and not value.is_property_set(name):
            sink.add(name)
            sink.add(("UNSET_REGISTERED_PROPERTY", kind))
            continue
        try:
            item = getattr(value, name)
        except Exception as exc:
            raise PreservationError(f"Cannot read {value.bl_rna.identifier}.{name}: {exc}") from exc
        sink.add(name)
        if kind == "POINTER":
            if item is None:
                sink.add(None)
            elif isinstance(item, bpy.types.ID):
                sink.add(_id_ref(item))
            elif isinstance(item, bpy.types.Node):
                sink.add({"node": item.name, "tree": _id_ref(item.id_data)})
            elif isinstance(item, bpy.types.NodeSocket):
                sink.add(_socket_ref(item))
            else:
                _rna_into(sink, item, customprops=customprops, depth=depth + 1, ancestry=ancestry)
        elif kind == "COLLECTION":
            sink.add(len(item))
            for child in item:
                if isinstance(child, bpy.types.ID):
                    sink.add(_id_ref(child))
                else:
                    _rna_into(sink, child, customprops=customprops, depth=depth + 1, ancestry=ancestry)
        else:
            sink.add(item)
    if customprops:
        sink.add(_customprops(value))


def _array_into(sink, collection, property_name, dtype, width=1):
    """One contiguous NumPy array per native property, released immediately.

    foreach_get avoids constructing millions of Python vectors/integers. No large
    coordinate lists or topology copies survive the call. Memory is bounded by
    the largest single mesh/property, not all meshes or an evaluated scene copy.
    """
    _, np = _blender()
    length = len(collection)
    sink.add((property_name, length, width, dtype))
    if not length:
        return
    array = np.empty(length * width, dtype=np.dtype(dtype))
    try:
        collection.foreach_get(property_name, array)
    except Exception as exc:
        raise PreservationError(f"Cannot foreach_get {property_name}, {length} items: {exc}") from exc
    sink.raw(b"A", memoryview(array).cast("B"))


def _collection_arrays(collection, fields):
    sink = _Hash()
    for name, dtype, width in fields:
        # Optional version-specific fields are recorded as absent, not silently
        # omitted on only one side of a comparison.
        if not len(collection) or hasattr(collection[0], name):
            _array_into(sink, collection, name, dtype, width)
        else:
            sink.add((name, "unavailable"))
    return sink.hexdigest()


def _attribute_values(attribute):
    dtype = attribute.data_type
    fields = {
        "FLOAT": [("value", "<f4", 1)],
        "INT": [("value", "<i4", 1)],
        "INT8": [("value", "i1", 1)],
        "INT32_2D": [("value", "<i4", 2)],
        "BOOLEAN": [("value", "?", 1)],
        "FLOAT_VECTOR": [("vector", "<f4", 3)],
        "FLOAT2": [("vector", "<f4", 2)],
        "FLOAT_COLOR": [("color", "<f4", 4)],
        "BYTE_COLOR": [("color_srgb", "<f4", 4)],
        "QUATERNION": [("value", "<f4", 4)],
        "FLOAT4X4": [("value", "<f4", 16)],
    }
    if dtype in fields:
        return _collection_arrays(attribute.data, fields[dtype])
    if dtype == "STRING":
        return _digest([entry.value for entry in attribute.data])
    # Explicit fallback for future Blender attribute storage types.
    sink = _Hash().add(dtype).add(len(attribute.data))
    for entry in attribute.data:
        _rna_into(sink, entry)
    return sink.hexdigest()


def _is_selection_attribute(name):
    return name in {".select_vert", ".select_edge", ".select_poly", ".selection"} or name.startswith((".vs.", ".es."))


@lru_cache(maxsize=2048)
def _empty_deform_weight_digest(vertex_count):
    # Exact canonical digest used for an empty group list on every vertex, with
    # bounded byte batches instead of invoking any per-vertex RNA accessor.
    empty_list = b"L" + struct.pack("<Q", 8) + struct.pack("<Q", 0)
    digest = hashlib.sha256()
    for start in range(0, vertex_count, 65536):
        digest.update(empty_list * min(65536, vertex_count - start))
    return digest.hexdigest()


def _deform_storage_guard(native_path, originals=None):
    bpy, _ = _blender()
    if not native_path or not Path(native_path).is_file():
        raise PreservationError("Deform-storage proof requires an existing, loaded native file")
    declared = {}
    for obj in bpy.data.objects:
        if originals is not None and _id_key(obj) not in originals.get("objects", set()):
            continue
        if len(obj.vertex_groups):
            declared[obj.name] = len(obj.vertex_groups)
    raw = _native_block_inventory(native_path)
    storage = {name: raw["native_types"].get(name, {}).get("payload_bytes", 0)
               for name in ("MDeformVert", "MDeformWeight")}
    reasons = []
    if declared:
        reasons.append("Original declared vertex groups are unsupported by this input-specific preservation helper")
    if any(storage.values()):
        reasons.append("Native MDeformVert/MDeformWeight storage is present; rejecting rather than invoking mutating RNA getters")
    return {"status": "PASS" if not reasons else "FAIL", "native_path": str(Path(native_path).resolve()),
            "decompressed_native_sha256": raw["decompressed_sha256"],
            "decompressed_native_bytes": raw["decompressed_bytes"],
            "raw_inventory_reader_backend": raw["reader_backend"],
            "raw_inventory_reader_executable": raw["reader_python_executable"],
            "raw_inventory_reader_source_sha256": raw["reader_source_sha256"],
            "zstandard_read_across_frames": raw["zstandard_read_across_frames"],
            "native_deform_storage_bytes": storage, "objects_with_declared_vertex_groups": declared,
            "no_per_vertex_group_getter_used": True, "reasons": reasons}


def _mesh_record(mesh):
    positions = _collection_arrays(mesh.vertices, [("co", "<f4", 3)])
    topology = _Hash()
    topology.add(_collection_arrays(mesh.edges, [("vertices", "<i4", 2), ("use_seam", "?", 1), ("use_edge_sharp", "?", 1), ("hide", "?", 1)]))
    topology.add(_collection_arrays(mesh.loops, [("vertex_index", "<i4", 1), ("edge_index", "<i4", 1)]))
    topology.add(_collection_arrays(mesh.polygons, [("loop_start", "<i4", 1), ("loop_total", "<i4", 1), ("material_index", "<i4", 1), ("use_smooth", "?", 1), ("hide", "?", 1)]))
    topology.add(_collection_arrays(mesh.vertices, [("hide", "?", 1)]))
    attrs = {}
    for attribute in sorted(mesh.attributes, key=lambda a: a.name):
        if _is_selection_attribute(attribute.name):
            continue
        attrs[attribute.name] = {
            "domain": attribute.domain,
            "data_type": attribute.data_type,
            "count": len(attribute.data),
            "sha256": _attribute_values(attribute),
        }
    uv = []
    for layer in mesh.uv_layers:
        # MeshUVLoop.pin_uv GETTERS can allocate a native .pn.<uv> attribute.
        # Read backing attributes only; never access that mutating legacy API.
        uv.append({"name": layer.name, "active_render": layer.active_render,
                   "active_clone": layer.active_clone,
                   "data_sha256": attrs[layer.name]["sha256"]})
    # Blender 4.3 MeshVertex.groups is NOT a read-only getter: its iterator
    # allocates a CD_MDEFORMVERT layer when absent. This input-specific helper
    # first proves raw native deform storage and object group declarations are
    # absent. Never touch that getter, even to ask whether a list is empty.
    groups_sha256 = _empty_deform_weight_digest(len(mesh.vertices))
    custom_normals = None
    if mesh.has_custom_normals:
        custom_normals = _collection_arrays(mesh.corner_normals, [("vector", "<f4", 3)])
    skins = _Hash()
    for layer in mesh.skin_vertices:
        skins.add(layer.name)
        skins.add(_collection_arrays(layer.data, [("radius", "<f4", 2), ("use_root", "?", 1), ("use_loose", "?", 1)]))
    return {
        "counts": {"vertices": len(mesh.vertices), "edges": len(mesh.edges), "loops": len(mesh.loops), "polygons": len(mesh.polygons)},
        "positions_sha256": positions,
        "topology_sha256": topology.hexdigest(),
        "attributes": attrs,
        "uv_layers": uv,
        "color_attribute_settings": {name: getattr(mesh.color_attributes, name) for name in ("active_color_name", "default_color_name", "render_color_index") if hasattr(mesh.color_attributes, name)},
        "deform_weights_sha256": groups_sha256,
        "deform_storage_policy": "native absence required; no MeshVertex.groups access",
        "custom_normals_sha256": custom_normals,
        "skin_vertices_sha256": skins.hexdigest(),
        "material_slots": [_id_ref(item) for item in mesh.materials],
        "properties_sha256": _rna_hash(mesh, skip=_MESH_SKIP),
    }


def _socket_ref(socket):
    node = socket.node
    sockets = node.outputs if socket.is_output else node.inputs
    index = next(i for i, candidate in enumerate(sockets) if candidate == socket)
    return {"node": node.name, "output": socket.is_output, "identifier": socket.identifier, "index": index}


def _node_tree_record(tree):
    if tree is None:
        return None
    nodes = {}
    for node in sorted(tree.nodes, key=lambda n: n.name):
        nodes[node.name] = {
            "type": node.bl_idname,
            "properties_sha256": _rna_hash(node, skip=_NODE_SKIP),
            "parent": node.parent.name if node.parent else None,
            "inputs": [_rna_hash(socket, skip=_SOCKET_SKIP) for socket in node.inputs],
            "outputs": [_rna_hash(socket, skip=_SOCKET_SKIP) for socket in node.outputs],
            "internal_links": sorted([(_socket_ref(link.from_socket), _socket_ref(link.to_socket)) for link in node.internal_links], key=lambda item: json.dumps(item, sort_keys=True)),
        }
    links = []
    for link in tree.links:
        links.append({"from": _socket_ref(link.from_socket), "to": _socket_ref(link.to_socket),
                      "muted": link.is_muted,
                      "multi_input_sort_id": getattr(link, "multi_input_sort_id", None)})
    links.sort(key=lambda item: json.dumps(item, sort_keys=True))
    return {
        "properties_sha256": _rna_hash(tree, skip=_NODETREE_SKIP),
        "nodes": nodes,
        "links_sha256": _digest(links),
        "interface_sha256": _rna_hash(tree.interface) if hasattr(tree, "interface") else None,
    }


def _object_record(obj):
    return {
        "type": obj.type,
        "data": _id_ref(obj.data),
        "properties_sha256": _rna_hash(obj, skip=_OBJECT_SKIP),
        "collections": sorted(_id_key(c) for c in obj.users_collection),
        "material_slots": [{"link": slot.link, "material": _id_ref(slot.material)} for slot in obj.material_slots],
        "modifiers_sha256": _digest([_rna_hash(modifier) for modifier in obj.modifiers]),
        "constraints_sha256": _digest([_rna_hash(constraint) for constraint in obj.constraints]),
        "vertex_groups_sha256": _digest([_rna_hash(group) for group in obj.vertex_groups]),
        "pose_sha256": _rna_hash(obj.pose) if obj.pose else None,
        "rigid_body_sha256": _rna_hash(obj.rigid_body) if obj.rigid_body else None,
        "rigid_body_constraint_sha256": _rna_hash(obj.rigid_body_constraint) if obj.rigid_body_constraint else None,
        "particle_systems_sha256": _digest([_rna_hash(system) for system in obj.particle_systems]),
        "animation_sha256": _rna_hash(obj.animation_data) if obj.animation_data else None,
    }


def _filtered_keys(collection, original_keys):
    keys = sorted(_id_key(item) for item in collection)
    return keys if original_keys is None else [key for key in keys if key in original_keys]


def _collection_record(collection, originals):
    return {
        "properties_sha256": _rna_hash(collection, skip=_COLLECTION_SKIP),
        "objects": _filtered_keys(collection.objects, originals.get("objects") if originals else None),
        "children": _filtered_keys(collection.children, originals.get("collections") if originals else None),
    }


def _layer_tree(layer_collection, original_collections):
    result = {}
    def visit(layer, path):
        collection = layer.collection
        key = _id_key(collection)
        is_original = original_collections is None or key in original_collections or not path
        current = path + (key,)
        if is_original:
            result[json.dumps(current, separators=(",", ":"))] = _rna_hash(
                layer, skip=("children", "collection", "parent", "is_visible", "visible_get"))
        for child in layer.children:
            visit(child, current)
    visit(layer_collection, ())
    return result


def _scene_record(scene, originals):
    object_keys = originals.get("objects") if originals else None
    collection_keys = originals.get("collections") if originals else None
    views = {}
    for layer in scene.view_layers:
        hidden = {}
        for obj in layer.objects:
            key = _id_key(obj)
            if object_keys is None or key in object_keys:
                hidden[key] = bool(obj.hide_get(view_layer=layer))
        views[layer.name] = {
            "properties_sha256": _rna_hash(layer, skip=("objects", "layer_collection", "active_layer_collection", "depsgraph")),
            "layer_collections": _layer_tree(layer.layer_collection, collection_keys),
            "object_hide_state": hidden,
        }
    return {
        "properties_sha256": _rna_hash(scene, skip=_SCENE_SKIP, customprops=False),
        "customprops": _customprops(scene),
        "objects": _filtered_keys(scene.objects, object_keys),
        "root_collection": _collection_record(scene.collection, originals),
        "view_layers": views,
        "node_tree": _node_tree_record(scene.node_tree),
        "animation_sha256": _rna_hash(scene.animation_data) if scene.animation_data else None,
        "sequence_editor_sha256": _rna_hash(scene.sequence_editor) if scene.sequence_editor else None,
    }


def _image_record(image):
    packed = []
    for item in image.packed_files:
        packed.append({"filepath": item.filepath, "sha256": _digest(item.packed_file.data),
                       "size": item.packed_file.size})
    if not packed and image.packed_file:
        packed.append({"sha256": _digest(image.packed_file.data), "size": image.packed_file.size})
    return {"properties_sha256": _rna_hash(image, skip=_IMAGE_SKIP), "packed": packed}


def _id_record(category, item, originals):
    if category == "objects":
        return _object_record(item)
    if category == "meshes":
        return _mesh_record(item)
    if category == "node_groups":
        return _node_tree_record(item)
    if category == "collections":
        return _collection_record(item, originals)
    if category == "scenes":
        return _scene_record(item, originals)
    if category == "images":
        return _image_record(item)
    if category == "texts":
        return {"properties_sha256": _rna_hash(item, skip=("lines",)), "text_sha256": _digest(item.as_string())}
    record = {"properties_sha256": _rna_hash(item, skip=("node_tree",))}
    if hasattr(item, "node_tree"):
        record["node_tree"] = _node_tree_record(item.node_tree)
    return record


def _native_items(category):
    bpy, _ = _blender()
    items = getattr(bpy.data, category)
    if category == "images":
        # Blender creates these render/compositor buffers at runtime. They are
        # not persistent image assets and may vanish or appear after export.
        return (item for item in items if item.type not in {"RENDER_RESULT", "COMPOSITING"})
    return items


def _capture(originals=None):
    bpy, _ = _blender()
    result = {}
    for category in ID_COLLECTIONS:
        if not hasattr(bpy.data, category):
            continue
        records = {}
        for item in sorted(_native_items(category), key=_id_key):
            key = _id_key(item)
            if originals is not None and key not in originals.get(category, set()):
                continue
            try:
                records[key] = _id_record(category, item, originals)
            except PreservationError:
                raise
            except Exception as exc:
                raise PreservationError(f"Could not capture {category}/{item.name}: {exc}") from exc
        result[category] = records
    return result


def _original_sets(baseline):
    return {category: set(records) for category, records in baseline["datablocks"].items()}


def _fingerprint(datablocks):
    return _digest(datablocks)


def capture_baseline(scene=None, *, source_path=None, expected_sha256=None,
                     expected_object_count=None, source_paths=()):
    """Capture all original native IDs; return a compact JSON-compatible record.

    `scene` is accepted for builder convenience. All scenes are protected. Set
    expected_sha256 and expected_object_count to anchor this to the intended input.
    Script source paths are explicit; this helper's own bytes are always included.
    """
    bpy, _ = _blender()
    start = time.monotonic()
    if scene is not None and scene not in list(bpy.data.scenes):
        raise PreservationError("The supplied scene is not in bpy.data.scenes")
    source = Path(source_path or bpy.data.filepath).resolve() if (source_path or bpy.data.filepath) else None
    if source_path and Path(bpy.data.filepath).resolve() != source:
        raise PreservationError("Loaded native does not match source_path")
    source_sha = file_sha256(source) if source else None
    if expected_sha256 and source_sha != expected_sha256:
        raise PreservationError(f"Input SHA-256 mismatch: expected {expected_sha256}, got {source_sha}")
    if expected_object_count is not None and len(bpy.data.objects) != expected_object_count:
        raise PreservationError(f"Original object count mismatch: expected {expected_object_count}, got {len(bpy.data.objects)}")
    # Explicit immutable original sets ensure baseline and comparison apply the
    # identical collection/view-layer filtering rules from the very first pass.
    originals = {category: {_id_key(item) for item in _native_items(category)}
                 for category in ID_COLLECTIONS if hasattr(bpy.data, category)}
    deform_guard = _deform_storage_guard(source, originals)
    if deform_guard["status"] != "PASS":
        raise PreservationError("; ".join(deform_guard["reasons"]))
    datablocks = _capture(originals)
    record = {
        "schema": SCHEMA,
        "blender_version": list(bpy.app.version),
        "source_native": {"path": str(source) if source else None, "sha256": source_sha},
        "source_files": source_digests([Path(__file__), Path(__file__).with_name("audit_blend_blocks.py"), *source_paths]),
        "input_native_deform_storage_guard": deform_guard,
        "original_object_count": len(bpy.data.objects),
        "counts": {category: len(items) for category, items in datablocks.items()},
        "datablocks": datablocks,
        "original_state_sha256": _fingerprint(datablocks),
        "capture_seconds": round(time.monotonic() - start, 3),
        "coverage": {
            "native_original_ids_only": True,
            "original_mesh_arrays_attributes_uvs_weights_and_custom_normals": True,
            "original_object_transforms_parents_visibility_materials_and_modifiers": True,
            "original_materials_node_trees_node_groups_lights_worlds_and_cameras": True,
            "original_animation_collections_and_view_layer_visibility": True,
            "source_script_byte_digests": True,
            "excluded": ["selection/editor active items", "dependency-graph/evaluated caches", "generated tessellation/normals when no custom normals", "UI screens/workspaces/window managers/brushes", "generated Render Result/Viewer image buffers", "external texture file bytes (native paths and packed bytes are checked)"],
        },
    }
    if source and file_sha256(source) != source_sha:
        raise PreservationError("Source native bytes changed during baseline capture")
    return record


def _differences(before, after, path="", limit=60):
    result = []
    def visit(left, right, prefix):
        if len(result) >= limit:
            return
        if type(left) is not type(right):
            result.append(prefix + ": type changed")
        elif isinstance(left, dict):
            for key in sorted(left.keys() - right.keys()):
                result.append(f"{prefix}/{key}: missing")
                if len(result) >= limit:
                    return
            for key in sorted(right.keys() - left.keys()):
                result.append(f"{prefix}/{key}: unexpected addition")
                if len(result) >= limit:
                    return
            for key in sorted(left.keys() & right.keys()):
                visit(left[key], right[key], f"{prefix}/{key}")
        elif isinstance(left, list):
            if len(left) != len(right):
                result.append(f"{prefix}: length {len(left)} -> {len(right)}")
            else:
                for index, (a, b) in enumerate(zip(left, right)):
                    visit(a, b, f"{prefix}/{index}")
        elif left != right:
            # Don't leak custom values into QA output; identify the path only.
            result.append(prefix + ": changed")
    visit(before, after, path)
    return result[:limit]


def compare_baseline(baseline, *, allowed_scene_customprops=(), raise_on_error=True,
                     allowed_new_datablocks=DEFAULT_ALLOWED_NEW_DATABLOCKS,
                     allowed_new_object_types=DEFAULT_ALLOWED_NEW_OBJECT_TYPES,
                     verify_source_files=True, verify_source_native=True):
    """Compare every original ID, also usable after reopening a saved native.

    Returns a machine-readable PASS/FAIL report; raises PreservationError carrying
    `.report` on failure by default. New IDs are explicitly inventoried. Source
    comparison can be disabled only when reviewing a relocated delivery package;
    such omissions remain visible as NOT_CHECKED in the returned report.
    """
    bpy, _ = _blender()
    start = time.monotonic()
    if baseline.get("schema") != SCHEMA:
        raise PreservationError("Unsupported or missing preservation schema")
    if tuple(baseline["blender_version"][:2]) != tuple(bpy.app.version[:2]):
        raise PreservationError("Use the same Blender major/minor for exact native preservation comparisons")
    if _fingerprint(baseline["datablocks"]) != baseline["original_state_sha256"]:
        raise PreservationError("Baseline manifest fingerprint is invalid")
    originals = _original_sets(baseline)
    deform_guard = _deform_storage_guard(bpy.data.filepath, originals)
    current = _capture(originals)
    additions = {}
    disallowed = []
    for category in ID_COLLECTIONS:
        if not hasattr(bpy.data, category):
            continue
        extra = [item for item in _native_items(category) if _id_key(item) not in originals.get(category, set())]
        if not extra:
            continue
        additions[category] = [_id_ref(item) for item in sorted(extra, key=_id_key)]
        if category not in allowed_new_datablocks:
            disallowed.append(f"New {category} datablocks are not allowed")
        if category == "objects":
            for item in extra:
                if item.type not in allowed_new_object_types:
                    disallowed.append(f"New object {item.name} has disallowed type {item.type}")
    allowed_names = set(allowed_scene_customprops)
    intentional_scene_additions = {}
    for key, original in baseline["datablocks"].get("scenes", {}).items():
        if key not in current.get("scenes", {}):
            continue
        properties = current["scenes"][key]["customprops"]
        extra_names = properties.keys() - original["customprops"].keys()
        permitted = sorted(extra_names & allowed_names)
        intentional_scene_additions[key] = {name: properties.pop(name) for name in permitted}
    diffs = _differences(baseline["datablocks"], current, "datablocks")
    diffs.extend(deform_guard["reasons"])
    source_status = "NOT_CHECKED"
    source_path = baseline["source_native"]["path"]
    if verify_source_native and source_path:
        source_status = "PASS" if Path(source_path).is_file() and file_sha256(source_path) == baseline["source_native"]["sha256"] else "FAIL"
        if source_status != "PASS":
            diffs.append("source_native: original file is missing or its bytes changed")
    scripts_status = "NOT_CHECKED"
    changed_scripts = []
    if verify_source_files:
        for path, original in baseline["source_files"].items():
            if not Path(path).is_file() or file_sha256(path) != original["sha256"]:
                changed_scripts.append(path)
        scripts_status = "FAIL" if changed_scripts else "PASS"
        diffs.extend(f"source_file: changed or missing {path}" for path in changed_scripts)
    report = {
        "schema": SCHEMA,
        "status": "PASS" if not diffs and not disallowed else "FAIL",
        "loaded_native": str(Path(bpy.data.filepath).resolve()) if bpy.data.filepath else None,
        "blender_version": list(bpy.app.version),
        "original_object_count": baseline["original_object_count"],
        "original_counts": baseline["counts"],
        "current_object_count": len(bpy.data.objects),
        "original_state_sha256": baseline["original_state_sha256"],
        "observed_original_state_sha256": _fingerprint(current),
        "source_native_bytes": source_status,
        "source_script_bytes": scripts_status,
        "loaded_native_deform_storage_guard": deform_guard,
        "new_datablock_counts": {category: len(items) for category, items in additions.items()},
        "new_datablocks": additions,
        "permitted_new_scene_customprops": intentional_scene_additions,
        "differences": diffs,
        "disallowed_additions": disallowed,
        "verification_seconds": round(time.monotonic() - start, 3),
        "read_only": True,
    }
    if report["status"] != "PASS" and raise_on_error:
        raise PreservationError("Native preservation FAILED: " + "; ".join((diffs + disallowed)[:8]), report)
    return report


def save_manifest(record, path):
    """Write a QA JSON only; never write or modify any native model."""
    path = Path(path)
    if path.suffix.lower() != ".json":
        raise PreservationError("Preservation manifests must have a .json extension")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n", encoding="utf8")
    return str(path.resolve())


def load_manifest(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


capture_original = capture_baseline
assert_unchanged = compare_baseline
