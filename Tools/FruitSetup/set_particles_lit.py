"""Use Default Lit for fruit/heart/clock particles, retaining bomb material graphs."""
import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
mel=unreal.MaterialEditingLibrary
assets=unreal.EditorAssetLibrary
def signature(material):
    return {
        'shading_model':str(material.get_editor_property('shading_model')),
        'blend_mode':str(material.get_editor_property('blend_mode')),
        'inputs':[(str(prop),str(mel.get_material_property_input_node(material,prop)),str(mel.get_material_property_input_node_output_name(material,prop))) for prop in [unreal.MaterialProperty.MP_BASE_COLOR,unreal.MaterialProperty.MP_EMISSIVE_COLOR,unreal.MaterialProperty.MP_OPACITY]],
    }
bombs=[unreal.load_asset('/Game/Root/Assets/Materials/ItemEffects/'+name) for name in ['M_ExplosionGlow','M_ExplosionSmoke']]
bomb_before=[signature(m) for m in bombs]
report=[]
for path in ['/Game/Root/Assets/Materials/M_FruitChunks','/Game/Root/Assets/Materials/ItemEffects/M_ItemPieces']:
    material=unreal.load_asset(path);assert material
    opacity=mel.get_material_property_input_node(material,unreal.MaterialProperty.MP_OPACITY_MASK)
    base=mel.get_material_property_input_node(material,unreal.MaterialProperty.MP_BASE_COLOR)
    output=mel.get_material_property_input_node_output_name(material,unreal.MaterialProperty.MP_BASE_COLOR)
    if not base:
        base=mel.get_material_property_input_node(material,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        output=mel.get_material_property_input_node_output_name(material,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        if material.get_name()=='M_ItemPieces':
            # Its old emissive output multiplies texture/particle color by an
            # emission strength. Lit albedo uses the color without self-glow.
            inputs=list(mel.get_inputs_for_material_expression(material,base))
            tint=next((node for node in inputs if isinstance(node,unreal.MaterialExpressionMultiply)),None)
            if tint:base=tint;output=''
    assert base
    material.modify()
    material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    assert mel.connect_material_property(base,output,unreal.MaterialProperty.MP_BASE_COLOR)
    for prop,value,y in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR,0,650),(unreal.MaterialProperty.MP_ROUGHNESS,0.8,850),(unreal.MaterialProperty.MP_SPECULAR,0.2,1050),(unreal.MaterialProperty.MP_METALLIC,0,1250)]:
        constant=mel.create_material_expression(material,unreal.MaterialExpressionConstant,1600,y)
        constant.r=value
        assert mel.connect_material_property(constant,'',prop)
    mel.recompile_material(material)
    assert material.get_editor_property('shading_model')==unreal.MaterialShadingModel.MSM_DEFAULT_LIT
    assert mel.get_material_property_input_node(material,unreal.MaterialProperty.MP_BASE_COLOR)==base
    assert mel.get_material_property_input_node(material,unreal.MaterialProperty.MP_OPACITY_MASK)==opacity
    emission=mel.get_material_property_input_node(material,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    assert isinstance(emission,unreal.MaterialExpressionConstant) and emission.r==0
    assert assets.save_loaded_asset(material)
    report.append({'material':path,'shading_model':'Default Lit','emissive':0,'roughness':0.8,'opacity_preserved':True})
assert [signature(m) for m in bombs]==bomb_before,'Bomb material was changed'
result={'materials':report,'bomb_materials_unchanged':True}
(root/'Saved/MCP/particles-lit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('PARTICLES_LIT_SAVED:'+json.dumps(result))
