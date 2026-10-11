"""Restore only JSON-erased tuple pairs in recorded shader internal links.

The pinned preservation helper creates list[tuple[dict, dict]] for node internal
links. JSON represents those tuples as lists. Its canonical fingerprint already
encodes list and tuple sequences identically, but its diagnostic comparison checks
Python container types. This adapter restores that original in-memory type only.
It never edits the JSON file, native scene, helper, link order, or socket values.
Every socket shape is checked and before/after fingerprints must be identical to
the immutable recorded fingerprint. All other fields retain their original types.
"""
from pathlib import Path
import copy
import hashlib
import json
import preservation as p

_SOCKET_FIELDS = {'node', 'output', 'identifier', 'index'}
_NODE_FIELDS = {'type', 'properties_sha256', 'parent', 'inputs', 'outputs', 'internal_links'}


def restore_internal_link_pairs(baseline):
    expected = baseline['original_state_sha256']
    before = p._fingerprint(baseline['datablocks'])
    if before != expected:
        raise p.PreservationError('JSON baseline fingerprint is invalid before type restoration')
    restored = copy.deepcopy(baseline)
    converted = []

    def visit(value, path):
        if isinstance(value, dict):
            if 'internal_links' in value:
                if set(value) != _NODE_FIELDS or not isinstance(value['internal_links'], list):
                    raise p.PreservationError('Unexpected internal-link record shape at ' + path)
                pairs = value['internal_links']
                for index, pair in enumerate(pairs):
                    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                        raise p.PreservationError('Internal link is not an exact two-socket pair at ' + path)
                    for socket in pair:
                        if not isinstance(socket, dict) or set(socket) != _SOCKET_FIELDS:
                            raise p.PreservationError('Unexpected socket fields at ' + path)
                        if type(socket['node']) is not str or type(socket['identifier']) is not str:
                            raise p.PreservationError('Unexpected socket identity type at ' + path)
                        if type(socket['output']) is not bool or type(socket['index']) is not int:
                            raise p.PreservationError('Unexpected socket direction/index type at ' + path)
                    if isinstance(pair, list):
                        pairs[index] = tuple(pair)
                        converted.append(f'{path}/internal_links/{index}')
            for key, item in value.items():
                visit(item, f'{path}/{key}')
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                visit(item, f'{path}/{index}')

    visit(restored['datablocks'], 'datablocks')
    after = p._fingerprint(restored['datablocks'])
    if after != expected or before != after:
        raise p.PreservationError('Internal-link type restoration changed canonical contents')
    report = {
        'status': 'PASS',
        'scope': 'Only each shader-node internal_links pair changes from JSON list to its original tuple type.',
        'restored_pair_count': len(converted),
        'restored_pair_paths': converted,
        'baseline_fingerprint_before': before,
        'baseline_fingerprint_after': after,
        'canonical_contents_unchanged': True,
        'adapter_source_sha256': p.file_sha256(__file__),
        'pinned_preservation_helper_sha256': p.file_sha256(p.__file__),
    }
    return restored, report


def load_baseline(path):
    path = Path(path)
    raw = path.read_bytes()
    baseline = json.loads(raw)
    restored, report = restore_internal_link_pairs(baseline)
    report['baseline_json_path'] = str(path.resolve())
    report['baseline_json_sha256'] = hashlib.sha256(raw).hexdigest()
    if p.file_sha256(path) != report['baseline_json_sha256']:
        raise p.PreservationError('Baseline JSON bytes changed while being read')
    return restored, report
