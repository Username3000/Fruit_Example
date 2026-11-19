"""Render temporary PIE-only item/effect comparisons for visual inspection."""
import unreal,traceback
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world
gameplay=unreal.get_default_object(unreal.GameplayStatics)
def spawn(cls,location,rotation=unreal.Rotator()):
    transform=unreal.Transform(location=location,rotation=rotation)
    actor=gameplay.call_method('BeginDeferredActorSpawnFromClass',(world,cls,transform,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN))
    return gameplay.call_method('FinishSpawningActor',(actor,transform))
output=root/'Saved/MCP/ItemPreviews';output.mkdir(parents=True,exist_ok=True)
preview_refs=[]
preview_jobs=[]
for item in ['Heart','Clock','Bomb']:
    cls=unreal.load_class(None,f'/Game/Root/Blueprints/Items/B_Item_{item}.B_Item_{item}_C')
    model=spawn(cls,unreal.Vector(-150,0,400));model.set_actor_tick_enabled(False)
    source=spawn(cls,unreal.Vector(90,0,400));source.set_actor_tick_enabled(False)
    source.set_editor_property('CurrentVelocity',unreal.Vector(0,0,0))
    origin,extent,radius=unreal.SystemLibrary.get_component_bounds(source.get_component_by_class(unreal.StaticMeshComponent))
    before={c.get_path_name() for c in unreal.ObjectIterator(unreal.NiagaraComponent) if c.get_world()==world}
    source.call_method('Damage')
    components=[c for c in unreal.ObjectIterator(unreal.NiagaraComponent) if c.get_world()==world and c.get_path_name() not in before]
    for component in components:
        component.advance_simulation(14 if item=='Bomb' else 6,0.016666)
        component.set_paused(True)
    camera=spawn(unreal.SceneCapture2D,unreal.Vector(0,450,origin.z),unreal.Rotator(pitch=0,yaw=-90,roll=0))
    capture=camera.get_component_by_class(unreal.SceneCaptureComponent2D)
    target=unreal.RenderingLibrary.create_render_target2d(world,1200,600,unreal.TextureRenderTargetFormat.RTF_RGBA8,unreal.LinearColor(0.015,0.02,0.03,1))
    capture.set_editor_property('texture_target',target)
    capture.set_editor_property('capture_source',unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    capture.set_editor_property('primitive_render_mode',unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
    capture.set_editor_property('capture_every_frame',False)
    capture.set_editor_property('capture_on_movement',False)
    capture.set_editor_property('fov_angle',65)
    capture.show_only_actor_components(model)
    for component in components:capture.show_only_component(component)
    print('PREVIEW_CAMERA:'+item+':'+str(camera.get_actor_location())+':'+str(camera.get_actor_rotation())+':'+str(capture.get_world_rotation()))
    print('PREVIEW_MODEL:'+item+':'+str(model.get_actor_location())+':'+str(unreal.SystemLibrary.get_component_bounds(model.get_component_by_class(unreal.StaticMeshComponent)))+':'+str(model.get_component_by_class(unreal.StaticMeshComponent).is_visible()))
    preview_refs.extend([model,camera,capture,target,*components])
    preview_jobs.append((item,capture,target))
preview_state={'frames':0}
def preview_tick(delta):
    try:
        preview_state['frames']+=1
        if preview_state['frames']==3:
            print('PREVIEW_CAPTURE_FRAME')
            for item,capture,target in preview_jobs:capture.capture_scene()
        if preview_state['frames']==5:
            for item,capture,target in preview_jobs:
                unreal.RenderingLibrary.export_render_target(world,target,str(output),item+'.png')
                print('ITEM_PREVIEW:'+str(output/(item+'.png')))
            unreal.unregister_slate_post_tick_callback(preview_state['callback'])
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
            print('ITEM_PREVIEWS_FINISHED')
    except Exception:
        print(traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(preview_state['callback'])
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
preview_state['callback']=unreal.register_slate_post_tick_callback(preview_tick)
print('ITEM_PREVIEWS_STARTED')
