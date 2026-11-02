"""Build and check a real ZIP installation without touching live Blender data."""
from pathlib import Path
import argparse
import os
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--blender', type=Path, required=True)
parser.add_argument('--full', action='store_true', help='Require the eight non-redistributed fixture checks')
args = parser.parse_args()
assert args.blender.is_file(), args.blender
for directory in ('.build/temp', '.build/outputs'):
    (ROOT / directory).mkdir(parents=True, exist_ok=True)
if args.full:
    required = ['tests/fixtures/ogre_samples/robot.mesh', 'tests/fixtures/ogre_samples/robot.skeleton',
                'tests/fixtures/ogre_samples/ogrehead.mesh', 'tests/fixtures/reporters/142/untitled.blend',
                'tests/fixtures/reporters/240/swaptest.blend', 'tests/fixtures/bakugan_pack/sources.json',
                '.build/outputs/import_benchmark_baseline.npz', '.build/outputs/import_benchmark_baseline.json']
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing: parser.error('Missing optional fixtures for --full: ' + ', '.join(missing))
subprocess.run([sys.executable, str(ROOT / 'tools/package.py')], cwd=ROOT, check=True)
env = os.environ.copy()
run_id = uuid.uuid4().hex[:10]
for name, subdirectory in {
    'TEMP': 'temp', 'TMP': 'temp', 'TMPDIR': 'temp',
    'BLENDER_USER_CONFIG': 'profile/' + run_id + '/config',
    'BLENDER_USER_SCRIPTS': 'profile/' + run_id + '/scripts',
    'BLENDER_USER_DATAFILES': 'profile/datafiles', 'BLENDER_USER_EXTENSIONS': 'profile/extensions',
    'XDG_CACHE_HOME': 'temp/cache',
}.items():
    directory = ROOT / '.build' / subdirectory
    directory.mkdir(parents=True, exist_ok=True)
    env[name] = str(directory)
env['PYTHONDONTWRITEBYTECODE'] = '1'
env['OGRE_FULL_TESTS'] = '1' if args.full else '0'
log = ROOT / '.build/outputs/review_checks.log'
with log.open('w', encoding='utf-8') as stream:
    result = subprocess.run([str(args.blender), '--background', '--factory-startup', '--disable-autoexec',
        '--python-exit-code', '1', '--python', str(ROOT / 'tests/review_runner.py')],
        cwd=ROOT / '.build/temp', env=env, stdout=stream, stderr=subprocess.STDOUT)
print(log)
print(log.read_text(encoding='utf-8', errors='replace')[-5000:])
raise SystemExit(result.returncode)
