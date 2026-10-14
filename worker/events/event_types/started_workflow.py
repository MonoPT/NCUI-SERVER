from .eventType import EventType

class WorkflowStarted(EventType):
    name = "WorkflowStarted"
    
    def __init__(self, workflow_id: str):
        self.data = {"workflow_id": workflow_id}