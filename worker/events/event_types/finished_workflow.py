from .eventType import EventType

class WorkflowFinished(EventType):
    name = "WorkflowFinished"
    
    def __init__(self, workflow_id: str):
        self.data = {"workflow_id": workflow_id}