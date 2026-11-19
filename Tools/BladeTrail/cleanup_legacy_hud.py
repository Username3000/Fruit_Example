"""Remove the unused generated HUD after the controller migration is verified."""
import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
report=json.loads((root/'Saved/MCP/blade-controller-checks.json').read_text(encoding='utf-8'))
assert report['passed'],'Verify the controller renderer first'
assets=unreal.EditorAssetLibrary
lib=unreal.BlueprintEditorLibrary
gm=unreal.load_asset('/Game/Root/Blueprints/Base/B_FruitGameMode')
assert unreal.get_default_object(lib.generated_class(gm)).get_editor_property('HUDClass')==unreal.HUD.static_class()
bp=unreal.load_asset('/Game/Root/Blueprints/Base/B_FruitPlayerController')
editor=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph')
nodes=editor.list_all_nodes()
title=lambda n:str(lib.get_node_title(n)).replace(' ','')
button=next(n for n in nodes if title(n)=='LeftMouseButton')
gate=next(n for n in nodes if title(n)=='Gate')
tick=next(n for n in nodes if title(n)=='EventTick')
for start,key,wrapper,dest in [(button,'Pressed','BeginBladeStroke','Open'),(button,'Released','EndBladeStroke','Close'),(tick,'then','TickBladeTrail','Enter')]:
    connections=lib.find_output_pin(start,key).list_connected_pins();assert len(connections)==1
    node=connections[0].get_owning_node();assert title(node)==wrapper
    destinations=lib.find_then_pin(node).list_connected_pins()
    assert len(destinations)==1 and destinations[0].get_owning_node()==gate and str(destinations[0].get_pin_name())==dest
assert title(lib.find_output_pin(gate,'Exit').list_connected_pins()[0].get_owning_node())=='Branch'
cast=next(n for n in nodes if title(n)=='CastToB_FruitBase')
hit_call=lib.find_then_pin(cast).list_connected_pins()[0].get_owning_node()
assert hit_call.get_name()=='K2Node_CallFunction_2','Original fruit-hit call was replaced'
old='/Game/Root/Blueprints/Effects/B_BladeTrailHUD'
if assets.does_asset_exist(old):
    refs=assets.find_package_referencers_for_asset(old,load_assets_to_confirm=True)
    assert not refs,refs
    assert assets.delete_asset(old)
assert not assets.does_asset_exist(old)
for asset in [bp,gm,unreal.load_asset('/Game/Root/Assets/Materials/BladeTrail/M_BladeTrail')]:assert assets.save_loaded_asset(asset)
print('LEGACY_HUD_REMOVED_AND_SLICING_CONNECTIONS_VERIFIED')
