"""Install the exact candidate ZIP and run the selected Blender checks."""
from pathlib import Path
import json
import os
import runpy
import sys
import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ChatGPT/tests'))
from test_support import SKIPPED
manifest = json.loads((ROOT / 'ChatGPT/outputs/package_manifest.json').read_text())
archive = Path(manifest['archive'])
assert bpy.app.version == (5, 2, 3), bpy.app.version_string
assert bpy.ops.preferences.addon_install(filepath=str(archive), overwrite=True) == {'FINISHED'}
addon_utils.modules_refresh()
addon_utils.enable('io_ogre', default_set=True, persistent=False)
import io_ogre
installed = Path(io_ogre.__file__).resolve().parent.parent
assert installed.is_relative_to(ROOT / 'ChatGPT/profile') and installed != ROOT
assert '.'.join(map(str, io_ogre.bl_info['version'])) == manifest['version']

for suite in ('workflow', 'release_suite', 'upstream_issues', 'material_resources', 'import_performance'):
    if suite == 'import_performance' and os.environ.get('OGRE_FULL_TESTS') == '1':
        sys.argv = [__file__, '--', str(installed), 'optimized']
        runpy.run_path(str(ROOT / 'ChatGPT/tests/import_benchmark.py'), run_name='__main__')
    sys.argv = [__file__, '--', str(installed)]
    runpy.run_path(str(ROOT / 'ChatGPT/tests' / (suite + '.py')), run_name='__main__')

names = ('workflow_results', 'release_results', 'upstream_results', 'material_resources_results', 'import_performance_results')
results = [json.loads((ROOT / 'ChatGPT/outputs' / (name + '.json')).read_text()) for name in names]
tests = [test for result in results for test in result['tests']]
full = os.environ.get('OGRE_FULL_TESTS') == '1'
assert len(tests) == (73 if full else 65), len(tests)
assert len(SKIPPED) == (0 if full else 8), SKIPPED
assert all(test['passed'] for test in tests)
record = {'version': manifest['version'], 'blender': bpy.app.version_string, 'installed_zip': True,
          'passed': len(tests), 'failed': 0, 'skipped': SKIPPED, 'full_suite': full}
(ROOT / 'ChatGPT/outputs/review_checks.json').write_text(json.dumps(record, indent=2))
print('REVIEW_CHECKS_PASS', json.dumps(record))
