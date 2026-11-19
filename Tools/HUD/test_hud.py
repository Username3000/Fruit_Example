"""Runtime checks of the actual HUD class, live bindings, timer and heart states."""
import unreal,json,traceback
from pathlib import Path
hud_test_root=Path(unreal.Paths.project_dir()).resolve()
hud_test_state={'phase':'waiting','frames':0,'checks':[]}

def finish_hud_test(error=None):
    unreal.unregister_slate_post_tick_callback(hud_test_state['callback'])
    result={k:v for k,v in hud_test_state.items() if k not in ['callback','pc','gm','hud','widget','world']}
    result.update(passed=error is None,error=error)
    (hud_test_root/'Saved/MCP/hud-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('HUD_TEST_FINISHED',json.dumps(result))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()

def hud_check(condition,message):
    assert condition,message
    hud_test_state['checks'].append(message)

def tick_hud_test(delta):
    try:
        s=hud_test_state;s['frames']+=1
        if s['phase']=='waiting':
            world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if not world:
                assert s['frames']<400,'PIE failed to start';return
            pc=unreal.GameplayStatics.get_player_controller(world,0)
            if not pc or not pc.get_hud():return
            if unreal.GameplayStatics.get_time_seconds(world)<0.05:return
            gm=unreal.GameplayStatics.get_game_mode(world);hud=pc.get_hud()
            widget=hud.get_editor_property('GameWidget')
            if not widget or not widget.is_in_viewport():return
            if not widget.get_editor_property('FruitController'):
                assert s['frames']<40,'UMG did not construct';return
            hud_check(hud.get_class().get_name()=='B_FruitHUD_C','GameMode spawns actual B_FruitHUD (AHUD)')
            hud_check(widget.get_class().get_name()=='WBP_FruitHUD_C' and widget.is_in_viewport(),'Real UMG Widget Blueprint is added to viewport')
            hud_check(widget.get_editor_property('FruitController')==pc and widget.get_editor_property('FruitGameMode')==gm,'Widget references the live player controller and game mode')
            hud_check(pc.get_editor_property('CurrentHealth')==3 and pc.get_editor_property('MaxHealth')==3,'Player starts with three lives')
            hud_check(59<gm.get_editor_property('RemainingTime')<=60,'Round begins at sixty seconds')
            widget.call_method('RefreshHUD')
            hud_check(all(abs(widget.get_editor_property('Heart'+str(i+1)).get_editor_property('render_opacity')-1)<1e-5 for i in range(3)),'Three full UMG Images at maximum health')
            s.update(world=world,pc=pc,gm=gm,hud=hud,widget=widget,phase='countdown',started=unreal.GameplayStatics.get_time_seconds(world),remaining=gm.get_editor_property('RemainingTime'))
            return
        world=s['world'];pc=s['pc'];gm=s['gm'];hud=s['hud'];widget=s['widget'];now=unreal.GameplayStatics.get_time_seconds(world)
        if s['phase']=='countdown' and now-s['started']>=1.2:
            elapsed=now-s['started'];decrease=s['remaining']-gm.get_editor_property('RemainingTime')
            hud_check(abs(elapsed-decrease)<0.08,'GameMode countdown tracks elapsed game time')
            gm.set_actor_tick_enabled(False)
            gm.call_method('ResetRoundTimer')
            hud_check(gm.call_method('GetRoundTimeText')=='01:00','Sixty seconds formats as 01:00')
            gm.call_method('TickRoundTimer',(1.0,))
            hud_check(gm.call_method('GetRoundTimeText')=='00:59','Fifty-nine seconds formats as 00:59')
            gm.call_method('TickRoundTimer',(49.1,))
            hud_check(gm.call_method('GetRoundTimeText')=='00:10','Seconds are padded and rounded up')
            gm.call_method('TickRoundTimer',(100.0,))
            hud_check(gm.get_editor_property('RemainingTime')==0 and gm.call_method('GetRoundTimeText')=='00:00','Timer stops at zero and never becomes negative')
            pc.call_method('DamagePlayer',(1,))
            widget.call_method('RefreshHUD')
            alpha=[widget.get_editor_property('Heart'+str(i+1)).get_editor_property('render_opacity') for i in range(3)]
            hud_check(pc.get_editor_property('CurrentHealth')==2 and all(abs(a-b)<1e-5 for a,b in zip(alpha,[1,1,.3])),'Two lives display two full hearts and a rightmost heart at 30% alpha')
            pc.call_method('HealPlayer',(100,));hud_check(pc.get_editor_property('CurrentHealth')==3,'Healing cannot exceed three hearts')
            pc.call_method('DamagePlayer',(100,));hud_check(pc.get_editor_property('CurrentHealth')==0,'Damage cannot reduce lives below zero')
            pc.call_method('HealPlayer',(2,))
            pc.call_method('AddScore',(125,));hud_check(pc.get_editor_property('Score')==125,'HUD score source updates through existing AddScore function')
            gm.call_method('ResetRoundTimer');gm.call_method('TickRoundTimer',(17.0,))
            widget.call_method('RefreshHUD')
            hud_check(str(widget.get_editor_property('ScoreText').get_editor_property('text'))=='SCORE: 125' and str(widget.get_editor_property('TimerText').get_editor_property('text'))=='00:43','UMG TextBlocks display the live score and timer')
            hud_check(widget.get_editor_property('Heart1').get_editor_property('brush').resource_object.get_path_name()=='/Game/Root/Assets/Materials/UI/M_HUDHeart.M_HUDHeart','UMG heart Images use the brush for the existing heart icon')
            meshes=list(pc.get_editor_property('BladeSegments'))
            hud_check(len(meshes)==64 and all(c.get_owner()==pc for c in meshes),'Blade trail components remain owned by the controller')
            pc.call_method('EndBladeStroke')
            s.update(phase='capture',capture_frame=s['frames']+8,viewport=list(pc.get_viewport_size()),heart_opacities=alpha,timer_example=gm.call_method('GetRoundTimeText'))
        elif s['phase']=='capture' and s['frames']>=s['capture_frame']:
            shot=hud_test_root/'Saved/MCP/hud-umg-preview.png'
            unreal.SystemLibrary.execute_console_command(world,'Shot -showui -nosuffix filename="'+str(shot).replace('\\','/')+'"')
            s.update(phase='finish',finish_frame=s['frames']+8,screenshot=str(shot))
        elif s['phase']=='finish' and s['frames']>=s['finish_frame']:
            finish_hud_test()
    except Exception:finish_hud_test(traceback.format_exc())

hud_test_state['callback']=unreal.register_slate_post_tick_callback(tick_hud_test)
if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
print('HUD_TEST_QUEUED')
