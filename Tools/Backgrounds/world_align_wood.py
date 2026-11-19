"""Make the existing wood material independent of mesh UVs and object scale."""
import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
mel=unreal.MaterialEditingLibrary
assets=unreal.EditorAssetLibrary
material=unreal.load_asset('/Game/Root/Assets/Materials/Backgrounds/M_WoodBackground')
instance=unreal.load_asset('/Game/Root/Assets/Materials/Backgrounds/MI_WoodBackground')
texture=unreal.load_asset('/Game/Root/Assets/Textures/T_WoodBackground')
function=unreal.load_asset('/Engine/Functions/Engine_MaterialFunctions01/Texturing/WorldAlignedTexture.WorldAlignedTexture')
assert material and instance and texture and function
old_values={name:mel.get_material_instance_scalar_parameter_value(instance,name) for name in ['TilingU','TilingV','Brightness']}
material.modify();mel.delete_all_material_expressions(material)
def expr(cls,x,y):return mel.create_material_expression(material,cls,x,y)
def wire(a,b,pin,out=''):
    names=list(mel.get_material_expression_input_names(b))
    if pin not in names and len(names)==1:pin=names[0]
    assert mel.connect_material_expressions(a,out,b,pin),(b.get_name(),pin)
def scalar(name,value,x,y):
    n=expr(unreal.MaterialExpressionScalarParameter,x,y)
    n.set_editor_property('ParameterName',name);n.set_editor_property('DefaultValue',value)
    return n
def constant(value,x,y):
    n=expr(unreal.MaterialExpressionConstant,x,y);n.r=value;return n
def binary(cls,a,b,x,y):
    n=expr(cls,x,y);wire(a,n,'A');wire(b,n,'B');return n
size=scalar('TileSizeCm',100,-1400,0)
u=scalar('TilingU',1,-1400,300);v=scalar('TilingV',1,-1400,550)
minimum=constant(0.01,-1400,800)
u_safe=binary(unreal.MaterialExpressionMax,u,minimum,-1150,300)
v_safe=binary(unreal.MaterialExpressionMax,v,minimum,-1150,550)
size_safe=binary(unreal.MaterialExpressionMax,size,constant(1,-1400,-200),-1150,0)
horizontal=binary(unreal.MaterialExpressionDivide,size_safe,u_safe,-900,250)
vertical=binary(unreal.MaterialExpressionDivide,size_safe,v_safe,-900,550)
xy=binary(unreal.MaterialExpressionAppendVector,horizontal,horizontal,-650,250)
xyz=binary(unreal.MaterialExpressionAppendVector,xy,vertical,-400,250)
tex=expr(unreal.MaterialExpressionTextureObjectParameter,-650,-200)
tex.set_editor_property('ParameterName','WoodTexture');tex.texture=texture
projection=expr(unreal.MaterialExpressionMaterialFunctionCall,-100,0)
projection.set_editor_property('material_function',function)
wire(tex,projection,'TextureObject');wire(xyz,projection,'TextureSize')
brightness=scalar('Brightness',0.85,-100,550)
color=expr(unreal.MaterialExpressionMultiply,250,0)
wire(projection,color,'A','XYZ Texture');wire(brightness,color,'B')
assert mel.connect_material_property(color,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
mel.recompile_material(material)
assert assets.save_loaded_asset(material)
for name,value in old_values.items():
    assert abs(mel.get_material_instance_scalar_parameter_value(instance,name)-value)<0.0001,(name,value)
assert assets.save_loaded_asset(instance)
assert not any(isinstance(n,unreal.MaterialExpressionTextureCoordinate) for n in [size,u,v,projection])
report={'material':material.get_path_name(),'instance':instance.get_path_name(),'projection':'WorldAlignedTexture XYZ','tile_size_cm_default':100,'scale_independent':True,'preserved_instance_parameters':old_values}
(root/'Saved/MCP/wood-world-aligned.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assets.sync_browser_to_objects([instance.get_path_name()])
print('WOOD_WORLD_ALIGNED_SAVED:'+json.dumps(report))
