from .eventType import EventType

class DataframeUpdate(EventType):
    name = "DataframeUpdate"
    page: int
    total_pages: int
    df_id: str
    table_id: str
    total_entries: int
    df_data: str
    
    def __init__(self, page: int, total_pages: int, df_id: str, table_id: str, total_entries: int, df_data: str):
        self.data = {
            "page": page,
            "total_pages": total_pages,
            "df_id": df_id,
            "table_id": table_id,
            "total_entries": total_entries,
            "df_data": df_data
        }