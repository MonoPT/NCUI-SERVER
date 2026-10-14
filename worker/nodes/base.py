from typing import Any
from typing import TypeVar
from collections.abc import Callable
from worker.execution.state import GlobalState

from pathlib import Path
from enum import Enum

T = TypeVar("T")

class Output:
    handle: str
    value: Any
    
    def __init__(self, handle: str, value: Any):
            self.handle = handle
            self.value = value

class NodeOutput:
    node_id: str
    outputs: list[Output]
    return_data: None | str
    disable_nodes_after_handle: str | None # Used for control flow nodes
    files_to_upload: list[UploadFile] # List of possible files to upload to client
    
    def __init__(self, id: str, outputs: list[Output], return_data: None | str = None, disable_nodes_after_handle: str | None = None, files_to_upload: list[UploadFile] = list()):
        self.node_id = id
        self.outputs = outputs
        self.return_data = return_data
        self.disable_nodes_after_handle = disable_nodes_after_handle
        self.files_to_upload = files_to_upload
    
def get_connect_value_by_input_handle_name(
    target: str,
    predecessors: list[tuple[dict, dict]]
) -> T | None:    
    """
    Finds the value of the node connected to a pin (handle) by the name of the input handle
    """
    for node in predecessors:
        if node[0]["targetHandle"] == target:
            handle = node[0]["sourceHandle"]
            
            #pyrefly:ignore
            for output in node[1].outputs:
                if output.handle == handle:
                    return output.value
        
    return None
    
class Node:
    node_identifier: str # Name of the node
    node_author: str # Name of the author
    node_version: str # Version
    namespace: str # NameSpace
    
    node_group: str # Group it belongs to. eg: Image, control flow, operators, etc...
    
    node_fn: Callable[[dict, list[tuple[dict, dict]], GlobalState], NodeOutput]
    
    def __init__(self, identifier: str, author: str, version: str, group: str, namespace: str, fn: Callable[[dict, list[tuple[dict, dict]], GlobalState], NodeOutput]):
        self.node_identifier = identifier
        self.node_author = author
        self.node_version = version
        self.node_group = group
        self.node_fn = fn
        self.namespace = namespace
        
##
class UploadFolder(Enum):
    TEMP = "temp"
    OUTPUT = "assets/output"

class UploadFile:
    path: Path
    folder: UploadFolder

    def __init__(self, path: Path, folder: UploadFolder):
        self.path = path
        self.folder = folder
    
__all__ = ["get_connect_value_by_input_handle_name", "Output", "NodeOutput", "Node", "UploadFile", "UploadFolder"]
    
    