from node import Node, NodeOutput, Output

from state import GlobalState

def func(node: dict, predecessors: list[tuple[dict, dict]], gs: GlobalState) -> NodeOutput:
    
    try:
        value = int(node["data"]["int"])
    except ValueError:
        value = 0
    
    return NodeOutput(id=node["id"], outputs=[
        Output(handle="int_output", value=value)
    ])

class IntNode(Node):
    def __init__(self):
        identifier = "intNode"
        author = "MonoPT"
        namespace = "core"
        version = "1.0"
        group = "Image"
        fn = func
        namespace = namespace
                
        super().__init__(identifier, author, version, group, namespace, fn)
        
__all__ = ["IntNode"]