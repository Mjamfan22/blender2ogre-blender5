import bpy, os, sys, logging, mathutils, json, shutil, tempfile
from pprint import pprint
from bpy.props import *

logger = logging.getLogger('config')

AXIS_MODES =  [
    ('xyz', 'xyz', 'No Axis swapping'),
    ('xz-y', 'xz-y', 'Ogre standard'),
    ('-xzy', '-xzy', 'Non standard'),
]

MESH_TOOL_VERSIONS = [
    ('v1', 'v1', 'Export the mesh as a v1 object'),
    ('v2', 'v2', 'Export the mesh as a v2 object')
]

TANGENT_MODES =  [
    ('0', 'none', 'Do not export tangents'),
    ('3', 'generate', 'Generate tangents'),
    ('4', 'generate with parity', 'Generate with parity')
]

LOD_METHODS =  [
    ('0', 'meshtools', 'Generate LODs using OgreMesh Tools: does LOD by removing edges, which allows only changing the index buffer and re-use the vertex-buffer (storage efficient)'),
    ('1', 'blender', 'Generate LODs using Blenders "Decimate" Modifier: does LOD by collapsing vertices, which can result in a visually better LOD, but needs different vertex-buffers per LOD'),
    ('2', 'manual', 'Generate LODs by manually crafting the lower LODs: needs different vertex-buffers per LOD')
]

CONFIG_PATH = bpy.utils.user_resource('CONFIG', path='scripts', create=True)
CONFIG_FILENAME = 'io_ogre.json'
CONFIG_FILEPATH = os.path.join(CONFIG_PATH, CONFIG_FILENAME)

CONFIG = {}

_CONFIG_DEFAULTS_ALL = {
    # General
    'SWAP_AXIS' : 'xz-y',
    'EXPORT_PREFIX' : '',
    'MESH_TOOL_VERSION' : 'v2',
    'EXPORT_XML_DELETE' : True,

    # Scene
    'SCENE' : True,
    'SELECTED_ONLY' : True,
    'EXPORT_HIDDEN' : True,
    #'EXPORT_USER' : True,
    'FORCE_CAMERA' : True,
    'FORCE_LIGHTS' : True,
    'NODE_ANIMATION' : True,
    'NODE_KEYFRAMES' : False,
    'EXPORT_SKYBOX': False,
    'SKYBOX_RESOLUTION': 2048,

    # Materials
    'MATERIALS' : True,
    'COPY_SHADER_PROGRAMS' : True,
    'SEPARATE_MATERIALS' : True,
    'USE_FFP_PARAMETERS': False,

    # Textures
    'MAX_TEXTURE_SIZE' : 4096,
    'FORCE_IMAGE_FORMAT' : 'NONE',
    'TOUCH_TEXTURES' : True,
    'DDS_MIPS' : 16,

    # Armature
    'ONLY_DEFORMABLE_BONES' : False,
    'ONLY_KEYFRAMED_BONES' : False,
    'OGRE_INHERIT_SCALE' : False,
    'ARMATURE_ANIMATION' : True,
    'TRIM_BONE_WEIGHTS' : 0.01,
    'ONLY_KEYFRAMES' : False,
    'SHARED_ARMATURE' : False,

    # Mesh
    'MESH' : True,
    'APPLY_MODIFIERS' : True,
    'MESH_OVERWRITE' : True,
    'ARRAY' : True,
    'EXTREMITY_POINTS' : 0,
    'GENERATE_EDGE_LISTS' : False,
    'GENERATE_TANGENTS' : '0',
    'PACK_INT_10_10_10_2': False,
    'OPTIMISE_ANIMATIONS' : True,
    'INTERFACE_TOGGLE': False,
    'OPTIMISE_VERTEX_CACHE' : False,
    'OPTIMISE_VERTEX_BUFFERS' : True,
    'OPTIMISE_VERTEX_BUFFERS_OPTIONS' : 'puqs',
    'UNSHARE_GEOMETRY' : False,

    # LOD
    'LOD_GENERATION': '0',
    'LOD_LEVELS' : 0,
    'LOD_DISTANCE' : 300,
    'LOD_PERCENT' : 40,

    # Pose Animation
    'SHAPE_ANIMATIONS' : True,
    'SHAPE_NORMALS' : True,

    # Logging
    'ENABLE_LOGGING' : False,
    'DEBUG_LOGGING' : False,
    #'SHOW_LOG_NAME' : False,

    # Import
    'IMPORT_RESOURCE_PATH' : '',
    'IMPORT_XML_DELETE' : False,
    'IMPORT_NORMALS' : True,
    'MERGE_SUBMESHES' : True,
    'IMPORT_ANIMATIONS' : True,
    'ROUND_FRAMES' : True,
    'USE_SELECTED_SKELETON' : True,
    'IMPORT_SHAPEKEYS' : True,
}

_CONFIG_TAGS_ = 'OGRETOOLS_XML_CONVERTER OGRETOOLS_MESH_UPGRADER MESH_PREVIEWER IMAGE_MAGICK_CONVERT USER_MATERIALS SHADER_PROGRAMS'.split()

''' todo: Change pretty much all of these windows ones. Make a smarter way of detecting
    Ogre tools from various default folders. Also consider making a installer that
    ships Ogre cmd line tools to ease the setup steps for end users. '''

_BUNDLED_TOOLS = os.path.join(os.path.dirname(__file__), 'tools', 'windows')

_CONFIG_DEFAULTS_WINDOWS = {
    'OGRETOOLS_XML_CONVERTER' : os.path.join(_BUNDLED_TOOLS, 'OgreXMLConverter.exe'),
    'OGRETOOLS_MESH_UPGRADER' : os.path.join(_BUNDLED_TOOLS, 'OgreMeshUpgrader.exe'),
    'MESH_PREVIEWER' : 'ogre-meshviewer.bat',
    'IMAGE_MAGICK_CONVERT' : 'C:\\Program Files\\ImageMagick\\convert.exe',
    'USER_MATERIALS' : '',
    'SHADER_PROGRAMS' : ''
}

_CONFIG_DEFAULTS_UNIX = {
    # do not use absolute paths like /usr/bin/exe_name. some distris install to /usr/local/bin ...
    # just trust the env PATH variable
    'IMAGE_MAGICK_CONVERT' : 'convert',
    'OGRETOOLS_XML_CONVERTER' : 'OgreXMLConverter',
    'OGRETOOLS_MESH_UPGRADER' : 'OgreMeshUpgrader',
    'MESH_PREVIEWER' : 'ogre-meshviewer',
    'USER_MATERIALS' : '',
    'SHADER_PROGRAMS' : '~/',
    #'USER_MATERIALS' : '~/ogre_src_v1-7-3/Samples/Media/materials',
    #'SHADER_PROGRAMS' : '~/ogre_src_v1-7-3/Samples/Media/materials/programs',
}

# Unix: Replace ~ with absolute home dir path
if sys.platform.startswith('linux') or sys.platform.startswith('darwin') or sys.platform.startswith('freebsd'):
    for tag in _CONFIG_DEFAULTS_UNIX:
        path = _CONFIG_DEFAULTS_UNIX[ tag ]
        if path.startswith('~'):
            _CONFIG_DEFAULTS_UNIX[ tag ] = os.path.expanduser( path )
        elif tag.startswith('OGRETOOLS') and not os.path.isfile( path ):
            _CONFIG_DEFAULTS_UNIX[ tag ] = os.path.join( '/usr/bin', os.path.split( path )[-1] )
    del tag
    del path


## PUBLIC API continues

def load_config():
    global CONFIG
    logger.info('* Loading config: %s' % CONFIG_FILEPATH)
    config_dict = {}

    # Check if the config file exists and load it
    if os.path.isfile( CONFIG_FILEPATH ):
        try:
            with open( os.path.join(CONFIG_FILEPATH), 'r' ) as f:
                config_dict = json.load(f)
        except EOFError:
            logger.error('Config file: %s is empty' % CONFIG_FILEPATH)
        except Exception as e:
            logger.error('Can not read config from: %s' % CONFIG_FILEPATH)
            logger.error('Exception: %s' % e)
    else:
        logger.error('Config file: %s does not exist' % CONFIG_FILEPATH)

    if not isinstance(config_dict, dict):
        logger.warning('Ignoring a config file whose root is not an object')
        config_dict = {}
    for tag, default in _CONFIG_DEFAULTS_ALL.items():
        value = config_dict.get(tag, default)
        if type(value) is not type(default):
            config_dict[tag] = default
    enums = {'SWAP_AXIS':AXIS_MODES, 'MESH_TOOL_VERSION':MESH_TOOL_VERSIONS,
             'GENERATE_TANGENTS':TANGENT_MODES, 'LOD_GENERATION':LOD_METHODS}
    for tag, items in enums.items():
        if config_dict.get(tag, _CONFIG_DEFAULTS_ALL[tag]) not in {item[0] for item in items}:
            config_dict[tag] = _CONFIG_DEFAULTS_ALL[tag]

    # Load default values from _CONFIG_DEFAULTS_ALL if they don't exist after loading config from file
    for tag in _CONFIG_DEFAULTS_ALL:
        if tag not in config_dict:
            config_dict[ tag ] = _CONFIG_DEFAULTS_ALL[ tag ]

    # Load default values from _CONFIG_DEFAULTS_WINDOWS or _CONFIG_DEFAULTS_UNIX if they don't exist after loading config from file
    for tag in _CONFIG_TAGS_:
        if tag not in config_dict:
            if sys.platform.startswith('win'):
                config_dict[ tag ] = _CONFIG_DEFAULTS_WINDOWS[ tag ]
            elif sys.platform.startswith('linux') or sys.platform.startswith('darwin') or sys.platform.startswith('freebsd'):
                config_dict[ tag ] = _CONFIG_DEFAULTS_UNIX[ tag ]
            else:
                logger.error('Unknown platform: %s' % sys.platform)
                assert 0

    for tag in _CONFIG_TAGS_:
        if not isinstance(config_dict[tag], str):
            config_dict[tag] = (_CONFIG_DEFAULTS_WINDOWS if sys.platform.startswith('win') else _CONFIG_DEFAULTS_UNIX)[tag]
        config_dict[tag] = resolve_bundled_tool(tag, config_dict[tag])
    return config_dict


def resolve_bundled_tool(tag, value):
    """Repair relocated bundled/old default paths; preserve external tool choices."""
    if sys.platform.startswith('win') and tag in ('OGRETOOLS_XML_CONVERTER','OGRETOOLS_MESH_UPGRADER'):
        bundled = _CONFIG_DEFAULTS_WINDOWS[tag]
        expected = os.path.basename(bundled).lower()
        if os.path.basename(value).lower() == expected and not shutil.which(value) and os.path.isfile(bundled):
            logger.info('Using bundled tool after its previous path became unavailable: %s', tag)
            return bundled
    return value

def get(name, default=None):
    global CONFIG
    if name in CONFIG:
        return CONFIG[name]
    else:
        logger.error("Config option %s does not exist!" % name)
    return default

# Global CONFIG dictionary
CONFIG = load_config()

def update(**kwargs):
    global CONFIG
    for key,value in kwargs.items():
        if key not in _CONFIG_DEFAULTS_ALL:
            logger.warn("Trying to set CONFIG['%s'] = %s, but it is not a known config setting" % (key, value))
        #print("update() :: key: %s, value: %s" % (key, value))
        CONFIG[key] = value
    save_config()

def save_config():
    global CONFIG
    logger.info('* Saving config to: %s' % CONFIG_FILEPATH)
    #for key in CONFIG: print( '%s = %s' %(key, CONFIG[key]) )
    if os.path.isdir( CONFIG_PATH ):
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf8', dir=CONFIG_PATH,
                    prefix='io_ogre_', suffix='.tmp', delete=False) as f:
                temporary = f.name
                json.dump(CONFIG, f, indent=4)
            os.replace(temporary, CONFIG_FILEPATH)
        except Exception as e:
            logger.error('Can not write to %s' % CONFIG_FILEPATH)
            logger.error('Exception: %s' % e)
    else:
        logger.error('Config directory %s does not exist' % CONFIG_PATH)

def update_from_addon_preference(context):
    global CONFIG
    addon_preferences = context.preferences.addons["io_ogre"].preferences

    for key in _CONFIG_TAGS_:
        addon_pref_value = getattr(addon_preferences,key,None)
        if addon_pref_value is not None:
            CONFIG[key] = resolve_bundled_tool(key, addon_pref_value)
