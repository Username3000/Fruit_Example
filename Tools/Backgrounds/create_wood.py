"""Import the generated wood tile and create a ready-to-apply background material."""
import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
assets=unreal.EditorAssetLibrary
tools=unreal.AssetToolsHelpers.get_asset_tools()
mel=unreal.MaterialEditingLibrary
texture_path='/Game/Root/Assets/Textures/T_WoodBackground'
folder='/Game/Root/Assets/Materials/Backgrounds'
assets.make_directory(folder)
assert not assets.does_asset_exist(texture_path),'Use a versioned name instead of replacing an existing wood texture'
task=unreal.AssetImportTask()
task.filename=str(root/'SourceAssets/Backgrounds/T_WoodBackground.png')
task.destination_path='/Game/Root/Assets/Textures'
task.destination_name='T_WoodBackground'
task.automated=True;task.save=True
tools.import_asset_tasks([task])
texture=unreal.load_asset(texture_path);assert texture
texture.set_editor_property('srgb',True)
texture.set_editor_property('address_x',unreal.TextureAddress.TA_MIRROR)
texture.set_editor_property('address_y',unreal.TextureAddress.TA_MIRROR)
texture.set_editor_property('power_of_two_mode',unreal.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)
texture.set_editor_property('max_texture_size',1024)
texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_DEFAULT)
assert assets.save_loaded_asset(texture)

assert not assets.does_asset_exist(folder+'/M_WoodBackground')
material=tools.create_asset('M_WoodBackground',folder,unreal.Material,unreal.MaterialFactoryNew())
material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
def expr(cls,x,y):return mel.create_material_expression(material,cls,x,y)
def wire(a,b,pin,out=''):
    names=list(mel.get_material_expression_input_names(b))
    if pin not in names and len(names)==1:pin=names[0]
    assert mel.connect_material_expressions(a,out,b,pin),(b.get_name(),pin)
def scalar(name,value,x,y):
    n=expr(unreal.MaterialExpressionScalarParameter,x,y)
    n.set_editor_property('ParameterName',name);n.set_editor_property('DefaultValue',value)
    return n
uv=expr(unreal.MaterialExpressionTextureCoordinate,-900,0)
u=scalar('TilingU',1,-900,250);v=scalar('TilingV',1,-900,450)
tiling=expr(unreal.MaterialExpressionAppendVector,-650,250);wire(u,tiling,'A');wire(v,tiling,'B')
multiply=expr(unreal.MaterialExpressionMultiply,-400,0);wire(uv,multiply,'A');wire(tiling,multiply,'B')
sample=expr(unreal.MaterialExpressionTextureSample,-150,0);sample.texture=texture;wire(multiply,sample,'UVs')
brightness=scalar('Brightness',0.85,-150,400)
color=expr(unreal.MaterialExpressionMultiply,150,0);wire(sample,color,'A','RGB');wire(brightness,color,'B')
assert mel.connect_material_property(color,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
mel.recompile_material(material);assert assets.save_loaded_asset(material)

instance=tools.create_asset('MI_WoodBackground',folder,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
mel.set_material_instance_parent(instance,material)
for name,value in [('TilingU',1),('TilingV',1),('Brightness',0.85)]:
    mel.set_material_instance_scalar_parameter_value(instance,name,value)
assert assets.save_loaded_asset(instance)
assert instance.parent==material
report={'texture':texture.get_path_name(),'material':instance.get_path_name(),'source':str(root/'SourceAssets/Backgrounds/T_WoodBackground.png'),'address_mode':'Mirror in U and V, continuous edge colors','parameters':{'TilingU':1,'TilingV':1,'Brightness':0.85}}
(root/'Saved/MCP/wood-background.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assets.sync_browser_to_objects([instance.get_path_name(),texture.get_path_name()])
print('WOOD_BACKGROUND_READY:'+json.dumps(report))
# Keep the material independent of cube scale and mesh UV stretching.
world_aligned=root/'Tools/Backgrounds/world_align_wood.py'
exec(compile(world_aligned.read_text(encoding='utf-8'),str(world_aligned),'exec'))
