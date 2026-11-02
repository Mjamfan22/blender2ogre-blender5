"""Render a generated asset after real OGRE export/re-import; no external models."""
from pathlib import Path
import json
import math
import sys
import bpy
import addon_utils
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.build/outputs/review_demo'
OUT.mkdir(parents=True, exist_ok=True)
images = ROOT / 'docs/images'
images.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
addon_utils.enable('io_ogre', default_set=True, persistent=False)
from io_ogre import config
from io_ogre.report import Report
config.CONFIG.update(config._CONFIG_DEFAULTS_ALL)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
checker = bpy.data.images.new('Review_Checker', width=128, height=128)
colors = ((.025, .16, .2, 1), (.36, .85, .79, 1))
checker.pixels = [channel for y in range(128) for x in range(128) for channel in colors[((x // 16) + (y // 16)) % 2]]
checker.filepath_raw = str(OUT / 'review-checker.png')
checker.file_format = 'PNG'
checker.save()

def material(name, color, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = .28
    return mat

checkmat = material('Review_Checker', (.03, .55, .46))
node = checkmat.node_tree.nodes.new('ShaderNodeTexImage')
node.image = checker
checkmat.node_tree.links.new(node.outputs['Color'], checkmat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
copper = material('Review_Copper', (.85, .2, .055), .6)
bpy.ops.mesh.primitive_torus_add(major_segments=64, minor_segments=20, location=(0, 0, 1.6), major_radius=1.65, minor_radius=.49)
torus = bpy.context.object
torus.name = torus.data.name = 'Review_Orbit'
torus.rotation_euler = (math.radians(74), math.radians(12), math.radians(-12))
torus.data.materials.append(checkmat)
torus.data.materials.append(copper)
torus.data.uv_layers.new(name='UVDetail')
for polygon in torus.data.polygons:
    polygon.use_smooth = True
    polygon.material_index = 1 if polygon.center.x > .95 else 0
for source, target in zip(torus.data.uv_layers[0].data, torus.data.uv_layers[1].data): target.uv = source.uv * 2
for index, location in enumerate(((-2.05, -.05, .4), (2.05, .1, .4))):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=.38, location=location)
    obj = bpy.context.object
    obj.name = obj.data.name = 'Review_Satellite_' + str(index)
    obj.data.materials.append(copper if index == 0 else checkmat)
    for polygon in obj.data.polygons: polygon.use_smooth = True
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = torus
result = bpy.ops.ogre.export(filepath=str(OUT / 'review.scene'), EX_SELECTED_ONLY=True,
    EX_EXPORT_XML_DELETE=False, EX_FORCE_CAMERA=False, EX_FORCE_LIGHTS=False)
assert result == {'FINISHED'}, Report.errors
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
assert bpy.ops.ogre.import_mesh(filepath=str(OUT / 'review.scene'), IM_USE_SELECTED_SKELETON=False) == {'FINISHED'}, Report.errors
imported = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
orbit = next(obj for obj in imported if obj.data.name.startswith('Review_Orbit'))
assert len(orbit.data.uv_layers) == 2
assert len(orbit.data.materials) == 2
record = {'version': '0.9.8', 'source': 'generated synthetic geometry and checker image', 'native_binary_roundtrip': True,
    'imported_meshes': len(imported), 'orbit_triangles': len(orbit.data.polygons), 'orbit_uv_layers': len(orbit.data.uv_layers),
    'orbit_materials': len(orbit.data.materials), 'errors': list(Report.errors), 'warnings': list(Report.warnings)}
(OUT / 'provenance.json').write_text(json.dumps(record, indent=2))

# Studio scene belongs to the preview only; the three meshes above came through OGRE.
floor_mat = material('Studio_floor', (.018, .025, .04))
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.13))
floor = bpy.context.object
floor.name = 'Preview_Studio_Floor'
floor.data.materials.append(floor_mat)
bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=2.8, depth=.18, location=(0, 0, -.03))
base = bpy.context.object
base.name = 'Preview_Pedestal'
base.data.materials.append(material('Pedestal', (.035, .05, .075), .35))
bevel = base.modifiers.new('Soft edge', 'BEVEL')
bevel.width = .06
bevel.segments = 3
for name, position, power, size, color in (
    ('Key', (1, -5, 7), 1700, 5, (1, .87, .76)),
    ('Fill', (-5, -1, 4), 1100, 4, (.47, .75, 1)),
    ('Rim', (2, 4, 6), 2200, 3, (.55, 1, .88)),
):
    data = bpy.data.lights.new('Preview_' + name, 'AREA')
    data.energy = power
    data.shape = 'DISK'
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(data.name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (Vector((0, 0, 1)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add(location=(7.5, -11, 6.2))
camera = bpy.context.object
camera.name = 'Preview_Camera'
camera.rotation_euler = (Vector((0, 0, 1.15)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.lens = 56
scene = bpy.context.scene
scene.camera = camera
scene.world.color = (.05, .05, .05)
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(images / 'roundtrip-demo.png')
bpy.ops.render.render(write_still=True)
bpy.ops.object.select_all(action='DESELECT')
orbit.select_set(True)
bpy.context.view_layer.objects.active = orbit
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            space.region_3d.view_location = (0, 0, 1.1)
            space.region_3d.view_distance = 9
            space.region_3d.view_rotation = camera.rotation_euler.to_quaternion()
            space.shading.type = 'MATERIAL'
            space.overlay.show_floor = False
            space.overlay.show_stats = True
        elif area.type == 'PROPERTIES': area.spaces.active.context = 'MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'blender2ogre-v0.9.8-review.blend'))
print('REVIEW_DEMO_PASS', json.dumps(record))
