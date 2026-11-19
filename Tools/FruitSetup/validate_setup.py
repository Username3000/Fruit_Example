import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
lib=unreal.BlueprintEditorLibrary
base=unreal.load_asset('/Game/Root/Blueprints/B_FruitBase')
base_class=lib.generated_class(base)
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
checks=[]
for name in ['Apple','Banana','Coconut','Orange','Pear','Pineapple','Strawberry','Watermelon']:
    bp=unreal.load_asset('/Game/Root/Blueprints/Fruits/B_Fruit_'+name)
    assert lib.get_blueprint_parent_class(bp)==base_class
    lib.compile_blueprint(bp)
    cdo=unreal.get_default_object(lib.generated_class(bp))
    system=cdo.get_editor_property('FruitBurstSystem')
    assert system.get_name()=='NS_FruitPieces_'+name
    for graph in lib.list_graphs(bp):
        editor=unreal.BlueprintGraphEditor.get_graph_editor(graph)
        assert not editor.list_nodes_with_errors()
    emitter=unreal.find_object(system,'DirectionalBurst_1')
    data=json.loads(unreal.JsonObjectGraphFunctionLibrary.stringify([emitter],unreal.JsonStringifyOptions()))['__RootObjects'][0]
    inherited=next(m for m in data['Modules'] if m['__UObject']['Name']=='FruitInheritedVelocity')
    assert inherited.get('VelocityType','Linear')=='Linear'
    assert inherited['LinearVelocityDistribution']['ParameterBinding']['Name']=='User.InheritedVelocity'
    assert len({m['__UObject']['Class'] for m in data['Modules']})==len(data['Modules']), 'Duplicate stateless modules would be discarded on load'
    renderer=unreal.find_object(emitter,'Renderer')
    material=renderer.get_editor_property('material')
    assert isinstance(material,unreal.MaterialInstanceConstant)
    index=['Apple','Banana','Coconut','Orange','Pear','Pineapple','Strawberry','Watermelon'].index(name)
    assert abs(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material,'FruitIndex')-index)<0.01
    assert data['SpawnInfos'][0]['Amount']['Min']==3
    assert data['SpawnInfos'][0]['Amount']['Max']==3
    checks.append({'fruit':name,'parent':base_class.get_path_name(),'system':system.get_path_name(),'particles':3})
    unreal.EditorAssetLibrary.save_loaded_asset(bp)
for graph in lib.list_graphs(base):
    editor=unreal.BlueprintGraphEditor.get_graph_editor(graph)
    assert not editor.list_nodes_with_errors()
(root/'Saved/MCP/fruit-static-checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
unreal.EditorAssetLibrary.save_loaded_asset(base)
unreal.EditorAssetLibrary.save_directory('/Game/Root/Assets/VFX/Fruits',only_if_is_dirty=True,recursive=True)
unreal.EditorAssetLibrary.save_directory('/Game/Root/Assets/Materials/FruitChunks',only_if_is_dirty=True,recursive=True)
print('STATIC_CHECKS_PASSED:' + str(len(checks)))
unreal.EditorAssetLibrary.sync_browser_to_objects(['/Game/Root/Blueprints/Fruits/B_Fruit_'+row['fruit'] for row in checks])
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([unreal.load_asset('/Game/Root/Assets/VFX/Fruits/NS_FruitPieces_Apple')])
