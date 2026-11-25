"""blender2ogre DotScene animation, LGPL 2.1 or later.

Retains the upstream EasyOgreExporter-compatible transform track convention.
https://github.com/OGRECave/EasyOgreExporter/blob/master/source/ExScene.cpp
"""
import bpy
import mathutils
from .. import animation as anim_api, util, config


def sample_frames(first, last, step=1):
    """Include fractional boundaries and the final sample at any frame step."""
    first, last = float(first), float(last)
    if last < first:
        raise ValueError('Animation end is before its start')
    frames = [first]
    while frames[-1] + max(1, step) < last - 1e-7:
        frames.append(frames[-1] + max(1, step))
    if last - first > 1e-7:
        frames.append(last)
    return frames


def set_frame(frame):
    import math
    whole = math.floor(frame)
    bpy.context.scene.frame_set(whole, subframe=frame-whole)


def dot_nodeanim(ob, doc, xmlnode):
    if ob.type == 'ARMATURE' or not ob.animation_data:
        return
    anim = ob.animation_data
    clips = [(strip.action, strip.action_frame_start, strip.action_frame_end, strip.action_slot, strip.name)
        for track in anim.nla_tracks for strip in track.strips if strip.action]
    if not clips and anim.action:
        first, last = anim.action.frame_range
        clips = [(anim.action, first, last, anim.action_slot, anim.action.name)]
    if not clips:
        return
    saved = anim.action, anim.action_slot, anim.use_nla
    frame = bpy.context.scene.frame_current + bpy.context.scene.frame_subframe
    try:
        anim.use_nla = False
        names = set()
        for action, first, last, slot, name in clips:
            unique = name
            suffix = 2
            while unique in names:
                unique = '%s_%s' % (name, suffix)
                suffix += 1
            names.add(unique)
            anim_api.assign_action(ob, action, slot)
            write_animation(ob, action, first, last, doc, xmlnode, unique)
    finally:
        anim.action = saved[0]
        if saved[0] and saved[1]:
            anim.action_slot = saved[1]
        anim.use_nla = saved[2]
        set_frame(frame)


def write_animation(ob, action, frame_start, frame_end, doc, xmlnode, name=None):
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    elements = {child.tagName: child for child in xmlnode.childNodes}
    position, rotation, scale = (elements[tag].attributes for tag in ('position','rotation','scale'))
    base_pos = mathutils.Vector(tuple(float(position[axis]) for axis in ('x','y','z')))
    base_rot = mathutils.Quaternion(tuple(float(rotation[axis]) for axis in ('qw','qx','qy','qz')))
    base_scale = mathutils.Vector(tuple(float(scale[axis]) for axis in ('x','y','z')))
    if any(abs(value) < 1e-12 for value in base_scale):
        raise ValueError('Node animation requires a nonzero rest scale: ' + ob.name)
    containers = [child for child in xmlnode.childNodes if child.tagName == 'animations']
    container = containers[0] if containers else doc.createElement('animations')
    if not containers:
        xmlnode.appendChild(container)
    clip = doc.createElement('animation')
    for key, value in {'name':name or action.name, 'enable':'false', 'loop':'false',
            'interpolationMode':'linear', 'rotationInterpolationMode':'linear',
            'length':'%.9f' % ((frame_end-frame_start)/fps)}.items():
        clip.setAttribute(key, value)
    container.appendChild(clip)
    frames = sample_frames(frame_start, frame_end, scene.frame_step)
    if config.get('NODE_KEYFRAMES'):
        frames = sorted({float(frame_start), float(frame_end)} | {
            frame for frame in get_keyframes(action, ob) if frame_start <= frame <= frame_end})
    for frame in frames:
        set_frame(frame)
        local = ob.matrix_local
        pos = util.swap(local.to_translation()) - base_pos
        rot = base_rot.rotation_difference(util.swap(local.to_quaternion()))
        current_scale = calc_scale(local)
        scl = [current_scale[i]/base_scale[i] for i in range(3)]
        keyframe = doc.createElement('keyframe')
        keyframe.setAttribute('time','%.9f' % ((frame-frame_start)/fps))
        clip.appendChild(keyframe)
        for tag, axes, values in [('position',('x','y','z'),pos),
                ('rotation',('qw','qx','qy','qz'),rot), ('scale',('x','y','z'),scl)]:
            item = doc.createElement(tag)
            for axis, value in zip(axes, values):
                item.setAttribute(axis,'%.9f' % value)
            keyframe.appendChild(item)


def calc_scale(matrix_local):
    return mathutils.Vector(tuple(abs(value) for value in util.swap(matrix_local.to_scale())))


def get_keyframes(action, owner=None):
    return sorted({key.co.x for curve in anim_api.fcurves(action, owner) for key in curve.keyframe_points})
