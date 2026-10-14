from worker.nodes.base import Node, NodeOutput, Output, get_connect_value_by_input_handle_name

from worker.execution.state import GlobalState

def invert_colors(node: dict, predecessors: list[tuple[dict, dict]], gs: GlobalState) -> NodeOutput:
    from PIL import Image, ImageOps
        
    input_image: Image.Image | None = get_connect_value_by_input_handle_name("image_input", predecessors)
    
    outputs = []
    
    if input_image:
        inverted = ImageOps.invert(input_image.convert("RGB"))

        outputs.append(
             Output(handle="image_output", value=inverted)
        )
    
    return NodeOutput(id=node["id"], outputs=outputs)

class InvertColors(Node):
    def __init__(self):
        identifier = "invertColor"
        author = "MonoPT"
        namespace = "core"
        version = "1.0"
        group = "Image"
        fn = invert_colors
        namespace = namespace
                
        super().__init__(identifier, author, version, group, namespace, fn)
        
__all__ = ["InvertColors"]