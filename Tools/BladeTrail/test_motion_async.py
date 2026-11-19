"""Current motion/release integration test entry point."""
import unreal
from pathlib import Path
p=Path(unreal.Paths.project_dir())/'Tools/BladeTrail/test_controller_async.py'
exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'))
