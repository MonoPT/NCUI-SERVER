from .eventType import EventType

class NodeExecutionError(EventType):
    name = "NodeExecutionError"
    
    def __init__(self, workflow_id: str, node_id: str, msg: str):
        self.data = {"workflow_id": workflow_id, "node_id": node_id, "msg": msg}