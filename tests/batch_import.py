"""Batch file-browser/drop imports exercised against the installed add-on ZIP."""
from pathlib import Path
import hashlib
import json
import sys
import traceback
import uuid

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
MODULE_ROOT = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else ROOT
sys.path.insert(0, str(MODULE_ROOT))
addon_utils.enable('io_ogre', default_set=True, persistent=False)
from io_ogre import config, util
from io_ogre.import_batch import import_script
from io_ogre.ogre import ogre_import
from io_ogre.report import Report

OUT = ROOT / '.build/outputs/batch_import' / uuid.uuid4().hex[:8]
OUT.mkdir(parents=True)
RESULTS = []


def clear():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    config.CONFIG.update(config._CONFIG_DEFAULTS_ALL)
    Report.reset()


def case(fn):
    clear()
    try:
        fn()
        result = {'test': fn.__name__, 'passed': True}
    except Exception:
        result = {'test': fn.__name__, 'passed': False, 'detail': traceback.format_exc()}
        print(result['detail'])
    RESULTS.append(result)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def fixture(folder, name, skin=False):
    bones = '<boneassignments><vertexboneassignment vertexindex="0" boneindex="0" weight="1"/></boneassignments>' if skin else ''
    return write(folder / (name + '.mesh.xml'), '''<mesh>
<sharedgeometry vertexcount="3"><vertexbuffer positions="true" normals="true" texture_coords="2">
<vertex><position x="0" y="0" z="0"/><normal x="0" y="0" z="1"/><texcoord u="0" v="0"/><texcoord u="0.1" v="0.2"/></vertex>
<vertex><position x="2" y="0" z="0"/><normal x="0" y="0" z="1"/><texcoord u="1" v="0"/><texcoord u="0.8" v="0.2"/></vertex>
<vertex><position x="0" y="3" z="0"/><normal x="0" y="0" z="1"/><texcoord u="0" v="1"/><texcoord u="0.1" v="0.9"/></vertex>
</vertexbuffer></sharedgeometry>
<submeshes><submesh material="_missing_material_" usesharedvertices="true" operationtype="triangle_list">
<faces count="1"><face v1="0" v2="1" v3="2"/></faces></submesh></submeshes>''' + bones + '</mesh>')


def batch(folder, names, **settings):
    args = dict(directory=str(folder), files=[{'name': name} for name in names],
                IM_IMPORT_INTO_COLLECTION=True, IM_USE_SELECTED_SKELETON=False,
                IM_Vx_ENABLE_LOGGING=False)
    args.update(settings)
    return bpy.ops.ogre.import_mesh(**args)


@case
def batch_binary_xml_preserve_geometry_attributes_and_source_files():
    folder = OUT / 'binary and xml'
    xml = fixture(folder, 'body ü.v2')
    binary_xml = fixture(folder, 'wheel.v1')
    util.xml_convert(str(binary_xml))
    binary = folder / 'wheel.v1.mesh'
    assert binary.is_file()
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
    assert batch(folder, [xml.name, binary.name]) == {'FINISHED'}, Report.errors
    assert not Report.errors and not Report.warnings
    assert [r['collection'] for r in Report.import_results] == ['body ü.v2', 'wheel.v1']
    objects = list(bpy.context.scene.objects)
    assert len(objects) == 2 and set(bpy.context.selected_objects) == set(objects)
    assert Report.vertices == Report.orig_vertices == 6 and Report.faces == Report.triangles == 2
    for obj in objects:
        assert len(obj.data.vertices) == 3 and len(obj.data.polygons) == 1
        assert len(obj.data.uv_layers) == 2 and obj.data.has_custom_normals
        assert tuple(obj.data.vertices[2].co) == (0, 0, 3)
        assert tuple(obj.data.uv_layers[0].data[1].uv) == (1, 1)
        assert all(abs(n.vector.y + 1) < 1e-5 for n in obj.data.corner_normals)
        assert len(obj.users_collection) == 1 and obj.users_collection[0].name == obj.name
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
    assert 'Files: 2 imported, 0 failed' in Report.report()


@case
def batch_existing_and_duplicate_names_get_independent_collections():
    folder = OUT / 'duplicates'
    first, second = fixture(folder / 'a', 'part'), fixture(folder / 'b', 'part')
    existing = bpy.data.collections.new('part')
    bpy.context.scene.collection.children.link(existing)
    keep = bpy.data.objects.new('Keep', None)
    existing.objects.link(keep)
    names = [str(first.relative_to(folder)), str(second.relative_to(folder)), str(first.relative_to(folder))]
    assert batch(folder, names) == {'FINISHED'}
    assert len(Report.import_results) == 2
    assert [r['collection'] for r in Report.import_results] == ['part.001', 'part.002']
    assert list(existing.objects) == [keep] and list(keep.users_collection) == [existing]
    assert batch(folder, names) == {'FINISHED'}
    assert [r['collection'] for r in Report.import_results] == ['part.003', 'part.004']
    assert len(bpy.context.scene.objects) == 5


@case
def batch_scenes_keep_hierarchy_cameras_lights_and_transforms():
    folder = OUT / 'scene'
    mesh = fixture(folder, 'part')
    scene = write(folder / 'track.v2.scene', '''<scene><nodes><node name="Root">
<position x="2" y="3" z="4"/><node name="Child"><position x="1" y="0" z="0"/>
<entity name="TrackPart" meshFile="part.mesh.xml"/><light name="TrackLight" type="point"/>
<camera name="TrackCamera"/></node></node></nodes></scene>''')
    assert batch(folder, [scene.name, mesh.name]) == {'FINISHED'}, Report.errors
    track = bpy.data.collections['track.v2']
    standalone = bpy.data.collections['part']
    assert len(track.children) == 1 and len(track.objects) == 0
    items = {obj.name: obj for obj in track.all_objects}
    assert len(items) == 5 and len(standalone.all_objects) == 1
    assert items['Child'].parent == items['Root']
    assert items['TrackPart'].parent == items['Child']
    assert items['TrackLight'].parent == items['Child'] and items['TrackCamera'].parent == items['Child']
    assert tuple(items['TrackPart'].matrix_world.translation) == (3, -4, 3)
    assert len(Report.lights) == len(Report.cameras) == 1 and Report.triangles == 2
    assert set(bpy.context.selected_objects) == set(bpy.context.scene.objects)


@case
def batch_one_failure_rolls_back_only_that_file_and_continues():
    folder = OUT / 'partial'
    files = [fixture(folder, name) for name in ('first', 'broken', 'last')]
    world = bpy.context.scene.world
    before = world.color[:], bpy.context.scene.render.fps
    original = ogre_import.load_mesh
    def failing(path):
        result = original(path)
        if Path(path).stem.startswith('broken'):
            leak = bpy.data.collections.new('MustRollBack')
            bpy.context.scene.collection.children.link(leak)
            world.color = (0.2, 0.3, 0.4)
            bpy.context.scene.render.fps = 101
            raise ValueError('deliberate failure after mesh creation')
        return result
    ogre_import.load_mesh = failing
    try:
        assert batch(folder, [p.name for p in files]) == {'FINISHED'}
    finally:
        ogre_import.load_mesh = original
    assert [r['imported'] for r in Report.import_results] == [True, False, True]
    assert Report.import_results[1]['collection'] is None
    assert {o.name for o in bpy.context.scene.objects} == {'first', 'last'}
    assert set(bpy.data.collections.keys()) == {'first', 'last'}
    assert (world.color[:], bpy.context.scene.render.fps) == before
    assert Report.vertices == 6 and Report.faces == 2 and len(Report.meshes) == 2
    assert len(Report.errors) == 1 and 'broken.mesh.xml:' in Report.errors[0]
    assert len(bpy.context.selected_objects) == 2


@case
def batch_all_failed_preserves_existing_data_environment_and_selection():
    folder = OUT / 'all failed'
    bad = write(folder / 'bad.scene', '''<scene><environment><colourBackground r="1" g="0" b="0"/></environment>
<nodes><node name="Discard"><entity meshFile="not-present.mesh"/></node></nodes></scene>''')
    invalid = write(folder / 'invalid.xml', '<mesh><sharedgeometry>')
    keep = bpy.data.objects.new('Keep', None)
    bpy.context.scene.collection.objects.link(keep)
    keep.select_set(True)
    bpy.context.view_layer.objects.active = keep
    kinds = ('objects', 'collections', 'meshes', 'materials', 'cameras', 'lights', 'images', 'worlds')
    before = {kind: set(getattr(bpy.data, kind)) for kind in kinds}
    color = bpy.context.scene.world.color[:]
    assert batch(folder, [bad.name, invalid.name]) == {'CANCELLED'}
    assert all(set(getattr(bpy.data, kind)) == ids for kind, ids in before.items())
    assert bpy.context.scene.world.color[:] == color
    assert bpy.context.active_object == keep and bpy.context.selected_objects == [keep]
    assert len(Report.import_results) == 2 and not any(r['imported'] for r in Report.import_results)
    assert any(error.startswith('bad.scene:') for error in Report.errors)
    assert any(error.startswith('invalid.xml:') for error in Report.errors)
    assert Report.vertices == 0 and Report.meshes == []


@case
def batch_reuses_original_selected_skeleton_for_every_file():
    folder = OUT / 'selected rig'
    files = [fixture(folder, name, skin=True) for name in ('first', 'second')]
    armature = bpy.data.armatures.new('ExistingRig')
    rig = bpy.data.objects.new('ExistingRig', armature)
    bpy.context.scene.collection.objects.link(rig)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    bone = armature.edit_bones.new('RootBone')
    bone.head, bone.tail = (0, 0, 0), (0, 1, 0)
    bone['OGREID'] = 0
    bpy.ops.object.mode_set(mode='OBJECT')
    before_armatures = set(bpy.data.armatures)
    assert batch(folder, [p.name for p in files], IM_USE_SELECTED_SKELETON=True) == {'FINISHED'}, Report.errors
    assert set(bpy.data.armatures) == before_armatures
    for outcome in Report.import_results:
        objects = list(bpy.data.collections[outcome['collection']].all_objects)
        assert len(objects) == 1 and objects[0].type == 'MESH'
        obj = objects[0]
        assert obj.modifiers['OgreSkeleton'].object == rig
        assert obj.vertex_groups['RootBone'].weight(0) == 1
    assert list(rig.users_collection) == [bpy.context.scene.collection]
    assert rig not in bpy.context.selected_objects


@case
def batch_collection_option_can_keep_previous_root_linking():
    folder = OUT / 'no grouping'
    files = [fixture(folder, name) for name in ('one', 'two')]
    assert batch(folder, [p.name for p in files], IM_IMPORT_INTO_COLLECTION=False) == {'FINISHED'}
    assert len(bpy.data.collections) == 0
    assert all(list(obj.users_collection) == [bpy.context.scene.collection] for obj in bpy.context.scene.objects)
    assert all(r['collection'] is None for r in Report.import_results)
    assert bpy.ops.ogre.import_mesh(filepath=str(files[0]), IM_IMPORT_INTO_COLLECTION=False,
        IM_USE_SELECTED_SKELETON=False, IM_Vx_ENABLE_LOGGING=False) == {'FINISHED'}
    assert len(bpy.context.scene.objects) == 3 and len(bpy.data.collections) == 0


@case
def batch_multi_file_drop_and_quoted_replay_script():
    folder = OUT / "drop ü and quotes"
    files = [fixture(folder, name) for name in ("driver's body.v2", 'wheel ü')]
    settings = {'IM_IMPORT_INTO_COLLECTION': True, 'IM_USE_SELECTED_SKELETON': False, 'IM_Vx_ENABLE_LOGGING': False}
    assert bpy.ops.ogre.import_mesh('INVOKE_DEFAULT', directory=str(folder),
        files=[{'name': p.name} for p in files], **settings) == {'FINISHED'}
    assert len(Report.import_results) == 2 and all(r['imported'] for r in Report.import_results)
    script = import_script([str(p) for p in files], settings)
    clear()
    exec(compile(script, '<batch replay>', 'exec'), {})
    assert len(Report.import_results) == 2 and all(r['imported'] for r in Report.import_results)
    assert set(bpy.data.collections.keys()) == {"driver's body.v2", 'wheel ü'}


addon_utils.disable('io_ogre', default_set=True)
record = {'blender': bpy.app.version_string, 'module_root': str(MODULE_ROOT), 'tests': RESULTS}
(ROOT / '.build/outputs/batch_import_results.json').write_text(json.dumps(record, indent=2))
for item in RESULTS:
    print('PASS' if item['passed'] else 'FAIL', item['test'])
assert all(item['passed'] for item in RESULTS), 'Batch import regressions failed'
print('BATCH_IMPORT_PASS', len(RESULTS))
