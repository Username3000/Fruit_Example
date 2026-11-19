"""Run via Unreal MCP outside PIE, then send real mouse drags to its viewport.

Observe the LMB event's BladeHeld state; do not call Begin/EndBladeStroke.
The timer tick is disabled on the temporary PIE GameMode to keep tests repeatable.
Call finish_mouse_input_test() via MCP to write the report and end PIE.
"""
import json
import time
from pathlib import Path

import unreal

assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
mouse_test = {'events': [], 'previous': False, 'max_segments': 0, 'ready': False,
              'capture_mode': None, 'errors': [], 'label': 'saved_blueprint'}
mouse_log = max(Path(unreal.Paths.project_log_dir()).glob('*.log'), key=lambda p: p.stat().st_mtime)
mouse_log_start = len(mouse_log.read_text(encoding='utf-8', errors='replace').splitlines())


def observe_mouse_input(delta):
    try:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not world:
            return
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        if not pc:
            return
        if not mouse_test['ready']:
            unreal.GameplayStatics.get_game_mode(world).set_actor_tick_enabled(False)
            mouse_test['capture_mode'] = str(unreal.GameplayStatics.get_viewport_mouse_capture_mode(world))
            mouse_test['ready'] = True
        held = bool(pc.get_editor_property('BladeHeld'))
        mouse_test['max_segments'] = max(mouse_test['max_segments'], int(pc.get_editor_property('RenderedSegments')))
        if held != mouse_test['previous']:
            mouse_test['events'].append({'held': held, 'label': mouse_test['label'], 'time': time.time()})
            mouse_test['previous'] = held
    except Exception as error:
        message = str(error)
        if message not in mouse_test['errors']:
            mouse_test['errors'].append(message)


def finish_mouse_input_test():
    unreal.unregister_slate_post_tick_callback(mouse_test['callback'])
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    report = {k: v for k, v in mouse_test.items() if k != 'callback'}
    # Very short physical clicks can press and release in one game frame.
    # The user's existing PrintString nodes record both even if polling misses them.
    lines = mouse_log.read_text(encoding='utf-8', errors='replace').splitlines()[mouse_log_start:]
    report['blueprint_log_events'] = [line for line in lines if 'LogBlueprintUserMessages:' in line
                                    and (line.endswith(' PRESSED') or line.endswith(' RELEASED'))]
    report['released_at_finish'] = not pc.get_editor_property('BladeHeld')
    report['visible_segments_at_finish'] = sum(c.is_visible() for c in pc.get_editor_property('BladeSegments'))
    report['samples_at_finish'] = len(pc.get_editor_property('TrailSamples'))
    path = Path(unreal.Paths.project_dir()).resolve() / 'Saved/MCP/mouse-input-fixed.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()


mouse_test['callback'] = unreal.register_slate_post_tick_callback(observe_mouse_input)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
print('Mouse input observer started; waiting for real viewport clicks.')
