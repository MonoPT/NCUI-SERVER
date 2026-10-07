class Message:
    name: str
    data: dict[str, str]
        
    def __init__(self, name: str, data: dict):
        self.name = name
        self.data = data