"""Start the short test on the first PIE frame, before gameplay can end the session."""
import unreal,traceback
from pathlib import Path
motion_test_path=Path(unreal.Paths.project_dir())/'Tools/FruitSetup/test_visual_motion.py'
motion_start_state={'frames':0}
def start_motion_when_ready(delta,script_path=motion_test_path):
    motion_start_state['frames']+=1
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        unreal.unregister_slate_post_tick_callback(motion_start_state['callback'])
        exec(compile(script_path.read_text(encoding='utf-8'),str(script_path),'exec'),globals())
    elif motion_start_state['frames']>300:
        unreal.unregister_slate_post_tick_callback(motion_start_state['callback'])
        print('FRUIT_VISUAL_TEST_START_FAILED: PIE did not start')
motion_start_state['callback']=unreal.register_slate_post_tick_callback(start_motion_when_ready)
if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_play_simulate()
print('FRUIT_VISUAL_TEST_QUEUED')
