"""Run a development script in a disposable Blender profile."""
from pathlib import Path
import argparse
import os
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--blender', type=Path, required=True)
parser.add_argument('script', type=Path)
parser.add_argument('script_args', nargs='*')
args = parser.parse_args()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
run_id = uuid.uuid4().hex[:10]
for name, subdirectory in {'TEMP': 'temp', 'TMP': 'temp', 'TMPDIR': 'temp',
    'BLENDER_USER_CONFIG': 'profile/' + run_id + '/config', 'BLENDER_USER_SCRIPTS': 'profile/' + run_id + '/scripts',
    'BLENDER_USER_DATAFILES': 'profile/datafiles', 'BLENDER_USER_EXTENSIONS': 'profile/extensions'}.items():
    directory = ROOT / '.build' / subdirectory
    directory.mkdir(parents=True, exist_ok=True)
    env[name] = str(directory)
(ROOT / '.build/outputs').mkdir(parents=True, exist_ok=True)
log = ROOT / '.build/outputs' / (args.script.stem + '.log')
with log.open('w', encoding='utf-8') as output:
    result = subprocess.run([str(args.blender), '--background', '--factory-startup', '--disable-autoexec',
        '--python-exit-code', '1', '--python', str(args.script.resolve()), '--', *args.script_args],
        env=env, cwd=ROOT / '.build/temp', stdout=output, stderr=subprocess.STDOUT)
print(log)
print(log.read_text(encoding='utf-8', errors='replace')[-4000:])
raise SystemExit(result.returncode)
