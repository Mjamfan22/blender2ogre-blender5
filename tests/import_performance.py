"""Verify fast-import behavior and equivalence to the previous release."""
from pathlib import Path
import sys,json,traceback,uuid
import numpy as np
import bpy,addon_utils
ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
MODULE_ROOT=Path(args[0]) if args else ROOT
sys.path.insert(0,str(MODULE_ROOT)); addon_utils.enable('io_ogre',default_set=True,persistent=False)
from io_ogre import config
from io_ogre.report import Report
from io_ogre.ogre import fast_xml
from io_ogre.ogre.validation import validate_mesh
OUT=ROOT/'.build/outputs/import_performance'/uuid.uuid4().hex[:8]; OUT.mkdir(parents=True)
RESULTS=[]

def case(fn):
    from test_support import skip_fixture_case
    if skip_fixture_case(fn.__name__): return
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    config.CONFIG.update(config._CONFIG_DEFAULTS_ALL); Report.reset()
    try:
        fn(); item={'test':fn.__name__,'passed':True}
    except Exception:
        item={'test':fn.__name__,'passed':False,'detail':traceback.format_exc()}; print(item['detail'])
    RESULTS.append(item)

def fixture(folder,rig=False):
    folder.mkdir()
    xml='''<mesh><sharedgeometry vertexcount="3"><vertexbuffer positions="true" normals="true" colours_diffuse="true" texture_coords="2">
<vertex><position x="0" y="0" z="0"/><normal x="0" y="0" z="1"/><colour_diffuse value="1 0 0 0.5"/><texcoord u="0.1" v="0.2"/><texcoord u="0.3" v="0.4"/></vertex>
<vertex><position x="2" y="0" z="0"/><normal x="0" y="0" z="1"/><colour_diffuse value="0 1 0 1"/><texcoord u="0.5" v="0.6"/><texcoord u="0.7" v="0.8"/></vertex>
<vertex><position x="0" y="2" z="0"/><normal x="0" y="0" z="1"/><colour_diffuse value="0 0 1 1"/><texcoord u="0.9" v="0.1"/><texcoord u="0.2" v="0.3"/></vertex>
</vertexbuffer></sharedgeometry><submeshes>
<submesh material="SurfaceA" usesharedvertices="true"><faces count="1"><face v1="0" v2="1" v3="2"/></faces></submesh>
<submesh material="SurfaceB" usesharedvertices="true"><faces count="1"><face v1="2" v2="0" v3="1"/></faces></submesh>
</submeshes>RIG</mesh>'''
    rig_data='''<skeletonlink name="tiny.skeleton"/><boneassignments><vertexboneassignment vertexindex="0" boneindex="0" weight="1"/><vertexboneassignment vertexindex="1" boneindex="0" weight="1"/><vertexboneassignment vertexindex="2" boneindex="0" weight="1"/></boneassignments>''' if rig else ''
    file=folder/'asset.mesh.xml'; file.write_text(xml.replace('RIG',rig_data))
    (folder/'asset.material').write_text('material SurfaceA { technique { pass { diffuse 1 0 0 1 } } }\nmaterial SurfaceB { technique { pass { diffuse 0 1 0 1 } } }')
    if rig:
        (folder/'tiny.skeleton.xml').write_text('<skeleton><bones><bone id="0" name="Root"><position x="0" y="0" z="0"/><rotation angle="0"><axis x="0" y="1" z="0"/></rotation></bone></bones><bonehierarchy/></skeleton>')
    return file

def load(file,merge=True):
    assert bpy.ops.ogre.import_mesh(filepath=str(file),IM_MERGE_SUBMESHES=merge,IM_USE_SELECTED_SKELETON=False)=={'FINISHED'},Report.errors
    return [obj for obj in bpy.context.scene.objects if obj.type=='MESH']

@case
def shared_static_geometry_keeps_bulk_corner_attributes():
    objects=load(fixture(OUT/'shared'))
    assert len(objects)==1
    mesh=objects[0].data
    assert len(mesh.vertices)==3 and len(mesh.polygons)==2
    assert [mesh.materials[p.material_index].name for p in mesh.polygons]==['SurfaceA','SurfaceB']
    assert len(mesh.uv_layers)==2
    np.testing.assert_allclose(mesh.uv_layers[0].data[0].uv,(.1,.8),atol=1e-6)
    np.testing.assert_allclose(mesh.uv_layers[1].data[3].uv,(.2,.7),atol=1e-6)
    assert abs(mesh.color_attributes['Color'].data[0].color[3]-.5)<.005
    np.testing.assert_allclose(mesh.corner_normals[0].vector,(0,-1,0),atol=1e-4)

@case
def keep_submeshes_separate_still_works():
    objects=load(fixture(OUT/'separate'),merge=False)
    assert len(objects)==2 and all(len(obj.data.vertices)==3 for obj in objects)
    assert all(len(obj.data.uv_layers)==2 for obj in objects)

@case
def skeletal_shared_mesh_keeps_weights_and_rig():
    objects=load(fixture(OUT/'rig',rig=True))
    assert len(objects)==1 and objects[0].find_armature() is not None
    obj=objects[0]
    assert len(obj.data.polygons)==2 and len(obj.data.uv_layers)==2
    assert all(abs(obj.vertex_groups['Root'].weight(v.index)-1)<1e-6 for v in obj.data.vertices)

@case
def multiple_vertex_buffers_and_declared_counts():
    file=OUT/'buffers.mesh.xml'
    file.write_text('''<mesh><sharedgeometry vertexcount="3"><vertexbuffer positions="true"><vertex><position x="0" y="0" z="0"/></vertex><vertex><position x="1" y="0" z="0"/></vertex><vertex><position x="0" y="1" z="0"/></vertex></vertexbuffer><vertexbuffer positions="false" normals="true" texture_coords="1"><vertex><normal x="0" y="0" z="1"/><texcoord u="0" v="0"/></vertex><vertex><normal x="0" y="0" z="1"/><texcoord u="1" v="0"/></vertex><vertex><normal x="0" y="0" z="1"/><texcoord u="0" v="1"/></vertex></vertexbuffer></sharedgeometry><submeshes><submesh material="Test"><faces count="1"><face v1="0" v2="1" v3="2"/></faces></submesh></submeshes></mesh>''')
    with file.open() as source: doc=fast_xml.parse(source)
    data=fast_xml.collect_mesh({},doc,str,True); validate_mesh(data)
    assert len(data['sharedgeometry']['positions'])==3 and len(data['sharedgeometry']['normals'])==3
    assert data['sharedgeometry']['texcoordsets']==1
    file.write_text(file.read_text().replace('vertexcount="3"','vertexcount="4"'))
    try:
        with file.open() as source: doc=fast_xml.parse(source)
        fast_xml.collect_mesh({},doc,str,True)
        assert False,'Expected inconsistent buffer count rejection'
    except ValueError: pass

@case
def full_bakugan_import_matches_previous_release():
    baseline=np.load(ROOT/'.build/outputs/import_benchmark_baseline.npz')
    optimized=np.load(ROOT/'.build/outputs/import_benchmark_optimized.npz')
    differences={}
    for key,tolerance in [('positions',1e-6),('uvs',1e-6),('normals',1e-4),('materials',0)]:
        assert baseline[key].shape==optimized[key].shape,(key,baseline[key].shape,optimized[key].shape)
        np.testing.assert_allclose(baseline[key],optimized[key],atol=tolerance,rtol=0,err_msg=key)
        differences[key]=float(np.max(np.abs(baseline[key]-optimized[key])))
    before=json.loads((ROOT/'.build/outputs/import_benchmark_baseline.json').read_text())
    after=json.loads((ROOT/'.build/outputs/import_benchmark_optimized.json').read_text())
    assert before['triangles']==after['triangles']==190826
    assert before['uv_layers']==after['uv_layers']==8
    assert sorted(before['material_names'])==sorted(after['material_names'])
    assert after['warnings']==[] and after['vertices']==121422
    assert after['module_root']==str(MODULE_ROOT)
    record={'before_seconds':before['seconds'],'after_seconds':after['seconds'],
        'speedup':before['seconds']/after['seconds'],'baseline_vertices':before['vertices'],
        'optimized_vertices':after['vertices'],'triangles':after['triangles'],'uv_layers':after['uv_layers'],
        'maximum_corner_differences':differences,'installed_module_root':str(MODULE_ROOT)}
    (ROOT/'.build/outputs/import_speedup.json').write_text(json.dumps(record,indent=2))

addon_utils.disable('io_ogre',default_set=True)
record={'module_root':str(MODULE_ROOT),'blender':bpy.app.version_string,'output':str(OUT),'tests':RESULTS}
(ROOT/'.build/outputs/import_performance_results.json').write_text(json.dumps(record,indent=2))
for item in RESULTS: print('PASS' if item['passed'] else 'FAIL',item['test'])
assert all(item['passed'] for item in RESULTS),'Fast import regression failed'
print('IMPORT_PERFORMANCE_PASS',len(RESULTS))
