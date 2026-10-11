#!/usr/bin/env python3
"""Export a deterministic source ZIP with exactly bound release QA evidence."""
from pathlib import Path
import hashlib
import json
import runpy
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT.parent / 'Chosun_Campus_Walk_Source.zip'
EXCLUDED = {'.openai', '.git', 'node_modules', '.sites-runtime', 'qa', '__pycache__', 'historical-results', '.cache', '.pytest_cache', '.mypy_cache'}
SOURCE_DIRS = {'data', 'dist', 'scripts', 'tests'}
SOURCE_FILES = {'.gitignore', 'LICENSES.md', 'MODEL_PROVENANCE.json', 'QA.md', 'README.md', 'package.json', 'package-lock.json'}
SOURCE_SUFFIXES = {'.json', '.js', '.mjs', '.py', '.glb', '.txt', '.css', '.html', '.md', '.log'}
PRIVATE_NAMES = {'credentials.json', 'secrets.json', 'token.json', 'tokens.json'}

# Import read-only helpers without executing their CLI, then require a full release.
verifier = runpy.run_path(str(ROOT / 'scripts/verify-release.py'))
verifier['verify'](ROOT)
local_path = verifier['local_path']
QA_FILES = set()
QA_LOGS = set()
index = json.loads((ROOT / 'tests/FINAL_VALIDATION.json').read_text())


def evidence(name, wanted):
    path = local_path(ROOT, name)
    if hashlib.sha256(path.read_bytes()).hexdigest() != wanted:
        raise ValueError('QA evidence differs: ' + name)
    QA_FILES.add(name)
    if path.suffix == '.log':
        QA_LOGS.add(name)


for row in index['requiredReports'] + index.get('diagnosticReports', []):
    evidence(row['report'], row['sha256'])
    report = json.loads((ROOT / row['report']).read_text())
    archive = Path(row.get('archiveRoot', '.'))
    for name, wanted in {**report['resultSnapshots'], report['log']: report['logSha256']}.items():
        evidence((archive / name).as_posix(), wanted)
for name, wanted in index['historicalFullWalk']['artifacts'].items():
    evidence(name, wanted)
tyre_change_entry = index['tyreContactSourceChange']
evidence(tyre_change_entry['path'], tyre_change_entry['sha256'])
tyre_change = json.loads((ROOT / tyre_change_entry['path']).read_text())
for change in tyre_change['changes']:
    evidence(change['preserved'], change['before'])
    evidence('tests/source-history/tyre-footprint-uncached/' + Path(change['file']).name, change['uncached_footprint_sha256'])
    evidence(change['file'], change['after'])
acceptance_entry = index['siteCloseoutAcceptance']
evidence(acceptance_entry['path'], acceptance_entry['sha256'])
acceptance = json.loads((ROOT / acceptance_entry['path']).read_text())
for name, wanted in acceptance['inputSha256'].items():
    evidence(name, wanted)
realism_entry = index['realismAcceptance']
evidence(realism_entry['path'], realism_entry['sha256'])
independent = realism_entry['independentClassification']
evidence(independent['path'], independent['sha256'])
realism_acceptance = json.loads((ROOT / realism_entry['path']).read_text())
for name, wanted in realism_acceptance['inputSha256'].items():
    evidence(name, wanted)
# Preserve explicitly hashed closeout logs alongside their unchanged source reports.
for manifest in sorted((ROOT / 'tests/closeout-evidence').rglob('sha256.json')):
    for name, wanted in json.loads(manifest.read_text()).items():
        relative = manifest.parent.relative_to(ROOT) / name
        evidence(relative.as_posix(), wanted)


def sources():
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        name = relative.as_posix()
        if not path.is_file() or path.is_symlink() or path.resolve() == OUTPUT:
            continue
        if any(part in EXCLUDED or part.startswith('.env') for part in relative.parts):
            continue
        if any(part.startswith('.') for part in relative.parts) and name != '.gitignore':
            continue
        if path.name.lower() in PRIVATE_NAMES:
            continue
        if len(relative.parts) == 1:
            if relative.name not in SOURCE_FILES:
                continue
        elif relative.parts[0] not in SOURCE_DIRS:
            continue
        if path.suffix not in SOURCE_SUFFIXES and name != '.gitignore':
            continue
        if path.suffix == '.log' and name not in QA_LOGS:
            continue
        if relative.parts[:2] in (('tests', 'runtime-runs'), ('tests', 'baseline-evidence')) and name not in QA_FILES:
            continue
        if relative.parts[0] == 'tests' and path.name.endswith('-candidate-results.json'):
            continue
        yield name, path.read_bytes()


def put(archive, name, data):
    info = zipfile.ZipInfo('Chosun_Campus_Walk/' + name, date_time=(2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)


files = list(sources())
release = json.loads((ROOT / 'dist/release-manifest.json').read_text())
required = {'tests/FINAL_VALIDATION.json', 'tests/BASELINE_EVIDENCE.json', 'tests/tyre-footprint-unit-results.json', 'dist/release-manifest.json'} | {'dist/' + name for name in release['files']} | QA_FILES
missing = required - {name for name, _ in files}
if missing:
    raise SystemExit('Missing release/evidence files: ' + ', '.join(sorted(missing)))
manifest = {'format': 1, 'files': {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} for name, data in files}}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(OUTPUT, 'w') as archive:
    for name, data in files:
        put(archive, name, data)
    put(archive, 'SOURCE_MANIFEST.json', (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode())
print(json.dumps({'archive': str(OUTPUT), 'files': len(files) + 1, 'bytes': OUTPUT.stat().st_size, 'sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}))
