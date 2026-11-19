import unreal,json
lib=unreal.BlueprintEditorLibrary
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
print('PLAYING:'+str(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()))
for name in ['Apple','Banana','Coconut','Orange','Pear','Pineapple','Strawberry','Watermelon']:
    bp=unreal.load_asset('/Game/Root/Blueprints/Fruits/B_Fruit_'+name)
    seen=set()
    for handle in sub.k2_gather_subobject_data_for_blueprint(bp):
        data=unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        mesh=unreal.SubobjectDataBlueprintFunctionLibrary.get_object_for_blueprint(data,bp)
        if isinstance(mesh,unreal.StaticMeshComponent) and mesh.get_path_name() not in seen:
            seen.add(mesh.get_path_name())
            print('MESH:'+name+':'+str(mesh.get_editor_property('relative_scale3d')))
    system=unreal.load_asset('/Game/Root/Assets/VFX/Fruits/NS_FruitPieces_'+name)
    emitter=unreal.find_object(system,'DirectionalBurst_1')
    init=next(m for m in emitter.get_editor_property('Modules') if m.get_class().get_name()=='NiagaraStatelessModule_InitializeParticle')
    print('CHUNKS:'+name+':'+init.get_editor_property('SpriteSizeDistribution').export_text())
    print('SPAWN:'+name+':'+emitter.get_editor_property('SpawnInfos')[0].export_text())
