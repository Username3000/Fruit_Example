"""PIE state checks for the controller-owned blade trail."""
import unreal,json,math
from pathlib import Path
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world
pc=unreal.GameplayStatics.get_player_controller(world,0)
assert pc.get_class().get_name()=='B_FruitPlayerController_C'
assert pc.get_hud().get_class()==unreal.GameplayStatics.get_game_mode(world).get_editor_property('HUDClass')
pc.call_method('EndBladeStroke')
now=unreal.GameplayStatics.get_real_time_seconds(world)
for i in range(90):pc.call_method('SubmitBladePoint',(unreal.Vector(100+i*3,200+math.sin(i/10)*30,now+i*0.0001),))
assert len(pc.get_editor_property('TrailSamples'))==64 and pc.get_editor_property('WriteIndex')==26
last=pc.get_editor_property('LastSample');index=pc.get_editor_property('WriteIndex')
pc.call_method('SubmitBladePoint',(unreal.Vector(last.x,last.y,last.z+0.1),))
assert pc.get_editor_property('WriteIndex')==index
pc.call_method('ClearBladeTrail')
assert not pc.get_editor_property('TrailSamples') and not pc.get_editor_property('HasSample')
report={'controller':pc.get_class().get_path_name(),'passed':True,'checks':['configured game HUD','64-point bounded ring buffer','no stationary samples','clear resets history']}
(Path(unreal.Paths.project_dir())/'Saved/MCP/blade-state-checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BLADE_STATE_CHECKS_PASSED:'+json.dumps(report))
