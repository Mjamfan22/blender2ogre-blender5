#!BPY

"""
Name: 'OGRE for Kenshi (*.MESH)'
Blender: 2.80
Group: 'Import/Export'
Tooltip: 'Import/Export Kenhi OGRE mesh files'

Author: Someone

Based on the Torchlight Impost/Export script by 'Dusho'

Thanks goes to 'goatman' for his port of Ogre export script from 2.49b to 2.5x,
and 'CCCenturion' for trying to refactor the code to be nicer (to be included)
"""

__author__ = "someone"
__version__ = "0.9.1 13-Sep-2019"

__bpydoc__ = """\
This script imports/exports Kenshi Ogre models into/from Blender.

Supported:<br>
    * import/export of basic meshes
    * import/export of skeleton
    * import/export of animations
    * import/export of vertex weights (ability to import characters and adjust rigs)
    * import/export of vertex colour (RGB)
    * import/export of vertex alpha (Uses second vertex colour layer called Alpha)
    * import/export of shape keys
    * Calculation of tangents and binormals for export

Known issues:<br>
    * imported materials will lose certain informations not applicable to Blender when exported

History:<br>
    * v0.9.1   (13-Sep-2019) - Fixed importing skeletons
    * v0.9.0   (07-May-2019) - Switched to Blender 2.80 API
    * v0.8.15  (17-Jul-2019) - Added option to import normals
    * v0.8.14  (14-May-2019) - Fixed blender deleting zero length bones
    * v0.8.13  (19-Mar-2019) - Exporting material files is optional
    * v0.8.12  (14-Mar-2019) - Fixed error exporting animation scale keyframes
    * v0.8.11  (26-Feb-2019) - Fixed tangents and binormals for mirrorred uvs
    * v0.8.10  (32-Jan-2019) - Fixed export when mesh has multiple uv sets
    * v0.8.9   (08-Mar-2018) - Added import option to match weight maps and link with a previously imported skeleton
    * v0.8.8   (26-Feb-2018) - Fixed export triangulation and custom normals
    * v0.8.7   (01-Feb-2018) - Scene frame rate adjusted on import, Fixed quatenion normalisation
    * v0.8.6   (31-Jan-2018) - Fixed crash exporting animations in blender 2.79
    * v0.8.5   (02-Jan-2018) - Optimisation: Use hashmap for duplicate vertex detection
    * v0.8.4   (20-Nov-2017) - Fixed animation quaternion interpolation
    * v0.8.3   (06-Nov-2017) - Warning when linked skeleton file not found
    * v0.8.2   (25-Sep-2017) - Fixed bone translations in animations
    * v0.8.1   (28-Jul-2017) - Added alpha component to vertex colour
    * v0.8.0   (30-Jun-2017) - Added animation and shape key support. Rewritten skeleton export
    * v0.7.2   (08-Dec-2016) - fixed divide by 0 error calculating tangents
    * v0.7.1   (07-Sep-2016) - bug fixes
    * v0.7.0   (02-Sep-2016) - Implemented changes needed for Kenshi: Persistant Ogre bone IDs, Export vertex colours. Generates tangents and binormals.
    * v0.6.2   (09-Mar-2013) - bug fixes (working with materials+textures), added 'Apply modifiers' and 'Copy textures'
    * v0.6.1   (27-Sep-2012) - updated to work with Blender 2.63a
    * v0.6     (01-Sep-2012) - added skeleton import + vertex weights import/export
    * v0.5     (06-Mar-2012) - added material import/export
    * v0.4.1   (29-Feb-2012) - flag for applying transformation, default=true
    * v0.4     (28-Feb-2012) - fixing export when no UV data are present
    * v0.3     (22-Feb-2012) - WIP - started cleaning + using OgreXMLConverter
    * v0.2     (19-Feb-2012) - WIP - working export of geometry and faces
    * v0.1     (18-Feb-2012) - initial 2.59 import code (from .xml)
    * v0.0     (12-Feb-2012) - file created
"""

"""
When importing: (x)-Blender, (x')-Ogre
vectors: x=x', y=-z', z=y'
UVtex: u=u', v = -v'+1

Inner data representation:
MESHDATA:
['sharedgeometry']: {}
    ['positions'] - vectors with [x,y,z]
    ['normals'] - vectors with [x,y,z]
    ['vertexcolors'] - vectors with [r,g,b,a]
    ['texcoordsets'] - integer (number of UV sets)
    ['uvsets'] - vectors with [u,v] * number or UV sets for vertex [[u,v]][[u,v]]...
    ['boneassignments']: {[boneName]} - for every bone name:
        [[vertexNumber], [weight]], [[vertexNumber], [weight]],  ..
['submeshes'][idx]
        [material] - string (material name)
        [materialOrig] - original material name - for searching in the shared materials file
        [faces] - vectors with faces [v1,v2,v3]
        [geometry] - identical to 'sharedgeometry' data content
['poses']
    ['pose'] - name, target, index (if target = submesh)
        ['poseoffset'] - vectors with index, nx, ny, nz, x, y, z
['materials']
    [(matID)]: {}
        ['texture'] - full path to texture file
        ['imageNameOnly'] - only image name from material file
['skeleton']: {[boneName]} for each bone
        ['name'] - bone name
        ['id'] - bone ID
        ['position'] - bone position [x,y,z]
        ['rotation'] - bone rotation [x,y,z,angle]
        ['parent'] - bone name of parent bone
        ['children'] - list with names if children ([child1, child2, ...])
['boneIDs']: {[bone ID]:[bone Name]} - dictionary with ID to name
['skeletonName'] - name of skeleton
[animations] - vector of animation tuples
  [animation] - tuple: ([tracks], name, length)
    [tracks] - vector of track tuples
      [track] - tuple: ([keyframes], type, target, index (>=0 if submesh, else: -1))
        [keyframes] - vector of keyframe tuples
          [keyframe] - tuple: ([poserefs], frame)
            [poserefs] - vector of poseref tuples
              poseref: tuple: (poseindex, influence)

Note: Bones store their OGREID as a custom variable so they are consistent when a mesh is exported
"""

# When bpy is already in local, we know this is not the initial import...
#if "bpy" in locals():
#    import importlib
#    print("RELOADING: material_parser.MaterialParser")
#    importlib.reload(material_parser)

import bpy
from xml.dom import minidom
from mathutils import Vector, Matrix, Quaternion
import math, os, subprocess, json
from .material_parser import MaterialParser
from .. import config, util
from ..util import *
from ..report import Report
from bpy_extras.io_utils import unpack_list

logger = logging.getLogger('ogre_import')

# Script internal options:
SHOW_IMPORT_DUMPS = False
SHOW_IMPORT_TRACE = False
MIN_BONE_LENGTH = 0.00001	# Prevent automatic removal of bones

# Makes sure name doesn't exceed Blenders naming limits
# Also keeps after name (as Torchlight uses names to identify types -boots, chest, ...- with names)
# TODO: This is not needed for Blender 2.62 and above
def GetValidBlenderName(name):

    newname = name.strip()
    
    maxChars = 20
    if bpy.app.version >= (2, 62, 0):
        maxChars = 63

    if(len(name) > maxChars):
        if(name.find("/") >= 0):
            if(name.find("Material") >= 0):
                # Replace 'Material' string with only 'Mt'
                newname = name.replace("Material", "Mt")
            # Check if it's still above 20
            if(len(newname) > maxChars):
                suffix = newname[newname.find("/"):]
                prefix = newname[0:(maxChars+1-len(suffix))]
                newname = prefix + suffix
        else:
            newname = name[0 : maxChars + 1]

    if(newname != name):
        logger.warning("Name truncated (%s -> %s)" % (name, newname))
        Report.warnings.append("Name truncated (%s -> %s)" % (name, newname))

    return newname

def xOpenFile(filename):
    logger.info("* Parsing file: %s ..." % filename)
    start = time.time()

    xml_file = open(filename, encoding='utf-8-sig')
    try:
        from .fast_xml import parse
        xml_doc = parse(xml_file)
        output = xml_doc
    except Exception:
        logger.error("File %s is not valid XML!" % filename)
        Report.errors.append("File %s is not valid XML!" % filename)
        output = 'None'
    xml_file.close()

    logger.info('- Done at %s seconds' % util.timer_diff_str(start))

    return output


def xCollectFaceData(facedata):
    faces = []
    for face in facedata.childNodes:
        if face.localName == 'face':
            v1 = int(face.getAttributeNode('v1').value)
            v2 = int(face.getAttributeNode('v2').value)
            v3 = int(face.getAttributeNode('v3').value)
            faces.append([v1, v2, v3])

    return faces


def xCollectVertexData(data):
    vertexdata = {}
    vertices = []
    normals = []
    vertexcolors = []

    for vb in data.childNodes:
        if vb.localName == 'vertexbuffer':
            if vb.hasAttribute('positions'):
                progressbar = util.ProgressBar("Vertices", len(vb.getElementsByTagName('vertex')))
                index = 0

                for vertex in vb.getElementsByTagName('vertex'):
                    progressbar.update(index)
                    index = index + 1

                    for vp in vertex.childNodes:
                        if vp.localName == 'position':
                            x = float(vp.getAttributeNode('x').value)
                            y = -float(vp.getAttributeNode('z').value)
                            z = float(vp.getAttributeNode('y').value)
                            vertices.append([x, y, z])
                vertexdata['positions'] = vertices

                sys.stdout.write("\n")

            if vb.hasAttribute('normals') and config.get('IMPORT_NORMALS') is True:
                for vertex in vb.getElementsByTagName('vertex'):
                    for vn in vertex.childNodes:
                        if vn.localName == 'normal':
                            x = float(vn.getAttributeNode('x').value)
                            y = -float(vn.getAttributeNode('z').value)
                            z = float(vn.getAttributeNode('y').value)
                            normals.append([x, y, z])
                vertexdata['normals'] = normals

            if vb.hasAttribute('colours_diffuse'):
                for vertex in vb.getElementsByTagName('vertex'):
                    for vcd in vertex.childNodes:
                        if vcd.localName == 'colour_diffuse':
                            rgba = vcd.getAttributeNode('value').value
                            r = float(rgba.split()[0])
                            g = float(rgba.split()[1])
                            b = float(rgba.split()[2])
                            a = float(rgba.split()[3])
                            vertexcolors.append([r, g, b, a])
                vertexdata['vertexcolors'] = vertexcolors

            if vb.hasAttribute('texture_coord_dimensions_0'):
                texcosets = int(vb.getAttributeNode('texture_coords').value)
                vertexdata['texcoordsets'] = texcosets
                uvcoordset = []
                for vertex in vb.getElementsByTagName('vertex'):
                    uvcoords = []
                    for vt in vertex.childNodes:
                        if vt.localName == 'texcoord':
                            u = float(vt.getAttributeNode('u').value)
                            v = -float(vt.getAttributeNode('v').value) + 1.0
                            uvcoords.append([u, v])

                    if len(uvcoords) > 0:
                        uvcoordset.append(uvcoords)
                vertexdata['uvsets'] = uvcoordset

    return vertexdata


def xCollectMeshData(meshData, xmldoc, meshname, dirname):
    logger.info("* Collecting mesh data...")
    from .fast_xml import Document, collect_mesh
    if isinstance(xmldoc, Document):
        return collect_mesh(meshData, xmldoc, GetValidBlenderName, config.get('IMPORT_NORMALS'))
    
    #global has_skeleton
    faceslist = []
    subMeshData = []
    allObjs = []
    isSharedGeometry = False
    sharedGeom = []
    hasSkeleton = 'boneIDs' in meshData

    # Collect shared geometry
    if(len(xmldoc.getElementsByTagName('sharedgeometry')) > 0):
        isSharedGeometry = True
        for subnodes in xmldoc.getElementsByTagName('sharedgeometry'):
            meshData['sharedgeometry'] = xCollectVertexData(subnodes)

        if hasSkeleton:
            for subnodes in xmldoc.getElementsByTagName('boneassignments'):
                meshData['sharedgeometry']['boneassignments'] = xCollectBoneAssignments(meshData, subnodes)

    # Collect submeshes data
    for submeshes in xmldoc.getElementsByTagName('submeshes'):
        for submesh in submeshes.childNodes:
            if submesh.localName == 'submesh':
                materialOrig = "Material"
                if submesh.getAttributeNode('material') is not None:
                    materialOrig = str(submesh.getAttributeNode('material').value)
                # To avoid Blender naming limit problems
                material = GetValidBlenderName(materialOrig)
                sm = {}
                sm['material'] = material
                sm['materialOrig'] = materialOrig
                for subnodes in submesh.childNodes:
                    if subnodes.localName == 'faces':
                        facescount = int(subnodes.getAttributeNode('count').value)
                        sm['faces'] = xCollectFaceData(subnodes)

                        if len(xCollectFaceData(subnodes)) != facescount:
                            logger.debug("FacesCount doesn't match!")
                            break

                    if (subnodes.localName == 'geometry'):
                        vertexcount = int(subnodes.getAttributeNode('vertexcount').value)
                        sm['geometry'] = xCollectVertexData(subnodes)

                    if hasSkeleton and subnodes.localName == 'boneassignments' and isSharedGeometry==False:
                        sm['geometry']['boneassignments'] = xCollectBoneAssignments(meshData, subnodes)

                subMeshData.append(sm)

    meshData['submeshes'] = subMeshData

    return meshData


def xCollectBoneAssignments(meshData, xmldoc):
    boneIDtoName = meshData['boneIDs']

    VertexGroups = {}
    for vg in xmldoc.childNodes:
        if vg.localName == 'vertexboneassignment':
            VG = str(vg.getAttributeNode('boneindex').value)
            if VG in boneIDtoName.keys():
                VGNew = boneIDtoName[VG]
            else:
                VGNew = 'Group ' + VG
            if VGNew not in VertexGroups.keys():
                VertexGroups[VGNew] = []

    for vg in xmldoc.childNodes:
        if vg.localName == 'vertexboneassignment':

            VG = str(vg.getAttributeNode('boneindex').value)
            if VG in boneIDtoName.keys():
                VGNew = boneIDtoName[VG]
            else:
                VGNew = VG
            verti = int(vg.getAttributeNode('vertexindex').value)
            weight = float(vg.getAttributeNode('weight').value)
            #logger.debug("bone=%s, vert=%s, weight=%s" % (VGNew, verti, weight))
            VertexGroups[VGNew].append([verti, weight])

    return VertexGroups


def xCollectPoseData(meshData, xmldoc):
    logger.info("* Collecting pose data...")

    poses = xmldoc.getElementsByTagName('poses')
    if(len(poses) == 0):
        return

    meshData['poses'] = []

    for pose in poses[0].getElementsByTagName('pose'):
        name = pose.getAttribute('name')
        target = pose.getAttribute('target')

        poseData = {}
        poseData['name'] = name
        if target == 'submesh':
            index = pose.getAttribute('index')
            poseData['submesh'] = int(index)
            logger.info("+ Pose: %s, index: %s, target: %s" % (name, index, target))
        else:
            logger.info("+ Pose: %s, target: %s" % (name, target))
        poseData['data'] = data = []
        meshData['poses'].append(poseData)
        for value in pose.getElementsByTagName('poseoffset'):
            index = int(value.getAttribute('index'))
            x = float(value.getAttribute('x'))
            y = float(value.getAttribute('y'))
            z = float(value.getAttribute('z'))
            data.append((index, x, -z, y))

    # Let's see if there are Pose animations as well
    # https://ogrecave.github.io/ogre/api/13/_animation.html#Pose-Animation
    animations_tag = xmldoc.getElementsByTagName('animations')
    if(len(animations_tag) == 0):
        return

    animations = []

    fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base

    for animation_tag in animations_tag[0].getElementsByTagName('animation'):
        name = animation_tag.getAttribute('name')
        length = animation_tag.getAttribute('length')

        logger.info("+ Animation: %s, length: %s" % (name, length))

        tracks = []

        for track_tag in animation_tag.getElementsByTagName('track'):
            target = track_tag.getAttribute('target')
            type = track_tag.getAttribute('type')

            # If the type of animations were not pose after all... bail
            if type != "pose":
                return

            if target == 'submesh':
                submesh_index = track_tag.getAttribute('index')
                logger.info("+ Track: %s, index: %s, target: %s" % (name, submesh_index, target))
            else:
                submesh_index = -1
                logger.info("+ Track: %s, target: %s" % (name, target))

            for keyframes_tag in track_tag.getElementsByTagName('keyframes'):

                keyframes = []

                for keyframe_tag in keyframes_tag.getElementsByTagName('keyframe'):

                    time = float(keyframe_tag.getAttribute('time'))
                    frame = time * fps + 1
                    #print("frame: %s, time: %s" % (frame, time))

                    if config.get('ROUND_FRAMES') is True:
                        frame = round(frame)

                    poserefs = []

                    for poseref_tag in keyframe_tag.getElementsByTagName('poseref'):
                        influence = poseref_tag.getAttribute('influence')
                        poseindex = poseref_tag.getAttribute('poseindex')

                        poseref = (poseindex, influence)
                        poserefs.append(poseref)

                    keyframe = (poserefs, frame)
                    keyframes.append(keyframe)

            track = (keyframes, type, target, submesh_index)
            tracks.append(track)

        animation = (tracks, name, length)
        animations.append(animation)

    meshData['pose_animations'] = animations


from .. import animation as anim_api


def bCreatePoseAnimations(ob, meshData, subMeshIndex):
    if 'pose_animations' in meshData and len(meshData['pose_animations']) > 0:
        logger.info("+ Creating pose animations...")

        # Create animation data for the shape animations
        shape_keys = ob.data.shape_keys

        if shape_keys.animation_data is None:
            shape_keys.animation_data_create()

        shape_key_names = []
        for pose in meshData['poses']:
            shape_key_names.append(pose['name'])

        for animation in meshData['pose_animations']:
            tracks = animation[0]
            name = animation[1]
            length = float(animation[2])

            logger.debug("- Animation: %s, length: %s" % (name, length))

            fcurves = {}

            actions = meshData.setdefault('_pose_actions', {})
            if name not in actions:
                actions[name] = bpy.data.actions.new(name)
                Report.shape_animations.append(name)
            action = actions[name]
            for shape_key_name in shape_key_names:
                data_path = 'key_blocks["' + bpy.utils.escape_identifier(shape_key_name) + '"].value'
                fcurves[shape_key_name] = anim_api.new_fcurve(action, shape_keys, data_path)
            slot = anim_api.action_slot(action, shape_keys)
            track = shape_keys.animation_data.nla_tracks.new()
            track.name = name
            track.mute = True
            strip = track.strips.new(name, 0, action)
            strip.action_slot = slot

            for track in tracks:
                keyframes = track[0]
                type = track[1]
                target = track[2]
                submesh_index = int(track[3])
                logger.debug("- Track -- type: %s, target: %s, submesh_index: %s" % (type, target, submesh_index))

                # If we are not dealing with shared geometry and this track does not apply to this submesh... skip
                if(submesh_index >= 0 and submesh_index != subMeshIndex):
                    logger.debug("Skipping submesh_index: %s" % submesh_index)
                    continue

                # Create fcurves
                for keyframe in keyframes:
                    poserefs = keyframe[0]
                    frame = keyframe[1]

                    # We have to account for the shape keys not referenced in the poserefs
                    referenced_shape_keys = []

                    for poseref in poserefs:
                        pose_index = int(poseref[0])
                        influence = float(poseref[1])
                        shape_key_name = meshData['poses'][pose_index]['name']
                        referenced_shape_keys.append(shape_key_name)

                        fcurve = fcurves[shape_key_name]
                        fcurve.keyframe_points.insert(frame, influence).interpolation = 'LINEAR'

                    # Set influence to 0 for shape keys not referenced in the poserefs
                    # Otherwise the animation will look bad
                    for shape_key_name in [item for item in shape_key_names if item not in referenced_shape_keys]:
                        fcurve = fcurves[shape_key_name]
                        fcurve.keyframe_points.insert(frame, 0).interpolation = 'LINEAR'


def xGetSkeletonLink(xmldoc, folder):
    skeletonFile = "None"
    if(len(xmldoc.getElementsByTagName("skeletonlink")) > 0):
        # Get the skeleton link of the mesh
        skeletonLink = xmldoc.getElementsByTagName("skeletonlink")[0]
        skeletonName = skeletonLink.getAttribute("name")
        skeletonFile = os.path.join(folder, skeletonName)
        # Check for existence of skeleton file
        if not os.path.isfile(skeletonFile) and os.path.isfile(skeletonFile + '.xml'):
            skeletonFile += '.xml'
        if not os.path.isfile(skeletonFile):
            logger.warning("Ogre skeleton missing: %s" % skeletonFile)
            Report.warnings.append("Cannot find linked skeleton file '%s'\nIt must be in the same directory as the mesh file." % skeletonName)
            skeletonFile = "None"

    return skeletonFile


#def xCollectBoneData(meshData, xDoc, name, folder):
def xCollectBoneData(meshData, xDoc):
    logger.info("* Collecting bone data...")
    
    OGRE_Bones = {}
    BoneIDToName = {}
    meshData['skeleton'] = OGRE_Bones
    meshData['boneIDs'] = BoneIDToName

    for bones in xDoc.getElementsByTagName('bones'):
        for bone in bones.childNodes:
            OGRE_Bone = {}
            if bone.localName == 'bone':
                boneName = str(bone.getAttributeNode('name').value)
                boneID = int(bone.getAttributeNode('id').value)
                OGRE_Bone['name'] = boneName
                OGRE_Bone['id'] = boneID
                BoneIDToName[str(boneID)] = boneName

                for b in bone.childNodes:
                    if b.localName == 'position':
                        x = float(b.getAttributeNode('x').value)
                        y = float(b.getAttributeNode('y').value)
                        z = float(b.getAttributeNode('z').value)
                        OGRE_Bone['position'] = [x, y, z]
                    if b.localName == 'rotation':
                        angle = float(b.getAttributeNode('angle').value)
                        axis = xGetChild(b, 'axis')
                        axisx = float(axis.getAttributeNode('x').value)
                        axisy = float(axis.getAttributeNode('y').value)
                        axisz = float(axis.getAttributeNode('z').value)
                        OGRE_Bone['rotation'] = [axisx, axisy, axisz, angle]

                OGRE_Bones[boneName] = OGRE_Bone

    for bonehierarchy in xDoc.getElementsByTagName('bonehierarchy'):
        for boneparent in bonehierarchy.childNodes:
            if boneparent.localName == 'boneparent':
                Bone = str(boneparent.getAttributeNode('bone').value)
                Parent = str(boneparent.getAttributeNode('parent').value)
                OGRE_Bones[Bone]['parent'] = Parent

    from .skeleton_import import prepare_rest
    prepare_rest(meshData)

    return OGRE_Bones


def calcBoneChildren(BonesData):
    for bone in BonesData.keys():
        childlist = []
        for key in BonesData.keys():
            if 'parent' in BonesData[key]:
                parent = BonesData[key]['parent']
                if parent == bone:
                    childlist.append(key)
        BonesData[bone]['children'] = childlist


def calcHelperBones(BonesData):
    count = 0
    helperBones = {}
    for bone in BonesData.keys():
        if ((len(BonesData[bone]['children']) == 0) or
                (len(BonesData[bone]['children']) > 1)):
            HelperBone = {}
            HelperBone['position'] = [0.2, 0.0, 0.0]
            HelperBone['parent'] = bone
            HelperBone['rotation'] = [1.0, 0.0, 0.0, 0.0]
            HelperBone['flag'] = 'helper'
            HelperBone['name'] = 'Helper' + str(count)
            HelperBone['children'] = []
            helperBones['Helper' + str(count)] = HelperBone
            count += 1
    for hBone in helperBones.keys():
        BonesData[hBone] = helperBones[hBone]


def calcZeroBones(BonesData):
    zeroBones = {}
    for bone in BonesData.keys():
        pos = BonesData[bone]['position']
        if (math.sqrt(pos[0]**2 + pos[1]**2 + pos[2]**2)) == 0:
            ZeroBone = {}
            ZeroBone['position'] = [0.2, 0.0, 0.0]
            ZeroBone['rotation'] = [1.0, 0.0, 0.0, 0.0]
            if 'parent' in BonesData[bone]:
                ZeroBone['parent'] = BonesData[bone]['parent']
            ZeroBone['flag'] = 'zerobone'
            ZeroBone['name'] = 'Zero' + bone
            ZeroBone['children'] = []
            zeroBones['Zero' + bone] = ZeroBone
            if 'parent' in BonesData[bone]:
                BonesData[BonesData[bone]['parent']]['children'].append('Zero' + bone)
    for hBone in zeroBones.keys():
        BonesData[hBone] = zeroBones[hBone]


def calcBoneHeadPositions(BonesData):
    for key in BonesData.keys():

        start = 0
        thisbone = key
        posh = BonesData[key]['position']
        #print("SetBonesASPositions: bone=%s, org. position=%s" % (key, posh))
        while start == 0:
            if 'parent' in BonesData[thisbone]:
                parentbone = BonesData[thisbone]['parent']
                prot = BonesData[parentbone]['rotation']
                ppos = BonesData[parentbone]['position']

                #protmat = RotationMatrix(math.degrees(prot[3]), 3, 'r', Vector(prot[0], prot[1], prot[2])).invert()
                protmat = Matrix.Rotation(math.degrees(prot[3]), 3, Vector([prot[0], prot[1], prot[2]])).inverted()
                #print ("SetBonesASPositions: bone=%s, protmat=%s" % (key, protmat))
                #print(protmat)
                #newposh = protmat * Vector([posh[0], posh[1], posh[2]])
                #newposh = protmat * Vector([posh[2], posh[1], posh[0]]) #02
                newposh = protmat.transposed() @ Vector([posh[0], posh[1], posh[2]]) #03
                #print("SetBonesASPositions: bone=%s, newposh=%s" % (key, newposh))
                positionh = VectorSum(ppos,newposh)

                posh = positionh

                thisbone = parentbone
            else:
                start = 1

        BonesData[key]['posHAS'] = posh
        #print("SetBonesASPositions: bone=%s, posHAS=%s" % (key, posh))


def calcBoneRotations(BonesDic):
    objDic = {}
    scn = bpy.context.scene
    #scn = Scene.GetCurrent()
    for bone in BonesDic.keys():
        #obj = Object.New('Empty',bone)
        obj = bpy.data.objects.new(bone, None)
        objDic[bone] = obj
        scn.collection.objects.link(obj)
    #print("all objects created")
    #print(bpy.data.objects)
    for bone in BonesDic.keys():
        if 'parent' in BonesDic[bone]:
            #Parent = Object.Get(BonesDic[bone]['parent'])
            #print(BonesDic[bone]['parent'])
            Parent = objDic.get(BonesDic[bone]['parent'])
            object = objDic.get(bone)
            object.parent = Parent
            #Parent.makeParent([object])
    #print("all parents linked")
    for bone in BonesDic.keys():
        obj = objDic.get(bone)
        rot = BonesDic[bone]['rotation']
        loc = BonesDic[bone]['position']
        #print ("CreateEmptys:bone=%s, rot=%s" % (bone, rot))
        #print ("CreateEmptys:bone=%s, loc=%s" % (bone, loc))
        euler = Matrix.Rotation(rot[3], 3, Vector([rot[0], -rot[2], rot[1]])).to_euler()
        obj.location = [loc[0], -loc[2], loc[1]]
        #print ("CreateEmptys:bone=%s, euler=%s" % (bone, euler))
        #print ("CreateEmptys:bone=%s, obj.rotation_euler=%s" % (bone,[math.radians(euler[0]),math.radians(euler[1]),math.radians(euler[2])]))
        #obj.rotation_euler = [math.radians(euler[0]),math.radians(euler[1]),math.radians(euler[2])]
        #print ("CreateEmptys:bone=%s, obj.rotation_euler=%s" % (bone,[euler[0],euler[1],euler[2]])) # 02
        obj.rotation_euler = [euler[0], euler[1], euler[2]] # 02
    # Redraw()
    bpy.context.view_layer.update()
    # print("all objects rotated")
    for bone in BonesDic.keys():
        obj = objDic.get(bone)
        # TODO: need to get rotation matrix out of objects rotation
        # loc, rot, scale = obj.matrix_local.decompose()
        loc, rot, scale = obj.matrix_world.decompose() #02
        rotmatAS = rot.to_matrix()
        # print(rotmatAS)
        #obj.rotation_quaternion.
        #rotmatAS = Matrix(.matrix_local..getMatrix().rotationPart()
        BonesDic[bone]['rotmatAS'] = rotmatAS
        #print ("CreateEmptys:bone=%s, rotmatAS=%s" % (bone, rotmatAS))
    # print("all matrices stored")

    #for bone in BonesDic.keys():
    #    obj = objDic.get(bone)
    #    scn.collection.objects.unlink(obj)
    #    del obj

    # TODO cyclic
    for bone in BonesDic.keys():
        obj = objDic.get(bone)
        #obj.select = True
        #bpy.ops.object.select_name(bone, False)
        #bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        scn.collection.objects.unlink(obj) # TODO: cyclic message in console
        #del obj
        #bpy.context.scene.objects.unlink(obj)
        bpy.data.objects.remove(obj)

    bpy.context.view_layer.update()
    #removedObj = {}
    #children=1
    #while children > 0:
    #    children = 0
    #    for bone in BonesDic.keys():
    #        if('children' in BonesDic[bone].keys() and bone not in removedObj):
    #            if len(BonesDic[bone]['children'])==0:
    #                obj = objDic.get(bone)
    #                scn.objects.unlink(obj)
    #                del obj
    #                removedObj[bone]=True
    #            else:
    #                children+=1

    #print("all objects removed")

def VectorSum(vec1, vec2):
    vecout = [0, 0, 0]
    vecout[0] = vec1[0] + vec2[0]
    vecout[1] = vec1[1] + vec2[1]
    vecout[2] = vec1[2] + vec2[2]

    return vecout

## =========================================================================================== ##
def quaternionFromAngleAxis(angle, x, y, z):
    r = angle * 0.5
    s = math.sin(r)
    c = math.cos(r)
    return (c, x*s, y*s, z*s)


def xGetChild(node, tag):
    for n in node.childNodes:
        if n.nodeType == 1 and n.tagName == tag:
            return n
    return None


def xAnalyseFPS(xDoc):
    fps = 0
    lastTime = 1e8
    samples = 0
    for container in xDoc.getElementsByTagName('animations'):
        for animation in container.childNodes:
            if animation.nodeType == 1 and animation.tagName == 'animation':
                tracks = xGetChild(animation, 'tracks')
                for track in tracks.childNodes:
                    if track.nodeType == 1:
                        for keyframe in xGetChild(track, 'keyframes').childNodes:
                            if keyframe.nodeType == 1:
                                time = float(keyframe.getAttribute('time'))
                                if time > lastTime:
                                    fps = max(fps, 1 / (time - lastTime))
                                lastTime = time
                                samples = samples + 1
                                if samples > 100:
                                    return round(fps, 2)    # stop here
    return round(fps, 2)


def xCollectAnimations(meshData, xDoc):
    logger.info("* Collecting animation data...")

    if 'animations' not in meshData:
        meshData['animations'] = {}
    for container in xDoc.getElementsByTagName('animations'):
        for animation in container.childNodes:
            if animation.nodeType == 1 and animation.tagName == 'animation':
                name = animation.getAttribute('name')

                # read action data
                action = {}
                tracks = xGetChild(animation, 'tracks')
                xReadAnimation(action, tracks.childNodes)
                meshData['animations'][name] = action


def xReadAnimation(action, tracks):
    fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
    for track in tracks:
        if track.nodeType != 1:
            continue
        target = track.getAttribute('bone')
        action[target] = trackData = [[] for i in range(3)]  # pos, rot, scl
        for keyframe in xGetChild(track, 'keyframes').childNodes:
            if keyframe.nodeType != 1:
                continue
            time = float(keyframe.getAttribute('time'))
            frame = time * fps
            if config.get('ROUND_FRAMES') is True:
                frame = round(frame)
            for key in keyframe.childNodes:
                if key.nodeType != 1:
                    continue
                if key.tagName == 'translate':
                    x = float(key.getAttribute('x'))
                    y = float(key.getAttribute('y'))
                    z = float(key.getAttribute('z'))
                    trackData[0].append([frame, (x, y, z)])
                elif key.tagName == 'rotate':
                    axis = xGetChild(key, 'axis')
                    angle = key.getAttribute('angle')
                    x = axis.getAttribute('x')
                    y = axis.getAttribute('y')
                    z = axis.getAttribute('z')
                    # skip if axis contains #INF or #IND
                    if '#' not in x and '#' not in y and '#' not in z:
                        quat = quaternionFromAngleAxis(float(angle), float(x), float(y), float(z))
                        trackData[1].append([frame, quat])
                elif key.tagName == 'scale':
                    x = float(key.getAttribute('x'))
                    y = float(key.getAttribute('y'))
                    z = float(key.getAttribute('z'))
                    trackData[2].append([frame, (x, y, z)])


def bCreateAnimations(meshData):
    if meshData.get('animations'):
        from .skeleton_import import create_animations
        create_animations(meshData)


def bCreateMesh(meshData, folder, name, filepath):
    if 'skeleton' in meshData:
        skeletonName = meshData['skeletonName']
        bCreateSkeleton(meshData, skeletonName)

    logger.info("+ Creating mesh: %s" % name)

    # From collected data create all sub meshes
    subObjs = bCreateSubMeshes(meshData, name)
    # Skin submeshes
    #bSkinMesh(subObjs)

    # Move to parent skeleton if there
    if 'armature' in meshData:
        arm = meshData['armature']
        for obj in subObjs:
            logger.debug('Move to %s' % arm.location)
            obj.location = arm.location
            obj.rotation_euler = arm.rotation_euler
            obj.rotation_axis_angle = arm.rotation_axis_angle
            obj.rotation_quaternion = arm.rotation_quaternion

    bpy.ops.object.select_all(action='DESELECT')

    # Temporarily select all imported objects
    for subOb in subObjs:
        subOb.select_set(True)

    # TODO: Try to merge everything into the armature object
    if not subObjs:
        raise ValueError('The mesh contains no importable submeshes')
    if config.get('MERGE_SUBMESHES') is True and len(subObjs) > 1:
        bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = name
        ob.data.name = name

    Report.meshes.append( name )

    # Dump import structure
    if SHOW_IMPORT_DUMPS:
        import_dump = filepath.replace(".xml", ".json")
        with open( import_dump, 'w' ) as f:
            json.dump(meshData, f, indent=4)


def bCreateSkeleton(meshData, name):
    from .skeleton_import import create_skeleton
    return create_skeleton(meshData, name)


def bMergeVertices(subMesh):
    # This sort of works, but leaves all uv seams as sharp.
    geometry = subMesh['geometry']
    vertices = geometry['positions']
    normals = geometry['normals']
    uvsets = geometry['uvsets'] if 'uvsets' in geometry else None
    lookup = {}
    map = [i for i in range(len(vertices))]
    for i in range(len(vertices)):
        vert = vertices[i]
        norm = normals[i]
        uv = tuple(uvsets[i][0]) if uvsets else None
        item = (tuple(vert), tuple(norm), uv)
        target = lookup.get(item)
        if target is None:
            lookup[item] = i
        else:
            map[i] = target
    # update faces
    faces = subMesh['faces']
    for face in faces:
        for i in range(len(face)):
            face[i] = map[face[i]]


def append_material(ob, meshData, subMeshData):
    """Reuse one material per source name throughout a single import."""
    name = subMeshData['material']
    key = subMeshData.get('materialOrig',name)
    cache = meshData.setdefault('_blender_materials',{})
    if key not in cache:
        if key in meshData['materials']:
            from .material_import import create_material
            cache[key] = create_material(name,meshData['materials'][key])
            if name not in Report.materials:
                Report.materials.append(name)
        else:
            logger.warning('Definition of material: "%s" not found!',name)
            Report.warnings.append('Definition of material: "%s" not found!' % name)
            cache[key] = bpy.data.materials.new(name=name)
    material = cache[key]
    index = ob.data.materials.find(material.name)
    if index < 0:
        index = len(ob.data.materials)
        ob.data.materials.append(material)
    return index


def bCreateSubMeshes(meshData, meshName):
    import numpy as np
    allObjects = []
    submeshes = meshData['submeshes']
    # Static submeshes with shared geometry can use one vertex buffer directly.
    # Rig and morph imports retain their established topology/animation path.
    shared_merge = (config.get('MERGE_SUBMESHES') and len(submeshes)>1 and
        'sharedgeometry' in meshData and all('geometry' not in sub for sub in submeshes) and
        not any(key in meshData for key in ('boneIDs','skeleton','armature','poses')))
    original_submeshes = submeshes
    if shared_merge:
        submeshes = [dict(submeshes[0],faces=[face for sub in submeshes for face in sub['faces']])]
    scene = bpy.context.scene
    layer = bpy.context.view_layer

    for subMeshIndex in range(len(submeshes)):
        subMeshData = submeshes[subMeshIndex]
        subMeshName = subMeshData['material']

        # Create mesh and object
        object_name = meshName if shared_merge else subMeshName
        me = bpy.data.meshes.new(object_name)
        ob = bpy.data.objects.new(object_name, me)

        # Link object to scene
        scene.collection.objects.link(ob)
        layer.objects.active = ob
        layer.update()

        # Check for submesh geometry, or take the shared one
        if 'geometry' in subMeshData.keys():
            geometry = subMeshData['geometry']
        else:
            geometry = meshData['sharedgeometry']

        verts = geometry['positions']
        faces = subMeshData['faces']

        hasNormals = False
        if 'normals' in geometry.keys():
            normals = geometry['normals']
            hasNormals = True

        # Mesh vertices and faces
        VertLength = len(verts)
        FaceLength = len(faces)
        me.vertices.add(VertLength)
        me.loops.add(FaceLength * 3)
        me.polygons.add(FaceLength)

        me.vertices.foreach_set('co',np.asarray(verts,dtype='f').ravel())
        loop_vertices = np.asarray(faces,dtype='i').ravel()
        me.polygons.foreach_set('loop_start',np.arange(0,FaceLength*3,3,dtype='i'))
        me.polygons.foreach_set('loop_total',np.full(FaceLength,3,dtype='i'))
        me.loops.foreach_set('vertex_index',loop_vertices)

        hasTexture = False
        # Material for the submesh
        # Create image texture from image.
        if shared_merge:
            slots = [np.full(len(sub['faces']),append_material(ob,meshData,sub),dtype='i') for sub in original_submeshes]
            me.polygons.foreach_set('material_index',np.concatenate(slots))
        else:
            append_material(ob,meshData,subMeshData)

        # Texture coordinates
        if 'texcoordsets' in geometry and 'uvsets' in geometry:
            uvsets = np.asarray(geometry['uvsets'],dtype='f')
            for j in range(geometry['texcoordsets']):
                uvData = me.uv_layers.new(name='UVLayer'+str(j)).data
                uvData.foreach_set('uv',uvsets[loop_vertices,j,:].ravel())

        # Vertex colors
        if 'vertexcolors' in geometry and len(geometry['vertexcolors']) > 0:
            colourData = None
            if (bpy.app.version >= (3, 2, 0)):
                colourData = me.color_attributes.new(name='Color', domain='CORNER', type='BYTE_COLOR').data
            else:
                colourData = me.vertex_colors.new(name='Color').data

            vcolors = np.asarray(geometry['vertexcolors'],dtype='f')
            colourData.foreach_set('color',vcolors[loop_vertices].ravel())

        # Bone assignments:
        if 'boneIDs' in meshData:
            if 'boneassignments' in geometry.keys():
                vgroups = geometry['boneassignments']
                for vgname, vgroup in vgroups.items():
                    #logger.debug("creating VGroup %s" % vgname)
                    grp = ob.vertex_groups.new(name=vgname)
                    for (v, w) in vgroup:
                        #grp.add([v], w, 'REPLACE')
                        grp.add([v], w, 'ADD')

        # Give mesh object an armature modifier, using vertex groups but not envelopes
        if 'skeleton' in meshData:
            skeletonName = meshData['skeletonName']
            Report.armatures.append(skeletonName)

            mod = ob.modifiers.new('OgreSkeleton', 'ARMATURE')
            mod.object = meshData['rig']  # gets the rig object
            mod.use_bone_envelopes = False
            mod.use_vertex_groups = True

        elif 'armature' in meshData:
            mod = ob.modifiers.new('OgreSkeleton', 'ARMATURE')
            mod.object = meshData['armature']
            mod.use_bone_envelopes = False
            mod.use_vertex_groups = True

        # Shape keys (poses)
        if 'poses' in meshData:
            # Must have base shape
            base = ob.shape_key_add(name='Basis')

            for pose in meshData['poses']:
                if('submesh' not in pose or pose['submesh'] == subMeshIndex):
                    name = pose['name']
                    Report.shape_keys.append(name)

                    logger.info('* Creating pose: %s' % name)
                    shape = ob.shape_key_add(name=name)
                    for vkey in pose['data']:
                        b = base.data[vkey[0]].co
                        me.shape_keys.key_blocks[name].data[vkey[0]].co = [vkey[1] + b[0], vkey[2] + b[1], vkey[3] + b[2]]

            bCreatePoseAnimations(ob, meshData, subMeshIndex)

        # Update mesh with new data
        #me.calc_loop_triangles()
        me.update(calc_edges=True)

        # Try to set custom normals
        if hasNormals:
            if bpy.app.version < (4, 1, 0):
                me.use_auto_smooth = True
            me.normals_split_custom_set_from_vertices(normals)

        Report.orig_vertices = len( me.vertices )
        Report.faces += len( me.polygons )

        # Preserve source triangles, normals, UV seams, and shape topology.

        Report.triangles += len( me.polygons )
        Report.vertices += len( me.vertices )

        allObjects.append(ob)

    return allObjects


def matchFace(face, vertices, mesh, index):
    if index >= len(mesh.polygons):
        return False  # ?? err - what broke
    loop = mesh.polygons[index].loop_start
    for v in face:
        vi = mesh.loops[loop].vertex_index
        vx = mesh.vertices[vi].co

        if (vx-Vector(vertices[v])).length_squared > 1e-6:
            return False

        # if vx != Vector(vertices[v]):
        #    return False  # May need threshold ?
        loop += 1
    return True


def getBoneNameMapFromArmature(arm):
    # Get Ogre bone IDs - need to be in edit mode to access edit_bones
    # Arm should already be the active object
    boneMap = {}
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    for bone in arm.data.edit_bones:
        if 'OGREID' in bone:
            boneMap[ str(bone['OGREID']) ] = bone.name;
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    return boneMap


def load_scene(filepath):
    from .scene_import import load_scene as read_scene
    return read_scene(filepath)


def load_mesh(filepath):
    import tempfile
    with tempfile.TemporaryDirectory(prefix='blender2ogre_import_') as workdir:
        return _load_mesh(filepath, workdir)


def _load_mesh(filepath, workdir):
    logger.info("* Loading mesh from: %s" % str(filepath))

    pathMeshXml = None
    # Get the mesh as .xml file
    if filepath.lower().endswith(".mesh"):
        pathMeshXml = os.path.join(workdir, os.path.basename(filepath) + ".xml")
        if mesh_convert(filepath, pathMeshXml):
            pass
        else:
            logger.error("Failed to convert .mesh file %s to .xml" % filepath)
            Report.errors.append("Failed to convert .mesh file to .xml")
            return {'CANCELLED'}
    elif filepath.lower().endswith(".xml"):
        pathMeshXml = filepath
    else:
        return {'CANCELLED'}

    folder = os.path.dirname(filepath)
    nameDotMeshDotXml = os.path.split(pathMeshXml)[1]
    nameDotMesh = os.path.splitext(nameDotMeshDotXml)[0]
    onlyName = os.path.splitext(nameDotMesh)[0]

    # Material
    meshMaterials = []
    nameDotMaterial = onlyName + ".material"
    pathMaterial = os.path.join(folder, nameDotMaterial)
    if not os.path.isfile(pathMaterial):
        # Search directory for .material
        for filename in os.listdir(folder):
            if ".material" in filename:
                # Material file
                pathMaterial = os.path.join(folder, filename)
                meshMaterials.append(pathMaterial)
                #logger.info("alternative material file: %s" % pathMaterial)
    else:
        meshMaterials.append(pathMaterial)

    # Try to parse xml file
    xDocMeshData = xOpenFile(pathMeshXml)

    meshData = {}
    if xDocMeshData == "None":
        return {'CANCELLED'}
    if xDocMeshData.documentElement.tagName != "mesh":
        Report.errors.append("The selected XML document is not an OGRE mesh")
        return {'CANCELLED'}
    if xDocMeshData != "None":
        # Skeleton data
        # Get the mesh as .xml file
        skeletonFile = xGetSkeletonLink(xDocMeshData, folder)

        # Use selected skeleton
        selectedSkeleton = bpy.context.active_object \
            if (config.get('USE_SELECTED_SKELETON') is True
                and bpy.context.active_object
                and bpy.context.active_object.type == 'ARMATURE') else None
        if selectedSkeleton:
            map = getBoneNameMapFromArmature(selectedSkeleton)
            if map:
                meshData['boneIDs'] = map
                meshData['armature'] = selectedSkeleton
            else:
                logger.warning("Selected armature has no OGRE data.")
                Report.warnings.append("Selected armature has no OGRE data.")

        # There is valid skeleton link and existing file
        elif skeletonFile != "None":
            skeletonFileXml = skeletonFile if skeletonFile.lower().endswith(".xml") else os.path.join(workdir, os.path.basename(skeletonFile) + ".xml")
            if skeletonFileXml == skeletonFile or mesh_convert(skeletonFile, skeletonFileXml):

                # Parse .xml skeleton file
                xDocSkeletonData = xOpenFile(skeletonFileXml)
                if xDocSkeletonData != "None":
                    xCollectBoneData(meshData, xDocSkeletonData)
                    meshData['skeletonName'] = os.path.basename(skeletonFile).split('.skeleton')[0]

                    # Parse animations
                    if config.get('IMPORT_ANIMATIONS') is True:
                        fps = xAnalyseFPS(xDocSkeletonData)
                        if(fps and (config.get('ROUND_FRAMES') is True)):
                            logger.info(" * Setting FPS to %s" % fps)
                            bpy.context.scene.render.fps = round(fps)
                            bpy.context.scene.render.fps_base = round(fps) / fps
                        xCollectAnimations(meshData, xDocSkeletonData)

            else:
                logger.warning("Failed to load linked skeleton")
                Report.warnings.append("Failed to load linked skeleton")

        # Collect mesh data
        xCollectMeshData(meshData, xDocMeshData, onlyName, folder)
        from .validation import validate_mesh
        validate_mesh(meshData)
        MaterialParser.xCollectMaterialData(meshData, onlyName, folder)
        
        if config.get('IMPORT_SHAPEKEYS') is True:
            xCollectPoseData(meshData, xDocMeshData)

        # Geometry and animation channels are plain arrays now. Release the
        # large XML tree before allocating Blender's mesh buffers.
        xDocMeshData.unlink()

        # After collecting is done, start creating stuff#
        # Create skeleton (if any) and mesh from parsed data
        bCreateMesh(meshData, folder, onlyName, pathMeshXml)
        bCreateAnimations(meshData)

    return {'FINISHED'}
