"""Author the editable UMG HUD via project MCP; preserves existing player stats and round timer."""
import unreal
from pathlib import Path
hud_setup_dir=Path(unreal.Paths.project_dir())/'Tools/HUD'
for hud_setup_name in ['create_widget_tree.py','migrate_to_umg.py']:
    hud_setup_path=hud_setup_dir/hud_setup_name
    exec(compile(hud_setup_path.read_text(encoding='utf-8'),str(hud_setup_path),'exec'))
