from .eventType import EventType

class NodeSkipped(EventType):
    name = "NodeSkipped"
    
    def __init__(self, workflow_id: str, node_id: str):
        self.data = {"workflow_id": workflow_id, "node_id": node_id, "msg": ""}