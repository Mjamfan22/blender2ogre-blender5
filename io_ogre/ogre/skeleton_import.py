"""Exact OGRE bind transforms and local animation channels (LGPL 2.1+)."""
import math
import bpy
from mathutils import Matrix, Vector, Quaternion
from .. import animation as anim_api
from ..report import Report

CHANGE_BASIS = Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))


def prepare_rest(data):
    bones = data['skeleton']
    rest, pending = {}, set()
    def build(name):
        if name in rest:
            return rest[name]
        if name in pending:
            raise ValueError('Cyclic OGRE bone hierarchy')
        if name not in bones:
            raise ValueError('Missing parent bone: ' + name)
        pending.add(name)
        bone = bones[name]
        x,y,z,angle = bone.get('rotation',(0,1,0,0))
        rotation = Quaternion((x,y,z),angle) if abs(angle)>1e-12 else Quaternion()
        position = Vector(bone.get('position',(0,0,0)))
        if not all(math.isfinite(v) for v in (*position,*rotation)):
            raise ValueError('Non-finite skeleton transform')
        local = Matrix.Translation(position) @ rotation.to_matrix().to_4x4()
        parent = bone.get('parent')
        global_matrix = build(parent)['global'] @ local if parent else local
        pending.remove(name)
        rest[name] = {'local':local, 'global':global_matrix, 'rotation':rotation}
        return rest[name]
    for name in bones:
        build(name)
    data['_ogre_rest'] = rest


def create_skeleton(data,name):
    if '_ogre_rest' not in data:
        prepare_rest(data)
    bones,rest = data['skeleton'],data['_ogre_rest']
    armature = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name,armature)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True); rig.show_in_front = True
    data['rig'] = rig
    names = {}
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        for source,bone in bones.items():
            item = armature.edit_bones.new(source)
            names[source] = item.name
            lengths = [(rest[child]['global'].translation-rest[source]['global'].translation).length
                for child in bones if bones[child].get('parent')==source]
            item.length = max(0.01, min((value for value in lengths if value>1e-5),default=0.2))
            # A newly created EditBone has zero length. Setting its matrix
            # before giving it length loses its direction when length changes.
            item.matrix = CHANGE_BASIS @ rest[source]['global']
            item['OGREID'] = bone['id']
        for source,bone in bones.items():
            if bone.get('parent'):
                armature.edit_bones[names[source]].parent = armature.edit_bones[names[bone['parent']]]
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
    data['_bone_names'] = names
    data['boneIDs'] = {str(bone['id']):names[source] for source,bone in bones.items()}
    return rig


def create_animations(data):
    rig,rest = data['rig'],data['_ogre_rest']
    names = data['_bone_names']
    for name,tracks in data.get('animations',{}).items():
        action = bpy.data.actions.new(name)
        Report.armature_animations.append(name)
        for target,channels in tracks.items():
            if target not in names:
                Report.warnings.append('Animation refers to missing bone: '+target)
                continue
            bone = rig.pose.bones[names[target]]
            bone.rotation_mode = 'QUATERNION'
            previous = None
            for index,(path,keys) in enumerate(zip(('location','rotation_quaternion','scale'),channels)):
                for frame,value in keys:
                    if index==0:
                        value = rest[target]['rotation'].inverted() @ Vector(value)
                    elif index==1:
                        value = Quaternion(value).normalized()
                        if previous and value.dot(previous)<0:
                            value.negate()
                        previous = value.copy()
                    if not math.isfinite(frame) or not all(math.isfinite(v) for v in value):
                        raise ValueError('Non-finite skeleton animation key')
                    for channel,component in enumerate(value):
                        curve = anim_api.new_fcurve(action,rig,bone.path_from_id(path),channel,bone.name)
                        curve.keyframe_points.insert(frame,component).interpolation='LINEAR'
        track = rig.animation_data_create().nla_tracks.new()
        track.name = name; track.mute = True
        strip = track.strips.new(name,0,action)
        strip.action_slot = anim_api.action_slot(action,rig)
