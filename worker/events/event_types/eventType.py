class EventType:
    name: str
    data: dict
    
    def __init__(self, name: str, data: dict):
        self.name = name
        self.data = data
        
    def to_dict(self):
        return {
            "name": self.name,
            "data": self.data
        }