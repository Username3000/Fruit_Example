"""Calibrate visible chunk size and bind it to the damaged mesh's camera-plane bounds."""
import unreal, json
from pathlib import Path

root=Path(unreal.Paths.project_dir()).resolve()
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None,'End PIE before editing'
names=['Apple','Banana','Coconut','Orange','Pear','Pineapple','Strawberry','Watermelon']
lib=unreal.BlueprintEditorLibrary

# Crop each atlas cell in the material so transparent margins do not shrink
# the visible fragment. Separate bounds keep both variants equally large.
material=unreal.load_asset('/Game/Root/Assets/Materials/M_FruitChunks')
material.modify()
expressions=list(unreal.MaterialEditingLibrary.get_material_expressions(material)) if hasattr(unreal.MaterialEditingLibrary,'get_material_expressions') else [o for o in unreal.ObjectIterator(unreal.MaterialExpression) if o.get_outer()==material]
params=[e for e in expressions if isinstance(e,unreal.MaterialExpressionScalarParameter)]
if not any(str(p.get_editor_property('ParameterName'))=='ChunkCropScaleA' for p in params):
    uv=next(e for e in expressions if isinstance(e,unreal.MaterialExpressionTextureCoordinate))
    variant=next(e for e in expressions if isinstance(e,unreal.MaterialExpressionFloor) and e.get_editor_property('material_expression_editor_x') < -1000)
    cell_uv=next(e for e in expressions if isinstance(e,unreal.MaterialExpressionAdd) and e.get_editor_property('material_expression_editor_x')==-250)
    def expr(cls,x,y):return unreal.MaterialEditingLibrary.create_material_expression(material,cls,x,y)
    def wire(a,out,b,pin):
        inputs=list(unreal.MaterialEditingLibrary.get_material_expression_input_names(b))
        if pin not in inputs and len(inputs)==1:pin=inputs[0]
        assert unreal.MaterialEditingLibrary.connect_material_expressions(a,out,b,pin),(b.get_name(),pin,inputs)
    def interpolated(label,default,y):
        a=expr(unreal.MaterialExpressionScalarParameter,-1400,y)
        b=expr(unreal.MaterialExpressionScalarParameter,-1400,y+150)
        for node,suffix in [(a,'A'),(b,'B')]:
            node.set_editor_property('ParameterName','ChunkCrop'+label+suffix)
            node.set_editor_property('DefaultValue',default)
        lerp=expr(unreal.MaterialExpressionLinearInterpolate,-1100,y)
        wire(a,'',lerp,'A');wire(b,'',lerp,'B');wire(variant,'',lerp,'Alpha')
        return lerp
    scale=interpolated('Scale',1,850)
    ox=interpolated('OffsetX',0,1200)
    oy=interpolated('OffsetY',0,1550)
    offset=expr(unreal.MaterialExpressionAppendVector,-800,1300)
    wire(ox,'',offset,'A');wire(oy,'',offset,'B')
    mul=expr(unreal.MaterialExpressionMultiply,-750,850)
    wire(uv,'',mul,'A');wire(scale,'',mul,'B')
    crop=expr(unreal.MaterialExpressionAdd,-500,850)
    wire(mul,'',crop,'A');wire(offset,'',crop,'B')
    wire(crop,'',cell_uv,'A')
unreal.MaterialEditingLibrary.recompile_material(material)
assert unreal.EditorAssetLibrary.save_loaded_asset(material)
bounds=json.loads((root/'SourceAssets/FruitVFX/chunk_uv_bounds.json').read_text(encoding='utf-8'))
for index,fruit in enumerate(names):
    instance=unreal.load_asset('/Game/Root/Assets/Materials/FruitChunks/MI_FruitChunks_'+fruit)
    for offset,suffix in [(0,'A'),(1,'B')]:
        row=bounds[index*2+offset]
        for label,key in [('Scale','scale'),('OffsetX','offset_x'),('OffsetY','offset_y')]:
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instance,'ChunkCrop'+label+suffix,row[key])
            actual=unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(instance,'ChunkCrop'+label+suffix)
            assert abs(actual-row[key])<0.0001,('Crop parameter',fruit,label,suffix,actual,row[key])
    assert unreal.EditorAssetLibrary.save_loaded_asset(instance)
print('ATLAS_CROPPING_SAVED')

# Add camera-plane size calculation to the existing base function, retaining
# existing movement and Damage wiring. Set the vector2 binding before Activate.
bp=unreal.load_asset('/Game/Root/Blueprints/B_FruitBase')
bp.modify()
editor=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'SpawnFruitPieces')
nodes=list(editor.list_all_nodes())
def title(n):return str(lib.get_node_title(n))
def inp(n,name):
    p=lib.find_input_pin(n,name);assert p.is_valid(),n.get_name()+'.'+name
    return p
def out(n,name='ReturnValue'):
    p=lib.find_output_pin(n,name);assert p.is_valid(),n.get_name()+'.'+name
    return p
def link(a,b):assert a.try_create_connection(b),str(a.get_pin_name())+'->'+str(b.get_pin_name())
def call(path,x,y):
    n=editor.add_call_function_node(path);assert n,path
    lib.set_node_pos(n,unreal.IntPoint(x,y));return n
if not any('Vector2' in title(n) and 'Set Niagara' in title(n) for n in nodes):
    component_bounds=next(n for n in nodes if title(n)=='GetComponentBounds')
    spawn=next(n for n in nodes if title(n)=='SpawnSystemAtLocation')
    activate=next(n for n in nodes if title(n)=='Activate')
    camera=call('/Script/Engine.GameplayStatics.GetPlayerCameraManager',0,1100)
    rotation=call('/Script/Engine.PlayerCameraManager.GetCameraRotation',250,1100)
    link(out(camera),lib.find_self_pin(rotation))
    extents=[]
    for direction,y in [('Right',1000),('Up',1400)]:
        axis=call('/Script/Engine.KismetMathLibrary.Get'+direction+'Vector',500,y)
        link(out(rotation),inp(axis,'InRot'))
        absolute=call('/Script/Engine.KismetMathLibrary.Vector_GetAbs',750,y)
        link(out(axis),inp(absolute,'A'))
        dot=call('/Script/Engine.KismetMathLibrary.Dot_VectorVector',1000,y)
        link(out(component_bounds,'BoxExtent'),inp(dot,'A'));link(out(absolute),inp(dot,'B'))
        extents.append(dot)
    maximum=call('/Script/Engine.KismetMathLibrary.FMax',1250,1100)
    link(out(extents[0]),inp(maximum,'A'));link(out(extents[1]),inp(maximum,'B'))
    diameter=call('/Script/Engine.KismetMathLibrary.Multiply_DoubleDouble',1450,1100)
    link(out(maximum),inp(diameter,'A'))
    assert inp(diameter,'B').set_pin_value('1.4') # 2 * half-extent * 70%.
    vec2=call('/Script/Engine.KismetMathLibrary.MakeVector2D',1650,1100)
    link(out(diameter),inp(vec2,'X'));link(out(diameter),inp(vec2,'Y'))
    set_size=call('/Script/Niagara.NiagaraComponent.SetNiagaraVariableVec2',1650,350)
    assert inp(set_size,'InVariableName').set_pin_value('User.PieceSize')
    link(out(vec2),inp(set_size,'InValue'));link(out(spawn),lib.find_self_pin(set_size))
    old=list(lib.find_execute_pin(activate).list_connected_pins());assert len(old)==1
    lib.find_execute_pin(activate).break_pin_links()
    link(old[0],lib.find_execute_pin(set_size));link(lib.find_then_pin(set_size),lib.find_execute_pin(activate))
    lib.set_node_pos(activate,unreal.IntPoint(2100,0))
    editor.add_comment_node('Visible piece size = 70% of mesh size in camera plane. Atlas margins are cropped in material. Set size before activation.',unreal.Vector2D(-80,900),unreal.Vector2D(2100,950))
lib.compile_blueprint(bp)
assert not editor.list_nodes_with_errors(),'Base size calculation failed to compile'
assert unreal.EditorAssetLibrary.save_loaded_asset(bp)
print('DYNAMIC_PIECE_SIZE_SAVED')

report=[]
for fruit in names:
    system=unreal.load_asset('/Game/Root/Assets/VFX/Fruits/NS_FruitPieces_'+fruit)
    emitter=unreal.find_object(system,'DirectionalBurst_1')
    data=json.loads(unreal.JsonObjectGraphFunctionLibrary.stringify([emitter],unreal.JsonStringifyOptions()))['__RootObjects'][0]
    vec2type=next(v['TypeDefHandle']['RegisteredTypeIndex'] for v in data['ParticleDataSetCompiledData']['Variables'] if v['Name']=='SpriteSize')
    init=next(m for m in emitter.get_editor_property('Modules') if m.get_class().get_name()=='NiagaraStatelessModule_InitializeParticle')
    system.modify();init.modify()
    size=init.get_editor_property('SpriteSizeDistribution').copy()
    assert size.import_text(f'(Mode=Binding,ParameterBinding=(Name="User.PieceSize",TypeDefHandle=(RegisteredTypeIndex={vec2type})))')
    init.set_editor_property('SpriteSizeDistribution',size)
    lifetime=init.get_editor_property('LifetimeDistribution').copy()
    assert lifetime.import_text('(Min=2.2,Max=4.2,Mode=UniformRange,ChannelConstantsAndRanges=(2.2,4.2))')
    init.set_editor_property('LifetimeDistribution',lifetime)
    # Keep initialized size over life; pineapple deliberately uses half-size pieces.
    for module in emitter.get_editor_property('Modules'):
        if module.get_class().get_name()=='NiagaraStatelessModule_ScaleSpriteSize' and fruit=='Pineapple':
            scale=module.get_editor_property('ScaleDistribution').copy()
            assert scale.import_text('(Mode=UniformConstant,ChannelConstantsAndRanges=(0.5))')
            module.set_editor_property('ScaleDistribution',scale)
            module.set_editor_property('bModuleEnabled',True)
        elif module.get_class().get_name() in ['NiagaraStatelessModule_ScaleSpriteSize','NiagaraStatelessModule_ScaleSpriteSizeBySpeed']:
            module.set_editor_property('bModuleEnabled',False)
    # Nested Python property changes do not notify the owning emitter's runtime
    # cache. Notify it after all module edits so PIE uses the new distributions.
    emitter.set_editor_property('Modules',list(emitter.get_editor_property('Modules')))
    assert unreal.EditorAssetLibrary.save_loaded_asset(system)
    assert str(init.get_editor_property('SpriteSizeDistribution').get_editor_property('ParameterBinding').get_editor_property('Name'))=='User.PieceSize'
    actual=init.get_editor_property('LifetimeDistribution')
    assert abs(actual.get_editor_property('Min')-2.2)<0.01 and abs(actual.get_editor_property('Max')-4.2)<0.01
    report.append({'fruit':fruit,'visible_piece_fraction':0.35 if fruit=='Pineapple' else 0.7,'lifetime_seconds':[2.2,4.2]})
    child=unreal.load_asset('/Game/Root/Blueprints/Fruits/B_Fruit_'+fruit)
    lib.compile_blueprint(child)
    assert unreal.EditorAssetLibrary.save_loaded_asset(child)
    print('PROPORTIONAL:'+json.dumps(report[-1]))
(root/'Saved/MCP/fruit-proportions.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
lib.refresh_all_open_blueprint_editors()
print('FRUIT_PROPORTIONS_SAVED:'+str(len(report)))
