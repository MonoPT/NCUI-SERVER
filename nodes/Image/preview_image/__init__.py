from node import Node, NodeOutput, Output, get_connect_value_by_input_handle_name
from state import GlobalState
from pathlib import Path
from fs import storage_folder, UploadFile, UploadFolder, resolve_path_to_main_machine

def main(node: dict, predecessors: list[tuple[dict, dict]], gs: GlobalState) -> NodeOutput:
    from PIL import Image
    import uuid
            
    input_image: Image.Image | None = get_connect_value_by_input_handle_name("image_input", predecessors)
    
    return_data = None

    file_upload = list()
    
    if input_image:
        filename = f"{uuid.uuid4()}".replace("-", "_")

        temp_f = storage_folder("temp")
        
        save_path = Path(f"{temp_f}/{filename}.jpg")
        
        input_image = input_image.convert("RGB")
        
        input_image.save(save_path)
        
        return_data = f"{{\"value\": \"{resolve_path_to_main_machine(save_path)}\"}}"

        file_upload.append(UploadFile(path=save_path, folder=UploadFolder.TEMP))
    
    return NodeOutput(
        id=node["id"], 
        outputs=[], 
        return_data=return_data,
        files_to_upload=file_upload
    )

class PreviewImage(Node):
    def __init__(self):
        identifier = "previewImage"
        author = "MonoPT"
        namespace = "core"
        version = "1.0"
        group = "Image"
        fn = main
        namespace = namespace
                
        super().__init__(identifier, author, version, group, namespace, fn)
        
__all__ = ["PreviewImage"]