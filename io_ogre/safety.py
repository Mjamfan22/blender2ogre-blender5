"""Operation state guards for blender2ogre (LGPL 2.1 or later)."""
import bpy
import os
import shutil
import tempfile
from pathlib import Path


class ExportState:
    """Restore editing state, including when an exporter or converter fails."""
    def __enter__(self):
        scene = bpy.context.scene
        self.time = scene.frame_current, scene.frame_subframe
        self.selection = list(bpy.context.selected_objects)
        self.active = bpy.context.view_layer.objects.active
        self.objects = set(bpy.data.objects)
        self.transforms = [(obj, obj.matrix_basis.copy()) for obj in scene.objects]
        self.visibility = [(obj, obj.hide_viewport, obj.hide_render) for obj in scene.objects]
        self.meshes = set(bpy.data.meshes)
        self.modifiers = [(mod, mod.show_viewport, mod.show_render)
            for obj in scene.objects for mod in obj.modifiers]
        owners = list(scene.objects) + [mesh.shape_keys for mesh in bpy.data.meshes if mesh.shape_keys]
        self.animations = [(owner.animation_data, owner.animation_data.action,
            owner.animation_data.action_slot, owner.animation_data.use_nla)
            for owner in owners if owner.animation_data]
        self.poses = [(bone, bone.matrix_basis.copy()) for obj in scene.objects
            if obj.type == 'ARMATURE' for bone in obj.pose.bones]
        self.shapes = [(key, key.value) for mesh in bpy.data.meshes if mesh.shape_keys
            for key in mesh.shape_keys.key_blocks]
        self.shadows = [(mat, 'visible_shadow' in mat, mat.get('visible_shadow')) for mat in bpy.data.materials]
        return self

    def __exit__(self, *exc):
        for anim, action, slot, nla in self.animations:
            anim.action = action
            if action and slot:
                anim.action_slot = slot
            anim.use_nla = nla
        for mod, viewport, render in self.modifiers:
            mod.show_viewport, mod.show_render = viewport, render
        for bone, basis in self.poses:
            bone.matrix_basis = basis
        for key, value in self.shapes:
            key.value = value
        for mat, existed, value in self.shadows:
            if existed:
                mat['visible_shadow'] = value
            elif 'visible_shadow' in mat:
                del mat['visible_shadow']
        for obj in set(bpy.data.objects) - self.objects:
            obj.to_mesh_clear()
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in set(bpy.data.meshes) - self.meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        bpy.context.scene.frame_set(self.time[0], subframe=self.time[1])
        for obj, basis in self.transforms:
            obj.matrix_basis = basis
        for obj, viewport, render in self.visibility:
            obj.hide_viewport, obj.hide_render = viewport, render
        for bone, basis in self.poses:
            bone.matrix_basis = basis
        for key, value in self.shapes:
            key.value = value
        bpy.ops.object.select_all(action='DESELECT')
        for obj in self.selection:
            if obj.name in bpy.context.view_layer.objects:
                obj.select_set(True)
        bpy.context.view_layer.objects.active = self.active
        return False


class ImportTransaction:
    """Discard only IDs created by a cancelled import; retain existing assets."""
    kinds = ('objects', 'collections', 'meshes', 'armatures', 'materials',
             'actions', 'cameras', 'lights', 'textures', 'images', 'worlds')

    def __enter__(self):
        self.committed = False
        self.ids = {kind: set(getattr(bpy.data, kind)) for kind in self.kinds}
        self.scene = bpy.context.scene
        self.world = self.scene.world
        self.time = self.scene.frame_current, self.scene.frame_subframe
        self.fps = self.scene.render.fps, self.scene.render.fps_base
        self.active = bpy.context.view_layer.objects.active
        self.selection = list(bpy.context.selected_objects)
        if self.world:
            self.color = self.world.color[:]
            self.backgrounds = [(node, node.inputs['Color'].default_value[:])
                for node in self.world.node_tree.nodes if node.type == 'BACKGROUND'] if self.world.use_nodes else []
            mist = self.world.mist_settings
            self.mist = {name: getattr(mist, name) for name in
                ('use_mist', 'start', 'depth', 'intensity', 'falloff')}
        return self

    def commit(self):
        self.committed = True

    def __exit__(self, exc_type, *exc):
        if exc_type is None and self.committed:
            return False
        # A parser can fail in Edit Mode while constructing an armature.
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        self.scene.world = self.world
        for kind in self.kinds:
            collection = getattr(bpy.data, kind)
            for item in set(collection) - self.ids[kind]:
                collection.remove(item, do_unlink=True)
        if self.world:
            self.world.color = self.color
            for node, color in self.backgrounds:
                node.inputs['Color'].default_value = color
            for name, value in self.mist.items():
                setattr(self.world.mist_settings, name, value)
        self.scene.render.fps, self.scene.render.fps_base = self.fps
        self.scene.frame_set(self.time[0], subframe=self.time[1])
        bpy.ops.object.select_all(action='DESELECT')
        for obj in self.selection:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = self.active
        return False


class ExportFiles:
    """Publish a completed export as a unit; restore old files on commit failure."""
    def __init__(self, destination, overwrite_mesh=True):
        self.destination = Path(destination).resolve()
        self.overwrite_mesh = overwrite_mesh

    def __enter__(self):
        self.destination.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='.blender2ogre_', dir=self.destination)
        self.folder = Path(self.temp.name)
        return self

    def commit(self):
        pairs = []
        for source in sorted(self.folder.rglob('*')):
            if not source.is_file():
                continue
            relative = source.relative_to(self.folder)
            target = (self.destination / relative).resolve()
            if not target.is_relative_to(self.destination) or target.is_dir():
                raise ValueError('Invalid export target: ' + str(target))
            if not self.overwrite_mesh and target.exists() and target.name.lower().endswith(('.mesh','.mesh.xml','.skeleton','.skeleton.xml')):
                continue
            pairs.append((source,target,relative))
        backups = self.folder/'_previous_files'
        published = []
        try:
            for source,target,relative in pairs:
                backup = backups/relative
                existed = target.exists()
                if existed:
                    backup.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(target,backup)
                target.parent.mkdir(parents=True,exist_ok=True)
                os.replace(source,target)
                published.append((target,backup,existed))
        except Exception:
            for target,backup,existed in reversed(published):
                if existed:
                    os.replace(backup,target)
                else:
                    target.unlink()
            raise

    def __exit__(self,*exc):
        self.temp.cleanup()
        return False
