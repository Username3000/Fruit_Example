"""Create Heart/Clock/Bomb children and their item-specific Niagara effects via MCP."""
import unreal,json
from pathlib import Path

root=Path(unreal.Paths.project_dir()).resolve()
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None,'End PIE before authoring items'
assets=unreal.EditorAssetLibrary
tools=unreal.AssetToolsHelpers.get_asset_tools()
lib=unreal.BlueprintEditorLibrary
mel=unreal.MaterialEditingLibrary
fx='/Game/Root/Assets/VFX/Items'
matfolder='/Game/Root/Assets/Materials/ItemEffects'
folder='/Game/Root/Blueprints/Items'
for directory in [fx,matfolder,folder]:assets.make_directory(directory)
texture=unreal.load_asset('/Game/Root/Assets/Textures/T_ItemEffects_Atlas')
if not texture:
    task=unreal.AssetImportTask()
    task.filename=str(root/'SourceAssets/ItemVFX/T_ItemEffects_Atlas.png')
    task.destination_path='/Game/Root/Assets/Textures'
    task.destination_name='T_ItemEffects_Atlas'
    task.automated=True;task.save=True
    tools.import_asset_tasks([task])
    texture=unreal.load_asset('/Game/Root/Assets/Textures/T_ItemEffects_Atlas')
assert texture
texture.set_editor_property('srgb',True)
texture.set_editor_property('address_x',unreal.TextureAddress.TA_CLAMP)
texture.set_editor_property('address_y',unreal.TextureAddress.TA_CLAMP)
assets.save_loaded_asset(texture)

def create_material(name,blend):
    path=matfolder+'/'+name
    material=unreal.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(name,matfolder,unreal.Material,unreal.MaterialFactoryNew())
    material.modify()
    mel.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode',blend)
    lit=blend==unreal.BlendMode.BLEND_MASKED
    material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_DEFAULT_LIT if lit else unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided',True)
    material.set_editor_property('opacity_mask_clip_value',0.5)
    mel.set_material_usage(material,unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    def expr(cls,x,y):return mel.create_material_expression(material,cls,x,y)
    def wire(a,b,pin,out=''):
        inputs=list(mel.get_material_expression_input_names(b))
        if pin not in inputs and len(inputs)==1:pin=inputs[0]
        assert mel.connect_material_expressions(a,out,b,pin),(b.get_name(),pin,inputs)
    def constant(value,x,y):
        node=expr(unreal.MaterialExpressionConstant,x,y);node.r=value;return node
    def param(name,value,x,y):
        node=expr(unreal.MaterialExpressionScalarParameter,x,y)
        node.set_editor_property('ParameterName',name);node.set_editor_property('DefaultValue',value)
        return node
    def binary(cls,a,b,x,y):
        node=expr(cls,x,y);wire(a,node,'A');wire(b,node,'B');return node
    def append(a,b,x,y):return binary(unreal.MaterialExpressionAppendVector,a,b,x,y)
    random=expr(unreal.MaterialExpressionParticleRandom,-1900,600)
    two=constant(2,-1900,800)
    random2=binary(unreal.MaterialExpressionMultiply,random,two,-1680,600)
    variant=expr(unreal.MaterialExpressionFloor,-1480,600);wire(random2,variant,'Input')
    def choose(label,default,y):
        a=param(label+'A',default,-1900,y)
        b=param(label+'B',default,-1900,y+150)
        lerp=expr(unreal.MaterialExpressionLinearInterpolate,-1450,y)
        wire(a,lerp,'A');wire(b,lerp,'B');wire(variant,lerp,'Alpha')
        return lerp
    tile=choose('Cell',0,0)
    sx=choose('CropScaleX',1,1000);sy=choose('CropScaleY',1,1400)
    ox=choose('CropOffsetX',0,1800);oy=choose('CropOffsetY',0,2200)
    scale=append(sx,sy,-1100,1100);offset=append(ox,oy,-1100,1900)
    uv=expr(unreal.MaterialExpressionTextureCoordinate,-1100,700)
    scaled=binary(unreal.MaterialExpressionMultiply,uv,scale,-850,1000)
    cropped=binary(unreal.MaterialExpressionAdd,scaled,offset,-620,1000)
    four=constant(4,-1200,-300)
    col=binary(unreal.MaterialExpressionFmod,tile,four,-950,0)
    rowfloat=binary(unreal.MaterialExpressionDivide,tile,four,-950,200)
    row=expr(unreal.MaterialExpressionFloor,-700,200);wire(rowfloat,row,'Input')
    cell=append(col,row,-450,0)
    celluv=binary(unreal.MaterialExpressionAdd,cropped,cell,-220,300)
    atlas_scale=append(constant(0.25,-450,600),constant(0.5,-450,800),-220,700)
    atlasuv=binary(unreal.MaterialExpressionMultiply,celluv,atlas_scale,0,300)
    sample=expr(unreal.MaterialExpressionTextureSample,220,300)
    sample.texture=texture;wire(atlasuv,sample,'UVs')
    color=expr(unreal.MaterialExpressionParticleColor,220,800)
    tint=expr(unreal.MaterialExpressionMultiply,450,0)
    wire(sample,tint,'A','RGB');wire(color,tint,'B','RGB')
    strength=param('Emission',1,200,-200)
    emitted=binary(unreal.MaterialExpressionMultiply,tint,strength,700,0)
    if lit:
        assert mel.connect_material_property(tint,'',unreal.MaterialProperty.MP_BASE_COLOR)
        assert mel.connect_material_property(constant(0.8,1000,-300),'',unreal.MaterialProperty.MP_ROUGHNESS)
        assert mel.connect_material_property(constant(0.2,1200,-300),'',unreal.MaterialProperty.MP_SPECULAR)
    else:
        assert mel.connect_material_property(emitted,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    # Suppress almost-transparent colored speckles from generated alpha edges.
    alpha=expr(unreal.MaterialExpressionPower,450,400)
    wire(sample,alpha,'Base','A');wire(two,alpha,'Exp')
    particle_alpha=expr(unreal.MaterialExpressionMultiply,700,400)
    wire(alpha,particle_alpha,'A');wire(color,particle_alpha,'B','A')
    age=expr(unreal.MaterialExpressionParticleRelativeTime,200,1300)
    inverse=expr(unreal.MaterialExpressionOneMinus,450,1300);wire(age,inverse,'Input')
    fade_rate=constant(4 if blend==unreal.BlendMode.BLEND_MASKED else 1.3,450,1550)
    fade0=binary(unreal.MaterialExpressionMultiply,inverse,fade_rate,700,1300)
    fade=expr(unreal.MaterialExpressionSaturate,900,1300);wire(fade0,fade,'Input')
    opacity=binary(unreal.MaterialExpressionMultiply,particle_alpha,fade,1150,500)
    property=unreal.MaterialProperty.MP_OPACITY_MASK if blend==unreal.BlendMode.BLEND_MASKED else unreal.MaterialProperty.MP_OPACITY
    assert mel.connect_material_property(opacity,'',property)
    mel.recompile_material(material)
    assert assets.save_loaded_asset(material)
    return material

materials={
    'masked':create_material('M_ItemPieces',unreal.BlendMode.BLEND_MASKED),
    'additive':create_material('M_ExplosionGlow',unreal.BlendMode.BLEND_ADDITIVE),
    'smoke':create_material('M_ExplosionSmoke',unreal.BlendMode.BLEND_TRANSLUCENT),
}
bounds=json.loads((root/'SourceAssets/ItemVFX/chunk_uv_bounds.json').read_text(encoding='utf-8'))
def instance(name,kind,cells,emission=1):
    asset_name='MI_'+name
    path=matfolder+'/'+asset_name
    result=unreal.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(asset_name,matfolder,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(result,materials[kind])
    for cell,suffix in zip(cells,['A','B']):
        row=bounds[cell]
        values={'Cell':cell,'CropScaleX':row['crop_scale'][0],'CropScaleY':row['crop_scale'][1],'CropOffsetX':row['crop_offset'][0],'CropOffsetY':row['crop_offset'][1]}
        for key,value in values.items():
            mel.set_material_instance_scalar_parameter_value(result,key+suffix,value)
            assert abs(mel.get_material_instance_scalar_parameter_value(result,key+suffix)-value)<0.0001
    mel.set_material_instance_scalar_parameter_value(result,'Emission',emission)
    assert assets.save_loaded_asset(result)
    return result

def edit(obj,prop,text):
    value=obj.get_editor_property(prop).copy();assert value.import_text(text),prop
    obj.set_editor_property(prop,value)
def scalar(obj,prop,a,b=None):
    b=a if b is None else b
    mode='UniformConstant' if a==b else 'UniformRange'
    constants=str(a) if a==b else f'{a},{b}'
    edit(obj,prop,f'(Min={a},Max={b},Mode={mode},ChannelConstantsAndRanges=({constants}))')
def vec(obj,prop,a,b=None):
    b=a if b is None else b
    mode='NonUniformConstant' if a==b else 'NonUniformRange'
    constants=','.join(map(str,a if a==b else a+b))
    edit(obj,prop,f'(Min=(X={a[0]},Y={a[1]},Z={a[2]}),Max=(X={b[0]},Y={b[1]},Z={b[2]}),Mode={mode},ChannelConstantsAndRanges=({constants}))')
def module(emitter,kind):return next(m for m in emitter.get_editor_property('Modules') if m.get_class().get_name()=='NiagaraStatelessModule_'+kind)
def size_curve(obj,prop,begin,end):
    edit(obj,prop,f'(Mode=UniformCurve,ChannelCurves=((Keys=((Time=0,Value={begin}),(Time=1,Value={end})))),ChannelConstantsAndRanges=(1))')

configs=[
    dict(name='HeartMiniHearts',kind='masked',cells=[0,1],count=7,life=[2.8,4.2],size=[0.32,0.44],radius=20,gravity=120,drag=0.22,inherit=True,accel=[[-130,-130,120],[130,130,260]],spin=35),
    dict(name='ClockPieces',kind='masked',cells=[2,3],count=4,life=[2.2,4.2],size=[0.8,1.05],radius=30,gravity=650,drag=0.08,inherit=True,accel=[[-500,-500,-100],[500,500,400]],spin=320),
    dict(name='BombFlash',kind='additive',cells=[6,6],count=1,life=[0.12,0.18],size=[4.2,4.2],radius=0,gravity=0,drag=0,velocity=[[0,0,0],[0,0,0]],spin=0,emission=4),
    dict(name='BombFire',kind='additive',cells=[4,4],count=8,life=[0.4,0.8],size=[1.25,1.25],grow=[0.45,1.8],radius=8,gravity=0,drag=0.7,velocity=[[-240,-240,-140],[240,240,280]],spin=90,emission=2.2),
    dict(name='BombSmoke',kind='smoke',cells=[5,5],count=6,life=[1.8,3.2],size=[1.4,1.4],grow=[0.4,2.0],radius=18,gravity=-40,drag=0.8,velocity=[[-100,-100,80],[100,100,210]],spin=40),
    dict(name='BombShockwave',kind='additive',cells=[7,7],count=1,life=[0.3,0.45],size=[4.4,4.4],grow=[0.15,1.5],radius=0,gravity=0,drag=0,velocity=[[0,0,0],[0,0,0]],spin=0,emission=2),
    dict(name='BombSparks',kind='additive',cells=[6,6],count=12,life=[0.55,1.0],size=[0.08,0.16],radius=4,gravity=600,drag=0.1,velocity=[[-650,-650,-150],[650,650,650]],spin=450,emission=5),
]
template=unreal.load_asset('/Game/Root/Assets/VFX/Fruits/NS_FruitPieces_Apple')
systems={}
for config in configs:
    name=config['name'];path=fx+'/NS_'+name
    system=unreal.load_asset(path) if assets.does_asset_exist(path) else assets.duplicate_asset(template.get_path_name(),path)
    system.modify()
    emitter=unreal.find_object(system,'DirectionalBurst_1')
    init=module(emitter,'InitializeParticle')
    # User.PieceSize is already 70% of the mesh's camera-plane size in B_FruitBase.
    scalar(init,'LifetimeDistribution',*config['life'])
    scalar(init,'SpriteRotationDistribution',-18 if name=='HeartMiniHearts' else -180,18 if name=='HeartMiniHearts' else 180)
    count=config['count']
    spawn=emitter.get_editor_property('SpawnInfos')[0].copy()
    assert spawn.import_text(f'(Type=Burst,SpawnTime=0,Amount=(Min={count},Max={count},Mode=UniformConstant),bEnabled=True)')
    emitter.set_editor_property('SpawnInfos',[spawn])
    scale=module(emitter,'ScaleSpriteSize');scale.set_editor_property('bModuleEnabled',True)
    if 'grow' in config:size_curve(scale,'ScaleDistribution',*config['grow'])
    else:
        a,b=config['size']
        edit(scale,'ScaleDistribution',f'(Mode=UniformRange,Min=(X={a},Y={a}),Max=(X={b},Y={b}),ChannelConstantsAndRanges=({a},{b}))')
    if 'grow' in config:
        # The growth curve includes each layer's base size relative to User.PieceSize.
        a,b=[v*config['size'][0] for v in config['grow']]
        size_curve(scale,'ScaleDistribution',a,b)
    shape=module(emitter,'ShapeLocation');shape.set_editor_property('bModuleEnabled',True)
    scalar(shape,'SphereRadius',config['radius'])
    velocity=module(emitter,'AddVelocity');velocity.set_editor_property('bModuleEnabled',True)
    if not config.get('inherit'):
        vec(velocity,'LinearVelocityDistribution',*config['velocity'])
    force=module(emitter,'AccelerationForce')
    force.set_editor_property('bModuleEnabled','accel' in config)
    if 'accel' in config:vec(force,'AccelerationDistribution',*config['accel'])
    vec(module(emitter,'GravityForce'),'GravityDistribution',[0,0,-config['gravity']])
    scalar(module(emitter,'Drag'),'DragDistribution',config['drag'])
    spin=module(emitter,'SpriteRotationRate');spin.set_editor_property('bModuleEnabled',bool(config['spin']))
    scalar(spin,'RotationRateDistribution',-config['spin'],config['spin'])
    module(emitter,'ScaleColor').set_editor_property('bModuleEnabled',False)
    renderer=unreal.find_object(emitter,'Renderer')
    renderer.set_editor_property('material',instance(name,config['kind'],config['cells'],config.get('emission',1)))
    renderer.set_editor_property('alignment',unreal.NiagaraSpriteAlignment.UNALIGNED)
    emitter.set_editor_property('FixedBounds',unreal.Box(unreal.Vector(-6000,-6000,-6000),unreal.Vector(6000,6000,6000)))
    # Rebuild stateless runtime data after editing the nested modules.
    emitter.set_editor_property('Modules',list(emitter.get_editor_property('Modules')))
    assert assets.save_loaded_asset(system)
    systems[name]=system
    print('ITEM_EFFECT:'+name+':'+str(count)+':'+init.get_editor_property('LifetimeDistribution').export_text())

base=unreal.load_asset('/Game/Root/Blueprints/B_FruitBase')
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
blueprints={}
for item,effect in [('Heart','HeartMiniHearts'),('Clock','ClockPieces'),('Bomb','BombFire')]:
    path=folder+'/B_Item_'+item
    bp=unreal.load_asset(path) if assets.does_asset_exist(path) else None
    if not bp:
        factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',lib.generated_class(base))
        bp=tools.create_asset('B_Item_'+item,folder,unreal.Blueprint,factory)
    bp.modify();lib.compile_blueprint(bp)
    meshes={}
    for handle in sub.k2_gather_subobject_data_for_blueprint(bp):
        data=unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        component=unreal.SubobjectDataBlueprintFunctionLibrary.get_object_for_blueprint(data,bp)
        if isinstance(component,unreal.StaticMeshComponent):meshes[component.get_path_name()]=component
    assert len(meshes)==1,item
    component=next(iter(meshes.values()))
    component.set_static_mesh(unreal.load_asset('/Game/Root/Assets/Meshes/Items/SM_'+item))
    component.set_editor_property('override_materials',[])
    component.set_relative_scale3d(unreal.Vector(2.5,2.5,2.5))
    lib.compile_blueprint(bp)
    cdo=unreal.get_default_object(lib.generated_class(bp))
    cdo.set_editor_property('FruitBurstSystem',systems[effect])
    blueprints[item]=bp
    assert assets.save_loaded_asset(bp)

# The bomb overrides only the effect function. Its inherited Damage still calls
# the effect and then destroys the actor. All five detached layers auto-destroy.
bp=blueprints['Bomb']
graph=lib.add_function_override(bp,'SpawnFruitPieces');assert graph
editor=unreal.BlueprintGraphEditor.get_graph_editor(graph)
editor.remove_nodes([n for n in editor.list_all_nodes() if not isinstance(n,unreal.K2Node_FunctionEntry)])
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
mesh=editor.add_get_member_variable_node('Mesh');lib.set_node_pos(mesh,unreal.IntPoint(0,700))
component_bounds=call('/Script/Engine.KismetSystemLibrary.GetComponentBounds',250,700)
link(out(mesh,'Mesh'),inp(component_bounds,'Component'))
camera=call('/Script/Engine.GameplayStatics.GetPlayerCameraManager',0,1100)
rotation=call('/Script/Engine.PlayerCameraManager.GetCameraRotation',250,1100)
link(out(camera),lib.find_self_pin(rotation))
extents=[]
for direction,y in [('Right',1100),('Up',1450)]:
    axis=call('/Script/Engine.KismetMathLibrary.Get'+direction+'Vector',500,y);link(out(rotation),inp(axis,'InRot'))
    absolute=call('/Script/Engine.KismetMathLibrary.Vector_GetAbs',750,y);link(out(axis),inp(absolute,'A'))
    dot=call('/Script/Engine.KismetMathLibrary.Dot_VectorVector',1000,y)
    link(out(component_bounds,'BoxExtent'),inp(dot,'A'));link(out(absolute),inp(dot,'B'));extents.append(dot)
maximum=call('/Script/Engine.KismetMathLibrary.FMax',1250,1100)
link(out(extents[0]),inp(maximum,'A'));link(out(extents[1]),inp(maximum,'B'))
diameter=call('/Script/Engine.KismetMathLibrary.Multiply_DoubleDouble',1450,1100)
link(out(maximum),inp(diameter,'A'));assert inp(diameter,'B').set_pin_value('1.4')
vec2=call('/Script/Engine.KismetMathLibrary.MakeVector2D',1650,1100)
link(out(diameter),inp(vec2,'X'));link(out(diameter),inp(vec2,'Y'))
previous=editor.find_graph_entry_pin()
for index,name in enumerate(['BombFlash','BombFire','BombSmoke','BombShockwave','BombSparks']):
    x=index*1200
    spawn=call('/Script/Niagara.NiagaraFunctionLibrary.SpawnSystemAtLocation',x,0)
    link(previous,lib.find_execute_pin(spawn))
    assert inp(spawn,'SystemTemplate').set_pin_value(systems[name].get_path_name())
    link(out(component_bounds,'Origin'),inp(spawn,'Location'))
    for key,value in [('bAutoActivate','false'),('bAutoDestroy','true'),('bPreCullCheck','false'),('Scale','1,1,1')]:
        assert inp(spawn,key).set_pin_value(value)
    valid=call('/Script/Engine.KismetSystemLibrary.IsValid',x+350,400)
    link(out(spawn),inp(valid,'Object'))
    branch=editor.add_branch_node();lib.set_node_pos(branch,unreal.IntPoint(x+350,0))
    link(lib.find_then_pin(spawn),lib.find_execute_pin(branch));link(out(valid),lib.find_condition_pin(branch))
    size=call('/Script/Niagara.NiagaraComponent.SetNiagaraVariableVec2',x+600,0)
    link(lib.find_then_pin(branch),lib.find_execute_pin(size));link(out(spawn),lib.find_self_pin(size))
    assert inp(size,'InVariableName').set_pin_value('User.PieceSize');link(out(vec2),inp(size,'InValue'))
    activate=call('/Script/Engine.ActorComponent.Activate',x+950,0)
    link(lib.find_then_pin(size),lib.find_execute_pin(activate));link(out(spawn),lib.find_self_pin(activate))
    assert inp(activate,'bReset').set_pin_value('true')
    previous=lib.find_then_pin(activate)
    editor.add_comment_node(name+': detached, scaled to the bomb, auto-destroy.',unreal.Vector2D(x-50,-150),unreal.Vector2D(1180,750))
lib.compile_blueprint(bp)
assert not editor.list_nodes_with_errors(),'Bomb effect graph failed to compile'
assert assets.save_loaded_asset(bp)

report=[]
for item,bp in blueprints.items():
    lib.compile_blueprint(bp)
    assert lib.get_blueprint_parent_class(bp)==lib.generated_class(base)
    for graph in lib.list_graphs(bp):assert not unreal.BlueprintGraphEditor.get_graph_editor(graph).list_nodes_with_errors()
    assert assets.save_loaded_asset(bp)
    report.append({'item':item,'blueprint':bp.get_path_name(),'effect':unreal.get_default_object(lib.generated_class(bp)).get_editor_property('FruitBurstSystem').get_path_name()})
(root/'Saved/MCP/item-setup.json').write_text(json.dumps({'blueprints':report,'effects':configs},indent=2),encoding='utf-8')
lib.refresh_all_open_blueprint_editors()
assets.sync_browser_to_objects([bp.get_path_name() for bp in blueprints.values()])
print('ITEM_BLUEPRINTS_SAVED:'+str(len(report)))
# Duplicated systems also need their system VM scripts compiled, independently
# of the lightweight emitter's module cache. Save compiled assets afterward.
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world,'fx.RebuildDirtyScripts')
print('ITEM_COMPILATION_REQUESTED')
