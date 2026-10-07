from pprint import pprint
from node import Node, NodeOutput, Output, get_connect_value_by_input_handle_name
import polars as pl

import polars as pl
from state import GlobalState
import uuid

def func(node: dict, predecessors: list[tuple[dict, dict]], gs: GlobalState) -> NodeOutput:
    from PIL import Image
    import json
            
    input_df: pl.LazyFrame | None = get_connect_value_by_input_handle_name("df_input", predecessors)

    df_id = uuid.uuid4()
    
    if input_df is not None:
        gs.push_df(str(df_id), input_df)
        
    return NodeOutput(id=node["id"], outputs=[], return_data=f"{{\"df_id\": \"{str(df_id)}\"}}")

class DisplayDF(Node):
    def __init__(self):
        identifier = "displayDF"
        author = "MonoPT"
        namespace = "core"
        version = "1.0"
        group = "dataframe"
        fn = func
        namespace = namespace
                
        super().__init__(identifier, author, version, group, namespace, fn)
        
__all__ = ["DisplayDF"]