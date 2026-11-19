"""Render the same cube at scales 1 and 3, checking identical world-space texels."""
import unreal,json,traceback
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert world
gameplay=unreal.get_default_object(unreal.GameplayStatics)
def spawn(cls,location,rotation=unreal.Rotator()):
    transform=unreal.Transform(location=location,rotation=rotation)
    actor=gameplay.call_method('BeginDeferredActorSpawnFromClass',(world,cls,transform,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN))
    return gameplay.call_method('FinishSpawningActor',(actor,transform))
cube=spawn(unreal.StaticMeshActor,unreal.Vector(0,0,10000))
mesh=cube.get_component_by_class(unreal.StaticMeshComponent)
mesh.set_mobility(unreal.ComponentMobility.MOVABLE)
mesh.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube.Cube'))
instance=unreal.load_asset('/Game/Root/Assets/Materials/Backgrounds/MI_WoodBackground')
test_material=unreal.MaterialLibrary.create_dynamic_material_instance(world,instance)
test_material.set_scalar_parameter_value('Brightness',1.0)
mesh.set_material(0,test_material)
camera=spawn(unreal.SceneCapture2D,unreal.Vector(0,400,10000),unreal.Rotator(pitch=0,yaw=-90,roll=0))
capture=camera.get_component_by_class(unreal.SceneCaptureComponent2D)
target=unreal.RenderingLibrary.create_render_target2d(world,1024,512,unreal.TextureRenderTargetFormat.RTF_RGBA8,unreal.LinearColor(0,0,0,1))
capture.set_editor_property('texture_target',target)
capture.set_editor_property('capture_source',unreal.SceneCaptureSource.SCS_SCENE_COLOR_HDR)
capture.set_editor_property('primitive_render_mode',unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
capture.set_editor_property('capture_every_frame',False)
capture.set_editor_property('capture_on_movement',False)
capture.set_editor_property('fov_angle',60)
capture.show_only_actor_components(cube)
state={'frame':0,'samples':{}}
points=[(x,y) for y in [196,226,256,286,316] for x in [452,482,512,542,572]]
def read():
    values=[]
    for x,y in points:
        c=unreal.RenderingLibrary.read_render_target_raw_pixel(world,target,x,y)
        values.append([c.r,c.g,c.b])
    return values
def finish(error=None):
    unreal.unregister_slate_post_tick_callback(state['callback'])
    report={'passed':error is None,'error':error,'scales_compared':[[1,1,1],[3,1,1]],'sample_count':len(points),'maximum_color_difference':state.get('maximum_color_difference'),'samples':state['samples']}
    (root/'Saved/MCP/wood-scale-checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('WOOD_SCALE_TEST_FINISHED:'+json.dumps({k:v for k,v in report.items() if k!='samples'}))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
def tick(delta):
    try:
        state['frame']+=1
        if state['frame']==3:capture.capture_scene()
        if state['frame']==5:
            state['samples']['unit_cube']=read()
            unreal.RenderingLibrary.export_render_target(world,target,str(root/'Saved/MCP'),'wood-cube-scale-1.png')
            cube.set_actor_scale3d(unreal.Vector(3,1,1))
        if state['frame']==8:capture.capture_scene()
        if state['frame']==10:
            state['samples']['wide_cube']=read()
            unreal.RenderingLibrary.export_render_target(world,target,str(root/'Saved/MCP'),'wood-cube-scale-3.png')
            error=max(abs(a-b) for row_a,row_b in zip(state['samples']['unit_cube'],state['samples']['wide_cube']) for a,b in zip(row_a,row_b))
            state['maximum_color_difference']=error
            assert error<0.01,('Texture changed at identical world positions after scaling',error)
            colors=state['samples']['unit_cube']
            assert max(v[0] for v in colors)-min(v[0] for v in colors)>0.005,'Captured material has no wood pattern'
            finish()
    except Exception:finish(traceback.format_exc())
state['callback']=unreal.register_slate_post_tick_callback(tick)
print('WOOD_SCALE_TEST_STARTED')
