import unreal
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
for folder in ['/Game/Root/Assets/VFX/Items','/Game/Root/Assets/Materials/ItemEffects','/Game/Root/Blueprints/Items']:
    assert unreal.EditorAssetLibrary.save_directory(folder,only_if_is_dirty=False,recursive=True)
unreal.EditorAssetLibrary.save_loaded_asset(unreal.load_asset('/Game/Root/Assets/Textures/T_ItemEffects_Atlas'))
print('ITEM_ASSETS_SAVED')
