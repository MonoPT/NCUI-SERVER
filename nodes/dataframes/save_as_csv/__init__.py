from node import Node, NodeOutput, Output, get_connect_value_by_input_handle_name
import polars as pl

from state import GlobalState
from fs import storage_folder, UploadFile, UploadFolder
from execution_context import filename as safe_filename

def func(node: dict, predecessors: list[tuple[dict, dict]], gs: GlobalState) -> NodeOutput:
    from PIL import Image
            
    input_df: pl.LazyFrame | None = get_connect_value_by_input_handle_name("df_input", predecessors)
    filename: str | None = get_connect_value_by_input_handle_name("string_input", predecessors)
                
    if not filename:
        filename = node["data"]["filename"] or "output"

    if not filename.endswith(".csv"):
        filename = f"{filename}.csv"

    filename = safe_filename(filename)
    uploads = []
    if input_df is not None:
        output_dir = storage_folder("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / filename
        if path.is_symlink():
            raise ValueError("Symlink output")
        input_df.collect().write_csv(path)
        uploads.append(UploadFile(path=path, folder=UploadFolder.OUTPUT))
    
    return NodeOutput(id=node["id"], outputs=[], files_to_upload=uploads)

class SaveDFasCSV(Node):
    def __init__(self):
        identifier = "saveDFasCSV"
        author = "MonoPT"
        namespace = "core"
        version = "1.0"
        group = "dataframe"
        fn = func
        namespace = namespace
                
        super().__init__(identifier, author, version, group, namespace, fn)
        
__all__ = ["SaveDFasCSV"]