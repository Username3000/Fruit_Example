"""Editable UMG Designer layout. Run inside Unreal through project MCP."""
import unreal,json,shutil
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
assets=unreal.EditorAssetLibrary;L=unreal.BlueprintEditorLibrary
for relative in ['Blueprints/UI/B_FruitHUD']:
    source=root/('Content/Root/'+relative+'.uasset');dest=root/('Saved/Backups/HUD/BeforeUMG/'+source.name)
    if source.exists() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
bp=unreal.load_asset('/Game/Root/Blueprints/UI/WBP_FruitHUD')
if not bp:
    factory=unreal.WidgetBlueprintFactory();factory.set_editor_property('parent_class',unreal.UserWidget)
    bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('WBP_FruitHUD','/Game/Root/Blueprints/UI',None,factory)
assert bp
tree=unreal.find_object(bp,'WidgetTree')
print('UMG_TREE',tree)

# The UI brush samples the existing heart, preserving its alpha and facet colors.
mel=unreal.MaterialEditingLibrary
material=unreal.load_asset('/Game/Root/Assets/Materials/UI/M_HUDHeart')
if not material:material=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_HUDHeart','/Game/Root/Assets/Materials/UI',unreal.Material,unreal.MaterialFactoryNew())
material.modify();material.set_editor_property('material_domain',unreal.MaterialDomain.MD_UI)
material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
mel.delete_all_material_expressions(material)
crop=json.loads((root/'SourceAssets/ItemVFX/chunk_uv_bounds.json').read_text(encoding='utf-8'))[0]
uv=mel.create_material_expression(material,unreal.MaterialExpressionTextureCoordinate,-800,0)
scale=mel.create_material_expression(material,unreal.MaterialExpressionConstant2Vector,-800,180)
scale.r=crop['crop_scale'][0]/4;scale.g=crop['crop_scale'][1]/2
multiply=mel.create_material_expression(material,unreal.MaterialExpressionMultiply,-550,0)
assert mel.connect_material_expressions(uv,'',multiply,'A');assert mel.connect_material_expressions(scale,'',multiply,'B')
offset=mel.create_material_expression(material,unreal.MaterialExpressionConstant2Vector,-550,180)
offset.r=crop['crop_offset'][0]/4;offset.g=crop['crop_offset'][1]/2
add=mel.create_material_expression(material,unreal.MaterialExpressionAdd,-300,0)
assert mel.connect_material_expressions(multiply,'',add,'A');assert mel.connect_material_expressions(offset,'',add,'B')
sample=mel.create_material_expression(material,unreal.MaterialExpressionTextureSample,-60,0)
sample.texture=unreal.load_asset('/Game/Root/Assets/Textures/T_ItemEffects_Atlas')
assert mel.connect_material_expressions(add,'',sample,'UVs')
assert mel.connect_material_property(sample,'RGB',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
assert mel.connect_material_property(sample,'A',unreal.MaterialProperty.MP_OPACITY)
mel.recompile_material(material);assert assets.save_loaded_asset(material)

bp.modify()
canvas=unreal.find_object(tree,'HUDCanvas') or unreal.new_object(unreal.CanvasPanel,outer=tree,name='HUDCanvas')
canvas.clear_children()
system=unreal.get_default_object(unreal.SystemLibrary)
system.call_method('SetObjectPropertyByName',(tree,'RootWidget',canvas))
canvas.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)

def widget(cls,name,parent):
    w=unreal.find_object(tree,name) or unreal.new_object(cls,outer=tree,name=name)
    w.remove_from_parent()
    if isinstance(w,unreal.PanelWidget):w.clear_children()
    system.call_method('SetBoolPropertyByName',(w,'bIsVariable',True))
    w.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
    return w,parent.add_child(w)

def anchored(slot,ax,ay,x,y,alignx=0,aligny=0,autosize=True,size=(0,0)):
    slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(ax,ay),maximum=unreal.Vector2D(ax,ay)))
    slot.set_alignment(unreal.Vector2D(alignx,aligny));slot.set_auto_size(autosize)
    slot.set_offsets(unreal.Margin(x,y,*size))

font=unreal.SlateFontInfo(font_object=unreal.load_asset('/Engine/EngineFonts/Roboto'),size=28,typeface_font_name='Bold')
def label(name,text):
    w,s=widget(unreal.TextBlock,name,canvas)
    w.set_text(text);w.set_font(font)
    w.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor.WHITE))
    w.set_shadow_color_and_opacity(unreal.LinearColor(0,0,0,0.65));w.set_shadow_offset(unreal.Vector2D(2,2))
    return w,s
score,s=label('ScoreText','SCORE: 0');anchored(s,0,0,28,28)
timer,s=label('TimerText','01:00');timer.set_editor_property('justification',unreal.TextJustify.RIGHT);anchored(s,1,0,-28,28,1,0)
row,s=widget(unreal.HorizontalBox,'HealthRow',canvas);anchored(s,0,1,28,-28,0,1)
for i in range(3):
    box,slot=widget(unreal.SizeBox,'HeartSize'+str(i+1),row)
    box.set_width_override(64);box.set_height_override(64)
    slot.set_padding(unreal.Margin(0,0,10 if i<2 else 0,0))
    image,slot=widget(unreal.Image,'Heart'+str(i+1),box)
    image.set_brush_from_material(material)
    image.set_color_and_opacity(unreal.LinearColor.WHITE)

L.compile_blueprint(bp)
print('UMG_DESIGNER_CREATED',bp.get_path_name(),[(w.get_name(),w.get_class().get_name()) for w in [canvas,score,timer,row]])
print('UMG_VARS',list(map(str,L.list_member_variable_names(bp,include_inherited_members=False))))
print('UMG_EVENTS',[(g.get_name(),[(n.get_name(),str(L.get_node_title(n))) for n in unreal.BlueprintGraphEditor.get_graph_editor(g).list_all_nodes()]) for g in L.list_graphs(bp)])
