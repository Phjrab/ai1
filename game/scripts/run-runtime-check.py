#!/usr/bin/env python3
"""Run one runtime check and bind its log/results to the exact game inputs."""
import datetime
import hashlib
import json
import pathlib
import resource
import shutil
import subprocess
import sys
import time

root = pathlib.Path(__file__).resolve().parents[1]
# Optional external memory barrier used by the coordinated final validation queue.
gate = root.parent / 'runtime_loader_pause.json'
while gate.exists() and json.loads(gate.read_text()).get('hold', False):
    time.sleep(1)
settings = json.loads(gate.read_text()) if gate.exists() else {}
control = pathlib.Path(settings['catalogueControlDirectory']) if settings.get('catalogueControlDirectory') else None
if control and control.exists():
    (control / 'pause_after_current').touch()
    while True:
        state = json.loads((control / 'status.json').read_text())
        if state.get('state') in ('paused_by_parent', 'all_69_rendered', 'stopped_at_boundary'): break
        time.sleep(1)
test = pathlib.Path(sys.argv[1])
if test.is_absolute() or (test.parts[:1] != ('tests',) and test != pathlib.Path('scripts/benchmark-car-grounding.mjs')) or test.suffix != '.mjs' or '..' in test.parts:
    raise SystemExit('Expected a repository tests/*.mjs path')

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

files = {p for directory in ('dist', 'data', 'tests') for p in (root / directory).rglob('*')
         if p.is_file() and p.suffix in ('.js', '.mjs', '.glb', '.json')
         and (directory != 'tests' or p.suffix == '.mjs' or 'fixtures' in p.relative_to(root / 'tests').parts)}
files.add(root / test)  # Bind the explicitly authorized benchmark script as well.
if test == pathlib.Path('scripts/benchmark-car-grounding.mjs'): files.add(root / 'scripts/road-tyre-face-probe.mjs')
hashes = {str(p.relative_to(root)): digest(p) for p in sorted(files)}
manifest_path = root / 'data/native-export-manifest.json'
manifest = json.loads(manifest_path.read_text())
report = {'test': str(test), 'runnerSha256': digest(pathlib.Path(__file__)), 'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'nativeSourceSha256': manifest['source_sha256'],
          'rawGLBSha256': {pathlib.Path(x['file']).name: x['sha256'] for x in manifest['exports']},
          'inputSha256': hashes, 'browserVerified': False, 'status': 'running'}
out = root / 'tests/runtime-runs'
out.mkdir(exist_ok=True)
report_path = out / (test.stem + '.json')
log_path = out / (test.stem + '.log')
if report_path.exists():
    previous_bytes = report_path.read_bytes()
    previous = json.loads(previous_bytes)
    stamp = previous.get('startedUTC', 'undated').replace(':', '').replace('+', '_')
    archive = out / 'history' / (test.stem + '-' + stamp + '-' + hashlib.sha256(previous_bytes).hexdigest()[:8])
    archive.mkdir(parents=True, exist_ok=True)
    shutil.copy2(report_path, archive / report_path.name)
    if log_path.exists(): shutil.copy2(log_path, archive / log_path.name)
    prior_snapshots = out / (test.stem + '-results')
    if prior_snapshots.exists(): shutil.copytree(prior_snapshots, archive / 'results', dirs_exist_ok=True)
report_path.write_text(json.dumps(report, indent=2) + '\n')
before = {p: (p.stat().st_mtime_ns, digest(p)) for p in (root / 'tests').glob('*results.json')}
began = time.monotonic()
with log_path.open('w') as log:
    process = subprocess.run(['node', str(test)], cwd=root, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT)
report.update(status='passed' if process.returncode == 0 else 'failed', exitCode=process.returncode,
              elapsedSeconds=round(time.monotonic() - began, 3),
              maxRSS_MB=round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 2),
              completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              log=str(log_path.relative_to(root)), logSha256=digest(log_path))
report['resultsSha256'] = {str(p.relative_to(root)): digest(p) for p in (root / 'tests').glob('*results.json')
                          if p not in before or (p.stat().st_mtime_ns, digest(p)) != before[p]}
snapshot_dir = out / (test.stem + '-results')
snapshot_dir.mkdir(exist_ok=True)
report['resultSnapshots'] = {}
for relative, sha in report['resultsSha256'].items():
    target = snapshot_dir / pathlib.Path(relative).name
    shutil.copy2(root / relative, target)
    if digest(target) != sha:
        raise RuntimeError('Result snapshot differs: ' + relative)
    report['resultSnapshots'][str(target.relative_to(root))] = sha
report['changedInputFiles'] = [name for name, sha in hashes.items() if digest(root / name) != sha]
if report['changedInputFiles']:
    report['status'] = 'invalidated_inputs_changed'
report_path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k not in ('inputSha256', 'rawGLBSha256')}, indent=2))
raise SystemExit(process.returncode or bool(report['changedInputFiles']))
