"""Move blade trail ownership, input, history and rendering into the existing controller."""
import unreal,json,shutil
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None,'End PIE first'
lib=unreal.BlueprintEditorLibrary
assets=unreal.EditorAssetLibrary
tools=unreal.AssetToolsHelpers.get_asset_tools()
mel=unreal.MaterialEditingLibrary
math='/Script/Engine.KismetMathLibrary.'
array='/Script/Engine.KismetArrayLibrary.'
bp=unreal.load_asset('/Game/Root/Blueprints/Base/B_FruitPlayerController')
for assetname,relative in [('B_FruitPlayerController','Base/B_FruitPlayerController'),('B_BladeTrailHUD','Effects/B_BladeTrailHUD')]:
    source=root/('Content/Root/Blueprints/'+relative+'.uasset')
    dest=root/('Saved/Backups/BladeTrail/'+assetname+'.before-controller-trail.uasset')
    if source.exists() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)

# Mesh quads face a camera-parallel plane, with exact screen-pixel deprojection.
# Local mesh coordinates provide stable longitudinal/cross-section coordinates.
material=unreal.load_asset('/Game/Root/Assets/Materials/BladeTrail/M_BladeTrail')
material.modify();mel.delete_all_material_expressions(material)
material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_ADDITIVE)
material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
material.set_editor_property('two_sided',True)
material.set_editor_property('disable_depth_test',True)
def expr(cls,x,y):return mel.create_material_expression(material,cls,x,y)
def wire(a,b,pin,out=''):
    names=list(mel.get_material_expression_input_names(b))
    if pin not in names and len(names)==1:pin=names[0]
    assert mel.connect_material_expressions(a,out,b,pin),(b.get_name(),pin,names)
def constant(value,x,y):n=expr(unreal.MaterialExpressionConstant,x,y);n.r=value;return n
def binary(cls,a,b,x,y):
    n=expr(cls,x,y);wire(a,n,'A');wire(b,n,'B');return n
def power(a,b,x,y):
    n=expr(unreal.MaterialExpressionPower,x,y);wire(a,n,'Base');wire(b,n,'Exp');return n
def mask(a,channel,x,y):
    n=expr(unreal.MaterialExpressionComponentMask,x,y)
    for c in ['R','G','B','A']:n.set_editor_property(c,c==channel)
    wire(a,n,'Input');return n
def parameter(name,value,x,y):
    n=expr(unreal.MaterialExpressionScalarParameter,x,y)
    n.set_editor_property('ParameterName',name);n.set_editor_property('DefaultValue',value);return n
local=expr(unreal.MaterialExpressionPreSkinnedPosition,-1700,0)
interpolated=expr(unreal.MaterialExpressionVertexInterpolator,-1550,0);wire(local,interpolated,'Input')
scaled=binary(unreal.MaterialExpressionMultiply,interpolated,constant(0.01,-1700,300),-1450,0)
coords=binary(unreal.MaterialExpressionAdd,scaled,constant(0.5,-1450,300),-1200,0)
u=mask(coords,'R',-1000,-100);v=mask(coords,'G',-1000,200)
fade=expr(unreal.MaterialExpressionLinearInterpolate,-700,-200)
wire(parameter('BladeFadeStart',0,-1000,-500),fade,'A')
wire(parameter('BladeFadeEnd',1,-1000,-350),fade,'B');wire(u,fade,'Alpha')
two=constant(2,-1000,450)
centered=binary(unreal.MaterialExpressionSubtract,binary(unreal.MaterialExpressionMultiply,v,two,-750,200),constant(1,-750,450),-500,200)
absolute=expr(unreal.MaterialExpressionAbs,-300,200);wire(centered,absolute,'Input')
inverse=expr(unreal.MaterialExpressionOneMinus,-100,200);wire(absolute,inverse,'Input')
cross=expr(unreal.MaterialExpressionSaturate,100,200);wire(inverse,cross,'Input')
glow=power(cross,two,300,200);core=power(cross,constant(18,100,450),300,450)
cyan=expr(unreal.MaterialExpressionConstant3Vector,300,750);cyan.constant=unreal.LinearColor(0.08,0.65,1,1)
white=expr(unreal.MaterialExpressionConstant3Vector,300,950);white.constant=unreal.LinearColor(2.4,2.7,3,1)
combined=binary(unreal.MaterialExpressionAdd,binary(unreal.MaterialExpressionMultiply,glow,cyan,550,200),binary(unreal.MaterialExpressionMultiply,core,white,550,450),800,200)
emitted=binary(unreal.MaterialExpressionMultiply,combined,power(fade,two,550,-200),1050,200)
mel.connect_material_property(emitted,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
mel.connect_material_property(constant(1,1050,450),'',unreal.MaterialProperty.MP_OPACITY)
mel.recompile_material(material);assert assets.save_loaded_asset(material)

bp.modify()
integer=lib.get_basic_type_by_name('int');real=lib.get_basic_type_by_name('real');boolean=lib.get_basic_type_by_name('bool')
vector=lib.get_struct_type(unreal.Vector.static_struct())
variables={
    'TrailSamples':lib.get_array_type(vector),'WriteIndex':integer,'LastSample':vector,'HasSample':boolean,
    'TrailLifetime':real,'TrailWidth':real,'MinPointDistance':real,'TrailDepth':real,
    'LastViewportX':integer,'LastViewportY':integer,'RenderedSegments':integer,'BladeHeld':boolean,
    'TrailMaterial':lib.get_object_reference_type(unreal.MaterialInterface),
    'BladeSegments':lib.get_array_type(lib.get_object_reference_type(unreal.StaticMeshComponent)),
    'BladeMaterials':lib.get_array_type(lib.get_object_reference_type(unreal.MaterialInstanceDynamic)),
}
existing=set(map(str,lib.list_member_variable_names(bp,include_inherited_members=False)))
for name,kind in variables.items():
    if name not in existing:assert lib.add_member_variable(bp,name,kind),name
    lib.set_blueprint_variable_category(bp,name,'Blade Trail' if name in ['TrailLifetime','TrailWidth','MinPointDistance','TrailDepth','TrailMaterial'] else 'Blade Trail|Runtime')
for name in ['TrailLifetime','TrailWidth','MinPointDistance']:lib.set_blueprint_variable_instance_editable(bp,name,True)
signatures={
    'InitializeBladeTrail':[], 'HideBladeTrail':[], 'ClearBladeTrail':[],
    'BeginBladeStroke':[], 'EndBladeStroke':[], 'TickBladeTrail':[], 'UpdateHeldBladeTrail':[],
    'PushBladePoint':[('Sample',vector)],'SubmitBladePoint':[('Sample',vector)],
    'BladeScreenToWorld':[('Point',vector)],
    'DrawBladeSegment':[('Start',vector),('End',vector),('Now',real),('SegmentIndex',integer)],
    'RenderBladeTrail':[('Now',real)],'ReadHeldBladeMouse':[],
}
for name,inputs in signatures.items():
    graph=lib.find_graph(bp,name)
    e=unreal.BlueprintGraphEditor.get_graph_editor(graph) if graph else unreal.BlueprintGraphEditor.create_and_edit_function_graph(bp,name)
    e.remove_nodes([n for n in e.list_all_nodes() if not isinstance(n,unreal.K2Node_FunctionEntry)])
    entry=next(n for n in e.list_all_nodes() if isinstance(n,unreal.K2Node_FunctionEntry))
    for arg,kind in inputs:
        if not lib.find_output_pin(entry,arg).is_valid():e.add_graph_input_parameter(arg,kind)
    if name=='BladeScreenToWorld':
        e.set_is_pure_function(True)
        # Output parameters survive the owned graph's node regeneration.
        if not any(str(p.get_pin_name())=='WorldPoint' for n in e.list_all_nodes() for p in lib.list_input_pins(n)):
            try:e.add_graph_output_parameter('WorldPoint',vector)
            except Exception:pass
lib.compile_blueprint(bp)
scope={};exec(compile((root/'Tools/BladeTrail/graph_helpers.py').read_text(encoding='utf-8'),'graph_helpers.py','exec'),scope)
Graph=scope['Graph'];inp=scope['inp'];out=scope['out'];link=scope['link'];literal=scope['literal']
def G(name):return Graph(bp,name)
def chain(g,*nodes):
    for a,b in zip(nodes,nodes[1:]):g.after(a,b)
def loop(g,first,last):
    n=g.pos(g.e.add_macro_node('/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForLoop'));assert n
    literal(n,'FirstIndex',first)
    if isinstance(last,unreal.BlueprintGraphPin):link(last,inp(n,'LastIndex'))
    else:literal(n,'LastIndex',last)
    return n
def length(g,name):return out(g.call_with(array+'Array_Length',{'TargetArray':g.get(name)}))
def element(g,name,index):return out(g.call_with(array+'Array_Get',{'TargetArray':g.get(name),'Index':index}),'Item')
def target(g,path,component,values):
    node=g.call_with(path,values);link(component,lib.find_self_pin(node));return node

g=G('InitializeBladeTrail')
show=g.call_with('/Script/Engine.Actor.SetActorHiddenInGame',{'bNewHidden':'false'})
g.begin(show)
lp=loop(g,0,63);g.after(show,lp)
add=g.call_with('/Script/Engine.Actor.AddComponentByClass',{'Class':'/Script/Engine.StaticMeshComponent','bManualAttachment':'true'})
identity=g.call(math+'MakeTransform');link(out(identity),inp(add,'RelativeTransform'))
link(out(lp,'LoopBody'),lib.find_execute_pin(add))
store=g.call_with(array+'Array_Add',{'TargetArray':g.get('BladeSegments')})
# Ask the editor schema to insert a normal pure cast into this one connection.
# Restore the editor preference immediately; generated nodes retain the cast.
settings=unreal.get_default_object(unreal.load_class(None,'/Script/BlueprintGraph.BlueprintEditorSettings'))
old_autocast=settings.get_editor_property('bAutoCastObjectConnections')
try:
    settings.set_editor_property('bAutoCastObjectConnections',True)
    link(out(add),inp(store,'NewItem'))
finally:settings.set_editor_property('bAutoCastObjectConnections',old_autocast)
component=inp(store,'NewItem').list_connected_pins()[0]
mobility=target(g,'/Script/Engine.SceneComponent.SetMobility',component,{'NewMobility':'Movable'})
collision=target(g,'/Script/Engine.PrimitiveComponent.SetCollisionEnabled',component,{'NewType':'NoCollision'})
overlap=target(g,'/Script/Engine.PrimitiveComponent.SetGenerateOverlapEvents',component,{'bInGenerateOverlapEvents':'false'})
shadow=target(g,'/Script/Engine.PrimitiveComponent.SetCastShadow',component,{'NewCastShadow':'false'})
mesh=target(g,'/Script/Engine.StaticMeshComponent.SetStaticMesh',component,{'NewMesh':'/Engine/BasicShapes/Plane.Plane'})
priority=target(g,'/Script/Engine.PrimitiveComponent.SetTranslucentSortPriority',component,{'NewTranslucentSortPriority':1000})
mid=target(g,'/Script/Engine.PrimitiveComponent.CreateDynamicMaterialInstance',component,{'ElementIndex':0,'SourceMaterial':g.get('TrailMaterial')})
save_mid=g.call_with(array+'Array_Add',{'TargetArray':g.get('BladeMaterials'),'NewItem':out(mid)})
hidden=target(g,'/Script/Engine.SceneComponent.SetVisibility',component,{'bNewVisibility':'false','bPropagateToChildren':'false'})
chain(g,add,store,mobility,collision,overlap,shadow,mesh,priority,mid,save_mid,hidden)
g.comment('Controller-owned pool of 64 reusable mesh components. No collision, overlaps or shadows. No extra actors, widgets or HUD dependency.')

g=G('HideBladeTrail')
reset=g.set('RenderedSegments',0);g.begin(reset)
lp=loop(g,0,g.op('Subtract_IntInt',length(g,'BladeSegments'),1));g.after(reset,lp)
hide=target(g,'/Script/Engine.SceneComponent.SetVisibility',element(g,'BladeSegments',out(lp,'Index')),{'bNewVisibility':'false','bPropagateToChildren':'false'})
link(out(lp,'LoopBody'),lib.find_execute_pin(hide))
g.comment('Reuse the component pool; hide unused quads before each frame and immediately on release.')

g=G('ClearBladeTrail')
clear=g.call_with(array+'Array_Clear',{'TargetArray':g.get('TrailSamples')});g.begin(clear)
index=g.set('WriteIndex',0);has=g.set('HasSample','false');hide=g.own('HideBladeTrail')
chain(g,clear,index,has,hide)
for name,value in [('BeginBladeStroke','true'),('EndBladeStroke','false')]:
    g=G(name);held=g.set('BladeHeld',value);clear=g.own('ClearBladeTrail');g.begin(held);g.after(held,clear)
    g.comment('Same Left Mouse Button event as the slicing Gate. New press starts clean; release immediately removes the trail.')

g=G('PushBladePoint')
store=g.call_with(array+'Array_Set',{'TargetArray':g.get('TrailSamples'),'Index':g.get('WriteIndex'),'Item':g.arg('Sample'),'bSizeToFit':'true'});g.begin(store)
last=g.set('LastSample',g.arg('Sample'));has=g.set('HasSample','true')
idx=g.set('WriteIndex',g.op('Percent_IntInt',g.op('Add_IntInt',g.get('WriteIndex'),1),64));chain(g,store,last,has,idx)
g=G('SubmitBladePoint')
distance=g.op('Vector_Distance2D',g.arg('Sample'),g.get('LastSample'),akey='V1',bkey='V2')
accept=g.op('BooleanOR',g.op('Not_PreBool',g.get('HasSample')),g.op('Greater_DoubleDouble',distance,g.get('MinPointDistance')))
branch=g.branch(accept);g.begin(branch)
push=g.call_with(g.class_path+'.PushBladePoint',{'Sample':g.arg('Sample')});link(lib.find_then_pin(branch),lib.find_execute_pin(push))

g=G('BladeScreenToWorld')
point=g.call_with(math+'BreakVector',{'InVec':g.arg('Point')})
deproject=g.call_with('/Script/Engine.PlayerController.DeprojectScreenPositionToWorld',{'ScreenX':out(point,'X'),'ScreenY':out(point,'Y')})
camera=g.call('/Script/Engine.GameplayStatics.GetPlayerCameraManager')
loc=g.call('/Script/Engine.PlayerCameraManager.GetCameraLocation');link(out(camera),lib.find_self_pin(loc))
rot=g.call('/Script/Engine.PlayerCameraManager.GetCameraRotation');link(out(camera),lib.find_self_pin(rot))
forward=out(g.call_with(math+'GetForwardVector',{'InRot':out(rot)}))
center=g.op('Add_VectorVector',out(loc),g.op('Multiply_VectorFloat',forward,g.get('TrailDepth')))
numerator=g.op('Dot_VectorVector',g.op('Subtract_VectorVector',center,out(deproject,'WorldLocation')),forward)
denominator=g.op('FMax',g.op('Dot_VectorVector',out(deproject,'WorldDirection'),forward),0.0001)
world=g.op('Add_VectorVector',out(deproject,'WorldLocation'),g.op('Multiply_VectorFloat',out(deproject,'WorldDirection'),g.op('Divide_DoubleDouble',numerator,denominator)))
result=g.pos(g.e.add_return_node());assert inp(result,'WorldPoint').is_valid()
link(world,inp(result,'WorldPoint'));g.begin(result)
g.comment('Deproject screen pixels onto a camera-parallel plane. Handles perspective, orthographic view, camera movement and viewport aspect ratio.')

g=G('DrawBladeSegment')
original=g.call_with(math+'BreakVector',{'InVec':g.arg('Start')});b=g.call_with(math+'BreakVector',{'InVec':g.arg('End')})
duration=g.op('FMax',g.get('TrailLifetime'),0.01)
cutoff=g.op('Subtract_DoubleDouble',g.arg('Now'),duration)
span=g.op('FMax',g.op('Subtract_DoubleDouble',out(b,'Z'),out(original,'Z')),0.000001)
fraction=g.op('Divide_DoubleDouble',g.op('Subtract_DoubleDouble',cutoff,out(original,'Z')),span)
fraction=out(g.call_with(math+'FClamp',{'Value':fraction,'Min':0,'Max':1}))
clipped=out(g.call_with(math+'VLerp',{'A':g.arg('Start'),'B':g.arg('End'),'Alpha':fraction}))
a=g.call_with(math+'BreakVector',{'InVec':clipped})
age=g.op('Subtract_DoubleDouble',g.arg('Now'),out(b,'Z'))
distance=g.op('Vector_Distance2D',clipped,g.arg('End'),akey='V1',bkey='V2')
condition=g.op('BooleanAND',g.op('Less_DoubleDouble',age,duration),g.op('Greater_DoubleDouble',distance,0.1))
branch=g.branch(condition);g.begin(branch)
def fade_for(point):
    value=g.op('Subtract_DoubleDouble',1,g.op('Divide_DoubleDouble',g.op('Subtract_DoubleDouble',g.arg('Now'),out(point,'Z')),duration))
    return out(g.call_with(math+'FClamp',{'Value':value,'Min':0,'Max':1}))
fade_a=fade_for(a);fade_b=fade_for(b)
height=g.op('FMax',g.op('Multiply_DoubleDouble',g.get('TrailWidth'),g.op('Multiply_DoubleDouble',g.op('Add_DoubleDouble',fade_a,fade_b),0.5)),1)
wa=out(g.call_with(g.class_path+'.BladeScreenToWorld',{'Point':clipped}),'WorldPoint')
wb=out(g.call_with(g.class_path+'.BladeScreenToWorld',{'Point':g.arg('End')}),'WorldPoint')
offset=out(g.call_with(math+'MakeVector',{'X':out(a,'X'),'Y':g.op('Add_DoubleDouble',out(a,'Y'),height),'Z':0}))
wo=out(g.call_with(g.class_path+'.BladeScreenToWorld',{'Point':offset}),'WorldPoint')
center=out(g.call_with(math+'VLerp',{'A':wa,'B':wb,'Alpha':0.5}))
dx=g.op('Subtract_VectorVector',wb,wa)
world_length=g.op('Vector_Distance',wa,wb,akey='V1',bkey='V2')
world_height=g.op('Vector_Distance',wa,wo,akey='V1',bkey='V2')
camera=g.call('/Script/Engine.GameplayStatics.GetPlayerCameraManager')
rotation=g.call('/Script/Engine.PlayerCameraManager.GetCameraRotation');link(out(camera),lib.find_self_pin(rotation))
normal=g.op('NegateVector',out(g.call_with(math+'GetForwardVector',{'InRot':out(rotation)})))
orientation=out(g.call_with(math+'MakeRotFromXZ',{'X':dx,'Z':normal}))
scale=out(g.call_with(math+'MakeVector',{'X':g.op('Divide_DoubleDouble',world_length,100),'Y':g.op('Divide_DoubleDouble',world_height,100),'Z':1}))
transform=out(g.call_with(math+'MakeTransform',{'Location':center,'Rotation':orientation,'Scale':scale}))
mesh=element(g,'BladeSegments',g.arg('SegmentIndex'));mid=element(g,'BladeMaterials',g.arg('SegmentIndex'))
set_a=target(g,'/Script/Engine.MaterialInstanceDynamic.SetScalarParameterValue',mid,{'ParameterName':'BladeFadeStart','Value':fade_a})
set_b=target(g,'/Script/Engine.MaterialInstanceDynamic.SetScalarParameterValue',mid,{'ParameterName':'BladeFadeEnd','Value':fade_b})
move=target(g,'/Script/Engine.SceneComponent.K2_SetWorldTransform',mesh,{'NewTransform':transform,'bSweep':'false','bTeleport':'true'})
show=target(g,'/Script/Engine.SceneComponent.SetVisibility',mesh,{'bNewVisibility':'true','bPropagateToChildren':'false'})
count=g.set('RenderedSegments',g.op('Add_IntInt',g.get('RenderedSegments'),1))
link(lib.find_then_pin(branch),lib.find_execute_pin(set_a));chain(g,set_a,set_b,move,show,count)
g.comment('Controller renders camera-facing reusable quads. Screen-space history, clipped ages, tapered width and independent fade material per segment. No collision or HUD.')

g=G('RenderBladeTrail')
last=g.call_with(math+'BreakVector',{'InVec':g.get('LastSample')})
alive=g.op('Less_DoubleDouble',g.op('Subtract_DoubleDouble',g.arg('Now'),out(last,'Z')),g.op('FMax',g.get('TrailLifetime'),0.01))
branch=g.branch(alive);g.begin(branch)
clear=g.own('ClearBladeTrail');link(lib.find_else_pin(branch),lib.find_execute_pin(clear))
lp=loop(g,0,g.op('Subtract_IntInt',length(g,'TrailSamples'),2));link(lib.find_then_pin(branch),inp(lp,'execute'))
n=length(g,'TrailSamples');first=g.op('SelectInt',g.get('WriteIndex'),0)
link(g.op('GreaterEqual_IntInt',n,64),inp(first.get_owning_node(),'bPickA'))
i=g.op('Percent_IntInt',g.op('Add_IntInt',first,out(lp,'Index')),64);j=g.op('Percent_IntInt',g.op('Add_IntInt',i,1),64)
draw=g.call_with(g.class_path+'.DrawBladeSegment',{'Start':element(g,'TrailSamples',i),'End':element(g,'TrailSamples',j),'Now':g.arg('Now'),'SegmentIndex':out(lp,'Index')})
link(out(lp,'LoopBody'),lib.find_execute_pin(draw))

g=G('ReadHeldBladeMouse')
viewport=g.call('/Script/Engine.PlayerController.GetViewportSize')
width=g.set('LastViewportX',out(viewport,'SizeX'));height=g.set('LastViewportY',out(viewport,'SizeY'));g.begin(width);g.after(width,height)
mouse=g.call('/Script/Engine.PlayerController.GetMousePosition')
valid=out(mouse)
for coordinate,size in [('LocationX','LastViewportX'),('LocationY','LastViewportY')]:
    valid=g.op('BooleanAND',valid,g.op('GreaterEqual_DoubleDouble',out(mouse,coordinate),0))
    valid=g.op('BooleanAND',valid,g.op('Less_DoubleDouble',out(mouse,coordinate),g.get(size)))
branch=g.branch(valid);g.after(height,branch)
clear=g.own('ClearBladeTrail');link(lib.find_else_pin(branch),lib.find_execute_pin(clear))
time=g.call('/Script/Engine.GameplayStatics.GetRealTimeSeconds')
sample=out(g.call_with(math+'MakeVector',{'X':out(mouse,'LocationX'),'Y':out(mouse,'LocationY'),'Z':out(time)}))
submit=g.call_with(g.class_path+'.SubmitBladePoint',{'Sample':sample});render=g.call_with(g.class_path+'.RenderBladeTrail',{'Now':out(time)})
link(lib.find_then_pin(branch),lib.find_execute_pin(submit));g.after(submit,render)

g=G('UpdateHeldBladeTrail')
hide=g.own('HideBladeTrail');g.begin(hide)
branch=g.branch(g.get('BladeHeld'));g.after(hide,branch)
read=g.own('ReadHeldBladeMouse');clear=g.own('ClearBladeTrail')
link(lib.find_then_pin(branch),lib.find_execute_pin(read));link(lib.find_else_pin(branch),lib.find_execute_pin(clear))
g=G('TickBladeTrail')
empty=g.op('EqualEqual_IntInt',length(g,'BladeSegments'),0)
branch=g.branch(empty);g.begin(branch)
initialize=g.own('InitializeBladeTrail');update=g.own('UpdateHeldBladeTrail')
link(lib.find_then_pin(branch),lib.find_execute_pin(initialize));g.after(initialize,update)
link(lib.find_else_pin(branch),lib.find_execute_pin(update))

# Preserve the controller's existing Gate/trace/cast/Damage nodes and connections.
e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph')
nodes=list(e.list_all_nodes())
tick=next(n for n in nodes if str(lib.get_node_title(n))=='Event Tick')
mouse=next(n for n in nodes if str(lib.get_node_title(n))=='Left Mouse Button')
gate=next(n for n in nodes if str(lib.get_node_title(n))=='Gate')
def insert(source,dest,function,pos):
    # These three owned wrapper calls are safe to regenerate without touching
    # the actual slicing logic downstream of Gate.Exit.
    for p in list(source.list_connected_pins()):
        node=p.get_owning_node()
        if str(lib.get_node_title(node)).replace(' ','')==function:e.remove_nodes([node])
    source.break_pin_links();dest.break_pin_links()
    call=e.add_call_function_node(lib.generated_class(bp).get_path_name()+'.'+function);assert call
    lib.set_node_pos(call,unreal.IntPoint(*pos))
    link(source,lib.find_execute_pin(call));link(lib.find_then_pin(call),dest)
insert(out(mouse,'Pressed'),inp(gate,'Open'),'BeginBladeStroke',(-650,450))
insert(out(mouse,'Released'),inp(gate,'Close'),'EndBladeStroke',(-650,750))
insert(lib.find_then_pin(tick),inp(gate,'Enter'),'TickBladeTrail',(-650,50))
e.add_comment_node('Blade trail shares Left Mouse Button with the existing slicing Gate. Press = fresh stroke; release = hide/reset. Tick updates owned components before the original hit test.',unreal.Vector2D(-1000,-180),unreal.Vector2D(900,1250))
lib.compile_blueprint(bp)
errors=[]
for graph in lib.list_graphs(bp):
    for node in unreal.BlueprintGraphEditor.get_graph_editor(graph).list_nodes_with_errors():
        errors.append([graph.get_name(),str(lib.get_node_title(node)),str(node.get_editor_property('ErrorMsg'))])
assert not errors,errors
cdo=unreal.get_default_object(lib.generated_class(bp))
for name,value in [('TrailLifetime',0.2),('TrailWidth',34),('MinPointDistance',1.5),('TrailDepth',150),('TrailMaterial',material),('BladeHeld',False)]:cdo.set_editor_property(name,value)
assert assets.save_loaded_asset(bp)

gm=unreal.load_asset('/Game/Root/Blueprints/Base/B_FruitGameMode');gm.modify()
unreal.get_default_object(lib.generated_class(gm)).set_editor_property('HUDClass',unreal.HUD)
lib.compile_blueprint(gm);assert assets.save_loaded_asset(gm)
assert unreal.get_default_object(lib.generated_class(gm)).get_editor_property('HUDClass')==unreal.HUD.static_class()
lib.refresh_all_open_blueprint_editors();assets.sync_browser_to_objects([bp.get_path_name()])
report={'controller':bp.get_path_name(),'renderer':'64 owned StaticMeshComponents','input':'existing Left Mouse Button Pressed/Released and Gate','lifetime':0.2,'compile_errors':errors,'hud_dependency':False}
(root/'Saved/MCP/blade-controller-setup.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BLADE_CONTROLLER_SAVED:'+json.dumps(report))
