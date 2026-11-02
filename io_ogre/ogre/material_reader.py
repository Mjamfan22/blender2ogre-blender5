"""Read basic material properties after script inheritance (LGPL 2.1+)."""
from pathlib import Path


def read_materials(resolver, names=None):
    materials = {}
    names = list(resolver.definitions) if names is None else sorted(names)
    for name in names:
        if name in resolver.abstract:
            continue
        try:
            nodes = resolver.substitute(resolver.resolve(name), resolver.globals)
        except ValueError as error:
            resolver.warn('Material "%s": %s. Its material name will be preserved with a basic placeholder.' % (name,error))
            continue
        info = {}
        for header, _ in nodes:
            if header[:1] == ['receive_shadows'] and len(header)>1:
                info['receive_shadows'] = header[1] == 'on'
        techniques = [body for h,body in nodes if h[0]=='technique' and body is not None]
        passes = [body for h,body in techniques[0] if h[0]=='pass' and body is not None] if techniques else []
        if not passes:
            materials[name] = info
            continue
        first = passes[0]
        for header, body in first:
            key = header[0]
            args = [resolver.unquote(value) for value in header[1:]]
            if key in ('diffuse','ambient','specular','emissive','depth_bias'):
                if args == ['vertexcolour']:
                    info['vertexcolour'] = True
                else:
                    try:
                        values = [float(value) for value in args]
                        if values:
                            info[key] = values
                    except ValueError:
                        resolver.warn('Unsupported numeric property in material "%s": %s' % (name,' '.join(header)))
            elif key in ('scene_blend','cull_hardware','alpha_rejection') and args:
                info[key] = args if key == 'alpha_rejection' else args[0]
            elif key == 'rtshader_system' and body:
                info['pbr'] = any(h[:2] == ['lighting_stage','metal_roughness'] for h,_ in body)
        # First texture in the first pass is the base map. Specular/reflection
        # maps and later passes must never overwrite it as the old parser did.
        for header, body in first:
            if header[0] != 'texture_unit' or body is None:
                continue
            texture = next((h for h,_ in body if h[0]=='texture' and len(h)>1),None)
            if texture is None:
                continue
            filename = resolver.unquote(texture[1])
            source = resolver.sources['material',name].parent
            found = resolver.resources.find(filename,source)
            if found is None:
                found = resolver.resources.find(str(Path(filename).with_suffix('.dds')),source)
            if found:
                info['texture'] = str(found)
                info['imageNameOnly'] = filename
            else:
                resolver.warn('Base texture "%s" for material "%s" was not found in the asset resources' % (filename,name))
            break
        materials[name] = info
    return materials
