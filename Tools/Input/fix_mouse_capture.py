"""Run through Unreal MCP. Keep Game Only and deliver capture clicks to gameplay."""
import json
import shutil
from pathlib import Path

import unreal

assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
root = Path(unreal.Paths.project_dir()).resolve()
assert root.name == 'Fruit_Example'
lib = unreal.BlueprintEditorLibrary
bp = unreal.load_asset('/Game/Root/Blueprints/UI/B_FruitHUD')
editor = unreal.BlueprintGraphEditor.get_graph_editor(lib.find_graph(bp, 'ShowHUDWidget'))
nodes = editor.list_all_nodes()
game_only = next(n for n in nodes if str(lib.get_node_title(n)) == 'SetInputMode_GameOnly')
existing = [n for n in nodes if str(lib.get_node_title(n)) == 'SetViewportMouseCaptureMode']
assert not existing, 'Capture override already exists; inspect before changing it.'
successors = list(lib.find_then_pin(game_only).list_connected_pins())
assert len(successors) == 1

backup = root / 'Saved/Backups/MouseInput/B_FruitHUD.before-capture-fix.uasset'
backup.parent.mkdir(parents=True, exist_ok=True)
assert not backup.exists(), 'Keep the original backup; inspect before rerunning.'
shutil.copy2(root / 'Content/Root/Blueprints/UI/B_FruitHUD.uasset', backup)

with unreal.ScopedEditorTransaction('Preserve mouse press after Game Only'):
    bp.modify()
    # Make room along the existing execution wire, preserving the user's graph.
    for node in nodes:
        pos = lib.get_node_pos(node)
        if pos.x >= 1396 and pos.y >= 0:
            lib.set_node_pos(node, unreal.IntPoint(pos.x + 650, pos.y))
    capture = editor.add_call_function_node('/Script/Engine.GameplayStatics.SetViewportMouseCaptureMode')
    lib.set_node_pos(capture, unreal.IntPoint(1440, 208))
    assert lib.find_input_pin(capture, 'MouseCaptureMode').set_pin_value('CapturePermanently_IncludingInitialMouseDown')
    lib.find_then_pin(game_only).break_pin_links()
    assert lib.find_then_pin(game_only).try_create_connection(lib.find_execute_pin(capture))
    assert lib.find_then_pin(capture).try_create_connection(successors[0])
    editor.add_comment_to_nodes('Visible cursor: deliver capture clicks to the controller. Apply AFTER Game Only (it resets capture mode).', [game_only, capture], 35)
    lib.compile_blueprint(bp)

assert not editor.list_nodes_with_errors(), str(editor.list_nodes_with_errors())
print(json.dumps({'blueprint': bp.get_path_name(), 'backup': str(backup),
                  'capture_mode': lib.find_input_pin(capture, 'MouseCaptureMode').get_pin_value(),
                  'errors': len(editor.list_nodes_with_errors()),
                  'warnings': len(editor.list_nodes_with_warnings())}))
# Saving is explicit: the caller saves after reviewing compilation and PIE results.
