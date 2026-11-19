"""UMG owns all presentation; AHUD only creates and removes the Widget Blueprint."""
import unreal
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
L=unreal.BlueprintEditorLibrary;assets=unreal.EditorAssetLibrary
scope={};exec(compile((root/'Tools/BladeTrail/graph_helpers.py').read_text(encoding='utf-8'),'graph_helpers.py','exec'),scope)
Graph=scope['Graph'];inp=scope['inp'];out=scope['out'];link=scope['link'];literal=scope['literal']
widget=unreal.load_asset('/Game/Root/Blueprints/UI/WBP_FruitHUD');hud=unreal.load_asset('/Game/Root/Blueprints/UI/B_FruitHUD')
pc=unreal.load_asset('/Game/Root/Blueprints/Base/B_FruitPlayerController');gm=unreal.load_asset('/Game/Root/Blueprints/Base/B_FruitGameMode')
math='/Script/Engine.KismetMathLibrary.'
def variable(bp,name,kind):
    if name not in set(map(str,L.list_member_variable_names(bp,include_inherited_members=False))):assert L.add_member_variable(bp,name,kind)
    L.set_blueprint_variable_category(bp,name,'HUD')
def function(bp,name,args=()):
    old=L.find_graph(bp,name)
    e=unreal.BlueprintGraphEditor.get_graph_editor(old) if old else unreal.BlueprintGraphEditor.create_and_edit_function_graph(bp,name)
    e.remove_nodes([n for n in e.list_all_nodes() if not isinstance(n,unreal.K2Node_FunctionEntry)])
    entry=next(n for n in e.list_all_nodes() if isinstance(n,unreal.K2Node_FunctionEntry))
    for key,kind in args:
        if not L.find_output_pin(entry,key).is_valid():assert e.add_graph_input_parameter(key,kind)
def external_get(g,name,bp,target):
    n=g.pos(g.e.add_get_member_variable_node(name,L.generated_class(bp).get_path_name()));link(target,L.find_self_pin(n));return out(n,name)
def target(g,path,obj,values):
    n=g.call_with(path,values);link(obj,L.find_self_pin(n));return n
def position(n,x,y):L.set_node_pos(n,unreal.IntPoint(x,y))
def event_call(bp,native,title,fn,xy=(0,0)):
    e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph')
    event=next((n for n in e.list_all_nodes() if isinstance(n,unreal.K2Node_Event) and str(L.get_node_title(n))==title),None)
    if not event:event=L.add_event_override(bp,native,unreal.IntPoint(*xy))
    L.find_then_pin(event).break_pin_links()
    call=e.add_call_function_node(L.generated_class(bp).get_path_name()+'.'+fn)
    link(L.find_then_pin(event),L.find_execute_pin(call));position(event,*xy);position(call,xy[0]+300,xy[1])
    return event,call

variable(widget,'FruitController',L.get_object_reference_type(L.generated_class(pc)))
variable(widget,'FruitGameMode',L.get_object_reference_type(L.generated_class(gm)))
for fn in ['CacheHUDReferences','RefreshHUD','UpdateScore','UpdateTimer','UpdateHealth']:function(widget,fn)
function(widget,'UpdateHeart',[('Heart',L.get_object_reference_type(unreal.Image)),('Filled',L.get_basic_type_by_name('bool'))])
variable(hud,'GameWidget',L.get_object_reference_type(L.generated_class(widget)))
function(hud,'ShowGameWidget');function(hud,'RemoveGameWidget')
for b in [widget,hud]:L.compile_blueprint(b)

g=Graph(widget,'CacheHUDReferences')
owner=g.call('/Script/UMG.Widget.GetOwningPlayer');mode=g.call('/Script/Engine.GameplayStatics.GetGameMode')
settings=unreal.get_default_object(unreal.load_class(None,'/Script/BlueprintGraph.BlueprintEditorSettings'))
previous=settings.get_editor_property('bAutoCastObjectConnections');settings.set_editor_property('bAutoCastObjectConnections',True)
try:setpc=g.set('FruitController',out(owner));setgm=g.set('FruitGameMode',out(mode))
finally:settings.set_editor_property('bAutoCastObjectConnections',previous)
g.begin(setpc);g.after(setpc,setgm)
position(owner,0,180);position(mode,500,180);position(setpc,400,0);position(setgm,900,0)

g=Graph(widget,'UpdateScore')
score=external_get(g,'Score',pc,g.get('FruitController'))
label=out(g.call_with('/Script/Engine.KismetStringLibrary.BuildString_Int',{'Prefix':'SCORE: ','InInt':score}))
text=out(g.call_with('/Script/Engine.KismetTextLibrary.Conv_StringToText',{'InString':label}))
apply=target(g,'/Script/UMG.TextBlock.SetText',g.get('ScoreText'),{'InText':text});g.begin(apply)
position(apply,1100,0)

g=Graph(widget,'UpdateTimer')
timer=target(g,L.generated_class(gm).get_path_name()+'.GetRoundTimeText',g.get('FruitGameMode'),{})
text=out(g.call_with('/Script/Engine.KismetTextLibrary.Conv_StringToText',{'InString':out(timer,'TimeText')}))
apply=target(g,'/Script/UMG.TextBlock.SetText',g.get('TimerText'),{'InText':text});g.begin(apply);position(apply,1050,0)

g=Graph(widget,'UpdateHeart')
alpha=out(g.call_with(math+'SelectFloat',{'A':1,'B':0.3,'bPickA':g.arg('Filled')}))
apply=target(g,'/Script/UMG.Widget.SetRenderOpacity',g.arg('Heart'),{'InOpacity':alpha});g.begin(apply)
position(apply,650,0)

g=Graph(widget,'UpdateHealth')
health=external_get(g,'CurrentHealth',pc,g.get('FruitController'))
calls=[]
for i in range(3):
    condition=g.op('Greater_IntInt',health,i)
    call=g.own('UpdateHeart');link(g.get('Heart'+str(i+1)),inp(call,'Heart'));link(condition,inp(call,'Filled'))
    calls.append(call);position(call,450+i*360,0)
    position(condition.get_owning_node(),450+i*360,230)
g.begin(calls[0]);g.after(calls[0],calls[1]);g.after(calls[1],calls[2])

g=Graph(widget,'RefreshHUD')
a=out(g.call_with('/Script/Engine.KismetSystemLibrary.IsValid',{'Object':g.get('FruitController')}))
b=out(g.call_with('/Script/Engine.KismetSystemLibrary.IsValid',{'Object':g.get('FruitGameMode')}))
ready=g.branch(g.op('BooleanAND',a,b));g.begin(ready)
score=g.own('UpdateScore');timer=g.own('UpdateTimer');health=g.own('UpdateHealth')
link(L.find_then_pin(ready),L.find_execute_pin(score));g.after(score,timer);g.after(timer,health)
position(ready,700,0);position(score,1000,0);position(timer,1250,0);position(health,1500,0)

L.compile_blueprint(widget)
e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(widget,'EventGraph')
e.remove_nodes([n for n in e.list_all_nodes() if isinstance(n,unreal.K2Node_CallFunction) and str(L.get_node_title(n)).replace(' ','') in {'CacheHUDReferences','RefreshHUD'}])
event,call=event_call(widget,'Construct','Event Construct','CacheHUDReferences',(0,0))
e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(widget,'EventGraph')
refresh=e.add_call_function_node(L.generated_class(widget).get_path_name()+'.RefreshHUD');link(L.find_then_pin(call),L.find_execute_pin(refresh));position(refresh,650,0)
event_call(widget,'Tick','Event Tick','RefreshHUD',(0,350))

g=Graph(hud,'ShowGameWidget')
already=g.branch(out(g.call_with('/Script/Engine.KismetSystemLibrary.IsValid',{'Object':g.get('GameWidget')})));g.begin(already)
owner=g.call('/Script/Engine.HUD.GetOwningPlayerController')
create=g.call_with('/Script/UMG.WidgetBlueprintLibrary.Create',{'WidgetType':L.generated_class(widget).get_path_name(),'OwningPlayer':out(owner)})
settings.set_editor_property('bAutoCastObjectConnections',True)
try:store=g.set('GameWidget',out(create))
finally:settings.set_editor_property('bAutoCastObjectConnections',previous)
add=target(g,'/Script/UMG.UserWidget.AddToViewport',g.get('GameWidget'),{'ZOrder':0})
link(L.find_else_pin(already),L.find_execute_pin(create));g.after(create,store);g.after(store,add)
for n,x,y in [(already,300,0),(owner,300,220),(create,650,0),(store,1100,0),(add,1450,0)]:position(n,x,y)

g=Graph(hud,'RemoveGameWidget')
valid=g.branch(out(g.call_with('/Script/Engine.KismetSystemLibrary.IsValid',{'Object':g.get('GameWidget')})));g.begin(valid)
remove=target(g,'/Script/UMG.Widget.RemoveFromParent',g.get('GameWidget'),{})
link(L.find_then_pin(valid),L.find_execute_pin(remove));position(remove,700,0)

# Delete only the previous Canvas implementation and its owned event calls.
e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(hud,'EventGraph')
old_names={'InitializeHUDData','DrawGameHUD','DrawHUDLabel','GetHeartOpacity'}
e.remove_nodes([n for n in e.list_all_nodes() if str(L.get_node_title(n)).replace(' ','') in old_names|{'ShowGameWidget','RemoveGameWidget'} or str(L.get_node_title(n))=='Event ReceiveDrawHUD'])
for name in old_names:
    old=L.find_graph(hud,name)
    if old:L.remove_graph(hud,old)
for name in ['FruitController','FruitGameMode','HeartTexture','HUDFont']:
    if name in set(map(str,L.list_member_variable_names(hud,include_inherited_members=False))):e.remove_member_variable(name)
L.compile_blueprint(hud)
event_call(hud,'ReceiveBeginPlay','Event BeginPlay','ShowGameWidget')
event_call(hud,'ReceiveEndPlay','Event EndPlay','RemoveGameWidget',(0,350))
for b in [widget,hud]:
    L.compile_blueprint(b)
    errors=[str(n.get_editor_property('ErrorMsg')) for graph in L.list_graphs(b) for n in unreal.BlueprintGraphEditor.get_graph_editor(graph).list_nodes_with_errors()]
    assert not errors,(b.get_name(),errors)
    assert assets.save_loaded_asset(b)
print('UMG_MIGRATION_COMPLETE',widget.get_path_name(),hud.get_path_name())
