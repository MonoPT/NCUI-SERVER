from worker.nodes.base import Node, NodeOutput, Output, get_connect_value_by_input_handle_name

from worker.execution.state import GlobalState

def string(node: dict, predecessors: list[tuple[dict, dict]], gs: GlobalState) -> NodeOutput:
    string_data = node["data"]["string"]
    
    return NodeOutput(id=node["id"], outputs=[
        Output(handle="string_output", value=string_data)
    ])

class StringNode(Node):
    def __init__(self):
        identifier = "stringNode"
        author = "MonoPT"
        namespace = "core"
        version = "1.0"
        group = "Image"
        fn = string
        namespace = namespace
                
        super().__init__(identifier, author, version, group, namespace, fn)
        
__all__ = ["StringNode"]