from typing import Any
from worker.nodes.base import Node, NodeOutput, Output, get_connect_value_by_input_handle_name
from worker.execution.state import GlobalState

def func(node: dict, predecessors: list[tuple[dict, dict]], gs: GlobalState) -> NodeOutput:
    
    condition: bool | None = get_connect_value_by_input_handle_name("condition_input", predecessors)
    
    true_val: Any | None = get_connect_value_by_input_handle_name("input_if_true", predecessors)
    false_val: Any | None = get_connect_value_by_input_handle_name("input_if_false", predecessors)
    
    disable_after_handle = "output_if_false"
    
    if not condition:
        disable_after_handle = "output_if_true"
    
    return NodeOutput(id=node["id"], outputs=[
        Output(handle="output_if_true", value=true_val),
        Output(handle="output_if_false", value=false_val)
    ], disable_nodes_after_handle=disable_after_handle)

class branchNode(Node):
    def __init__(self):
        identifier = "branchNode"
        author = "MonoPT"
        namespace = "core"
        version = "1.0"
        group = "control_flow"
        fn = func
        namespace = namespace
                
        super().__init__(identifier, author, version, group, namespace, fn)
        
__all__ = ["branchNode"]