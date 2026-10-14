from worker.nodes.base import Node, NodeOutput, Output

from worker.execution.state import GlobalState

def func(node: dict, predecessors: list[tuple[dict, dict]], gs: GlobalState) -> NodeOutput:
    
    try:
        value = float(node["data"]["float"])
    except ValueError:
        value = 0.0
    
    return NodeOutput(id=node["id"], outputs=[
        Output(handle="float_output", value=value)
    ])

class FloatNode(Node):
    def __init__(self):
        identifier = "floatNode"
        author = "MonoPT"
        namespace = "core"
        version = "1.0"
        group = "Image"
        fn = func
        namespace = namespace
                
        super().__init__(identifier, author, version, group, namespace, fn)
        
__all__ = ["FloatNode"]