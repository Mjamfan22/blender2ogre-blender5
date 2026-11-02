"""Time a real import and save per-corner data for equivalence verification."""
from pathlib import Path
import json, sys, time, platform
import bpy, addon_utils, numpy as np
ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
MODULE_ROOT=Path(args[0]) if args else ROOT
LABEL=args[1] if len(args)>1 else 'baseline'
sys.path.insert(0,str(MODULE_ROOT)); addon_utils.enable('io_ogre',default_set=True,persistent=False)
import io_ogre
from io_ogre.ogre import ogre_import as importer, validation
from io_ogre.ogre.material_parser import MaterialParser
from io_ogre import config
from io_ogre.report import Report
PHASES={}

def watch(owner,name,label):
    original=getattr(owner,name)
    def measured(*args,**kw):
        start=time.perf_counter()
        try: return original(*args,**kw)
        finally:
            entry=PHASES.setdefault(label,{'seconds':0,'calls':0})
            entry['seconds']+=time.perf_counter()-start; entry['calls']+=1
    setattr(owner,name,measured)

for name in ('xOpenFile','xCollectMeshData','bCreateSubMeshes','bCreateMesh'):
    watch(importer,name,name)
watch(validation,'validate_mesh','validation')
watch(MaterialParser,'xCollectMaterialData','materials')
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
# Avoid earlier suites' materials/images affecting names or texture-load timing.
for material in list(bpy.data.materials): bpy.data.materials.remove(material)
for image in list(bpy.data.images):
    if image.type!='RENDER_RESULT': bpy.data.images.remove(image)
config.CONFIG.update(config._CONFIG_DEFAULTS_ALL)
file=ROOT/'tests/fixtures/bakugan_pack/crd_trucks/bakugan_dragonoid/bakugan_dragonoid_body.mesh'
start=time.perf_counter()
result=bpy.ops.ogre.import_mesh(filepath=str(file),IM_USE_SELECTED_SKELETON=False,IM_Vx_ENABLE_LOGGING=False)
elapsed=time.perf_counter()-start
assert result=={'FINISHED'},Report.errors
obj=next(ob for ob in bpy.context.scene.objects if ob.type=='MESH'); mesh=obj.data
positions=np.empty(len(mesh.vertices)*3,dtype='f'); mesh.vertices.foreach_get('co',positions)
indices=np.empty(len(mesh.loops),dtype='i'); mesh.loops.foreach_get('vertex_index',indices)
normals=np.empty(len(mesh.loops)*3,dtype='f'); mesh.corner_normals.foreach_get('vector',normals)
uvs=[]
for layer in mesh.uv_layers:
    data=np.empty(len(mesh.loops)*2,dtype='f'); layer.data.foreach_get('uv',data); uvs.append(data.reshape(-1,2))
material_names=[mat.name for mat in mesh.materials]
material_indices=np.empty(len(mesh.polygons),dtype='i'); mesh.polygons.foreach_get('material_index',material_indices)
canonical={name:index for index,name in enumerate(sorted(material_names))}
material_ids=np.asarray([canonical[material_names[index]] for index in material_indices],dtype='i').reshape(-1,1)
corners=positions.reshape(-1,3)[indices].reshape(-1,9)
uv_data=np.concatenate(uvs,axis=1).reshape(len(mesh.polygons),-1) if uvs else np.empty((len(mesh.polygons),0))
keys=np.concatenate((material_ids,np.round(corners,5),np.round(uv_data,6)),axis=1)
order=np.lexsort(keys[:,::-1].T[::-1])
prefix=ROOT/'.build/outputs'/('import_benchmark_'+LABEL)
np.savez_compressed(str(prefix)+'.npz',positions=corners[order],normals=normals.reshape(-1,9)[order],uvs=uv_data[order],materials=material_ids[order])
record={'version':'.'.join(map(str,io_ogre.bl_info['version'])),'label':LABEL,'blender':bpy.app.version_string,
    'platform':platform.platform(),'module_root':str(MODULE_ROOT),'seconds':elapsed,'phases':PHASES,
    'vertices':len(mesh.vertices),'triangles':len(mesh.polygons),'uv_layers':len(mesh.uv_layers),
    'material_names':material_names,'warnings':list(Report.warnings)}
Path(str(prefix)+'.json').write_text(json.dumps(record,indent=2))
print('IMPORT_BENCHMARK',json.dumps(record))
