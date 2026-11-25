"""ElementTree mesh reading with a small legacy DOM interface (LGPL 2.1+)."""
import xml.etree.ElementTree as ET


class Attribute:
    __slots__ = ('value',)
    def __init__(self, value): self.value = value


class Node:
    __slots__ = ('element',)
    nodeType = 1
    def __init__(self, element): self.element = element
    @property
    def localName(self): return self.element.tag
    @property
    def tagName(self): return self.element.tag
    @property
    def childNodes(self): return [Node(child) for child in self.element]
    def getAttribute(self, name): return self.element.get(name, '')
    def hasAttribute(self, name): return name in self.element.attrib
    def getAttributeNode(self, name):
        return Attribute(self.element.attrib[name]) if name in self.element.attrib else None
    def getElementsByTagName(self, tag):
        return [Node(item) for item in self.element.iter(tag) if item is not self.element]


class Document(Node):
    @property
    def documentElement(self): return Node(self.element)
    def getElementsByTagName(self, tag): return [Node(item) for item in self.element.iter(tag)]
    def unlink(self): self.element.clear()


def parse(file):
    return Document(ET.parse(file).getroot())


def assignments(element, names):
    result = {}
    if element is not None:
        for item in element.findall('vertexboneassignment'):
            index = item.get('boneindex')
            name = names.get(index, 'Group '+str(index))
            result.setdefault(name,[]).append([int(item.get('vertexindex')),float(item.get('weight'))])
    return result


def vertex_data(element, import_normals):
    result = {}
    count = int(element.get('vertexcount', '0'))
    for buffer in element.findall('vertexbuffer'):
        vertices = buffer.findall('vertex')
        if len(vertices) != count:
            raise ValueError('Vertex buffer count does not match its geometry')
        positions, normals, colors, uvs = [], [], [], []
        for vertex in vertices:
            position = vertex.find('position')
            if position is not None:
                positions.append((float(position.get('x')), -float(position.get('z')), float(position.get('y'))))
            normal = vertex.find('normal') if import_normals else None
            if normal is not None:
                normals.append((float(normal.get('x')), -float(normal.get('z')), float(normal.get('y'))))
            color = vertex.find('colour_diffuse')
            if color is not None:
                rgba = tuple(map(float,color.get('value').split()))
                colors.append((*rgba,1.0) if len(rgba)==3 else rgba)
            coordinates = vertex.findall('texcoord')
            if coordinates:
                uvs.append([(float(uv.get('u')),1.0-float(uv.get('v'))) for uv in coordinates])
        for key, values in (('positions',positions),('normals',normals),('vertexcolors',colors)):
            if values:
                if key in result:
                    raise ValueError('Duplicate vertex attribute buffer: '+key)
                result[key] = values
        if uvs:
            if len(uvs)!=count or any(len(uv)!=len(uvs[0]) for uv in uvs):
                raise ValueError('Inconsistent vertex texture coordinates')
            declared = int(buffer.get('texture_coords',str(len(uvs[0]))))
            if declared != len(uvs[0]):
                raise ValueError('Texture-coordinate count does not match its buffer')
            if 'uvsets' in result:
                result['uvsets'] = [old+new for old,new in zip(result['uvsets'],uvs)]
            else:
                result['uvsets'] = uvs
            result['texcoordsets'] = len(result['uvsets'][0])
    return result


def collect_mesh(data, document, name_function, import_normals):
    root = document.element
    names = data.get('boneIDs',{})
    shared = root.find('sharedgeometry')
    if shared is not None:
        data['sharedgeometry'] = vertex_data(shared,import_normals)
        if names:
            data['sharedgeometry']['boneassignments'] = assignments(root.find('boneassignments'),names)
    submeshes = []
    for source in root.findall('./submeshes/submesh'):
        if source.get('operationtype','triangle_list') != 'triangle_list':
            raise ValueError('Only triangle-list OGRE submeshes are supported')
        material = source.get('material','Material')
        item = {'material':name_function(material),'materialOrig':material}
        faces = source.find('faces')
        if faces is None:
            raise ValueError('OGRE submesh has no face buffer')
        item['faces'] = [(int(face.get('v1')),int(face.get('v2')),int(face.get('v3'))) for face in faces.findall('face')]
        if int(faces.get('count',str(len(item['faces'])))) != len(item['faces']):
            raise ValueError('Face count does not match its buffer')
        geometry = source.find('geometry')
        if geometry is not None:
            item['geometry'] = vertex_data(geometry,import_normals)
            if names:
                item['geometry']['boneassignments'] = assignments(source.find('boneassignments'),names)
        submeshes.append(item)
    data['submeshes'] = submeshes
    return data
