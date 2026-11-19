"""Exercise the functions wired to LMB, actual cursor movement and release cleanup."""
import unreal,json,math,traceback
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert world
pc=unreal.GameplayStatics.get_player_controller(world,0)
assert pc.get_class().get_name()=='B_FruitPlayerController_C'
assert pc.get_hud().get_class()==unreal.GameplayStatics.get_game_mode(world).get_editor_property('HUDClass'),'Configured game HUD is not active'
meshes=list(pc.get_editor_property('BladeSegments'))
mids=list(pc.get_editor_property('BladeMaterials'))
assert len(meshes)==64 and len(mids)==64,(len(meshes),len(mids))
assert all(c.get_owner()==pc and c.get_collision_enabled()==unreal.CollisionEnabled.NO_COLLISION for c in meshes)
width,height=pc.get_viewport_size()
for sx,sy in [(width*.2,height*.2),(width*.75,height*.7)]:
    sx,sy=int(sx),int(sy)
    point=pc.call_method('BladeScreenToWorld',(unreal.Vector(sx,sy,0),))
    screen=pc.project_world_location_to_screen(point,False)
    assert screen and abs(screen.x-sx)<0.1 and abs(screen.y-sy)<0.1,('Screen deprojection mismatch',point,screen,sx,sy)
original=pc.get_mouse_position()
pc.call_method('EndBladeStroke')
state={'phase':'unheld','frame':0,'maximum_segments':0,'checks':['configured game HUD active','64 components and materials owned by controller','all blade components have no collision','screen positions round-trip to the camera plane'],'phase_time':unreal.GameplayStatics.get_real_time_seconds(world)}
shot=root/'Saved/MCP/blade-controller-preview.png'

def visible():return sum(c.is_visible() for c in meshes)
def finish(error=None):
    unreal.unregister_slate_post_tick_callback(state['callback'])
    pc.call_method('EndBladeStroke')
    if original:pc.set_mouse_location(int(original[0]),int(original[1]))
    report={k:v for k,v in state.items() if k!='callback'}
    report.update({'passed':error is None,'error':error,'screenshot':str(shot) if shot.exists() else None})
    (root/'Saved/MCP/blade-controller-checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('BLADE_CONTROLLER_TEST_FINISHED:'+json.dumps(report))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()

def tick(delta):
    try:
        now=unreal.GameplayStatics.get_real_time_seconds(world)
        state['maximum_segments']=max(state['maximum_segments'],pc.get_editor_property('RenderedSegments'))
        phase=state['phase'];i=state['frame']
        if phase=='unheld':
            assert not pc.get_editor_property('BladeHeld') and visible()==0 and not pc.get_editor_property('TrailSamples'),'Trail visible without holding'
            pc.set_mouse_location(int(width*(.2+i*.03)),int(height*.5))
            if i==4:
                state['checks'].append('moving unheld cursor shows no trail')
                pc.call_method('BeginBladeStroke');state.update({'phase':'held','frame':0});return
        elif phase=='held':
            t=i/14
            pc.set_mouse_location(int(width*(.3+.4*t)),int(height*(.55-.13*math.sin(t*math.pi))))
            if i==11 and visible()>0:
                samples=list(pc.get_editor_property('TrailSamples'))
                for component in meshes:
                    if component.is_visible():
                        center=unreal.SystemLibrary.get_component_bounds(component)[0]
                        screen=pc.project_world_location_to_screen(center,False)
                        assert screen and min(p.x for p in samples)-3<=screen.x<=max(p.x for p in samples)+3 and min(p.y for p in samples)-3<=screen.y<=max(p.y for p in samples)+3,('Rendered quad is outside cursor history',center,screen)
                state['checks'].append('rendered quad centers project onto the cursor path')
                unreal.SystemLibrary.execute_console_command(world,'Shot -nosuffix filename="'+str(shot).replace('\\','/')+'"')
            if i==14:
                assert state['maximum_segments']>0 and visible()>0,'Held cursor did not produce visible quads'
                state['checks'].append('held mouse movement renders visible trail')
                state.update({'phase':'stationary','phase_time':now,'frame':0});return
        elif phase=='stationary':
            if now-state['phase_time']>.7:
                assert visible()==0 and pc.get_editor_property('RenderedSegments')==0,'Stationary held trail did not fade'
                state['checks'].append('stationary held trail fades in time')
                pc.call_method('EndBladeStroke')
                assert not pc.get_editor_property('BladeHeld') and visible()==0 and not pc.get_editor_property('TrailSamples')
                state['checks'].append('release immediately hides and clears history')
                state.update({'phase':'released','frame':0});return
        elif phase=='released':
            assert visible()==0 and not pc.get_editor_property('TrailSamples'),'Moving after release recreated the trail'
            pc.set_mouse_location(int(width*(.3+i*.06)),int(height*.7))
            if i==3:
                pc.call_method('BeginBladeStroke');pc.set_mouse_location(int(width*.8),int(height*.3))
                state.update({'phase':'newstroke','frame':0});return
        elif phase=='newstroke':
            if i==0:
                assert len(pc.get_editor_property('TrailSamples'))<=1 and visible()==0,'New press connected to old cursor history'
                state['checks'].append('new press starts without connecting to old stroke')
                pc.set_mouse_location(int(width*.85),int(height*.4))
            else:
                pc.call_method('EndBladeStroke');assert visible()==0
                finish();return
        state['frame']+=1
    except Exception:finish(traceback.format_exc())

state['callback']=unreal.register_slate_post_tick_callback(tick)
print('BLADE_CONTROLLER_TEST_STARTED')
