"""Package only installable runtime and user documentation."""
from pathlib import Path
import ast
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'io_ogre'
tree=ast.parse((SOURCE/'__init__.py').read_text())
info=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='bl_info' for target in node.targets))
version='.'.join(map(str,info['version']))
TARGET=ROOT/('ChatGPT/temp/blender2ogre_Blender_5_2_v'+version+'.zip')
files=[]
for path in sorted(SOURCE.rglob('*'), key=lambda item: item.relative_to(SOURCE).as_posix().casefold()):
    if not path.is_file(): continue
    if '__pycache__' in path.relative_to(SOURCE).parts or path.suffix == '.pyc': continue
    assert not any(part in ('ChatGPT','__pycache__','.git') for part in path.relative_to(SOURCE).parts)
    assert path.suffix.lower() not in ('.pyc','.log','.blend','.zip','.pdb'), path
    assert path.name.lower() not in ('agents.md','skill.md')
    if path.suffix=='.py': ast.parse(path.read_text(encoding='utf8'),filename=str(path))
    files.append(path)
with zipfile.ZipFile(TARGET,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as output:
    for path in files:
        info=zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), date_time=(2026,10,25,0,0,0))
        info.create_system=0 # Match the verified Windows ZIP on every build host.
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=0o100644<<16
        output.writestr(info,path.read_bytes())
with zipfile.ZipFile(TARGET) as archive:
    assert archive.testzip() is None
    assert {name.split('/')[0] for name in archive.namelist()}=={'io_ogre'}
record={'archive':str(TARGET),'version':version,'sha256':hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        'bytes':TARGET.stat().st_size,'files':len(files),
        'runtime_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(ROOT/'ChatGPT/outputs/package_manifest.json').write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items() if k!='runtime_sha256'},indent=2))
