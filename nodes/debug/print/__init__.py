from worker.nodes.base import Node, NodeOutput, Output, get_connect_value_by_input_handle_name
from typing import Any

from worker.execution.state import GlobalState

def print_fn(node: dict, predecessors: list[tuple[dict, dict]], gs: GlobalState) -> NodeOutput:
    value: Any | None = get_connect_value_by_input_handle_name("any_input", predecessors)
    
    from pprint import pprint
    
    pprint(f"printing: {value}")
        
    return NodeOutput(id=node["id"], outputs=[], return_data=f"{{\"value\": \"{str(value)}\"}}")

class PrintNode(Node):
    def __init__(self):
        identifier = "printNode"
        author = "MonoPT"
        namespace = "core"
        version = "1.0"
        group = "Image"
        fn = print_fn
        namespace = namespace
                
        super().__init__(identifier, author, version, group, namespace, fn)
        
__all__ = ["PrintNode"]