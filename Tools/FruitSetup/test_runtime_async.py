"""Frame-aware PIE test: inspect live Niagara particles after real simulation ticks."""
import unreal,json,traceback
from pathlib import Path

root=Path(unreal.Paths.project_dir()).resolve()
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world,'Start PIE first'
names=['Apple','Banana','Coconut','Orange','Pear','Pineapple','Strawberry','Watermelon']
cases=[(name,1.0) for name in names]+[('Apple',2.0)]
state={'index':0,'time':0.0,'component':None,'sampled':False,'results':[]}
gameplay=unreal.get_default_object(unreal.GameplayStatics)

def finish(error=None):
    unreal.unregister_slate_post_tick_callback(state['callback'])
    report={'passed':error is None,'results':state['results'],'current':state.get('row'),'error':error}
    (root/'Saved/MCP/fruit-runtime-checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('FRUIT_RUNTIME_FINISHED:' + json.dumps(report))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()

def tick(delta):
    try:
        if state['component'] is None:
            i=state['index']
            if i==len(cases):
                finish()
                return
            fruit,actor_scale=cases[i]
            cls=unreal.load_class(None,f'/Game/Root/Blueprints/Fruits/B_Fruit_{fruit}.B_Fruit_{fruit}_C')
            transform=unreal.Transform(location=unreal.Vector(0,0,400),scale=unreal.Vector(actor_scale,actor_scale,actor_scale))
            actor=gameplay.call_method('BeginDeferredActorSpawnFromClass',(world,cls,transform,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN))
            actor=gameplay.call_method('FinishSpawningActor',(actor,transform))
            velocity=unreal.Vector(500 if i%2==0 else -500,0,250)
            unreal.get_default_object(unreal.SystemLibrary).call_method('SetVectorPropertyByName',(actor,'CurrentVelocity',velocity))
            assert actor.get_component_by_class(unreal.StaticMeshComponent).static_mesh.get_name()=='SM_'+fruit
            mesh=actor.get_component_by_class(unreal.StaticMeshComponent)
            origin,extent,radius=unreal.SystemLibrary.get_component_bounds(mesh)
            camera=unreal.GameplayStatics.get_player_camera_manager(world,0)
            rotation=camera.get_camera_rotation()
            right=unreal.MathLibrary.get_right_vector(rotation)
            up=unreal.MathLibrary.get_up_vector(rotation)
            diameter=2*max(sum(abs(getattr(axis,k))*getattr(extent,k) for k in ['x','y','z']) for axis in [right,up])
            before={c.get_path_name() for c in unreal.ObjectIterator(unreal.NiagaraComponent) if c.get_world()==world}
            actor.call_method('DectroyFruit')
            components=[c for c in unreal.ObjectIterator(unreal.NiagaraComponent) if c.get_world()==world and c.get_path_name() not in before]
            assert len(components)==1,fruit+': expected one burst'
            component=components[0]
            assert component.get_asset().get_name()=='NS_FruitPieces_'+fruit
            inherited,found=component.get_variable_vec3('User.InheritedVelocity')
            assert found and abs(inherited.x-velocity.x)<0.01 and abs(inherited.z-velocity.z)<0.01
            piece_size,size_found=component.get_variable_vec2('User.PieceSize')
            assert size_found and abs(piece_size.x-diameter*0.7)<0.01 and abs(piece_size.y-diameter*0.7)<0.01,('Incorrect proportional size',fruit,piece_size,diameter)
            remaining=list(unreal.GameplayStatics.get_all_actors_of_class(world,cls))
            assert actor not in remaining or actor.is_actor_being_destroyed(),fruit+': fruit survived Damage: '+str([a.get_name() for a in remaining])
            state.update({'component':component,'spawn_time':unreal.GameplayStatics.get_time_seconds(world),'time':0.0,'sampled':False,'long_life_checked':False,'piece_size':piece_size.x,'velocity':velocity,'row':{'fruit':fruit,'actor_scale':actor_scale,'mesh_camera_diameter_cm':diameter,'piece_size_cm':piece_size.x,'visible_fraction':piece_size.x/diameter,'actor_destroyed':True,'spawned_one_system':True,'inherited_velocity':[inherited.x,inherited.y,inherited.z]}})
            return
        state['time']=unreal.GameplayStatics.get_time_seconds(world)-state['spawn_time']
        component=state['component']
        if not state['sampled'] and state['time']>=0.12:
            params=unreal.NiagaraSimCacheCreateParameters()
            params.attribute_capture_mode=unreal.NiagaraSimCacheAttributeCaptureMode.ALL
            params.include_debug_data=True
            params.allow_velocity_extrapolation=True
            capture=unreal.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(world)
            cache=unreal.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(capture,params,component)
            if cache:
                emitter=cache.get_emitter_name(0)
                positions=list(cache.read_position_attribute('Position',emitter))
                velocities=list(cache.read_vector_attribute('Velocity',emitter))
                randoms=list(cache.read_float_attribute('MaterialRandom',emitter))
                expected=names.index(state['row']['fruit'])*2
                frames=[expected+min(int(r*2),1) for r in randoms]
                state['row'].update({'cache_captured':True,'particles':len(positions),'mean_velocity':[sum(getattr(v,k) for v in velocities)/len(velocities) for k in ['x','y','z']] if velocities else None,'sprite_cells':sorted(set(frames))})
                assert len(positions)==3,'Expected three particles'
                sizes=list(cache.read_vector2_attribute('SpriteSize',emitter))
                expected_size=state['piece_size']*(0.5 if state['row']['fruit']=='Pineapple' else 1.0)
                assert len(sizes)==3 and all(abs(s.x-expected_size)<0.1 and abs(s.y-expected_size)<0.1 for s in sizes),('Live sprite size differs from binding',sizes,expected_size)
                state['row']['live_sprite_sizes_cm']=[[s.x,s.y] for s in sizes]
                if velocities:
                    assert sum(v.x for v in velocities)*state['velocity'].x>0,'Incorrect inherited flight direction'
                assert len(randoms)==3 and all(0<=r<=1 for r in randoms),'Missing per-particle atlas random values'
                renderer=unreal.find_object(unreal.find_object(component.get_asset(),'DirectionalBurst_1'),'Renderer')
                fruit_index=unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(renderer.get_editor_property('material'),'FruitIndex')
                assert abs(fruit_index-names.index(state['row']['fruit']))<0.01,'Incorrect fruit material instance'
                assert frames and all(expected<=int(f)<=expected+1 for f in frames),'Incorrect fruit sprite cells'
                state['sampled']=True
            elif state['time']>0.45:
                raise AssertionError('Unable to capture live fruit particles')
        if not state['long_life_checked'] and state['time']>=1.7:
            params=unreal.NiagaraSimCacheCreateParameters()
            params.attribute_capture_mode=unreal.NiagaraSimCacheAttributeCaptureMode.ALL
            params.include_debug_data=True
            params.allow_velocity_extrapolation=True
            capture=unreal.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(world)
            cache=unreal.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(capture,params,component)
            count=len(cache.read_position_attribute('Position',cache.get_emitter_name(0))) if cache else None
            assert cache and count==3,('Pieces disappeared before the new minimum lifetime',state['time'],component.is_active(),count,cache.get_start_seconds() if cache else None)
            state['row']['alive_after_1_7_seconds']=True
            state['long_life_checked']=True
        if state['time']>=5.2:
            # Auto-destroyed objects may already have been purged from the iterator.
            still_alive=component in [c for c in unreal.ObjectIterator(unreal.NiagaraComponent) if c.get_world()==world]
            assert not still_alive or not component.is_active(),'Effect did not auto-complete'
            state['row']['auto_completed']=True
            state['results'].append(state['row'])
            state['index']+=1
            state['component']=None
    except Exception:
        finish(traceback.format_exc())

state['callback']=unreal.register_slate_post_tick_callback(tick)
print('FRUIT_RUNTIME_ASYNC_STARTED')
