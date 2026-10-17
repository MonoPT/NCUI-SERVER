from .eventType import EventType


class WorkflowLog(EventType):
    name = "WorkflowLog"

    def __init__(
        self,
        workflow_id: str,
        node_id: str,
        stream: str,
        text: str,
    ):
        self.data = {
            "workflow_id": workflow_id,
            "node_id": node_id,
            "stream": stream,
            "text": text,
        }
