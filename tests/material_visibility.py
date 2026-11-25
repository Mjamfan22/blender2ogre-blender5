"""Import and rendered regressions for OGRE front/back material visibility."""
from pathlib import Path
import json
import sys
import traceback
import uuid

import addon_utils
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODULE_ROOT = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else ROOT
sys.path.insert(0, str(MODULE_ROOT))
addon_utils.enable('io_ogre', default_set=True, persistent=False)
from io_ogre import config
from io_ogre.report import Report

OUT = ROOT / '.build/outputs/material_visibility' / uuid.uuid4().hex[:8]
OUT.mkdir(parents=True)
RESULTS = []


def case(fn):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    config.CONFIG.update(config._CONFIG_DEFAULTS_ALL)
    Report.reset()
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


def mesh(folder, name, materials):
    subs = ''.join(f'<submesh material="{mat}" usesharedvertices="true"><faces count="1"><face v1="0" v2="1" v3="2"/></faces></submesh>' for mat in materials)
    path = write(folder / (name + '.mesh.xml'), '''<mesh><sharedgeometry vertexcount="3"><vertexbuffer positions="true">
<vertex><position x="0" y="0" z="0"/></vertex><vertex><position x="1" y="0" z="0"/></vertex>
<vertex><position x="0" y="1" z="0"/></vertex></vertexbuffer></sharedgeometry><submeshes>''' + subs + '</submeshes></mesh>')
    assert bpy.ops.ogre.import_mesh(filepath=str(path), IM_USE_SELECTED_SKELETON=False,
                                  IM_Vx_ENABLE_LOGGING=False) == {'FINISHED'}, Report.errors
    assert not Report.errors and not Report.warnings, (Report.errors, Report.warnings)
    return bpy.context.active_object


@case
def ogre_default_and_explicit_culling_preserve_existing_materials():
    folder = OUT / 'defaults'
    original = bpy.data.materials.new('VisibilityDefault')
    original.use_backface_culling = False
    write(folder / 'visibility.material', '''material VisibilityDefault
{
 technique { pass { diffuse 1 1 1 1 } }
}
material VisibilityClockwise
{
 technique { pass { cull_hardware clockwise } }
}
material VisibilityTwoSided
{
 technique { pass { cull_hardware none } }
}
''')
    obj = mesh(folder, 'visibility', ['VisibilityDefault', 'VisibilityClockwise', 'VisibilityTwoSided'])
    assert [mat.use_backface_culling for mat in obj.data.materials] == [True, True, False]
    assert obj.data.materials[0] != original and not original.use_backface_culling
    assert len(obj.data.polygons) == 3


@case
def inherited_two_sided_culling_and_child_override_are_retained():
    folder = OUT / 'inheritance'
    write(folder / 'inheritance.material', '''abstract material VisibilityBase
{
 technique { pass { cull_hardware none } }
}
material VisibilityInherited : VisibilityBase {}
material VisibilityOverride : VisibilityBase
{
 technique { pass { cull_hardware clockwise } }
}
material VisibilityLocal
{
 technique { pass { cull_hardware none } }
}
''')
    obj = mesh(folder, 'inheritance', ['VisibilityInherited', 'VisibilityOverride', 'VisibilityLocal'])
    assert [mat.use_backface_culling for mat in obj.data.materials] == [False, True, False]
    assert len(obj.data.vertices) == 3 and len(obj.data.polygons) == 3


@case
def rendered_banner_backing_cannot_cover_the_front_texture():
    folder = OUT / 'render'
    folder.mkdir(parents=True)
    for name, color in [('sponsor', (1, 0, 0, 1)), ('backing', (0.5, 0.5, 0.5, 1))]:
        image = bpy.data.images.new(name, width=2, height=2)
        image.pixels[:] = color * 4
        image.save(filepath=str(folder / (name + '.png')), save_copy=True)
    write(folder / 'banner.material', '''material SponsorFront
{
 technique { pass { texture_unit { texture sponsor.png } } }
}
material GrayBacking
{
 technique { pass { texture_unit { texture backing.png } } }
}
''')
    positions = [(-1, 0, 1), (1, 0, 1), (1, 0, -1), (-1, 0, -1),
                 (-1, 0.002, 1), (1, 0.002, 1), (1, 0.002, -1), (-1, 0.002, -1)]
    vertices = ''.join(f'<vertex><position x="{x}" y="{y}" z="{z}"/><normal x="0" y="{1 if i < 4 else -1}" z="0"/><texcoord u="{u}" v="{v}"/></vertex>'
                       for i, ((x, y, z), (u, v)) in enumerate(zip(positions, [(0, 0), (1, 0), (1, 1), (0, 1)] * 2)))
    path = write(folder / 'banner.mesh.xml', '<mesh><sharedgeometry vertexcount="8"><vertexbuffer positions="true" normals="true" texture_coords="1">' + vertices + '''</vertexbuffer></sharedgeometry><submeshes>
<submesh material="SponsorFront" usesharedvertices="true"><faces count="2"><face v1="0" v2="1" v3="2"/><face v1="0" v2="2" v3="3"/></faces></submesh>
<submesh material="GrayBacking" usesharedvertices="true"><faces count="2"><face v1="4" v2="6" v3="5"/><face v1="4" v2="7" v3="6"/></faces></submesh>
</submeshes></mesh>''')
    assert bpy.ops.ogre.import_mesh(filepath=str(path), IM_USE_SELECTED_SKELETON=False,
                                  IM_Vx_ENABLE_LOGGING=False) == {'FINISHED'}, Report.errors
    obj = bpy.context.active_object
    assert len(obj.data.polygons) == 4 and len(obj.data.uv_layers) == 1
    materials = list(obj.data.materials)
    assert len(materials) == 2 and all(mat.use_backface_culling for mat in materials)
    for mat in materials:
        shader = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        texture = shader.inputs['Base Color'].links[0].from_node
        assert texture.type == 'TEX_IMAGE'
        mat.node_tree.links.new(texture.outputs['Color'], shader.inputs['Emission Color'])
        shader.inputs['Emission Strength'].default_value = 1
    scene = bpy.context.scene
    assert 'EEVEE' in scene.render.engine, scene.render.engine
    camera = bpy.data.objects.new('VisibilityCamera', bpy.data.cameras.new('VisibilityCamera'))
    scene.collection.objects.link(camera)
    camera.location = (0, 0, 5)
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 2.5
    scene.camera = camera
    before = (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage,
              scene.render.filepath, scene.render.film_transparent)
    scene.render.resolution_x = scene.render.resolution_y = 32
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False

    def render(name):
        scene.render.filepath = str(folder / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(scene.render.filepath, check_existing=False)
        pixels = np.array(image.pixels[:]).reshape(32, 32, 4)
        return pixels[12:20, 12:20, :3].mean(axis=(0, 1))

    try:
        for mat in materials:
            mat.use_backface_culling = False
        broken = render('two_sided_backing')
        for mat in materials:
            mat.use_backface_culling = True
        corrected = render('source_culling')
        assert max(broken) - min(broken) < 0.08, broken
        assert corrected[0] > 0.3 and corrected[0] > corrected[1] * 2 and corrected[0] > corrected[2] * 2, corrected
        (ROOT / '.build/outputs/material_visibility_render.json').write_text(json.dumps(
            {'engine': scene.render.engine, 'two_sided_backing_rgb': broken.tolist(),
             'source_culling_rgb': corrected.tolist(), 'front_texture_visible': True}, indent=2))
    finally:
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage, scene.render.filepath, scene.render.film_transparent = before


addon_utils.disable('io_ogre', default_set=True)
(ROOT / '.build/outputs/material_visibility_results.json').write_text(json.dumps(
    {'blender': bpy.app.version_string, 'module_root': str(MODULE_ROOT), 'tests': RESULTS}, indent=2))
for result in RESULTS:
    print('PASS' if result['passed'] else 'FAIL', result['test'])
assert all(result['passed'] for result in RESULTS), 'Material visibility regressions failed'
print('MATERIAL_VISIBILITY_PASS', len(RESULTS))
