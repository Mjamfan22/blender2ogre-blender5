"""Regressions for OGRECave/blender2ogre open issue reports."""
from pathlib import Path
import json, sys, traceback, uuid, math, shutil
import xml.etree.ElementTree as ET
import bpy, addon_utils
from mathutils import Matrix, Vector, Quaternion
ROOT=Path(__file__).resolve().parents[2]
MODULE_ROOT=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv and len(sys.argv)>sys.argv.index('--')+1 else ROOT
sys.path.insert(0,str(MODULE_ROOT))
addon_utils.enable('io_ogre',default_set=True,persistent=False)
from io_ogre import config, util, animation
from io_ogre.report import Report
from io_ogre.ogre.material import OgreMaterialGenerator
OUT=ROOT/'ChatGPT/outputs/upstream_issues'/uuid.uuid4().hex[:8]
OUT.mkdir(parents=True)
RESULTS=[]

def clear():
    if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    config.CONFIG.update(config._CONFIG_DEFAULTS_ALL)
    scene=bpy.context.scene; scene.render.fps=24; scene.render.fps_base=1
    scene.frame_step=1; scene.frame_set(1)

def case(fn):
    from test_support import skip_fixture_case
    if skip_fixture_case(fn.__name__): return
    clear()
    try:
        fn(); result={'test':fn.__name__,'passed':True}
    except Exception:
        result={'test':fn.__name__,'passed':False,'detail':traceback.format_exc()}
        print(result['detail'])
    RESULTS.append(result)

def triangle(name):
    data=bpy.data.meshes.new(name)
    data.from_pydata([(0,0,0),(2,0,0),(0,3,0)],[],[(0,1,2)])
    ob=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(ob)
    ob.select_set(True); bpy.context.view_layer.objects.active=ob
    return ob

def export(folder,**options):
    folder.mkdir(exist_ok=True)
    args=dict(filepath=str(folder/'test.scene'),EX_EXPORT_XML_DELETE=False,EX_FORCE_CAMERA=False,EX_FORCE_LIGHTS=False)
    args.update(options)
    assert bpy.ops.ogre.export(**args)=={'FINISHED'},Report.errors
    assert not Report.errors,Report.errors
    return ET.parse(folder/'test.scene')

def make_rig(obj):
    data=bpy.data.armatures.new('IssueRig'); rig=bpy.data.objects.new('IssueRig',data)
    bpy.context.collection.objects.link(rig); bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT'); bone=data.edit_bones.new('Root'); bone.head=(0,0,0); bone.tail=(0,0,1)
    bpy.ops.object.mode_set(mode='OBJECT')
    mod=obj.modifiers.new('Rig','ARMATURE'); mod.object=rig
    vg=obj.vertex_groups.new(name='Root'); vg.add(list(range(3)),1,'REPLACE')
    bpy.context.view_layer.objects.active=obj
    return rig

@case
def issue248_selected_child_and_unselected_siblings():
    parent=triangle('ParentMesh'); child=triangle('SelectedChild'); sibling=triangle('SiblingMesh'); grandchild=triangle('Grandchild')
    child.parent=parent; sibling.parent=parent; grandchild.parent=child
    bpy.ops.object.select_all(action='DESELECT'); child.select_set(True)
    folder=OUT/'selected'; doc=export(folder,EX_SELECTED_ONLY=True)
    assert [item.get('name') for item in doc.findall('.//entity')]==['SelectedChild']
    assert {p.name for p in folder.glob('*.mesh')}=={'SelectedChild.mesh'}
    assert doc.find('.//node[@name="ParentMesh"]/node[@name="SelectedChild"]') is not None

@case
def issue248_selected_only_inside_merge_collection():
    a=triangle('SelectedMergePart'); b=triangle('UnselectedMergePart'); b.location.x=50
    collection=bpy.data.collections.new('merge.IssueMerge'); bpy.context.scene.collection.children.link(collection)
    collection.objects.link(a); collection.objects.link(b)
    bpy.ops.object.select_all(action='DESELECT'); a.select_set(True); bpy.context.view_layer.objects.active=a
    folder=OUT/'selected_merge'; export(folder,EX_SELECTED_ONLY=True)
    doc=ET.parse(folder/'IssueMerge.mesh.xml')
    assert len(doc.findall('.//face'))==1

@case
def issue255_opaque_and_translucent_materials():
    mat=bpy.data.materials.new('Opaque'); mat.use_nodes=True
    before=[(p,getattr(mat,p)) for p in ('surface_render_method','use_backface_culling')]
    text=OgreMaterialGenerator(mat, str(OUT)).generate()
    assert 'scene_blend' not in text and 'cull_hardware none' not in text and 'depth_write off' not in text,text
    assert before==[(p,getattr(mat,p)) for p,_ in before]
    node=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'); node.inputs['Alpha'].default_value=.4
    text=OgreMaterialGenerator(mat,str(OUT)).generate()
    assert 'scene_blend alpha_blend' in text and 'depth_write off' in text
    mat['ogre_alpha_mode']='MASK'; mat['ogre_alpha_threshold']=.25
    assert 'alpha_rejection greater_equal 63.75' in OgreMaterialGenerator(mat,str(OUT)).generate()

@case
def issue145_generated_and_packed_textures_without_conversion():
    obj=triangle('GeneratedTexture'); mat=bpy.data.materials.new('GeneratedSurface'); mat.use_nodes=True; obj.data.materials.append(mat)
    node=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    image=bpy.data.images.new('Generated.png',width=2,height=2); image.generated_color=(.2,.6,.9,1)
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=image
    mat.node_tree.links.new(tex.outputs['Color'],node.inputs['Base Color'])
    before=(image.filepath,image.filepath_raw,image.file_format,image.source)
    folder=OUT/'generated'; export(folder,EX_FORCE_IMAGE_FORMAT='NONE')
    assert (folder/'Generated.png').stat().st_size>0
    assert (image.filepath,image.filepath_raw,image.file_format,image.source)==before
    source=OUT/'packed_source.png'; image.save(filepath=str(source),save_copy=True)
    packed=bpy.data.images.load(str(source)); packed.pack(); tex.image=packed
    before=(packed.filepath,packed.filepath_raw,packed.file_format,packed.packed_file.data)
    folder=OUT/'packed'; export(folder,EX_FORCE_IMAGE_FORMAT='NONE')
    assert (folder/'packed_source.png').stat().st_size>0
    assert (packed.filepath,packed.filepath_raw,packed.file_format,packed.packed_file.data)==before

@case
def issue263_prefix_references_and_source_names():
    obj=triangle('PrefixMesh'); mat=bpy.data.materials.new('PrefixSurface'); obj.data.materials.append(mat)
    rig=make_rig(obj)
    before=(obj.name,obj.data.name,mat.name,rig.name,rig.data.name)
    folder=OUT/'prefix'; doc=export(folder,EX_EXPORT_PREFIX='Pack_')
    assert doc.find('.//entity').get('meshFile')=='Pack_PrefixMesh.mesh'
    assert (folder/'Pack_PrefixSurface.material').is_file()
    mesh=ET.parse(folder/'Pack_PrefixMesh.mesh.xml')
    assert mesh.find('skeletonlink').get('name')=='Pack_PrefixMesh.skeleton'
    assert (folder/'Pack_PrefixMesh.skeleton').is_file()
    assert mesh.find('.//submesh').get('material')=='Pack_PrefixSurface'
    assert before==(obj.name,obj.data.name,mat.name,rig.name,rig.data.name)
    doc=export(OUT/'prefix_shared',EX_EXPORT_PREFIX='Pack_',EX_SHARED_ARMATURE=True)
    mesh=ET.parse(OUT/'prefix_shared/Pack_PrefixMesh.mesh.xml')
    assert mesh.find('skeletonlink').get('name')=='Pack_IssueRig.skeleton'
    assert (OUT/'prefix_shared/Pack_IssueRig.skeleton').is_file()

@case
def issue263_manual_lod_prefix_references():
    obj=triangle('PrefixLOD'); lod=triangle('PrefixLOD_LOD_1')
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active=obj
    folder=OUT/'prefix_lod'; export(folder,EX_EXPORT_PREFIX='Pack_',EX_LOD_LEVELS=1,EX_LOD_GENERATION='2')
    mesh=ET.parse(folder/'Pack_PrefixLOD.mesh.xml')
    assert mesh.find('.//lodmanual').get('meshname')=='Pack_PrefixLOD_LOD_1.mesh'
    assert (folder/'Pack_PrefixLOD_LOD_1.mesh').is_file()

@case
def issue87_sparse_node_keys_preserve_endpoints():
    obj=triangle('SparseNode')
    for frame,x in [(1.25,0),(5.5,2),(11.75,4)]:
        obj.location.x=x; obj.keyframe_insert(data_path='location',frame=frame)
    folder=OUT/'sparse'; doc=export(folder,EX_NODE_KEYFRAMES=True)
    clip=doc.find('.//animation')
    assert len(clip.findall('keyframe'))==3
    assert [round(float(k.get('time'))*24+1.25,5) for k in clip.findall('keyframe')]==[1.25,5.5,11.75]
    doc=export(OUT/'baked',EX_NODE_KEYFRAMES=False)
    assert len(doc.findall('.//keyframe'))>3

@case
def issue59_mirror_toggle_preserves_modifier():
    obj=triangle('MirrorMesh'); mod=obj.modifiers.new('Mirror','MIRROR'); mod.use_clip=False
    folder=OUT/'mirror_on'; export(folder,EX_APPLY_MODIFIERS=True)
    count=len(ET.parse(folder/'MirrorMesh.mesh.xml').findall('.//face'))
    folder=OUT/'mirror_off'; export(folder,EX_APPLY_MODIFIERS=False)
    assert count==2 and len(ET.parse(folder/'MirrorMesh.mesh.xml').findall('.//face'))==1
    assert len(obj.modifiers)==1 and mod.show_viewport and mod.type=='MIRROR'

@case
def issue273_unshared_skin_weights_and_binary():
    obj=triangle('UnsharedSkin'); rig=make_rig(obj)
    folder=OUT/'unshared_skin'; export(folder,EX_UNSHARE_GEOMETRY=True)
    doc=ET.parse(folder/'UnsharedSkin.mesh.xml')
    assert doc.find('sharedgeometry') is None
    sub=doc.find('.//submesh'); assert sub.get('usesharedvertices')=='false'
    assert len(sub.findall('boneassignments/vertexboneassignment'))==3
    assert (folder/'UnsharedSkin.mesh').stat().st_size>0

@case
def issue266_multiple_slotted_skeletal_clips():
    obj=triangle('SlottedSkin'); rig=make_rig(obj); anim=rig.animation_data_create()
    for name,axis in [('MoveX',0),('MoveY',1)]:
        action=bpy.data.actions.new(name)
        for i in range(3):
            curve=animation.new_fcurve(action,rig,'pose.bones["Root"].location',i)
            curve.keyframe_points.insert(1,0); curve.keyframe_points.insert(8,2 if i==axis else 0)
        track=anim.nla_tracks.new(); strip=track.strips.new(name,1,action); strip.action_slot=animation.action_slot(action,rig)
    saved=[strip.action_slot for track in anim.nla_tracks for strip in track.strips]
    folder=OUT/'slotted_skin'; export(folder)
    doc=ET.parse(folder/'SlottedSkin.skeleton.xml'); clips=doc.findall('.//animation')
    assert {c.get('name') for c in clips}=={'MoveX','MoveY'}
    assert all(c.find('.//translate') is not None for c in clips)
    assert [strip.action_slot for track in anim.nla_tracks for strip in track.strips]==saved

@case
def issues231_240_camera_light_hierarchy_world_directions():
    parent=triangle('RotatedParent'); parent.rotation_euler=(.3,.4,.5); parent.location=(2,-3,4)
    sun_data=bpy.data.lights.new('Direction','SUN'); sun=bpy.data.objects.new('Direction',sun_data); bpy.context.collection.objects.link(sun)
    sun.parent=parent; sun.rotation_euler=(.2,-.1,.6)
    camera_data=bpy.data.cameras.new('View'); camera=bpy.data.objects.new('View',camera_data); bpy.context.collection.objects.link(camera)
    camera.parent=sun; camera.location=(1,2,3); camera.rotation_euler=(.7,.2,-.3)
    bpy.context.view_layer.update()
    expected={ob.name:util.axis_matrix() @ (ob.matrix_world.to_quaternion() @ Vector((0,0,-1))) for ob in (sun,camera)}
    doc=export(OUT/'directions',EX_SELECTED_ONLY=False)
    found={}
    def walk(node,world):
        r=node.find('rotation'); q=Quaternion(tuple(float(r.get(k,v)) for k,v in zip(('qw','qx','qy','qz'),(1,0,0,0)))) if r is not None else Quaternion()
        world=world @ q
        for kind in ('camera','light'):
            for item in node.findall(kind): found[item.get('name')]=world @ Vector((0,0,-1))
        for child in node.findall('node'): walk(child,world)
    for node in doc.findall('./nodes/node'): walk(node,Quaternion())
    assert set(found)==set(expected)
    for name in found: assert (found[name]-expected[name]).length<1e-5,(name,found[name],expected[name])

@case
def issue156_import_inheritance_variables_and_named_overrides():
    from io_ogre.ogre.material_parser import MaterialParser
    folder=OUT/'inheritance'; folder.mkdir()
    image=bpy.data.images.new('Tire.png',width=2,height=2); image.save(filepath=str(folder/'Tire.png'),save_copy=True)
    (folder/'base.material').write_text('''abstract material Base
{
    technique Main {
        pass Color {
            diffuse 0.3 0.5 0.7 1
            texture_unit Albedo { texture $texture }
        }
    }
}
''')
    (folder/'child.material').write_text('''import * from "base.material"
material Tire : Base {
    set $texture "Tire.png"
    technique Main {
        pass Color { diffuse 0.9 0.8 0.7 1 }
    }
}
''')
    mats={}; MaterialParser.xParseMaterial(mats,str(folder/'child.material'),str(folder))
    assert mats['Tire']['diffuse']==[.9,.8,.7,1],mats
    assert Path(mats['Tire']['texture'])==folder/'Tire.png',mats

@case
def issue156_missing_and_cyclic_material_dependencies_reported():
    from io_ogre.ogre.material_resolver import MaterialResolver
    folder=OUT/'bad_materials'; folder.mkdir()
    source=folder/'cycle.material'
    source.write_text('material A : B { }\nmaterial B : A { }\nmaterial Missing : Unknown { }\n')
    Report.reset(); text=MaterialResolver(folder).expand(source)
    assert any('Cyclic material inheritance' in w for w in Report.warnings),Report.warnings
    assert any('Missing parent material' in w for w in Report.warnings),Report.warnings
    assert 'material' not in text

@case
def issue138_renamed_principled_packed_metal_roughness_map():
    from io_ogre.ogre.material import gather_metallic_roughness_texture
    from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
    mat=bpy.data.materials.new('RenamedPBR'); mat.use_nodes=True
    shader=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'); shader.name='Artist shader'
    image=bpy.data.images.new('metal rough.png',width=2,height=2)
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=image
    channels=mat.node_tree.nodes.new('ShaderNodeSeparateColor')
    mat.node_tree.links.new(tex.outputs['Color'],channels.inputs[0])
    mat.node_tree.links.new(channels.outputs['Green'],shader.inputs['Roughness'])
    mat.node_tree.links.new(channels.outputs['Blue'],shader.inputs['Metallic'])
    assert gather_metallic_roughness_texture(PrincipledBSDFWrapper(mat)).image==image
    folder=OUT/'renamed_pbr'; folder.mkdir()
    generator=OgreMaterialGenerator(mat,str(folder)); text=generator.generate(); generator.copy_textures()
    assert 'lighting_stage metal_roughness texture metal_rough.png' in text,text
    assert (folder/'metal_rough.png').is_file()

@case
def issue184_missing_image_converter_has_actionable_error():
    previous=config.CONFIG['IMAGE_MAGICK_CONVERT']; config.CONFIG['IMAGE_MAGICK_CONVERT']=str(OUT/'missing-magick.exe')
    try:
        try:
            util.image_magick(bpy.data.images.new('ForConversion',width=1,height=1),'missing.png',str(OUT/'missing-result.png'))
            assert False,'Expected conversion failure'
        except RuntimeError as error:
            assert 'ImageMagick' in str(error) and 'preferences' in str(error),str(error)
    finally: config.CONFIG['IMAGE_MAGICK_CONVERT']=previous

@case
def issue263_external_material_names_not_prefixed():
    obj=triangle('ExternalMesh'); obj.data.materials.append(bpy.data.materials.new('extern.RuntimeMaterial'))
    folder=OUT/'external_prefix'; export(folder,EX_EXPORT_PREFIX='Pack_')
    doc=ET.parse(folder/'Pack_ExternalMesh.mesh.xml')
    assert doc.find('.//submesh').get('material')=='RuntimeMaterial'

@case
def issue272_import_operator_constructor_initializes_converter():
    from io_ogre.ui.importer import OP_ogre_import
    # Blender instantiates these through its RNA factory, the path that failed
    # in the report. Exercise EXEC_DEFAULT via an ordinary tiny XML import.
    folder=OUT/'import_operator'; folder.mkdir()
    obj=triangle('ConstructorMesh'); export(folder)
    assert bpy.ops.ogre.import_mesh(filepath=str(folder/'ConstructorMesh.mesh'))=={'FINISHED'},Report.errors

@case
def skeletal_export_disabled_does_not_leave_dangling_links():
    obj=triangle('StaticSkin'); rig=make_rig(obj)
    for unshared in (False,True):
        folder=OUT/('static_skin_'+str(unshared)); export(folder,EX_ARMATURE_ANIMATION=False,EX_UNSHARE_GEOMETRY=unshared)
        doc=ET.parse(folder/'StaticSkin.mesh.xml')
        assert doc.find('skeletonlink') is None
        assert not list(folder.glob('*.skeleton'))

@case
def issue273_filtered_bone_ids_match_both_geometry_modes():
    obj=triangle('FilteredSkin'); rig=make_rig(obj)
    bpy.context.view_layer.objects.active=rig; bpy.ops.object.mode_set(mode='EDIT')
    helper=rig.data.edit_bones.new('UnusedHelper'); helper.head=(1,0,0); helper.tail=(1,0,1)
    deform=rig.data.edit_bones.new('Deform'); deform.head=(0,0,1); deform.tail=(0,0,2); deform.parent=rig.data.edit_bones['Root']
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.data.bones['Root'].use_deform=False; rig.data.bones['UnusedHelper'].use_deform=False
    obj.vertex_groups['Root'].remove(list(range(3)))
    obj.vertex_groups.new(name='Deform').add(list(range(3)),1,'REPLACE')
    obj.vertex_groups.new(name='UnusedHelper').add([0],.5,'REPLACE')
    bpy.context.view_layer.objects.active=obj
    for unshared in (False,True):
        folder=OUT/('filtered_'+str(unshared)); export(folder,EX_ONLY_DEFORMABLE_BONES=True,EX_UNSHARE_GEOMETRY=unshared)
        skeleton=ET.parse(folder/'FilteredSkin.skeleton.xml')
        assert {b.get('name'):b.get('id') for b in skeleton.findall('./bones/bone')}=={'Root':'0','Deform':'1'}
        mesh=ET.parse(folder/'FilteredSkin.mesh.xml')
        assert {b.get('boneindex') for b in mesh.findall('.//vertexboneassignment')}=={'1'}

@case
def issue142_shared_skeleton_falls_back_for_distinct_bind_space():
    obj=triangle('SeparateBind'); rig=make_rig(obj); rig.location=(1,2,3)
    folder=OUT/'separate_bind'; export(folder,EX_SHARED_ARMATURE=True)
    assert ET.parse(folder/'SeparateBind.mesh.xml').find('skeletonlink').get('name')=='SeparateBind.skeleton'
    assert (folder/'SeparateBind.skeleton').is_file()
    assert any('bind spaces differ' in w for w in Report.warnings),Report.warnings

def load_fixture(number, name):
    file=ROOT/'ChatGPT/fixtures/reporters'/str(number)/name
    with bpy.data.libraries.load(str(file),link=False) as (source,target):
        target.objects=source.objects
    for obj in target.objects:
        if obj:
            bpy.context.collection.objects.link(obj)
            obj.select_set(True)
    bpy.context.view_layer.objects.active=next(obj for obj in target.objects if obj and obj.type=='MESH')
    bpy.context.view_layer.update()
    return [obj for obj in target.objects if obj]

def cloud(obj, frame):
    from io_ogre.ogre.node_anim import set_frame
    set_frame(frame); bpy.context.view_layer.update()
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [evaluated.matrix_world @ v.co for v in evaluated.data.vertices]

def cloud_error(expected, actual):
    from mathutils.kdtree import KDTree
    def distance(a,b):
        tree=KDTree(len(b))
        for i,point in enumerate(b): tree.insert(point,i)
        tree.balance()
        return max(tree.find(point)[2] for point in a)
    return max(distance(expected,actual),distance(actual,expected))

@case
def issue240_reporter_swaptest_geometry_roundtrip():
    objects=load_fixture(240,'swaptest.blend')
    meshes=[ob for ob in objects if ob.type=='MESH']
    expected={ob.name:cloud(ob,1) for ob in meshes}
    folder=OUT/'reporter_swaptest'; export(folder,EX_SELECTED_ONLY=False,EX_MATERIALS=False)
    clear()
    assert bpy.ops.ogre.import_mesh(filepath=str(folder/'test.scene'),IM_USE_SELECTED_SKELETON=False)=={'FINISHED'},Report.errors
    errors={}
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH': errors[obj.parent.name]=cloud_error(expected[obj.parent.name],cloud(obj,1))
    assert set(errors)==set(expected),errors
    (folder/'geometry_errors.json').write_text(json.dumps(errors))
    assert max(errors.values())<1e-4,errors

@case
def issue142_reporter_animated_character_roundtrip():
    objects=load_fixture(142,'untitled.blend')
    obj=next(o for o in objects if o.type=='MESH'); rig=obj.find_armature()
    strip=next(s for t in rig.animation_data.nla_tracks for s in t.strips if s.action)
    name=strip.action.name; first=strip.action_frame_start
    animation.assign_action(rig,strip.action,strip.action_slot); rig.animation_data.use_nla=False
    expected={frame:cloud(obj,frame) for frame in (first+3,first+16)}
    original_bones={}
    for frame in expected:
        cloud(obj,frame)
        original_bones[frame]={b.name:list((rig.matrix_world @ b.matrix).translation) for b in rig.pose.bones}
    folder=OUT/'reporter_character'; export(folder,EX_SELECTED_ONLY=False,EX_MATERIALS=False,EX_TRIM_BONE_WEIGHTS=0)
    raw=ET.parse(folder/(util.export_name(obj.data.name)+'.skeleton.xml'))
    util.mesh_convert(str(folder/(util.export_name(obj.data.name)+'.skeleton')),str(folder/'binary.skeleton.xml'))
    raw_bones={b.get('name'):b for b in raw.findall('./bones/bone')}
    raw_parents={b.get('bone'):b.get('parent') for b in raw.findall('./bonehierarchy/boneparent')}
    raw_tracks={t.get('bone'):t for t in raw.findall('.//animation/tracks/track')}
    def xyz(element, default=0): return Vector(tuple(float(element.get(k,default)) for k in ('x','y','z'))) if element is not None else Vector((default,)*3)
    def rotation(element): return Quaternion(xyz(element.find('axis')),float(element.get('angle'))) if element is not None else Quaternion()
    raw_errors={}
    for frame in expected:
        matrices={}
        def evaluate(name):
            if name in matrices: return matrices[name]
            b=raw_bones[name]; pos=xyz(b.find('position')); rot=rotation(b.find('rotation')); scale=Vector((1,1,1))
            if name in raw_tracks:
                k=min(raw_tracks[name].findall('./keyframes/keyframe'),key=lambda k:abs(float(k.get('time'))-(frame-first)/24))
                pos+=xyz(k.find('translate')); rot=rot @ rotation(k.find('rotate')); scale=xyz(k.find('scale'),1)
            local=Matrix.LocRotScale(pos,rot,scale)
            matrices[name]=evaluate(raw_parents[name]) @ local if name in raw_parents else local
            return matrices[name]
        raw_errors[str(frame)]={name:(Vector(original_bones[frame][name])-(obj.matrix_world @ util.axis_matrix().inverted().to_4x4() @ evaluate(name)).translation).length for name in raw_bones}
    (folder/'raw_bone_errors.json').write_text(json.dumps(raw_errors,indent=2))
    clear()
    assert bpy.ops.ogre.import_mesh(filepath=str(folder/'test.scene'),IM_USE_SELECTED_SKELETON=False)=={'FINISHED'},Report.errors
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH'); rig=obj.find_armature()
    strip=next(s for t in rig.animation_data.nla_tracks for s in t.strips if s.action.name.startswith(name))
    animation.assign_action(rig,strip.action,strip.action_slot); rig.animation_data.use_nla=False
    errors=[cloud_error(points,cloud(obj,frame-first)) for frame,points in expected.items()]
    debug={'first':first,'original_bounds':[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3) for points in [next(iter(expected.values()))]],'bone_errors':{}}
    for frame in expected:
        cloud(obj,frame-first)
        debug['bone_errors'][str(frame)]={b.name:(Vector(original_bones[frame][b.name])-(rig.matrix_world @ b.matrix).translation).length for b in rig.pose.bones}
    (folder/'debug.json').write_text(json.dumps(debug,indent=2))
    (folder/'deformation_errors.json').write_text(json.dumps(errors))
    assert max(errors)<0.01,errors

addon_utils.disable('io_ogre',default_set=True)
record={'blender':bpy.app.version_string,'module_root':str(MODULE_ROOT),'output':str(OUT),'tests':RESULTS}
(ROOT/'ChatGPT/outputs/upstream_results.json').write_text(json.dumps(record,indent=2))
for result in RESULTS: print('PASS' if result['passed'] else 'FAIL',result['test'])
assert all(item['passed'] for item in RESULTS),'Upstream regressions failed; see upstream_results.json'
print('UPSTREAM_SUITE_PASS',len(RESULTS))
