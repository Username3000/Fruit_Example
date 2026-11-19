"""Current blade-trail authoring entry point: controller-owned renderer."""
import unreal
from pathlib import Path
p=Path(unreal.Paths.project_dir())/'Tools/BladeTrail/migrate_controller.py'
exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'))
