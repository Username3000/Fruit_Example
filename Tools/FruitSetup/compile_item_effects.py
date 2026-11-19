import unreal
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
for name in ['HeartMiniHearts','ClockPieces','BombFlash','BombFire','BombSmoke','BombShockwave','BombSparks']:
    unreal.load_asset('/Game/Root/Assets/VFX/Items/NS_'+name)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world,'fx.RebuildDirtyScripts')
print('ITEM_COMPILATION_REQUESTED')
