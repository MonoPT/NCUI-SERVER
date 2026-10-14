from worker.nodes.base import Node, NodeOutput, Output

from worker.execution.state import GlobalState

def func(node: dict, predecessors: list[tuple[dict, dict]], gs: GlobalState) -> NodeOutput:
    
    try:
        value = bool(node["data"]["bool"])
    except ValueError:
        value = False
    
    return NodeOutput(id=node["id"], outputs=[
        Output(handle="bool_output", value=value)
    ])

class BoolNode(Node):
    def __init__(self):
        identifier = "boolNode"
        author = "MonoPT"
        namespace = "core"
        version = "1.0"
        group = "Image"
        fn = func
        namespace = namespace
                
        super().__init__(identifier, author, version, group, namespace, fn)
        
__all__ = ["BoolNode"]