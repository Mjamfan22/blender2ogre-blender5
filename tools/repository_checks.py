"""Static integrity checks; does not claim to run Blender regressions."""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
assert not (ROOT / 'ChatGPT').exists(), 'Use the standard tests/tools/docs layout'
manifest = json.loads((ROOT / 'docs/validation/runtime_manifest.json').read_text())
runtime = {p.relative_to(ROOT).as_posix(): p for p in (ROOT / 'io_ogre').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert set(runtime) == set(manifest['runtime_sha256']), 'Runtime file inventory differs'
for name, path in runtime.items():
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['runtime_sha256'][name], name
    assert path.name.lower() not in ('agents.md', 'skill.md')
for folder in ('io_ogre', 'tools', 'tests'):
    for path in (ROOT / folder).rglob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
for directory in ('.build/temp', '.build/outputs'):
    (ROOT / directory).mkdir(parents=True, exist_ok=True)
subprocess.run([sys.executable, str(ROOT / 'tools/package.py')], cwd=ROOT, check=True)
candidate = json.loads((ROOT / '.build/outputs/package_manifest.json').read_text())
assert candidate['sha256'] == manifest['sha256'] and candidate['bytes'] == manifest['bytes']
with zipfile.ZipFile(candidate['archive']) as archive:
    assert archive.testzip() is None
    assert set(archive.namelist()) == set(runtime)
    assert archive.namelist() == sorted(runtime, key=str.casefold), 'ZIP order must be independent of host filesystem'
    assert all(name.startswith('io_ogre/') and '__pycache__' not in name for name in archive.namelist())
documents = [ROOT / name for name in ('README.md', 'CHANGELOG.md', 'NOTICE.md', 'CONTRIBUTING.md', 'SECURITY.md')]
documents += list((ROOT / 'docs').glob('*.md'))
for path in documents:
    for target in re.findall(r'!?\[[^\]]*\]\(([^)\s]+)\)', path.read_text(encoding='utf-8')):
        if target.startswith(('https://', 'http://', '#', 'mailto:')): continue
        destination = (path.parent / target.split('#')[0]).resolve()
        assert destination.is_relative_to(ROOT) and destination.exists(), (str(path.relative_to(ROOT)), target)
for path in [*documents, *(ROOT / 'docs/validation').glob('*.json')]:
    text = path.read_text(encoding='utf-8')
    assert not re.search(r'[CD]:\\(?:Users\\mjamf|BM Chassis Pack|Blender[45]ImporterExporter)', text, re.I), path
print('REPOSITORY_INTEGRITY_PASS', manifest['version'], manifest['files'], manifest['sha256'])
