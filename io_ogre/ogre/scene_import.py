"""DotScene hierarchy import for blender2ogre (GNU LGPL 2.1 or later).

Adapted from ogre_import.load_scene; upstream authors and licensing are retained
in LICENSE.txt and UPSTREAM_README.md.
"""
from pathlib import Path
import math
import xml.etree.ElementTree as ET
import bpy
from mathutils import Quaternion, Vector
from .. import animation as anim_api, config
from ..report import Report


def load_scene(filepath):
    from .ogre_import import load_mesh

    root = ET.parse(filepath).getroot()
    if root.tag != 'scene':
        raise ValueError('The selected XML document is not an OGRE scene')
    folder = Path(filepath).parent
    collection = bpy.data.collections.new('OgreImport')
    bpy.context.scene.collection.children.link(collection)

    def number(element, name, default):
        return float(element.get(name, default)) if element is not None else float(default)

    def color(element, default=(1, 1, 1)):
        return tuple(number(element, axis, value) for axis, value in zip(('r', 'g', 'b'), default))

    def move_to_collection(obj):
        for previous in list(obj.users_collection):
            previous.objects.unlink(obj)
        collection.objects.link(obj)

    def read_animations(obj, node):
        if not config.get('IMPORT_ANIMATIONS'):
            return
        fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
        rest_pos, rest_rot, rest_scale = obj.location.copy(), obj.rotation_quaternion.copy(), obj.scale.copy()
        for clip in node.findall('animations/animation'):
            frames = clip.findall('keyframe')
            if not frames:
                continue
            action = bpy.data.actions.new(clip.get('name','OgreNodeAnimation'))
            curves = {}
            for frame in frames:
                pos, rot, scl = (frame.find(tag) for tag in ('position','rotation','scale'))
                location = rest_pos + Vector((number(pos,'x',0), -number(pos,'z',0), number(pos,'y',0)))
                delta = Quaternion((number(rot,'qw',1), number(rot,'qx',0), -number(rot,'qz',0), number(rot,'qy',0)))
                rotation = rest_rot @ delta
                scaling = (rest_scale.x*number(scl,'x',1), rest_scale.y*number(scl,'z',1), rest_scale.z*number(scl,'y',1))
                time = 1 + number(frame,'time',0) * fps
                for path, values in [('location',location),('rotation_quaternion',rotation),('scale',scaling)]:
                    for index, value in enumerate(values):
                        key = path, index
                        if key not in curves:
                            curves[key] = anim_api.new_fcurve(action,obj,path,index)
                        curves[key].keyframe_points.insert(time,value).interpolation = 'LINEAR'
            track = obj.animation_data_create().nla_tracks.new()
            track.name = action.name
            track.mute = True
            strip = track.strips.new(action.name,1,action)
            strip.action_slot = anim_api.action_slot(action,obj)

    environment = root.find('environment')
    if environment is not None:
        background = environment.find('colourBackground')
        if background is not None:
            if bpy.context.scene.world is None:
                bpy.context.scene.world = bpy.data.worlds.new('OgreWorld')
            bpy.context.scene.world.color = color(background, (0, 0, 0))
            world = bpy.context.scene.world
            if world.use_nodes:
                for shader in world.node_tree.nodes:
                    if shader.type == 'BACKGROUND':
                        shader.inputs['Color'].default_value = (*color(background, (0,0,0)), 1)
        fog = environment.find('fog')
        if fog is not None and bpy.context.scene.world:
            mist = bpy.context.scene.world.mist_settings
            mist.use_mist = True
            mist.start = number(fog, 'linearStart', 0)
            mist.depth = max(0.001, number(fog, 'linearEnd', 1000) - mist.start)
            mist.intensity = number(fog, 'expDensity', 0)
            mist.falloff = {'linear':'LINEAR', 'exp':'QUADRATIC', 'exp2':'INVERSE_QUADRATIC'}.get(fog.get('mode'), 'LINEAR')

    def read_node(node, parent=None):
        obj = bpy.data.objects.new(node.get('name', 'OgreNode'), None)
        collection.objects.link(obj)
        obj.parent = parent
        pos, rot, scale = (node.find(tag) for tag in ('position', 'rotation', 'scale'))
        obj.location = (number(pos,'x',0), -number(pos,'z',0), number(pos,'y',0))
        obj.rotation_mode = 'QUATERNION'
        if rot is not None and rot.get('angle') is not None:
            axis = (number(rot,'axisX',0), -number(rot,'axisZ',0), number(rot,'axisY',1))
            obj.rotation_quaternion = Quaternion(axis, number(rot,'angle',0))
        else:
            obj.rotation_quaternion = (number(rot,'qw',1), number(rot,'qx',0), -number(rot,'qz',0), number(rot,'qy',0))
        obj.scale = (number(scale,'x',1), number(scale,'z',1), number(scale,'y',1))

        for entity in node.findall('entity'):
            mesh_name = entity.get('meshFile')
            if not mesh_name:
                continue
            before = set(bpy.context.scene.objects)
            # Reusing an active armature is useful for standalone imports; each
            # scene entity must instead resolve its own linked skeleton.
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = None
            if load_mesh(str(folder/mesh_name)) != {'FINISHED'}:
                raise ValueError('Could not load scene mesh: ' + mesh_name)
            created = set(bpy.context.scene.objects) - before
            for imported in created:
                move_to_collection(imported)
                if imported.parent not in created:
                    imported.parent = obj
            active = bpy.context.active_object
            if active in created:
                active.name = entity.get('name', active.name)

        for light in node.findall('light'):
            kind = light.get('type', 'point')
            data = bpy.data.lights.new(light.get('name', 'OgreLight'),
                {'point':'POINT','directional':'SUN','spot':'SPOT','rect':'AREA'}.get(kind,'POINT'))
            data.color = color(light.find('colourDiffuse'))
            # Match blender2ogre's existing energy / 10 export convention.
            data.energy = number(light,'powerScale',1) * 10
            if kind == 'rect':
                data.shape = 'RECTANGLE'
                size = light.find('lightSourceSize')
                data.size = number(size,'width',1)
                data.size_y = number(size,'height',1)
            light_range = light.find('lightRange')
            if kind == 'spot' and light_range is not None:
                data.spot_size = number(light_range,'outer',math.pi/4)
                data.spot_blend = max(0,min(1,1-number(light_range,'inner',0)/max(data.spot_size,1e-8)))
            item = bpy.data.objects.new(data.name, data)
            collection.objects.link(item)
            item.parent = obj
            item.rotation_mode = 'QUATERNION'
            item.rotation_quaternion = Quaternion((1, 0, 0), math.pi/2)
            Report.lights.append(item.name)

        for camera in node.findall('camera'):
            data = bpy.data.cameras.new(camera.get('name','OgreCamera'))
            data.type = 'ORTHO' if camera.get('projectionType') == 'orthographic' else 'PERSP'
            render = bpy.context.scene.render
            aspect = number(camera, 'aspectRatio',
                render.resolution_x * render.pixel_aspect_x / max(1, render.resolution_y * render.pixel_aspect_y))
            fovy = number(camera,'fov',math.pi/4)
            data.sensor_fit = 'HORIZONTAL' if aspect >= 1 else 'VERTICAL'
            data.angle = 2*math.atan(math.tan(fovy/2)*aspect) if aspect >= 1 else fovy
            data.ortho_scale = number(camera,'orthoScale',6)
            clip = camera.find('clipping')
            data.clip_start = number(clip,'near',0.1)
            data.clip_end = number(clip,'far',1000)
            item = bpy.data.objects.new(data.name,data)
            collection.objects.link(item)
            item.parent = obj
            item.rotation_mode = 'QUATERNION'
            item.rotation_quaternion = Quaternion((1, 0, 0), math.pi/2)
            Report.cameras.append(item.name)

        for child in node.findall('node'):
            read_node(child,obj)
        read_animations(obj,node)

    nodes = root.find('nodes')
    if nodes is not None:
        for node in nodes.findall('node'):
            read_node(node)
    return {'FINISHED'}
