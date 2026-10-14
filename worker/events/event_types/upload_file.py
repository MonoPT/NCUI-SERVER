from .eventType import EventType

class UploadFileMetadata(EventType):
    name = "UploadFileMetadata"
    metadata: list[dict] # transfer_id, filename, folder, and exact size
    
    def __init__(self, metadata: list[dict]):
        self.data = {
            "metadata": metadata
        }