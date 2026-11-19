"""Adjust only fruit mesh scale, piece size and count through MCP."""
import unreal,json
from pathlib import Path

root=Path(unreal.Paths.project_dir()).resolve()
library=unreal.BlueprintEditorLibrary
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
report=[]
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None,'End PIE before resizing assets'
for fruit in ['Apple','Banana','Coconut','Orange','Pear','Pineapple','Strawberry','Watermelon']:
    bp=unreal.load_asset('/Game/Root/Blueprints/Fruits/B_Fruit_'+fruit)
    bp.modify()
    meshes={}
    for handle in sub.k2_gather_subobject_data_for_blueprint(bp):
        data=unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        mesh=unreal.SubobjectDataBlueprintFunctionLibrary.get_object_for_blueprint(data,bp)
        if isinstance(mesh,unreal.StaticMeshComponent):meshes[mesh.get_path_name()]=mesh
    assert len(meshes)==1,fruit
    mesh=next(iter(meshes.values()))
    mesh.modify()
    mesh.set_relative_scale3d(unreal.Vector(2.5,2.5,2.5))
    library.compile_blueprint(bp)
    for graph in library.list_graphs(bp):
        assert not unreal.BlueprintGraphEditor.get_graph_editor(graph).list_nodes_with_errors(),fruit
    unreal.EditorAssetLibrary.save_loaded_asset(bp)

    system=unreal.load_asset('/Game/Root/Assets/VFX/Fruits/NS_FruitPieces_'+fruit)
    system.modify()
    emitter=unreal.find_object(system,'DirectionalBurst_1')
    init=next(m for m in emitter.get_editor_property('Modules') if m.get_class().get_name()=='NiagaraStatelessModule_InitializeParticle')
    maximum=88 if fruit in ['Coconut','Pineapple','Watermelon'] else 64
    minimum=maximum*0.65
    size=init.get_editor_property('SpriteSizeDistribution').copy()
    assert size.import_text(f'(Min=(X={minimum},Y={minimum}),Max=(X={maximum},Y={maximum}),Mode=UniformRange,ChannelConstantsAndRanges=({minimum},{maximum}))')
    init.set_editor_property('SpriteSizeDistribution',size)
    spawns=list(emitter.get_editor_property('SpawnInfos'))
    spawn=spawns[0].copy()
    assert spawn.import_text('(Type=Burst,SpawnTime=0,Amount=(Min=3,Max=3,Mode=UniformConstant),bEnabled=True)')
    emitter.set_editor_property('SpawnInfos',[spawn])
    unreal.EditorAssetLibrary.save_loaded_asset(system)

    actual_size=init.get_editor_property('SpriteSizeDistribution')
    assert abs(actual_size.get_editor_property('Max').get_editor_property('X')-maximum)<0.01
    amount=emitter.get_editor_property('SpawnInfos')[0].get_editor_property('Amount')
    assert amount.get_editor_property('Min')==3 and amount.get_editor_property('Max')==3
    # Read freshly compiled child templates rather than retaining old component objects.
    for handle in sub.k2_gather_subobject_data_for_blueprint(bp):
        data=unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        component=unreal.SubobjectDataBlueprintFunctionLibrary.get_object_for_blueprint(data,bp)
        if isinstance(component,unreal.StaticMeshComponent):
            scale=component.get_editor_property('relative_scale3d')
            assert abs(scale.x-2.5)<0.001 and abs(scale.y-2.5)<0.001 and abs(scale.z-2.5)<0.001
    report.append({'fruit':fruit,'mesh_scale':2.5,'piece_size_cm':[minimum,maximum],'piece_count':3})
    print('RESIZED:'+json.dumps(report[-1]))
(root/'Saved/MCP/fruit-size-adjustment.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
library.refresh_all_open_blueprint_editors()
print('FRUIT_SIZES_SAVED:'+str(len(report)))
calibration=root/'Tools/FruitSetup/proportion_pieces.py'
exec(compile(calibration.read_text(encoding='utf-8'),str(calibration),'exec'),{'__name__':'__main__'})
