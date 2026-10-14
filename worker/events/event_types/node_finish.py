from .eventType import EventType

class NodeExecutionFinish(EventType):
    name = "NodeExecutionFinish"
    
    def __init__(self, workflow_id: str, node_id: str, return_data: None | str = None):
        self.data = {"workflow_id": workflow_id, "node_id": node_id, "return_data": return_data}