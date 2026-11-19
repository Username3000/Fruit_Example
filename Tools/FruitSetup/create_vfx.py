"""Create eight fruit-specific Niagara bursts through the editor's Python API."""
import unreal, json
from pathlib import Path

root = Path(unreal.Paths.project_dir()).resolve()
fx = '/Game/Root/Assets/VFX/Fruits'
tex_path = '/Game/Root/Assets/Textures/T_FruitChunks_Atlas'
mat_path = '/Game/Root/Assets/Materials/M_FruitChunks'
tools = unreal.AssetToolsHelpers.get_asset_tools()
unreal.EditorAssetLibrary.make_directory(fx)

texture = unreal.load_asset(tex_path)
if not texture:
    task = unreal.AssetImportTask()
    task.filename = str(root/'SourceAssets/FruitVFX/T_FruitChunks_Atlas.png')
    task.destination_path = '/Game/Root/Assets/Textures'
    task.destination_name = 'T_FruitChunks_Atlas'
    task.automated = True
    task.save = True
    tools.import_asset_tasks([task])
    texture = unreal.load_asset(tex_path)
texture.set_editor_property('srgb', True)
texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_DEFAULT)
texture.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
texture.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)

material = unreal.load_asset(mat_path)
if True:
    if not material:
        material = tools.create_asset('M_FruitChunks', '/Game/Root/Assets/Materials', unreal.Material, unreal.MaterialFactoryNew())
    else:
        unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    material.set_editor_property('two_sided', True)
    material.set_editor_property('opacity_mask_clip_value', 0.5)
    unreal.MaterialEditingLibrary.set_material_usage(material, unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    def expr(cls,x,y):
        return unreal.MaterialEditingLibrary.create_material_expression(material,cls,x,y)
    def wire(source,output,dest,input_name):
        inputs=list(unreal.MaterialEditingLibrary.get_material_expression_input_names(dest))
        if input_name not in inputs and len(inputs)==1:
            input_name=inputs[0]
        assert unreal.MaterialEditingLibrary.connect_material_expressions(source,output,dest,input_name), dest.get_class().get_name()+':'+str(inputs)
    def constant(value,x,y):
        node=expr(unreal.MaterialExpressionConstant,x,y)
        node.r=value
        return node
    def binary(cls,a,b,x,y):
        node=expr(cls,x,y)
        wire(a,'',node,'A')
        wire(b,'',node,'B')
        return node
    # Each Niagara particle supplies stable MaterialRandom. Choose one of its
    # fruit's two atlas cells here, rather than animate SubImageIndex over life.
    fruit_index=expr(unreal.MaterialExpressionScalarParameter,-1900,0)
    fruit_index.set_editor_property('ParameterName','FruitIndex')
    fruit_index.set_editor_property('DefaultValue',0)
    random=expr(unreal.MaterialExpressionParticleRandom,-1900,300)
    two=constant(2,-1900,500)
    four=constant(4,-1300,600)
    quarter=constant(0.25,-700,600)
    fruit_base=binary(unreal.MaterialExpressionMultiply,fruit_index,two,-1650,0)
    random_two=binary(unreal.MaterialExpressionMultiply,random,two,-1650,300)
    variant=expr(unreal.MaterialExpressionFloor,-1430,300)
    wire(random_two,'',variant,'Input')
    tile=binary(unreal.MaterialExpressionAdd,fruit_base,variant,-1200,0)
    col=binary(unreal.MaterialExpressionFmod,tile,four,-950,0)
    row_float=binary(unreal.MaterialExpressionDivide,tile,four,-950,200)
    row=expr(unreal.MaterialExpressionFloor,-730,200)
    wire(row_float,'',row,'Input')
    offset=expr(unreal.MaterialExpressionAppendVector,-500,0)
    wire(col,'',offset,'A')
    wire(row,'',offset,'B')
    uv=expr(unreal.MaterialExpressionTextureCoordinate,-500,-220)
    cell_uv=binary(unreal.MaterialExpressionAdd,uv,offset,-250,0)
    atlas_uv=binary(unreal.MaterialExpressionMultiply,cell_uv,quarter,0,0)
    sample = expr(unreal.MaterialExpressionTextureSample, 220, 0)
    sample.texture = texture
    wire(atlas_uv,'',sample,'UVs')
    color = expr(unreal.MaterialExpressionParticleColor,220,350)
    multiply = expr(unreal.MaterialExpressionMultiply,550,250)
    assert unreal.MaterialEditingLibrary.connect_material_expressions(sample, 'A', multiply, 'A')
    assert unreal.MaterialEditingLibrary.connect_material_expressions(color, 'A', multiply, 'B')
    unreal.MaterialEditingLibrary.connect_material_property(sample, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
    unreal.MaterialEditingLibrary.connect_material_property(constant(0.8,800,600), '', unreal.MaterialProperty.MP_ROUGHNESS)
    unreal.MaterialEditingLibrary.connect_material_property(constant(0.2,800,800), '', unreal.MaterialProperty.MP_SPECULAR)
    unreal.MaterialEditingLibrary.connect_material_property(multiply, '', unreal.MaterialProperty.MP_OPACITY_MASK)
    unreal.MaterialEditingLibrary.recompile_material(material)

def struct_edit(obj, prop, text):
    value = obj.get_editor_property(prop).copy()
    assert value.import_text(text), prop + ':' + text
    obj.set_editor_property(prop, value)

def module(emitter, kind):
    return next(m for m in emitter.get_editor_property('Modules') if m.get_class().get_name()=='NiagaraStatelessModule_'+kind)

def scalar_range(obj, prop, low, high):
    struct_edit(obj, prop, f'(Min={low},Max={high},Mode=UniformRange,ChannelConstantsAndRanges=({low},{high}))')

template = unreal.load_asset('/Niagara/DefaultAssets/Templates/Systems/DirectionalBurstLightweight')
fruit_names = ['Apple','Banana','Coconut','Orange','Pear','Pineapple','Strawberry','Watermelon']
for index, name in enumerate(fruit_names):
    path = fx + '/NS_FruitPieces_' + name
    system = unreal.load_asset(path)
    if not system:
        system = unreal.EditorAssetLibrary.duplicate_asset(template.get_path_name(), path)
    assert system
    emitter = unreal.find_object(system, 'DirectionalBurst_1')
    assert emitter
    init = module(emitter, 'InitializeParticle')
    scalar_range(init, 'LifetimeDistribution', 2.2, 4.2)
    scalar_range(init, 'SpriteRotationDistribution', -180, 180)
    size = 88 if name in ['Coconut','Pineapple','Watermelon'] else 64
    struct_edit(init, 'SpriteSizeDistribution', f'(Min=(X={size*0.65},Y={size*0.65}),Max=(X={size},Y={size}),Mode=UniformRange,ChannelConstantsAndRanges=({size*0.65},{size}))')

    spawns = list(emitter.get_editor_property('SpawnInfos'))
    spawn = spawns[0].copy()
    assert spawn.import_text('(Type=Burst,SpawnTime=0,Amount=(Min=3,Max=3,Mode=UniformConstant),bEnabled=True)')
    emitter.set_editor_property('SpawnInfos', [spawn])

    # Stateless templates allow one instance of each module class and deduplicate
    # them on load. Keep ONE AddVelocity, then scatter with position/acceleration.
    modules=list(emitter.get_editor_property('Modules'))
    velocity_modules=[m for m in modules if m.get_class().get_name()=='NiagaraStatelessModule_AddVelocity']
    inherited=next((m for m in velocity_modules if m.get_name()=='FruitInheritedVelocity'),None)
    if inherited is None:
        # A fresh AddVelocity module defaults to Linear in the installed engine.
        inherited=unreal.new_object(velocity_modules[0].get_class(),emitter,'FruitInheritedVelocity')
        modules.insert(modules.index(velocity_modules[0]),inherited)
    emitter.set_editor_property('Modules',[m for m in modules if m not in velocity_modules or m==inherited])
    if inherited.get_name()!='FruitInheritedVelocity':
        assert inherited.rename('FruitInheritedVelocity',emitter)
    # SpawnFruitPieces uses identity rotation/scale, so local and world vectors
    # coincide; this preserves the original CurrentVelocity exactly.
    inherited.set_editor_property('bModuleEnabled', True)
    # Vec3 type handle is copied from a real FVector property in this loaded system.
    vector_type = json.loads(unreal.JsonObjectGraphFunctionLibrary.stringify([emitter],unreal.JsonStringifyOptions()))['__RootObjects'][0]['ParticleDataSetCompiledData']['Variables']
    vec_index = next(v['TypeDefHandle']['RegisteredTypeIndex'] for v in vector_type if v['Name']=='Velocity')
    struct_edit(inherited,'LinearVelocityDistribution', f'(Mode=Binding,ParameterBinding=(Name="User.InheritedVelocity",TypeDefHandle=(RegisteredTypeIndex={vec_index})))')

    shape=module(emitter,'ShapeLocation')
    shape.set_editor_property('bModuleEnabled',True)
    struct_edit(shape,'SphereRadius','(Min=40,Max=40,Mode=UniformConstant,ChannelConstantsAndRanges=(40))')
    scatter=module(emitter,'AccelerationForce')
    scatter.set_editor_property('bModuleEnabled',True)
    struct_edit(scatter,'AccelerationDistribution','(Min=(X=-650,Y=-650,Z=-300),Max=(X=650,Y=650,Z=500),Mode=NonUniformRange,ChannelConstantsAndRanges=(-650,-650,-300,650,650,500))')

    gravity = module(emitter, 'GravityForce')
    struct_edit(gravity,'GravityDistribution','(Min=(X=0,Y=0,Z=-850),Max=(X=0,Y=0,Z=-850),Mode=NonUniformConstant,ChannelConstantsAndRanges=(0,0,-850))')
    scalar_range(module(emitter,'Drag'), 'DragDistribution', 0.05, 0.12)
    rotation = module(emitter,'SpriteRotationRate')
    rotation.set_editor_property('bModuleEnabled', True)
    scalar_range(rotation, 'RotationRateDistribution', -400, 400)
    subuv = module(emitter, 'SubUVAnimation')
    subuv.set_editor_property('bModuleEnabled', False)

    instance_path='/Game/Root/Assets/Materials/FruitChunks/MI_FruitChunks_'+name
    instance=unreal.load_asset(instance_path) if unreal.EditorAssetLibrary.does_asset_exist(instance_path) else None
    if not instance:
        unreal.EditorAssetLibrary.make_directory('/Game/Root/Assets/Materials/FruitChunks')
        instance=tools.create_asset('MI_FruitChunks_'+name,'/Game/Root/Assets/Materials/FruitChunks',unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    unreal.MaterialEditingLibrary.set_material_instance_parent(instance,material)
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instance,'FruitIndex',index)
    unreal.EditorAssetLibrary.save_loaded_asset(instance)

    renderer = unreal.find_object(emitter,'Renderer')
    renderer.set_editor_property('material', instance)
    renderer.set_editor_property('alignment', unreal.NiagaraSpriteAlignment.UNALIGNED)
    renderer.set_editor_property('sub_image_size', unreal.Vector2D(1,1))
    renderer.set_editor_property('sub_image_blend', False)
    emitter.set_editor_property('FixedBounds', unreal.Box(unreal.Vector(-3000,-3000,-3000),unreal.Vector(3000,3000,3000)))
    unreal.EditorAssetLibrary.save_loaded_asset(system)
    print('FRUIT_SYSTEM:' + name + ':' + system.get_path_name())

unreal.EditorAssetLibrary.save_loaded_asset(texture)
unreal.EditorAssetLibrary.save_loaded_asset(material)
print('FRUIT_VFX_CREATED')
base=unreal.load_asset('/Game/Root/Blueprints/B_FruitBase')
if base and unreal.BlueprintEditorLibrary.find_graph(base,'SpawnFruitPieces'):
    calibration=root/'Tools/FruitSetup/proportion_pieces.py'
    exec(compile(calibration.read_text(encoding='utf-8'),str(calibration),'exec'),{'__name__':'__main__'})
