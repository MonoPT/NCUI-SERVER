from .eventType import EventType

class UploadFileMetadata(EventType):
    name = "UploadFileMetadata"
    metadata: list[tuple[str, str]] # (filename, folder_key)
    
    def __init__(self, metadata: list[tuple[str, str]]):
        self.data = {
            "metadata": metadata
        }