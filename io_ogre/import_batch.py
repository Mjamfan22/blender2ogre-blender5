"""Batch import orchestration for blender2ogre (LGPL 2.1 or later)."""
import logging
import os
from pathlib import Path

import bpy

from .report import Report
from .safety import ImportTransaction

logger = logging.getLogger('import')
REPORT_LISTS = ('materials', 'meshes', 'lights', 'cameras', 'armatures',
                'armature_animations', 'shape_keys', 'shape_animations',
                'textures', 'warnings', 'errors', 'messages', 'paths')
REPORT_COUNTS = ('vertices', 'orig_vertices', 'faces', 'triangles')


def selected_paths(filepath, directory, files):
    """Accept the file browser, multi-file drop and existing filepath scripts."""
    names = [item.name for item in files if item.name]
    if not names:
        return [os.path.abspath(bpy.path.abspath(filepath))] if filepath else []
    folder = bpy.path.abspath(directory) if directory else os.path.dirname(bpy.path.abspath(filepath))
    if not folder and any(not os.path.isabs(name) for name in names):
        raise ValueError('Choose a folder for the selected import files')
    result, seen = [], set()
    for name in names:
        path = os.path.abspath(os.path.join(folder, name))
        key = os.path.normcase(path)
        if key not in seen:
            result.append(path)
            seen.add(key)
    return result


def asset_name(filepath):
    name = Path(filepath).name
    return name[:-9] if name.lower().endswith('.mesh.xml') else os.path.splitext(name)[0]


def import_script(paths, settings):
    """Record a replayable operation, including all files and quoted names."""
    arguments = ['filepath=' + repr(paths[0])]
    if len(paths) > 1:
        folder = os.path.dirname(paths[0])
        arguments += ['directory=' + repr(folder),
                      'files=' + repr([{'name': os.path.relpath(path, folder)} for path in paths])]
    arguments += [name + '=' + repr(value) for name, value in settings.items()]
    return '# Blender Import Script:\n\nimport bpy\nbpy.ops.ogre.import_mesh(\n  ' + ',\n  '.join(arguments) + '\n)\n'


def group_import(transaction, destination):
    """Wrap newly created collections; move only newly created objects."""
    created_collections = set(bpy.data.collections) - transaction.ids['collections'] - {destination}
    parents = [bpy.context.scene.collection, *bpy.data.collections]
    for collection in created_collections:
        owners = [parent for parent in parents if collection.name in parent.children]
        if destination not in owners and not any(parent in created_collections for parent in owners):
            destination.children.link(collection)
        for parent in owners:
            if parent not in created_collections and parent != destination:
                parent.children.unlink(collection)
    objects = set(bpy.data.objects) - transaction.ids['objects']
    for obj in objects:
        owners = list(obj.users_collection)
        if not any(owner in created_collections or owner == destination for owner in owners):
            destination.objects.link(obj)
        for owner in owners:
            if owner not in created_collections and owner != destination:
                owner.objects.unlink(obj)
    return objects


def import_paths(paths, into_collections=True):
    """Commit successful files separately and report failures without data leaks."""
    from .ogre import ogre_import

    totals = {name: [] for name in REPORT_LISTS}
    totals.update({name: 0 for name in REPORT_COUNTS})
    outcomes, imported = [], set()
    initial_selection = list(bpy.context.selected_objects)
    initial_active = bpy.context.view_layer.objects.active
    last_active = None
    for filepath in paths:
        Report.reset()
        Report.importing = True
        # Each file sees the original selected rig, never a previous import's rig.
        bpy.ops.object.select_all(action='DESELECT')
        for obj in initial_selection:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = initial_active
        success = False
        destination = None
        try:
            with ImportTransaction() as transaction:
                if not filepath.lower().endswith(('.mesh', '.xml', '.scene')):
                    raise ValueError('Select an OGRE .mesh, .mesh.xml or .scene file')
                if not os.path.isfile(filepath):
                    raise ValueError('Import file does not exist: ' + filepath)
                if into_collections:
                    destination = bpy.data.collections.new(asset_name(filepath) or 'OgreAsset')
                    bpy.context.scene.collection.children.link(destination)
                loader = ogre_import.load_scene if filepath.lower().endswith('.scene') else ogre_import.load_mesh
                result = loader(filepath)
                success = result == {'FINISHED'} and not Report.errors
                if success:
                    created = (group_import(transaction, destination) if destination else
                               set(bpy.data.objects) - transaction.ids['objects'])
                    active = bpy.context.view_layer.objects.active
                    last_active = active if active in created else next(iter(sorted(created, key=lambda obj: obj.name)), last_active)
                    imported.update(created)
                    transaction.commit()
                elif not Report.errors:
                    Report.errors.append('Import was cancelled; check the source file and converter settings')
        except Exception as exc:
            success = False
            logger.exception('OGRE import failed: %s', filepath)
            Report.errors.append(str(exc))
        outcome = {'file': filepath, 'imported': success,
                   'collection': destination.name if success and destination else None}
        outcomes.append(outcome)
        for name in REPORT_LISTS:
            if success or name in ('warnings', 'errors', 'messages', 'paths'):
                values = getattr(Report, name)
                if len(paths) > 1 and name in ('warnings', 'errors', 'messages'):
                    values = [Path(filepath).name + ': ' + value for value in values]
                totals[name].extend(values)
        if success:
            for name in REPORT_COUNTS:
                totals[name] += getattr(Report, name)
    Report.reset()
    Report.importing = True
    Report.import_results = outcomes
    for name, value in totals.items():
        setattr(Report, name, value)
    if imported:
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action='DESELECT')
        for obj in imported:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = last_active
    return sum(item['imported'] for item in outcomes)
