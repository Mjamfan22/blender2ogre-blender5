"""Release regressions executed in the real, isolated Blender 5.2.3 process."""
from pathlib import Path
import hashlib
import json
import math
import shutil
import sys
import traceback
import uuid
import xml.etree.ElementTree as ET
import bpy
import addon_utils
from mathutils import Vector, Quaternion

ROOT=Path(__file__).resolve().parents[2]
MODULE_ROOT=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv and len(sys.argv)>sys.argv.index('--')+1 else ROOT
sys.path.insert(0,str(MODULE_ROOT))
addon_utils.enable('io_ogre',default_set=True,persistent=False)
assert addon_utils.check('io_ogre')[1]
from io_ogre import animation, config, util
from io_ogre.ogre import mesh as mesh_export
from io_ogre.report import Report

OUT=ROOT/'ChatGPT/outputs/release_suite'/uuid.uuid4().hex[:8]
OUT.mkdir(parents=True)
RESULTS=[]

def clear():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    scene=bpy.context.scene
    scene.render.fps=24; scene.render.fps_base=1
    scene.frame_step=1; scene.frame_set(1)

def case(fn):
    from test_support import skip_fixture_case
    if skip_fixture_case(fn.__name__): return
    clear()
    try:
        fn()
        result={'test':fn.__name__,'passed':True}
    except Exception:
        result={'test':fn.__name__,'passed':False,'detail':traceback.format_exc()}
        print(result['detail'])
    RESULTS.append(result)

def triangle(name='ReleaseMesh'):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata([(0,0,0),(2,0,0),(0,3,0)],[],[(0,1,2)])
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    obj.select_set(True); bpy.context.view_layer.objects.active=obj
    return obj

def export(folder,**kwargs):
    folder.mkdir(exist_ok=True)
    result=bpy.ops.ogre.export(filepath=str(folder/'test.scene'),EX_EXPORT_XML_DELETE=False,
        EX_FORCE_CAMERA=False,EX_FORCE_LIGHTS=False,**kwargs)
    assert result=={'FINISHED'},Report.errors
    assert not Report.errors,Report.errors
    return ET.parse(folder/'test.scene')

def fixture(folder,name='asset',material='FixtureMaterial',bad_index=False):
    folder.mkdir(exist_ok=True)
    text='''<mesh><sharedgeometry vertexcount="3"><vertexbuffer positions="true" normals="true"><vertex><position x="0" y="0" z="0"/><normal x="0" y="0" z="1"/></vertex><vertex><position x="2" y="0" z="0"/><normal x="0" y="0" z="1"/></vertex><vertex><position x="0" y="3" z="0"/><normal x="0" y="0" z="1"/></vertex></vertexbuffer></sharedgeometry><submeshes><submesh material="MATERIAL" usesharedvertices="true" operationtype="triangle_list"><faces count="1"><face v1="0" v2="1" v3="INDEX"/></faces></submesh></submeshes></mesh>'''
    path=folder/(name+'.mesh.xml')
    path.write_text(text.replace('MATERIAL',material).replace('INDEX','9000' if bad_index else '2'))
    return path

@case
def disabled_modifiers_unchanged():
    obj=triangle()
    first=obj.modifiers.new('Keep disabled','ARRAY'); first.show_viewport=False
    second=obj.modifiers.new('Keep enabled','ARMATURE')
    bpy.context.scene.frame_set(7,subframe=0.25)
    before=(obj.matrix_basis.copy(),set(bpy.data.objects),set(bpy.data.meshes))
    export(OUT/'modifiers')
    assert not first.show_viewport and second.show_viewport
    assert bpy.context.scene.frame_current==7 and bpy.context.scene.frame_subframe==0.25
    assert obj.matrix_basis==before[0]
    assert set(bpy.data.objects)==before[1] and set(bpy.data.meshes)==before[2]

@case
def failed_export_preserves_state_and_files():
    obj=triangle('FailureMesh'); mod=obj.modifiers.new('Array','ARRAY')
    for frame,x in [(1,0),(12,3)]:
        obj.location.x=x; obj.keyframe_insert(data_path='location',frame=frame)
    action=obj.animation_data.action; slot=obj.animation_data.action_slot
    bpy.context.scene.frame_set(7,subframe=0.5)
    folder=OUT/'failed_export'; folder.mkdir()
    (folder/'test.scene').write_bytes(b'EXISTING_SCENE')
    (folder/'FailureMesh.mesh').write_bytes(b'EXISTING_MESH')
    before={p.name:p.read_bytes() for p in folder.iterdir()}
    ids=set(bpy.data.objects),set(bpy.data.meshes)
    original=mesh_export.write_shared
    def fail(*args,**kwargs): raise RuntimeError('Intentional failure after evaluation')
    mesh_export.write_shared=fail
    try:
        status=bpy.ops.ogre.export(filepath=str(folder/'test.scene'))
    finally:
        mesh_export.write_shared=original
    assert status=={'CANCELLED'}
    assert {p.name:p.read_bytes() for p in folder.iterdir()}==before
    assert mod.show_viewport and obj.animation_data.action==action and obj.animation_data.action_slot==slot
    assert bpy.context.active_object==obj and obj.select_get()
    assert bpy.context.scene.frame_current==7 and bpy.context.scene.frame_subframe==0.5
    assert set(bpy.data.objects)==ids[0] and set(bpy.data.meshes)==ids[1]

@case
def failed_scene_rolls_back_all_imported_ids():
    existing=triangle('ExistingObject'); folder=OUT/'rollback'; path=fixture(folder)
    (folder/'asset.material').write_text('material FixtureMaterial { technique { pass { diffuse 1 0 0 1\n } } }')
    scene=folder/'broken.scene'
    scene.write_text('<scene><environment><colourBackground r="1" g="0" b="0"/></environment><nodes><node name="First"><entity meshFile="asset.mesh.xml"/></node><node name="Missing"><entity meshFile="absent.mesh"/></node></nodes></scene>')
    kinds=('objects','meshes','collections','materials','actions','images','armatures')
    before={kind:set(getattr(bpy.data,kind)) for kind in kinds}
    world=bpy.context.scene.world; color=world.color[:]
    backgrounds=[(n,n.inputs['Color'].default_value[:]) for n in world.node_tree.nodes if n.type=='BACKGROUND']
    assert bpy.ops.ogre.import_mesh(filepath=str(scene))=={'CANCELLED'}
    assert all(set(getattr(bpy.data,kind))==before[kind] for kind in kinds)
    assert world.color[:]==color
    assert all(n.inputs['Color'].default_value[:]==value for n,value in backgrounds)
    assert bpy.context.active_object==existing and existing.select_get()

@case
def source_xml_is_never_deleted():
    folder=OUT/'source_xml'; path=fixture(folder)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert bpy.ops.ogre.import_mesh(filepath=str(path),IM_IMPORT_XML_DELETE=True)=={'FINISHED'}
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    assert {p.name for p in folder.iterdir()}=={path.name}

@case
def binary_import_preserves_existing_xml_and_source():
    triangle('BinarySource'); folder=OUT/'binary_source'; export(folder)
    source=folder/'BinarySource.mesh'; sibling=folder/'BinarySource.mesh.xml'
    sibling.write_bytes(b'USER_AUTHORED_XML_MUST_STAY')
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
    assert bpy.ops.ogre.import_mesh(filepath=str(source),IM_IMPORT_XML_DELETE=True)=={'FINISHED'}
    after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
    assert before==after

@case
def materials_preserve_existing_and_translate_rgba():
    folder=OUT/'materials'; path=fixture(folder,material='ProtectedMaterial')
    old=bpy.data.materials.new('ProtectedMaterial'); old.use_nodes=True
    shader=next(n for n in old.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value=(0.7,0.8,0.9,1)
    nodes_before=len(old.node_tree.nodes)
    (folder/'asset.material').write_text('''material ProtectedMaterial
{
 technique {
  pass {
   diffuse 0.1 0.3 0.6 0.4
   emissive 0.2 0.1 0.0
   scene_blend alpha_blend
   cull_hardware none
  }
 }
}
''')
    assert bpy.ops.ogre.import_mesh(filepath=str(path))=={'FINISHED'}
    new=bpy.context.active_object.data.materials[0]
    assert new!=old and len(old.node_tree.nodes)==nodes_before
    assert abs(shader.inputs['Base Color'].default_value[0]-0.7)<1e-6
    bsdf=next(n for n in new.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    assert (Vector(bsdf.inputs['Base Color'].default_value[:3])-Vector((0.1,0.3,0.6))).length<1e-6
    assert abs(bsdf.inputs['Alpha'].default_value-0.4)<1e-6 and new.surface_render_method=='BLENDED'
    assert abs(bsdf.inputs['Emission Color'].default_value[0]-0.2)<1e-6

@case
def quoted_texture_filename():
    folder=OUT/'texture'; path=fixture(folder,material='TextureFixture')
    image=bpy.data.images.new('FixtureImage',width=2,height=2)
    image.filepath_raw=str(folder/'texture with spaces.png'); image.file_format='PNG'; image.save()
    (folder/'asset.material').write_text('''material TextureFixture {
technique { pass {
diffuse 1 1 1 0.5
scene_blend alpha_blend
texture_unit { texture "texture with spaces.png"
}
} }
}
''')
    assert bpy.ops.ogre.import_mesh(filepath=str(path))=={'FINISHED'}
    mat=bpy.context.active_object.data.materials[0]
    textures=[n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE']
    assert len(textures)==1 and Path(textures[0].image.filepath).name=='texture with spaces.png'
    bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    assert bsdf.inputs['Alpha'].is_linked

@case
def numeric_custom_normals_and_uv_roundtrip():
    obj=triangle('NormalsUV')
    layer=obj.data.uv_layers.new(name='UV')
    expected_uv=[(0.1,0.2),(0.9,0.3),(0.4,0.8)]
    for item,value in zip(layer.data,expected_uv): item.uv=value
    normal=Vector((0.3,0.4,0.8660254)).normalized()
    for poly in obj.data.polygons: poly.use_smooth=True
    obj.data.normals_split_custom_set_from_vertices([normal]*3)
    folder=OUT/'normals'; export(folder)
    clear(); assert bpy.ops.ogre.import_mesh(filepath=str(folder/'NormalsUV.mesh'))=={'FINISHED'}
    mesh=bpy.context.active_object.data
    assert len(mesh.polygons)==1 and len(mesh.vertices)==3
    assert all((item.vector-normal).length<1e-4 for item in mesh.corner_normals)
    assert all((item.uv-Vector(uv)).length<1e-5 for item,uv in zip(mesh.uv_layers[0].data,expected_uv))

@case
def unshared_colors_multiple_uvs_unused_slots():
    obj=triangle('UnsharedAttributes')
    obj.data.clear_geometry()
    obj.data.from_pydata([(0,0,0),(1,0,0),(0,1,0)]*2,[],[(0,1,2),(3,4,5)])
    obj.data.materials.append(bpy.data.materials.new('UnusedSlot'))
    obj.data.materials.append(bpy.data.materials.new('UsedSlot'))
    for poly in obj.data.polygons: poly.material_index=1
    for offset in (0,0.2):
        layer=obj.data.uv_layers.new(name='UV'+str(offset))
        for i,item in enumerate(layer.data): item.uv=(offset+(i%3)/4,offset+0.1)
    attr=obj.data.color_attributes.new(name='ReleaseColor',type='FLOAT_COLOR',domain='POINT')
    for i,item in enumerate(attr.data): item.color=(0.2,0.4,0.6,0.25 if i<3 else 0.75)
    folder=OUT/'unshared'; export(folder,EX_UNSHARE_GEOMETRY=True)
    doc=ET.parse(folder/'UnsharedAttributes.mesh.xml')
    assert len(doc.findall('.//submeshes/submesh'))==1
    assert len(doc.findall('.//texcoord'))==12
    assert {round(float(c.get('value').split()[-1]),2) for c in doc.findall('.//colour_diffuse')}=={0.25,0.75}
    assert doc.find('.//submeshname').get('index')=='0'
    clear(); assert bpy.ops.ogre.import_mesh(filepath=str(folder/'UnsharedAttributes.mesh'))=={'FINISHED'}
    mesh=bpy.context.active_object.data
    assert len(mesh.uv_layers)==2
    assert {round(item.color[3],2) for item in mesh.color_attributes[0].data}=={0.25,0.75}

@case
def unshared_without_material_or_uv():
    triangle('UnsharedBare'); folder=OUT/'bare'; export(folder,EX_UNSHARE_GEOMETRY=True)
    clear(); assert bpy.ops.ogre.import_mesh(filepath=str(folder/'UnsharedBare.mesh'))=={'FINISHED'}
    assert len(bpy.context.active_object.data.polygons)==1

@case
def shape_export_falls_back_without_data_loss():
    obj=triangle('ShapeFallback'); obj.shape_key_add(name='Basis')
    key=obj.shape_key_add(name='Lift'); key.data[2].co.z=1
    folder=OUT/'shape_fallback'; export(folder,EX_UNSHARE_GEOMETRY=True)
    doc=ET.parse(folder/'ShapeFallback.mesh.xml')
    assert doc.find('.//sharedgeometry') is not None and doc.findall('.//pose')
    assert any('preserve shape' in text for text in Report.warnings)

@case
def node_fractional_timing_and_animation_import():
    obj=triangle('FractionalNode'); obj.rotation_mode='QUATERNION'
    scene=bpy.context.scene; scene.render.fps=30; scene.render.fps_base=1.001; scene.frame_step=4
    for frame,loc,angle,scale in [(10.5,0,0,1),(20.25,2,0.5,1.5)]:
        obj.location=(loc,0,0); obj.rotation_quaternion=Quaternion((0,0,1),angle); obj.scale=(scale,scale,scale)
        for path in ('location','rotation_quaternion','scale'): obj.keyframe_insert(data_path=path,frame=frame)
    folder=OUT/'node'; doc=export(folder)
    clip=doc.find('.//animation'); keys=clip.findall('keyframe')
    assert float(keys[0].get('time'))==0
    duration=9.75/(scene.render.fps/scene.render.fps_base)
    assert abs(float(clip.get('length'))-duration)<1e-8
    assert abs(float(keys[-1].get('time'))-duration)<1e-8
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    assert bpy.ops.ogre.import_mesh(filepath=str(folder/'test.scene'))=={'FINISHED'}
    imported=bpy.data.objects['FractionalNode']; track=imported.animation_data.nla_tracks[0]
    strip=track.strips[0]; animation.assign_action(imported,strip.action,strip.action_slot)
    scene.frame_set(10,subframe=0.75); bpy.context.view_layer.update()
    assert abs(imported.location.x-2)<1e-4
    assert abs(imported.scale.x-1.5)<1e-4
    assert abs(imported.rotation_quaternion.angle-0.5)<1e-4

@case
def shared_action_uses_matching_slots():
    first=triangle('SlotFirst'); first.select_set(False)
    second=triangle('SlotSecond'); first.select_set(True)
    action=bpy.data.actions.new('SharedAction')
    for obj,end in [(first,2),(second,7)]:
        curve=animation.new_fcurve(action,obj,'location',0)
        curve.keyframe_points.insert(1,0); curve.keyframe_points.insert(12,end)
        slot=animation.action_slot(action,obj)
        track=obj.animation_data_create().nla_tracks.new()
        strip=track.strips.new(obj.name,1,action); strip.action_slot=slot
    folder=OUT/'slots'; doc=export(folder)
    for name,expected in [('SlotFirst',2),('SlotSecond',7)]:
        node=doc.find('.//node[@name="'+name+'"]')
        assert abs(float(node.findall('animations/animation/keyframe')[-1].find('position').get('x'))-expected)<1e-5

@case
def invalid_vertex_index_rejected_without_changes():
    existing=triangle('Retained')
    path=fixture(OUT/'invalid_mesh',bad_index=True)
    before=set(bpy.data.objects)
    assert bpy.ops.ogre.import_mesh(filepath=str(path))=={'CANCELLED'}
    assert set(bpy.data.objects)==before and bpy.context.active_object==existing

@case
def mesh_overwrite_option_preserves_binary():
    obj=triangle('KeepMesh'); folder=OUT/'overwrite'; export(folder)
    before=(folder/'KeepMesh.mesh').read_bytes()
    obj.data.vertices[1].co.x=999
    export(folder,EX_MESH_OVERWRITE=False)
    assert (folder/'KeepMesh.mesh').read_bytes()==before

@case
def relocated_paths_and_malformed_configuration():
    previous=config.CONFIG_FILEPATH
    path=OUT/'bad_config.json'
    config.CONFIG_FILEPATH=str(path)
    try:
        path.write_text('[]'); loaded=config.load_config()
        assert loaded['SWAP_AXIS']=='xz-y'
        path.write_text(json.dumps({'SWAP_AXIS':'invalid','MESH':[], 'OGRETOOLS_XML_CONVERTER':r'Q:\missing\io_ogre\tools\windows\OgreXMLConverter.exe'}))
        loaded=config.load_config()
        assert loaded['SWAP_AXIS']=='xz-y' and loaded['MESH'] is True
        assert Path(loaded['OGRETOOLS_XML_CONVERTER']).is_file()
        custom=r'Q:\external\OgreMeshTool.exe'
        assert config.resolve_bundled_tool('OGRETOOLS_XML_CONVERTER',custom)==custom
    finally:
        config.CONFIG_FILEPATH=previous

@case
def converter_timeout_terminates_process():
    python=Path(bpy.app.binary_path).parent/'5.2/python/bin/python.exe'
    proc=util._popen([str(python),'-c','import time; time.sleep(10)'])
    try:
        util._communicate(proc,timeout=0.05)
        assert False,'Process did not time out'
    except RuntimeError as exc:
        assert 'timed out' in str(exc)
    assert proc.poll() is not None

@case
def unicode_and_spaced_input_paths():
    folder=OUT/'spaces_Ã©'; path=fixture(folder,name='mÃ¨sh with spaces')
    assert bpy.ops.ogre.import_mesh(filepath=str(path))=={'FINISHED'}
    assert len(bpy.context.active_object.data.vertices)==3

@case
def existing_rig_name_is_not_reused():
    folder=OUT/'rig'; folder.mkdir()
    source=ROOT/'ChatGPT/fixtures/ogre_samples'
    for name in ('robot.mesh','robot.skeleton'): shutil.copy2(source/name,folder/name)
    data=bpy.data.armatures.new('robot'); existing=bpy.data.objects.new('robot',data)
    bpy.context.collection.objects.link(existing)
    assert bpy.ops.ogre.import_mesh(filepath=str(folder/'robot.mesh'),IM_USE_SELECTED_SKELETON=False)=={'FINISHED'}
    imported=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']
    assert imported
    assert all(mod.object!=existing and mod.object is not None for obj in imported for mod in obj.modifiers if mod.type=='ARMATURE')

@case
def submesh_names_and_spaced_materials():
    for unshared in (False,True):
        clear()
        obj=triangle('NamedMaterial')
        obj.data.materials.append(bpy.data.materials.new('Unused Material'))
        obj.data.materials.append(bpy.data.materials.new('Actual Material'))
        obj.data.polygons[0].material_index=1
        folder=OUT/('named_'+str(unshared)); export(folder,EX_UNSHARE_GEOMETRY=unshared)
        doc=ET.parse(next(folder.glob('*.mesh.xml')))
        submesh=doc.find('.//submeshes/submesh')
        material=submesh.get('material')
        assert material and ' ' not in material
        assert 'material '+material+' {' in (folder/(material+'.material')).read_text()
        names=doc.findall('.//submeshnames/submeshname')
        assert len(names)==1 and names[0].get('index')=='0'

@case
def binary_unicode_directory():
    triangle('UnicodeBinary')
    folder=OUT/'binary_Ã©'; export(folder)
    assert bpy.ops.ogre.import_mesh(filepath=str(folder/'UnicodeBinary.mesh'))=={'FINISHED'}
    assert len(bpy.context.active_object.data.polygons)==1

@case
def animated_robot_deformation_roundtrip():
    from mathutils.kdtree import KDTree
    folder=OUT/'animated_robot'; folder.mkdir()
    source=ROOT/'ChatGPT/fixtures/ogre_samples'
    for name in ('robot.mesh','robot.skeleton'): shutil.copy2(source/name,folder/name)
    assert bpy.ops.ogre.import_mesh(filepath=str(folder/'robot.mesh'),IM_USE_SELECTED_SKELETON=False)=={'FINISHED'}
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    rig=obj.find_armature()
    strip=next(s for t in rig.animation_data.nla_tracks for s in t.strips if 'Walk' in s.action.name)
    animation.assign_action(rig,strip.action,strip.action_slot); rig.animation_data.use_nla=False
    def cloud(target,frame):
        bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()
        evaluated=target.evaluated_get(bpy.context.evaluated_depsgraph_get())
        return [evaluated.matrix_world @ v.co for v in evaluated.data.vertices]
    before={frame:cloud(obj,frame) for frame in (4,17)}
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    dest=OUT/'robot_roundtrip'; export(dest)
    clear()
    assert bpy.ops.ogre.import_mesh(filepath=str(dest/'test.scene'),IM_USE_SELECTED_SKELETON=False)=={'FINISHED'}
    new=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    newrig=new.find_armature()
    newstrip=next(s for t in newrig.animation_data.nla_tracks for s in t.strips if 'Walk' in s.action.name)
    animation.assign_action(newrig,newstrip.action,newstrip.action_slot); newrig.animation_data.use_nla=False
    errors=[]
    for frame in (4,17):
        points=cloud(new,frame); tree=KDTree(len(points))
        for index,point in enumerate(points): tree.insert(point,index)
        tree.balance()
        errors.append(max(tree.find(point)[2] for point in before[frame]))
    (folder/'deformation_error.json').write_text(json.dumps(errors))
    assert max(errors)<0.01,errors

@case
def bundled_upgrader_lod_and_edges():
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2)
    obj=bpy.context.active_object
    obj.data.name='LODMesh'
    folder=OUT/'lod_é'
    export(folder,EX_Vx_GENERATE_EDGE_LISTS=True,EX_LOD_LEVELS=1,EX_LOD_PERCENT=40)
    binary=folder/'LODMesh.mesh'
    xml=folder/'processed.mesh.xml'
    assert util.mesh_convert(str(binary),str(xml))
    doc=ET.parse(xml)
    assert doc.find('.//levelofdetail') is not None

@case
def combined_material_scene_references_exist():
    obj=triangle('CombinedMaterial')
    obj.data.materials.append(bpy.data.materials.new('CombinedSurface'))
    folder=OUT/'combined_materials'; doc=export(folder,EX_SEPARATE_MATERIALS=False)
    files=doc.findall('.//externals/item/file')
    assert len(files)==1 and files[0].get('name')=='test.material'
    assert all((folder/item.get('name')).is_file() for item in files)

addon_utils.disable('io_ogre',default_set=True)
record={'blender':bpy.app.version_string,'module_root':str(MODULE_ROOT),'output':str(OUT),'tests':RESULTS}
(ROOT/'ChatGPT/outputs/release_results.json').write_text(json.dumps(record,indent=2))
for result in RESULTS: print('PASS' if result['passed'] else 'FAIL',result['test'])
assert all(item['passed'] for item in RESULTS),'Release regression failed; see release_results.json'
print('RELEASE_SUITE_PASS',len(RESULTS))
