import time
from uuid import uuid4

from node import Node, NodeOutput, Output, get_connect_value_by_input_handle_name
from state import GlobalState
from fs import assets_folder, UploadFile, UploadFolder

def save_image(node: dict, predecessors: list[tuple[dict, dict]], gs: GlobalState) -> NodeOutput:
    from PIL import Image
            
    input_image: Image.Image | None = get_connect_value_by_input_handle_name("image_input", predecessors)
    filename: str | None = get_connect_value_by_input_handle_name("string_input", predecessors)
                
    if not filename:
        filename = node["data"]["filename"] or str(uuid4())

    filename = str(filename.lstrip("/"))

    assets_path = assets_folder()
    
    full_path = assets_path / "output" / f"{filename}_{time.time()}.jpg"
    
    print(f"Saving image to {full_path}")

    file_upload = list()
    
    if input_image:
        input_image.save(full_path)

        file_upload.append(UploadFile(path=full_path, folder=UploadFolder.OUTPUT))
        
    return NodeOutput(id=node["id"], outputs=[], files_to_upload=file_upload)

class SaveImage(Node):
    def __init__(self):
        identifier = "saveImage"
        author = "MonoPT"
        namespace = "core"
        version = "1.0"
        group = "Image"
        fn = save_image
        namespace = namespace
                
        super().__init__(identifier, author, version, group, namespace, fn)
        
__all__ = ["SaveImage"]