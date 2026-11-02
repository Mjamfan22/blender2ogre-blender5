"""Validate parsed geometry before submitting arrays to Blender (LGPL 2.1+)."""
import math


def validate_mesh(data):
    if not data.get('submeshes'):
        raise ValueError('No OGRE submeshes were found')
    for submesh in data['submeshes']:
        geometry = submesh.get('geometry', data.get('sharedgeometry'))
        if not geometry or not geometry.get('positions'):
            raise ValueError('An OGRE submesh has no vertices')
        positions = geometry['positions']
        count = len(positions)
        if any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in positions):
            raise ValueError('Mesh positions must have three finite coordinates')
        for face in submesh.get('faces', ()):
            if len(face) != 3 or any(index < 0 or index >= count for index in face):
                raise ValueError('Face references a vertex outside its geometry')
        for name in ('normals','vertexcolors','uvsets'):
            if name in geometry and len(geometry[name]) != count:
                raise ValueError('Vertex attribute count mismatch: ' + name)
        for assignments in geometry.get('boneassignments', {}).values():
            for index, weight in assignments:
                if index < 0 or index >= count or not math.isfinite(weight) or weight < 0:
                    raise ValueError('Invalid vertex bone assignment')
