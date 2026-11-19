"""Add small relative spawn offsets and bounded flight sway to the eight fruit classes."""
import unreal,json,shutil
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None,'End PIE first'
lib=unreal.BlueprintEditorLibrary;assets=unreal.EditorAssetLibrary
bp=unreal.load_asset('/Game/Root/Blueprints/B_FruitBase')
backup=root/'Saved/Backups/FruitSetup/B_FruitBase.before-visual-motion.uasset'
if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'Content/Root/Blueprints/B_FruitBase.uasset',backup)
bp.modify()
real=lib.get_basic_type_by_name('real');boolean=lib.get_basic_type_by_name('bool')
vector=lib.get_struct_type(unreal.Vector.static_struct());rotator=lib.get_struct_type(unreal.Rotator.static_struct())
variables={
    'FruitVisualRotationEnabled':boolean,'FruitInitialAngleVariation':real,'FruitSwayAngle':real,
    'FruitVisualBaseRotation':rotator,'FruitInitialRotationOffset':rotator,
    'FruitSwayAmplitude':vector,'FruitSwayRate':real,'FruitVisualElapsed':real,'FruitVisualInitialized':boolean,
}
existing=set(map(str,lib.list_member_variable_names(bp,include_inherited_members=False)))
for name,kind in variables.items():
    if name not in existing:assert lib.add_member_variable(bp,name,kind),name
    lib.set_blueprint_variable_category(bp,name,'Fruit|Visual Motion' if name in ['FruitVisualRotationEnabled','FruitInitialAngleVariation','FruitSwayAngle'] else 'Fruit|Visual Motion|Runtime')
for name in ['FruitVisualRotationEnabled','FruitInitialAngleVariation','FruitSwayAngle']:lib.set_blueprint_variable_instance_editable(bp,name,True)
for name,inputs in [('InitializeFruitVisualRotation',[]),('TickFruitVisualRotation',[('DeltaSeconds',real)])]:
    graph=lib.find_graph(bp,name)
    e=unreal.BlueprintGraphEditor.get_graph_editor(graph) if graph else unreal.BlueprintGraphEditor.create_and_edit_function_graph(bp,name)
    e.remove_nodes([n for n in e.list_all_nodes() if not isinstance(n,unreal.K2Node_FunctionEntry)])
    entry=next(n for n in e.list_all_nodes() if isinstance(n,unreal.K2Node_FunctionEntry))
    for key,kind in inputs:
        if not lib.find_output_pin(entry,key).is_valid():e.add_graph_input_parameter(key,kind)
lib.compile_blueprint(bp)
scope={};exec(compile((root/'Tools/BladeTrail/graph_helpers.py').read_text(encoding='utf-8'),'graph_helpers.py','exec'),scope)
Graph=scope['Graph'];inp=scope['inp'];out=scope['out'];link=scope['link']
math='/Script/Engine.KismetMathLibrary.'
def chain(g,*nodes):
    for a,b in zip(nodes,nodes[1:]):g.after(a,b)
def mesh_call(g,path,values):
    n=g.call_with(path,values);link(g.get('Mesh'),lib.find_self_pin(n));return n

g=Graph(bp,'InitializeFruitVisualRotation')
enabled=g.branch(g.get('FruitVisualRotationEnabled'));g.begin(enabled)
already=g.branch(g.op('Not_PreBool',g.get('FruitVisualInitialized')))
link(lib.find_then_pin(enabled),lib.find_execute_pin(already))
transform=mesh_call(g,'/Script/Engine.SceneComponent.GetRelativeTransform',{})
split=g.call_with(math+'BreakTransform',{'InTransform':out(transform)})
base=g.set('FruitVisualBaseRotation',out(split,'Rotation'))
link(lib.find_then_pin(already),lib.find_execute_pin(base))
limit=g.op('FMax',g.get('FruitInitialAngleVariation'),0)
negative=g.op('Multiply_DoubleDouble',limit,-1)
offset={}
for axis in ['Pitch','Yaw','Roll']:
    offset[axis]=out(g.call_with(math+'RandomFloatInRange',{'Min':negative,'Max':limit}))
initial=g.set('FruitInitialRotationOffset',out(g.call_with(math+'MakeRotator',offset)))
unit=g.call(math+'RandomUnitVector')
amplitude=g.set('FruitSwayAmplitude',g.op('Multiply_VectorFloat',out(unit),g.get('FruitSwayAngle')))
rate=g.set('FruitSwayRate',out(g.call_with(math+'RandomFloatInRange',{'Min':0.75,'Max':1.2})))
elapsed=g.set('FruitVisualElapsed',0)
rotation=out(g.call_with(math+'ComposeRotators',{'A':g.get('FruitVisualBaseRotation'),'B':g.get('FruitInitialRotationOffset')}))
apply=mesh_call(g,'/Script/Engine.SceneComponent.K2_SetRelativeRotation',{'NewRotation':rotation,'bSweep':'false','bTeleport':'true'})
initialized=g.set('FruitVisualInitialized','true')
chain(g,base,initial,amplitude,rate,elapsed,apply,initialized)
g.comment('Capture the actual existing mesh pose. Add only +/-2 degrees per axis; cache all random values once. Fruit classes opt in; items retain their original behavior.')

g=Graph(bp,'TickFruitVisualRotation')
enabled=g.branch(g.get('FruitVisualRotationEnabled'));g.begin(enabled)
ready=g.branch(g.get('FruitVisualInitialized'));link(lib.find_then_pin(enabled),lib.find_execute_pin(ready))
initialize=g.own('InitializeFruitVisualRotation');link(lib.find_else_pin(ready),lib.find_execute_pin(initialize))
time=g.set('FruitVisualElapsed',g.op('Add_DoubleDouble',g.get('FruitVisualElapsed'),g.arg('DeltaSeconds')))
link(lib.find_then_pin(ready),lib.find_execute_pin(time));g.after(initialize,time)
phase=g.op('Multiply_DoubleDouble',g.get('FruitVisualElapsed'),g.get('FruitSwayRate'))
wave=g.op('Sin',phase)
sway=g.op('Multiply_VectorFloat',g.get('FruitSwayAmplitude'),wave)
xyz=g.call_with(math+'BreakVector',{'InVec':sway})
delta=out(g.call_with(math+'MakeRotator',{'Pitch':out(xyz,'X'),'Yaw':out(xyz,'Y'),'Roll':out(xyz,'Z')}))
jittered=out(g.call_with(math+'ComposeRotators',{'A':g.get('FruitVisualBaseRotation'),'B':g.get('FruitInitialRotationOffset')}))
pose=out(g.call_with(math+'ComposeRotators',{'A':jittered,'B':delta}))
apply=mesh_call(g,'/Script/Engine.SceneComponent.K2_SetRelativeRotation',{'NewRotation':pose,'bSweep':'false','bTeleport':'true'})
g.after(time,apply)
g.comment('Delta-time-based, bounded sine sway (6 degree amplitude). Preserves the authored/spawn pose and world-space launch velocity; never accumulates into full spins.')

e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph')
def hook(event_name,event_title,function,position):
    nodes=list(e.list_all_nodes())
    event=next((n for n in nodes if isinstance(n,unreal.K2Node_Event) and str(lib.get_node_title(n))==event_title),None)
    if not event:event=lib.add_event_override(bp,event_name,unreal.IntPoint(*position))
    assert event
    then=lib.find_then_pin(event)
    old=list(then.list_connected_pins())
    if old and str(lib.get_node_title(old[0].get_owning_node())).replace(' ','')==function:
        return old[0].get_owning_node()
    assert len(old)<=1
    then.break_pin_links()
    call=e.add_call_function_node(lib.generated_class(bp).get_path_name()+'.'+function);assert call
    lib.set_node_pos(call,unreal.IntPoint(position[0]+350,position[1]))
    link(then,lib.find_execute_pin(call))
    for destination in old:link(lib.find_then_pin(call),destination)
    return call
hook('ReceiveBeginPlay','Event BeginPlay','InitializeFruitVisualRotation',(-450,600))
tick=hook('ReceiveTick','Event Tick','TickFruitVisualRotation',(-450,-400))
event=next(n for n in e.list_all_nodes() if isinstance(n,unreal.K2Node_Event) and str(lib.get_node_title(n))=='Event Tick')
link(out(event,'DeltaSeconds'),inp(tick,'DeltaSeconds'))
lib.compile_blueprint(bp)
errors=[]
for graph in lib.list_graphs(bp):
    for node in unreal.BlueprintGraphEditor.get_graph_editor(graph).list_nodes_with_errors():errors.append([graph.get_name(),str(node.get_editor_property('ErrorMsg'))])
assert not errors,errors
cdo=unreal.get_default_object(lib.generated_class(bp))
for name,value in [('FruitVisualRotationEnabled',False),('FruitInitialAngleVariation',2.0),('FruitSwayAngle',6.0)]:cdo.set_editor_property(name,value)
assert assets.save_loaded_asset(bp)
fruits=['Apple','Banana','Coconut','Orange','Pear','Pineapple','Strawberry','Watermelon']
for fruit in fruits:
    child=unreal.load_asset('/Game/Root/Blueprints/Fruits/B_Fruit_'+fruit);assert child
    child.modify();lib.compile_blueprint(child)
    unreal.get_default_object(lib.generated_class(child)).set_editor_property('FruitVisualRotationEnabled',True)
    assert assets.save_loaded_asset(child)

system=unreal.load_asset('/Game/Root/Assets/VFX/Fruits/NS_FruitPieces_Pineapple')
emitter=unreal.find_object(system,'DirectionalBurst_1')
scale=next(m for m in emitter.get_editor_property('Modules') if m.get_class().get_name()=='NiagaraStatelessModule_ScaleSpriteSize')
system.modify();scale.modify()
value=scale.get_editor_property('ScaleDistribution').copy()
assert value.import_text('(Mode=UniformConstant,ChannelConstantsAndRanges=(0.5))')
scale.set_editor_property('ScaleDistribution',value)
scale.set_editor_property('bModuleEnabled',True)
emitter.set_editor_property('Modules',list(emitter.get_editor_property('Modules')))
assert assets.save_loaded_asset(system)
report={'fruits':fruits,'initial_variation_degrees':2,'sway_amplitude_degrees':6,'sway_frequency_radians_per_second':[0.75,1.2],'pineapple_piece_scale':0.5,'compile_errors':errors}
(root/'Saved/MCP/fruit-visual-motion-setup.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
lib.refresh_all_open_blueprint_editors()
print('FRUIT_VISUAL_MOTION_SAVED:'+json.dumps(report))
