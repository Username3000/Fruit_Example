"""PIE checks: preserved spawn pose, bounded rotation, original flight and half-size pineapple debris."""
import unreal,json,math,traceback
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert world
gameplay=unreal.get_default_object(unreal.GameplayStatics)
names=['Apple','Banana','Coconut','Orange','Pear','Pineapple','Strawberry','Watermelon']
state={'phase':'spawn','rows':[],'objects':[],'heart':None,'burst':None}
def angle(a,b):
    qa=unreal.MathLibrary.conv_rotator_to_quaternion(a);qb=unreal.MathLibrary.conv_rotator_to_quaternion(b)
    return math.degrees(unreal.MathLibrary.quat_angular_distance(qa,qb))
def spawn(name,item=False):
    path=f'/Game/Root/Blueprints/Items/B_Item_{name}.B_Item_{name}_C' if item else f'/Game/Root/Blueprints/Fruits/B_Fruit_{name}.B_Fruit_{name}_C'
    cls=unreal.load_class(None,path)
    transform=unreal.Transform(location=unreal.Vector(0,0,400),rotation=unreal.Rotator(pitch=0,yaw=25,roll=0))
    actor=gameplay.call_method('BeginDeferredActorSpawnFromClass',(world,cls,transform,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN))
    system=unreal.get_default_object(unreal.SystemLibrary)
    system.call_method('SetVectorPropertyByName',(actor,'Gravity',unreal.Vector(0,0,0)))
    system.call_method('SetVectorPropertyByName',(actor,'CurrentVelocity',unreal.Vector(200,0,300)))
    return gameplay.call_method('FinishSpawningActor',(actor,transform))
def finish(error=None):
    unreal.unregister_slate_post_tick_callback(state['callback'])
    report={'passed':error is None,'error':error,'fruits':state['rows'],'pineapple_live_particle_sizes':state.get('piece_sizes'),'pineapple_input_size':state.get('piece_input'),'heart_rotation_unchanged':state.get('heart_unchanged')}
    (root/'Saved/MCP/fruit-visual-motion-checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('FRUIT_VISUAL_MOTION_TEST_FINISHED:'+json.dumps(report))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
def tick(delta):
    try:
        now=unreal.GameplayStatics.get_time_seconds(world)
        if state['phase']=='spawn':
            for name in names:
                actor=spawn(name);mesh=actor.get_component_by_class(unreal.StaticMeshComponent)
                assert actor.get_editor_property('FruitVisualRotationEnabled')
                # BeginPlay should initialize before the first rendered frame.
                assert actor.get_editor_property('FruitVisualInitialized'),name+': BeginPlay rotation did not initialize'
                original=actor.get_editor_property('FruitVisualBaseRotation')
                initial=mesh.get_editor_property('relative_rotation').copy()
                degrees=angle(original,initial)
                assert degrees<3.6,(name,'Spawn orientation changed too much',degrees)
                offset=actor.get_editor_property('FruitInitialRotationOffset')
                assert all(abs(getattr(offset,k))<=2.001 for k in ['pitch','yaw','roll'])
                state['objects'].append((name,actor,mesh,initial,actor.get_actor_location()))
                state['rows'].append({'fruit':name,'initial_offset_degrees':degrees,'jitter':[offset.pitch,offset.yaw,offset.roll]})
            heart=spawn('Heart',True)
            assert not heart.get_editor_property('FruitVisualRotationEnabled')
            state['heart']=(heart,heart.get_component_by_class(unreal.StaticMeshComponent).get_editor_property('relative_rotation').copy())
            state.update({'phase':'motion','start_time':now});return
        if state['phase']=='motion' and now-state['start_time']>=0.8:
            elapsed=now-state['start_time']
            for i,(name,actor,mesh,initial,position) in enumerate(state['objects']):
                actual=mesh.get_editor_property('relative_rotation')
                degrees=angle(initial,actual)
                assert 0.05<degrees<6.2,(name,'Invalid flight rotation',degrees,actor.get_editor_property('FruitVisualElapsed'))
                moved=actor.get_actor_location()-position
                assert abs(moved.x-200*elapsed)<2 and abs(moved.z-300*elapsed)<2,(name,'Launch trajectory changed',moved,elapsed)
                state['rows'][i].update({'rotation_after_flight_degrees':degrees,'flight_unchanged':True})
            heart,initial=state['heart']
            state['heart_unchanged']=angle(initial,heart.get_component_by_class(unreal.StaticMeshComponent).get_editor_property('relative_rotation'))<0.01
            assert state['heart_unchanged']
            pineapple=next(a for name,a,mesh,initial,pos in state['objects'] if name=='Pineapple')
            before={c.get_path_name() for c in unreal.ObjectIterator(unreal.NiagaraComponent) if c.get_world()==world}
            pineapple.call_method('DectroyFruit')
            components=[c for c in unreal.ObjectIterator(unreal.NiagaraComponent) if c.get_world()==world and c.get_path_name() not in before]
            assert len(components)==1
            component=components[0]
            size,found=component.get_variable_vec2('User.PieceSize');assert found and size.x>0
            state.update({'phase':'particles','burst':component,'piece_input':size.x,'burst_time':now});return
        if state['phase']=='particles' and now-state['burst_time']>=0.12:
            params=unreal.NiagaraSimCacheCreateParameters()
            params.attribute_capture_mode=unreal.NiagaraSimCacheAttributeCaptureMode.ALL
            params.include_debug_data=True;params.allow_velocity_extrapolation=True
            cache=unreal.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(world)
            cache=unreal.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(cache,params,state['burst'])
            emitter=cache.get_emitter_name(0)
            sizes=list(cache.read_vector2_attribute('SpriteSize',emitter))
            assert len(sizes)==3 and all(abs(s.x-state['piece_input']*.5)<.1 and abs(s.y-state['piece_input']*.5)<.1 for s in sizes),('Pineapple pieces are not half size',sizes,state['piece_input'])
            state['piece_sizes']=[[s.x,s.y] for s in sizes]
            finish()
    except Exception:finish(traceback.format_exc())
state['callback']=unreal.register_slate_post_tick_callback(tick)
print('FRUIT_VISUAL_MOTION_TEST_STARTED')
