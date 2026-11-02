"""Shared asset-pack material regressions, including the reported Bakugan mesh."""
from pathlib import Path
import json, sys, traceback, uuid, hashlib
import bpy, addon_utils
ROOT=Path(__file__).resolve().parents[2]
MODULE_ROOT=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv and len(sys.argv)>sys.argv.index('--')+1 else ROOT
sys.path.insert(0,str(MODULE_ROOT))
addon_utils.enable('io_ogre',default_set=True,persistent=False)
from io_ogre import config
from io_ogre.report import Report
from io_ogre.ogre.material_parser import MaterialParser
from io_ogre.ogre.material_resolver import MaterialResolver
from io_ogre.ogre.resource_index import ResourceIndex
OUT=ROOT/'ChatGPT/outputs/material_resources'/uuid.uuid4().hex[:8]
OUT.mkdir(parents=True)
RESULTS=[]

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text,encoding='utf-8'); return path

def image(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    data=bpy.data.images.new(path.name,width=2,height=2); data.save(filepath=str(path),save_copy=True)
    return path

def case(fn):
    from test_support import skip_fixture_case
    if skip_fixture_case(fn.__name__): return
    if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    config.CONFIG.update(config._CONFIG_DEFAULTS_ALL); Report.reset()
    try:
        fn(); result={'test':fn.__name__,'passed':True}
    except Exception:
        result={'test':fn.__name__,'passed':False,'detail':traceback.format_exc()}; print(result['detail'])
    RESULTS.append(result)

def read(file):
    data={}; MaterialParser.xParseMaterial(data,str(file),str(file.parent)); return data

@case
def shared_pack_abstract_pass_uses_albedo_not_specular():
    root=OUT/'pack'; write(root/'truck.truck','fixture')
    base=write(root/'parts/base.material','''abstract pass lit {
scene_blend alpha_blend
vertex_program_ref Shader {}
texture_unit { texture $texture }
texture_unit { texture $spec }
}
abstract material base { technique { pass : lit {} } }
''')
    child=write(root/'trucks/local/body.material','''import * from "base.material"
material Body : base {
set $texture body.png
set $spec body-spec.png
}
''')
    albedo=image(child.parent/'body.png'); image(child.parent/'body-spec.png')
    data=read(child)
    assert Path(data['Body']['texture'])==albedo,data
    assert not Report.warnings,Report.warnings

@case
def shared_named_materials_discovered_from_mesh_references():
    root=OUT/'implicit'; write(root/'truck.truck','fixture')
    folder=root/'trucks/local'; folder.mkdir(parents=True)
    write(folder/'body.material','material Body { technique { pass { diffuse 1 0 0 1 } } }')
    write(root/'parts/shared/shared.material','material Glass { technique { pass { texture_unit { texture glass.png } } } }')
    texture=image(root/'parts/shared/glass.png')
    data={'submeshes':[{'material':'Body','materialOrig':'Body'},{'material':'Glass','materialOrig':'Glass'}]}
    MaterialParser.xCollectMaterialData(data,'body',str(folder))
    assert set(data['materials'])=={'Body','Glass'}
    assert Path(data['materials']['Glass']['texture'])==texture
    assert not Report.warnings,Report.warnings

@case
def explicit_resource_folder_resolves_shared_dependencies():
    folder=OUT/'standalone'; shared=OUT/'external_shared'
    write(shared/'base.material','abstract material base { technique { pass { texture_unit { texture $image } } } }')
    texture=image(shared/'paint.png')
    child=write(folder/'body.material','import * from "base.material"\nmaterial Body : base { set $image paint.png }')
    config.CONFIG['IMPORT_RESOURCE_PATH']=str(shared)
    assert Path(read(child)['Body']['texture'])==texture

@case
def ambiguous_shared_texture_is_reported():
    root=OUT/'ambiguous'; write(root/'truck.truck','fixture'); folder=root/'trucks/local'; folder.mkdir(parents=True)
    image(root/'one/duplicate.png'); image(root/'two/duplicate.png')
    index=ResourceIndex(folder)
    assert index.find('duplicate.png') is None
    assert any('Ambiguous asset resource' in w for w in Report.warnings),Report.warnings
    direct=image(folder/'duplicate.png')
    assert index.find('duplicate.png')==direct

@case
def abstract_pass_cycles_do_not_recurse_forever():
    file=write(OUT/'cycle/cycle.material','abstract pass a : b {}\nabstract pass b : a {}\nmaterial Body { technique { pass : a {} } }')
    assert read(file)=={}
    assert any('Cyclic pass inheritance' in w for w in Report.warnings),Report.warnings

@case
def quoted_named_pass_overrides_keep_inherited_texture():
    file=write(OUT/'quoted/body.material','''abstract pass base { diffuse 0.2 0.3 0.4 1
texture_unit { texture base.png }
}
abstract material Parent { technique "Main" { pass "Color" : base {} } }
material Body : Parent { technique Main { pass Color { diffuse 0.8 0.7 0.6 1 } } }
''')
    texture=image(file.parent/'base.png')
    data=read(file)
    assert data['Body']['diffuse']==[.8,.7,.6,1],data
    assert Path(data['Body']['texture'])==texture

@case
def standalone_lookup_stays_within_its_asset_folder():
    folder=OUT/'ordinary/local'; folder.mkdir(parents=True)
    index=ResourceIndex(folder)
    assert index.roots==[folder.resolve()],index.roots
    outside=write(OUT/'ordinary/unrelated.material','material Wrong {}')
    assert index.find('../unrelated.material') is None

@case
def inherited_alpha_rejection_preserves_image_alpha():
    from io_ogre.ogre.material_import import create_material
    texture=image(OUT/'masked/alpha.png')
    mat=create_material('Masked',{'texture':str(texture),'scene_blend':'alpha_blend','alpha_rejection':['greater','128']})
    assert mat['ogre_alpha_mode']=='BLEND'
    assert abs(mat['ogre_alpha_threshold']-128/255)<1e-6
    shader=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    assert shader.inputs['Alpha'].is_linked
    assert any(n.type=='MATH' and n.operation=='MULTIPLY' for n in mat.node_tree.nodes)

@case
def reported_bakugan_body_imports_all_three_base_textures():
    fixture=ROOT/'ChatGPT/fixtures/bakugan_pack'
    sources=json.loads((fixture/'sources.json').read_text())
    before={entry['source']:hashlib.sha256(Path(entry['source']).read_bytes()).hexdigest() for entry in sources}
    file=fixture/'crd_trucks/bakugan_dragonoid/bakugan_dragonoid_body.mesh'
    result=bpy.ops.ogre.import_mesh(filepath=str(file),IM_USE_SELECTED_SKELETON=False,IM_Vx_ENABLE_LOGGING=False)
    assert result=={'FINISHED'},Report.errors
    meshes=[ob for ob in bpy.context.scene.objects if ob.type=='MESH']
    assert len(meshes)==1
    obj=meshes[0]
    expected={'bakugan_dragonoid_body':'bakugan_dragonoid_body.png','Fiberglass':'Fiberglass2.png','V5Windshield':'V5Windshield.png'}
    found={}
    for mat in obj.data.materials:
        name=next((name for name in expected if mat.name==name or mat.name.startswith(name+'.')),None)
        if name:
            shader=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            texture=shader.inputs['Base Color'].links[0].from_node
            assert texture.type=='TEX_IMAGE'
            assert Path(texture.image.filepath).name==expected[name],(name,texture.image.filepath)
            # Blender loads image buffers lazily; force a real pixel read.
            assert len(texture.image.pixels)>0,(name,texture.image.filepath)
            pixel=texture.image.pixels[0]
            assert texture.image.has_data,(name,texture.image.filepath,pixel)
            found[name]=texture.image.filepath
    assert set(found)==set(expected),found
    bad=[w for w in Report.warnings if any(term in w.lower() for term in ('missing parent','not found','outside the asset','not found in'))]
    assert not bad,bad
    assert len(obj.data.polygons)==190826,len(obj.data.polygons)
    assert len(obj.data.uv_layers)>0
    for entry in sources:
        assert hashlib.sha256(Path(entry['source']).read_bytes()).hexdigest()==entry['sha256']==before[entry['source']]
    (OUT/'bakugan_result.json').write_text(json.dumps({'mesh':obj.name,'triangles':len(obj.data.polygons),'vertices':len(obj.data.vertices),'material_images':found,'warnings':Report.warnings,'originals_unchanged':True},indent=2))

addon_utils.disable('io_ogre',default_set=True)
record={'blender':bpy.app.version_string,'module_root':str(MODULE_ROOT),'output':str(OUT),'tests':RESULTS}
(ROOT/'ChatGPT/outputs/material_resources_results.json').write_text(json.dumps(record,indent=2))
for item in RESULTS: print('PASS' if item['passed'] else 'FAIL',item['test'])
assert all(item['passed'] for item in RESULTS),'Material resource regressions failed'
print('MATERIAL_RESOURCES_PASS',len(RESULTS))
