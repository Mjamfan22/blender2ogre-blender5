"""Real Blender regression checks; isolated assets, profiles, and converter runs."""
from pathlib import Path
import json
import math
import shutil
import sys
import traceback
import xml.etree.ElementTree as ET
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
module_root = Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv and len(sys.argv)>sys.argv.index('--')+1 else ROOT
sys.path.insert(0, str(module_root))
import bpy
import addon_utils
addon_utils.enable('io_ogre', default_set=True, persistent=False)
assert addon_utils.check('io_ogre')[1]
from io_ogre import config, util
from io_ogre.report import Report

OUT = ROOT/'ChatGPT/outputs/workflow'
OUT.mkdir(parents=True, exist_ok=True)
RESULTS = []

def case(fn):
    from test_support import skip_fixture_case
    if skip_fixture_case(fn.__name__): return
    try:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        for action in list(bpy.data.actions): bpy.data.actions.remove(action)
        Report.reset()
        fn()
        RESULTS.append({'test':fn.__name__,'passed':True})
    except Exception:
        detail=traceback.format_exc()
        print(detail)
        RESULTS.append({'test':fn.__name__,'passed':False,'detail':detail})

def export(folder, **kwargs):
    folder.mkdir(exist_ok=True)
    result=bpy.ops.ogre.export(filepath=str(folder/'test.scene'), EX_EXPORT_XML_DELETE=False,
        EX_FORCE_CAMERA=False, EX_FORCE_LIGHTS=False, **kwargs)
    assert result=={'FINISHED'}, result
    assert not Report.errors, Report.errors
    assert (folder/'test.scene').exists()
    return ET.parse(folder/'test.scene')

def triangle(name='Triangle', color_domain=None):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata([(0,0,0),(2,0,0),(0,3,0)],[],[(0,1,2)])
    mesh.uv_layers.new(name='UVMap')
    for item, uv in zip(mesh.uv_layers.active.data,[(0,0),(1,0),(0,1)]): item.uv=uv
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    if color_domain:
        attr=mesh.color_attributes.new(name='Color',type='FLOAT_COLOR',domain=color_domain)
        for item in attr.data: item.color=(0.2,0.4,0.6,0.5)
    return obj

@case
def bundled_converter():
    assert bpy.app.version==(5,2,3)
    assert Path(config.get('OGRETOOLS_XML_CONVERTER')).is_relative_to(module_root)
    assert util.detect_converter_type()=='OgreXMLConverter'
    assert util.xml_converter_version()==(13,3,2), util.xml_converter_parameters()

@case
def triangle_uv_colors_materials():
    obj=triangle(color_domain='CORNER')
    mat=bpy.data.materials.new('Tinted')
    mat.use_nodes=True
    shader=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value=(0.1,0.4,0.7,1)
    shader.inputs['Alpha'].default_value=0.4
    mat.surface_render_method='BLENDED'
    obj.data.materials.append(mat)
    folder=OUT/'triangle'
    export(folder, EX_GENERATE_TANGENTS='4')
    doc=ET.parse(folder/'Triangle.mesh.xml')
    assert len(doc.findall('.//face'))==1
    assert len(doc.findall('.//colour_diffuse'))==3
    assert len(doc.findall('.//texcoord'))==3
    assert 'scene_blend alpha_blend' in (folder/'Tinted.material').read_text()
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    assert bpy.ops.ogre.import_mesh(filepath=str(folder/'Triangle.mesh'))=={'FINISHED'}
    imported=bpy.context.active_object
    assert len(imported.data.polygons)==1
    assert len(imported.data.uv_layers)==1
    assert len(imported.data.color_attributes)==1
    assert abs(imported.data.color_attributes[0].data[0].color[3]-0.5)<0.01

@case
def point_colors():
    obj=triangle('PointColor',color_domain='POINT')
    folder=OUT/'point_colors'
    export(folder)
    doc=ET.parse(folder/'PointColor.mesh.xml')
    assert doc.find('.//vertexbuffer').get('colours_diffuse').lower()=='true'
    assert len(doc.findall('.//colour_diffuse'))==3

@case
def unshared_triangle():
    obj=triangle('Unshared')
    obj.data.materials.append(bpy.data.materials.new('Solid'))
    folder=OUT/'unshared'
    export(folder, EX_UNSHARE_GEOMETRY=True)
    doc=ET.parse(folder/'Unshared.mesh.xml')
    assert doc.find('.//submesh').get('usesharedvertices')=='false'
    assert len(doc.findall('.//face'))==1

@case
def shape_animation():
    obj=triangle('Morph')
    obj.shape_key_add(name='Basis')
    key=obj.shape_key_add(name='Lift')
    key.data[2].co.z+=1
    for frame,value in [(1,0),(12,1),(24,0)]:
        key.value=value
        key.keyframe_insert(data_path='value',frame=frame)
    action=obj.data.shape_keys.animation_data.action
    action.name='LiftClip'
    track=obj.data.shape_keys.animation_data.nla_tracks.new()
    track.strips.new('LiftClip',1,action)
    folder=OUT/'shape'
    export(folder)
    doc=ET.parse(folder/'Morph.mesh.xml')
    assert doc.findall('.//pose')
    assert doc.findall('.//animation')
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    assert bpy.ops.ogre.import_mesh(filepath=str(folder/'Morph.mesh'))=={'FINISHED'}
    imported=bpy.context.active_object
    assert imported.data.shape_keys.key_blocks.get('Lift')
    assert imported.data.shape_keys.animation_data.nla_tracks

@case
def multiple_morph_clips():
    obj=triangle('MorphClips')
    obj.shape_key_add(name='Basis')
    key=obj.shape_key_add(name='Lift')
    key.data[2].co.z=1
    keys=obj.data.shape_keys
    for name,peak in [('Small',0.25),('Large',1.0)]:
        keys.animation_data_clear()
        for frame,value in [(1,0),(12,peak),(24,0)]:
            key.value=value
            key.keyframe_insert(data_path='value',frame=frame)
        action=keys.animation_data.action; action.name=name; action.use_fake_user=True
    keys.animation_data_clear(); keys.animation_data_create()
    for name in ('Small','Large'):
        track=keys.animation_data.nla_tracks.new(); track.mute=True
        track.strips.new(name,1,bpy.data.actions[name])
    folder=OUT/'morph_clips'
    export(folder)
    doc=ET.parse(folder/'MorphClips.mesh.xml')
    peaks={a.get('name'):max(float(p.get('influence')) for p in a.findall('.//poseref')) for a in doc.findall('.//animation')}
    assert abs(peaks['Small']-0.25)<1e-5 and abs(peaks['Large']-1)<1e-5, peaks

@case
def node_animation():
    obj=triangle('Moving')
    for frame,x in [(1,0),(24,2)]:
        obj.location.x=x
        obj.keyframe_insert(data_path='location',frame=frame)
    action=obj.animation_data.action
    action.name='MoveClip'
    track=obj.animation_data.nla_tracks.new()
    track.strips.new('MoveClip',1,action)
    folder=OUT/'node'
    export(folder)
    assert ET.parse(folder/'test.scene').findall('.//animation')

@case
def original_robot_animations():
    source=ROOT/'ChatGPT/fixtures/ogre_samples'
    folder=OUT/'robot'
    folder.mkdir(exist_ok=True)
    for name in ('robot.mesh','robot.skeleton'): shutil.copy2(source/name,folder/name)
    assert bpy.ops.ogre.import_mesh(filepath=str(folder/'robot.mesh'),IM_USE_SELECTED_SKELETON=False)=={'FINISHED'}
    rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    assert len(rigs)==len(meshes)==1
    assert len(rigs[0].data.bones)>10
    assert len(rigs[0].animation_data.nla_tracks)>1
    clips=len(rigs[0].animation_data.nla_tracks)
    bpy.context.view_layer.objects.active=meshes[0]
    export(folder,EX_ONLY_KEYFRAMES=True,EX_ONLY_KEYFRAMED_BONES=True)
    skel=list(folder.glob('*.skeleton.xml'))
    assert skel
    assert max(len(ET.parse(p).findall('.//animation')) for p in skel)==clips

@case
def original_ogrehead():
    folder=OUT/'ogrehead'; folder.mkdir(exist_ok=True)
    source=ROOT/'ChatGPT/fixtures/ogre_samples/ogrehead.mesh'
    shutil.copy2(source,folder/source.name)
    assert bpy.ops.ogre.import_mesh(filepath=str(folder/source.name))=={'FINISHED'}
    assert len(bpy.context.active_object.data.vertices)>1000

@case
def nested_scene_transform():
    obj=triangle('SceneMesh')
    folder=OUT/'scene'; export(folder)
    scene=folder/'hierarchy.scene'
    scene.write_text('''<scene><nodes><node name="Parent"><position x="10" y="0" z="0"/><rotation qw="1" qx="0" qy="0" qz="0"/><scale x="1" y="1" z="1"/><node name="Child"><position x="2" y="0" z="0"/><rotation qw="1" qx="0" qy="0" qz="0"/><scale x="1" y="1" z="1"/><entity name="ChildMesh" meshFile="SceneMesh.mesh"/></node></node></nodes></scene>''')
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    assert bpy.ops.ogre.import_mesh(filepath=str(scene))=={'FINISHED'}
    child=bpy.data.objects['Child']
    bpy.context.view_layer.update()
    assert abs(child.matrix_world.translation.x-12)<1e-5, child.matrix_world
    assert len([o for o in bpy.context.scene.objects if o.type=='MESH'])==1

@case
def invalid_input_cancelled():
    bad=OUT/'missing.mesh'
    result=bpy.ops.ogre.import_mesh(filepath=str(bad))
    assert result=={'CANCELLED'}, result
    malformed=OUT/'bad.xml'; malformed.write_text('<mesh><broken>')
    assert bpy.ops.ogre.import_mesh(filepath=str(malformed))=={'CANCELLED'}
    assert bpy.ops.ogre.import_mesh(filepath=str(OUT/'missing.xml'))=={'CANCELLED'}

@case
def scene_cameras_and_lights():
    mesh=triangle('LitMesh')
    bpy.ops.object.camera_add(location=(1,2,3))
    bpy.context.object.name='RoundtripCamera'
    bpy.context.object.data.angle=0.7
    bpy.ops.object.light_add(type='POINT',location=(4,5,6))
    bpy.context.object.name='RoundtripLight'
    bpy.context.object.data.energy=25
    for obj in bpy.context.scene.objects: obj.select_set(True)
    folder=OUT/'lit_scene'; export(folder)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    assert bpy.ops.ogre.import_mesh(filepath=str(folder/'test.scene'))=={'FINISHED'}
    cameras=[o for o in bpy.context.scene.objects if o.type=='CAMERA']
    lights=[o for o in bpy.context.scene.objects if o.type=='LIGHT']
    assert len(cameras)==len(lights)==1
    bpy.context.view_layer.update()
    assert (cameras[0].matrix_world.translation-Vector((1,2,3))).length<1e-5
    assert abs(cameras[0].data.angle-0.7)<0.08
    assert abs(lights[0].data.energy-25)<1e-5

@case
def register_cycle():
    addon_utils.disable('io_ogre',default_set=True)
    assert not hasattr(bpy.types.Object,'use_draw_distance')
    assert not hasattr(bpy.types.Material,'use_ogre_parent_material')
    addon_utils.enable('io_ogre',default_set=True,persistent=False)
    assert addon_utils.check('io_ogre')[1]
    assert hasattr(bpy.types.Material,'use_ogre_parent_material')

addon_utils.disable('io_ogre',default_set=True)
report={'blender':bpy.app.version_string,'module_root':str(module_root),'tests':RESULTS}
(ROOT/'ChatGPT/outputs/workflow_results.json').write_text(json.dumps(report,indent=2))
for result in RESULTS: print('PASS' if result['passed'] else 'FAIL',result['test'])
assert all(r['passed'] for r in RESULTS), 'See workflow_results.json'
print('WORKFLOW_PASS')
