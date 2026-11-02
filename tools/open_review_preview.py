"""Open only the generated preview in a separate disposable Blender profile."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--blender', type=Path, required=True)
args = parser.parse_args()
file = ROOT / '.build/outputs/review_demo/blender2ogre-v0.9.8-review.blend'
assert file.is_file() and args.blender.is_file()
env = os.environ.copy()
run_id = uuid.uuid4().hex[:10]
for name, subdirectory in {'TEMP': 'temp', 'TMP': 'temp', 'TMPDIR': 'temp',
    'BLENDER_USER_CONFIG': 'profile/preview_' + run_id + '/config',
    'BLENDER_USER_SCRIPTS': 'profile/preview_' + run_id + '/scripts',
    'BLENDER_USER_DATAFILES': 'profile/datafiles', 'BLENDER_USER_EXTENSIONS': 'profile/extensions'}.items():
    directory = ROOT / '.build' / subdirectory
    directory.mkdir(parents=True, exist_ok=True)
    env[name] = str(directory)
env['PYTHONDONTWRITEBYTECODE'] = '1'
# Only this disposable profile receives preferences, preventing a first-run dialog.
subprocess.run([str(args.blender), '--background', '--factory-startup', '--python-expr',
    "import bpy; bpy.context.preferences.view.show_splash=False; bpy.ops.wm.save_userpref()"],
    env=env, cwd=ROOT / '.build/temp', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
process = subprocess.Popen([str(args.blender), '--factory-startup', '--disable-autoexec',
    '--gpu-backend', 'opengl', '--window-geometry', '70', '70', '1600', '1000', str(file),
    '--python', str(ROOT / 'tools/preview_screenshot.py')],
    env=env, cwd=ROOT / '.build/temp', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
(ROOT / '.build/outputs/preview_process.json').write_text(json.dumps({'pid': process.pid, 'file': str(file)}, indent=2))
print('Opened isolated review preview:', process.pid)
