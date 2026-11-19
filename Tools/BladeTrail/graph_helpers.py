"""Small Unreal Blueprint graph-authoring helpers; no asset mutations on import."""
import unreal
lib=unreal.BlueprintEditorLibrary
math='/Script/Engine.KismetMathLibrary.'

def inp(n,key):
    p=lib.find_input_pin(n,key);assert p.is_valid(),n.get_name()+'.'+key
    return p
def out(n,key='ReturnValue'):
    p=lib.find_output_pin(n,key);assert p.is_valid(),n.get_name()+'.'+key
    return p
def link(a,b):assert a.try_create_connection(b),str(a.get_pin_name())+' -> '+str(b.get_pin_name())
def literal(n,key,value):assert inp(n,key).set_pin_value(str(value)),key

class Graph:
    def __init__(self,bp,name):
        self.e=unreal.BlueprintGraphEditor.get_graph_editor(lib.find_graph(bp,name))
        self.class_path=lib.generated_class(bp).get_path_name()
        self.nodes=0
        self.entry=next(n for n in self.e.list_all_nodes() if isinstance(n,unreal.K2Node_FunctionEntry))
    def pos(self,n):
        i=self.nodes;self.nodes+=1
        lib.set_node_pos(n,unreal.IntPoint(250+(i%7)*290,(i//7)*240))
        return n
    def call(self,path):
        n=self.e.add_call_function_node(path);assert n,path
        return self.pos(n)
    def own(self,name):return self.call(self.class_path+'.'+name)
    def get(self,name):return out(self.pos(self.e.add_get_member_variable_node(name)),name)
    def set(self,name,value=None):
        n=self.pos(self.e.add_set_member_variable_node(name))
        if value is not None:
            if isinstance(value,unreal.BlueprintGraphPin):link(value,inp(n,name))
            else:literal(n,name,value)
        return n
    def arg(self,name):return out(self.entry,name)
    def begin(self,node):link(self.e.find_graph_entry_pin(),lib.find_execute_pin(node))
    def after(self,a,b):link(lib.find_then_pin(a),lib.find_execute_pin(b))
    def branch(self,condition):
        n=self.pos(self.e.add_branch_node());link(condition,lib.find_condition_pin(n));return n
    def op(self,name,a,b=None,akey='A',bkey='B'):
        n=self.call(math+name)
        for key,val in [(akey,a),(bkey,b)]:
            if isinstance(val,unreal.BlueprintGraphPin):link(val,inp(n,key))
        for key,val in [(akey,a),(bkey,b)]:
            if val is not None and not isinstance(val,unreal.BlueprintGraphPin):literal(n,key,val)
        return out(n)
    def call_with(self,path,values):
        n=self.call(path)
        for key,val in values.items():
            if isinstance(val,unreal.BlueprintGraphPin):link(val,inp(n,key))
            else:literal(n,key,val)
        return n
    def comment(self,text):
        self.e.add_comment_node(text,unreal.Vector2D(-50,-170),unreal.Vector2D(2450,max(750,((self.nodes+6)//7)*240+250)))
