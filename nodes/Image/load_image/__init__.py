from node import Node, NodeOutput, Output

from state import GlobalState
from fs import load_asset

from pathlib import Path

def load_image(node: dict, predecessors: list[tuple[dict, dict]], gs: GlobalState) -> NodeOutput:
    from PIL import Image

    data = node["data"]

    path: Path | None = None
    
    if (len(data["files"]) > 0):
        file = data["files"][0]
        
        path = load_asset(str(file["path"]))
     
    if not path:
        raise  FileNotFoundError(f"File not found: {path}")
        
    img = Image.open(path)
        
    return NodeOutput(id=node["id"], outputs=[
        Output(handle="image_output", value=img)
    ])

class LoadImage(Node):
    def __init__(self):
        identifier = "loadImage"
        author = "MonoPT"
        namespace = "core"
        version = "1.0"
        group = "Image"
        fn = load_image
        namespace = namespace
                
        super().__init__(identifier, author, version, group, namespace, fn)
        
__all__ = ["LoadImage"]