"""Conservative classic OGRE material translation (LGPL 2.1 or later)."""
import math
import bpy
from ..report import Report


def create_material(name, info):
    # Never overwrite a pre-existing material just because names match.
    material = bpy.data.materials.new(name or 'OgreMaterial')
    material.use_nodes = True
    nodes = material.node_tree.nodes
    shader = next(node for node in nodes if node.type == 'BSDF_PRINCIPLED')
    rgba = list(info.get('diffuse', (0.8, 0.8, 0.8, 1)))
    if len(rgba) == 3:
        rgba.append(1)
    material.diffuse_color = rgba[:4]
    shader.inputs['Base Color'].default_value = rgba[:4]
    shader.inputs['Alpha'].default_value = rgba[3]
    if info.get('pbr') and len(info.get('specular', ())) >= 2:
        shader.inputs['Roughness'].default_value = float(info['specular'][0])
        shader.inputs['Metallic'].default_value = float(info['specular'][1])
    elif len(info.get('specular', ())) == 5:
        shininess = max(0, float(info['specular'][4]))
        shader.inputs['Roughness'].default_value = math.sqrt(2/(shininess+2))
    if 'emissive' in info:
        shader.inputs['Emission Color'].default_value = (*info['emissive'][:3], 1)
        shader.inputs['Emission Strength'].default_value = 1
    transparent = rgba[3] < 1 or info.get('scene_blend') in ('alpha_blend', 'src_alpha')
    material.surface_render_method = 'BLENDED' if transparent else 'DITHERED'
    material.use_backface_culling = info.get('cull_hardware') not in ('none', None)
    texture_path = info.get('texture')
    if texture_path:
        texture = nodes.new('ShaderNodeTexImage')
        texture.location = (-600, 0)
        texture.image = bpy.data.images.load(texture_path, check_existing=True)
        material.node_tree.links.new(texture.outputs['Color'], shader.inputs['Base Color'])
        if transparent:
            material.node_tree.links.new(texture.outputs['Alpha'], shader.inputs['Alpha'])
        Report.textures.append(texture.image.name)
    return material
