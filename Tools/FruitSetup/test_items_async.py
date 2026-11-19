"""Exercise real Damage dispatch, live particles, growth and completion in PIE."""
import unreal,json,traceback
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world,'Start PIE first'
cases=[('Heart',7),('Clock',4),('Bomb',None),('Apple',3)]
state={'index':0,'components':None,'results':[]}
gameplay=unreal.get_default_object(unreal.GameplayStatics)

def capture(component,advance=False):
    params=unreal.NiagaraSimCacheCreateParameters()
    params.attribute_capture_mode=unreal.NiagaraSimCacheAttributeCaptureMode.ALL
    params.include_debug_data=True;params.allow_velocity_extrapolation=True
    cache=unreal.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(world)
    cache=unreal.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(cache,params,component,advance,0.016666)
    emitter=cache.get_emitter_name(0)
    positions=list(cache.read_position_attribute('Position',emitter))
    sizes=list(cache.read_vector2_attribute('SpriteSize',emitter))
    velocities=list(cache.read_vector_attribute('Velocity',emitter))
    return {'count':len(positions),'sizes_cm':[[s.x,s.y] for s in sizes],'velocities':[[v.x,v.y,v.z] for v in velocities]}

def finish(error=None):
    unreal.unregister_slate_post_tick_callback(state['callback'])
    report={'passed':error is None,'results':state['results'],'current':state.get('row'),'error':error}
    (root/'Saved/MCP/item-runtime-checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('ITEM_RUNTIME_FINISHED:'+json.dumps(report))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()

def tick(delta):
    try:
        if state['components'] is None:
            if state['index']==len(cases):finish();return
            item,count=cases[state['index']]
            path=f'/Game/Root/Blueprints/Items/B_Item_{item}.B_Item_{item}_C' if item!='Apple' else '/Game/Root/Blueprints/Fruits/B_Fruit_Apple.B_Fruit_Apple_C'
            cls=unreal.load_class(None,path)
            transform=unreal.Transform(location=unreal.Vector(0,0,400))
            actor=gameplay.call_method('BeginDeferredActorSpawnFromClass',(world,cls,transform,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN))
            actor=gameplay.call_method('FinishSpawningActor',(actor,transform))
            unreal.get_default_object(unreal.SystemLibrary).call_method('SetVectorPropertyByName',(actor,'CurrentVelocity',unreal.Vector(450,0,250)))
            assert actor.get_component_by_class(unreal.StaticMeshComponent).static_mesh.get_name()=='SM_'+item
            before={c.get_path_name() for c in unreal.ObjectIterator(unreal.NiagaraComponent) if c.get_world()==world}
            actor.call_method('DectroyFruit')
            components=[c for c in unreal.ObjectIterator(unreal.NiagaraComponent) if c.get_world()==world and c.get_path_name() not in before]
            assert len(components)==(5 if item=='Bomb' else 1),('Incorrect effect dispatch',item,len(components))
            assert actor.is_actor_being_destroyed() or actor not in unreal.GameplayStatics.get_all_actors_of_class(world,cls)
            row={'item':item,'actor_destroyed':True,'systems':{},'initial_samples':{}}
            for component in components:
                name=component.get_asset().get_name()
                size,found=component.get_variable_vec2('User.PieceSize')
                assert found and size.x>0
                row['systems'][name]={'binding_size_cm':size.x}
                sample=capture(component,True)
                row['initial_samples'][name]=sample
                if item!='Bomb':
                    assert sample['count']==count,(item,'incorrect particle count',sample)
                    low,high=(0.32,0.44) if item=='Heart' else ((0.8,1.05) if item=='Clock' else (1.0,1.0))
                    assert sample['sizes_cm'] and all(size.x*low-0.1<=s[0]<=size.x*high+0.1 for s in sample['sizes_cm']),(item,'incorrect visible size',size.x,sample)
                    velocity,found=component.get_variable_vec3('User.InheritedVelocity')
                    assert found and abs(velocity.x-450)<0.01
                else:
                    assert sample['count']>0,('Missing explosion layer',name,sample)
                    assert sample['sizes_cm'] and all(s[0]>0 and s[1]>0 for s in sample['sizes_cm']),('Invisible explosion layer',name,sample)
            if item=='Bomb':
                assert set(row['systems'])=={'NS_BombFlash','NS_BombFire','NS_BombSmoke','NS_BombShockwave','NS_BombSparks'}
                for name,expected in [('NS_BombFlash',1),('NS_BombFire',8),('NS_BombSmoke',6),('NS_BombShockwave',1),('NS_BombSparks',12)]:
                    assert row['initial_samples'][name]['count']==expected,(name,row['initial_samples'][name])
            state.update({'components':components,'spawn_time':unreal.GameplayStatics.get_time_seconds(world),'late_checked':False,'row':row})
            return
        elapsed=unreal.GameplayStatics.get_time_seconds(world)-state['spawn_time']
        if not state['late_checked'] and elapsed>=1.2:
            item=state['row']['item']
            target=next(c for c in state['components'] if c.get_asset() and c.get_asset().get_name()=='NS_BombSmoke') if item=='Bomb' else state['components'][0]
            sample=capture(target)
            assert sample['count']>0,('Effect disappeared early',item,elapsed,sample)
            if item=='Bomb':
                initial=state['row']['initial_samples']['NS_BombSmoke']['sizes_cm']
                assert max(s[0] for s in sample['sizes_cm'])>max(s[0] for s in initial)*1.15,('Smoke does not expand',initial,sample)
            state['row']['late_sample']=sample
            state['row']['alive_after_1_2_seconds']=True
            state['late_checked']=True
        if elapsed>=5.3:
            live=[c for c in unreal.ObjectIterator(unreal.NiagaraComponent) if c.get_world()==world]
            assert all(c not in live or not c.is_active() for c in state['components']),'Effects did not auto-complete'
            state['row']['auto_completed']=True
            state['results'].append(state['row'])
            (root/'Saved/MCP/item-runtime-progress.json').write_text(json.dumps(state['results'],indent=2),encoding='utf-8')
            state['index']+=1;state['components']=None
    except Exception:finish(traceback.format_exc())

state['callback']=unreal.register_slate_post_tick_callback(tick)
print('ITEM_RUNTIME_ASYNC_STARTED')
