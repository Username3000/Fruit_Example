"""Save only the current controller, material and GameMode assets."""
import unreal
lib=unreal.BlueprintEditorLibrary
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
for path in ['/Game/Root/Blueprints/Base/B_FruitPlayerController','/Game/Root/Blueprints/Base/B_FruitGameMode','/Game/Root/Assets/Materials/BladeTrail/M_BladeTrail']:
    assert unreal.EditorAssetLibrary.save_loaded_asset(unreal.load_asset(path))
print('BLADE_CONTROLLER_ASSETS_SAVED')
