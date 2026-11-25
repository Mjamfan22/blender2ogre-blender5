"""Shared asset-pack material regressions, including the reported Bakugan mesh."""
from pathlib import Path
import json, sys, traceback, uuid, hashlib
import bpy, addon_utils
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
MODULE_ROOT=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv and len(sys.argv)>sys.argv.index('--')+1 else ROOT
sys.path.insert(0,str(MODULE_ROOT))
addon_utils.enable('io_ogre',default_set=True,persistent=False)
from io_ogre import config
from io_ogre.report import Report
from io_ogre.ogre.material_parser import MaterialParser
from io_ogre.ogre.material_resolver import MaterialResolver
from io_ogre.ogre.resource_index import ResourceIndex
OUT=ROOT/'.build/outputs/material_resources'/uuid.uuid4().hex[:8]
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
def exporter_placeholder_import_is_informational_and_keeps_geometry():
    folder=OUT/'placeholder_mesh'
    source_name='placeholder_'+uuid.uuid4().hex[:8]
    file=write(folder/(source_name+'.mesh.xml'),'''<mesh>
<sharedgeometry vertexcount="3"><vertexbuffer positions="true">
<vertex><position x="0" y="0" z="0"/></vertex>
<vertex><position x="1" y="0" z="0"/></vertex>
<vertex><position x="0" y="1" z="0"/></vertex>
</vertexbuffer></sharedgeometry>
<submeshes><submesh material="_missing_material_" usesharedvertices="true" operationtype="triangle_list">
<faces count="1"><face v1="0" v2="1" v3="2"/></faces>
</submesh></submeshes></mesh>''')
    result=bpy.ops.ogre.import_mesh(filepath=str(file),IM_USE_SELECTED_SKELETON=False,IM_Vx_ENABLE_LOGGING=False)
    assert result=={'FINISHED'},Report.errors
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    assert obj.name==obj.data.name==source_name,(obj.name,obj.data.name)
    assert len(obj.data.vertices)==3 and len(obj.data.polygons)==1
    assert len(obj.data.materials)==1
    assert obj.data.materials[0]['ogre_placeholder'] is True
    assert not any(n.type=='TEX_IMAGE' for n in obj.data.materials[0].node_tree.nodes)
    assert not Report.warnings and not Report.errors,(Report.warnings,Report.errors)
    assert len(Report.messages)==1 and 'no source material or texture' in Report.messages[0],Report.messages

@case
def placeholder_file_names_keep_dots_and_are_unique_for_separate_submeshes():
    folder=OUT/'placeholder_names'
    source_name='collision.parts_'+uuid.uuid4().hex[:8]
    material_name='Authored_'+uuid.uuid4().hex[:8]
    submesh='<submesh material="%s" usesharedvertices="true"><faces count="1"><face v1="0" v2="1" v3="2"/></faces></submesh>'
    file=write(folder/(source_name+'.xml'),'''<mesh><sharedgeometry vertexcount="3"><vertexbuffer positions="true">
<vertex><position x="0" y="0" z="0"/></vertex><vertex><position x="1" y="0" z="0"/></vertex><vertex><position x="0" y="1" z="0"/></vertex>
</vertexbuffer></sharedgeometry><submeshes>'''+submesh%'_missing_material_'+submesh%'_missing_material_'+submesh%material_name+'</submeshes></mesh>')
    write(folder/(source_name+'.material'),'material '+material_name+' { technique { pass { diffuse 0.2 0.3 0.4 1 } } }')
    for _ in range(2):
        before=set(bpy.data.objects)
        assert bpy.ops.ogre.import_mesh(filepath=str(file),IM_MERGE_SUBMESHES=False,IM_USE_SELECTED_SKELETON=False,IM_Vx_ENABLE_LOGGING=False)=={'FINISHED'}
        imported=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
        assert len(imported)==3
        for obj in imported:
            prefix=source_name if obj.data.materials[0].get('ogre_placeholder') else material_name
            assert obj.name.startswith(prefix) and obj.data.name.startswith(prefix),(obj.name,obj.data.name,prefix)
            assert len(obj.data.vertices)==3 and len(obj.data.polygons)==1
        assert not Report.warnings,Report.warnings
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    assert len({o.name for o in objects})==len({o.data.name for o in objects})==6

@case
def supplied_placeholder_definition_is_preserved_and_missing_names_warn():
    from io_ogre.ogre.material_reader import read_materials
    folder=OUT/'placeholder_definition'
    file=write(folder/'local.material','material _missing_material_ { technique { pass { diffuse 0.1 0.2 0.3 1 } } }')
    resolver=MaterialResolver(folder); resolver.load(file)
    info=read_materials(resolver,{'_missing_material_'})['_missing_material_']
    assert info['diffuse']==[.1,.2,.3,1] and not info.get('placeholder'),info
    Report.reset()
    resolver=MaterialResolver(OUT/'unknown_placeholder')
    assert read_materials(resolver,{'_missing_material_custom_'})=={}
    assert any('Missing parent material' in w for w in Report.warnings),Report.warnings

@case
def ror_managed_base_recovers_reported_track_bus_and_tire_textures():
    folder=OUT/'managed_track'
    expected={'Allstar2019day2Fs':'track.png','day2bus':'bus.png',
              'day2bus2':'bus2.png','Allstartires':'tires.png'}
    text='import * from "managed_mats.material"\n'
    for name,filename in expected.items():
        image(folder/filename)
        text+='material "%s" : RoR/Managed_Mats/Base { technique BaseTechnique { pass BaseRender { texture_unit Diffuse_Map { texture "%s" } } } }\n' % (name,filename)
    data=read(write(folder/'track.material',text))
    assert set(data)==set(expected),data
    assert {name:Path(info['texture']).name for name,info in data.items()}==expected,data
    assert not Report.warnings,Report.warnings

@case
def ror_managed_base_supports_unnamed_passes_and_real_bases_win():
    folder=OUT/'managed_real'
    texture=image(folder/'local.png')
    file=write(folder/'local.material','''import * from "managed_mats.material"
material Local : RoR/Managed_Mats/BaseNoShadows {
technique { pass { texture_unit { texture local.png } } }
}
''')
    assert Path(read(file)['Local']['texture'])==texture
    assert not Report.warnings,Report.warnings
    # A supplied base must retain its actual inheritance and properties.
    write(folder/'managed_mats.material','abstract material RoR/Managed_Mats/BaseNoShadows { technique { pass { diffuse 0.2 0.3 0.4 1 } } }')
    data=read(file)
    assert data['Local']['diffuse']==[.2,.3,.4,1],data
    assert Path(data['Local']['texture'])==texture
    assert not Report.warnings,Report.warnings

@case
def ror_recovery_does_not_hide_unknown_parents_or_missing_images():
    folder=OUT/'managed_errors'
    file=write(folder/'local.material','''import * from "managed_mats.material"
material Custom : RoR/Managed_Mats/Custom {}
material Missing : RoR/Managed_Mats/Base {
technique { pass { texture_unit { texture absent.png } } }
}
''')
    data=read(file)
    assert set(data)=={'Missing'},data
    assert any('Missing parent material: RoR/Managed_Mats/Custom' in w for w in Report.warnings),Report.warnings
    assert any('Base texture "absent.png"' in w for w in Report.warnings),Report.warnings
    Report.reset()
    plain=write(OUT/'unrelated/local.material','import * from "unrelated.material"\nmaterial Custom : RoR/Managed_Mats/Base {}')
    assert read(plain)=={}
    assert any('unrelated.material' in w for w in Report.warnings),Report.warnings
    assert any('Missing parent material' in w for w in Report.warnings),Report.warnings

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
    fixture=ROOT/'tests/fixtures/bakugan_pack'
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
(ROOT/'.build/outputs/material_resources_results.json').write_text(json.dumps(record,indent=2))
for item in RESULTS: print('PASS' if item['passed'] else 'FAIL',item['test'])
assert all(item['passed'] for item in RESULTS),'Material resource regressions failed'
print('MATERIAL_RESOURCES_PASS',len(RESULTS))
