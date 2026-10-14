from pprint import pprint
from worker.execution.state import GlobalState
import websockets
import json
import math
import polars as pl

from worker.events.event_types.df_data import DataframeUpdate
from fastapi import WebSocket

async def get_df_data(gs: GlobalState, ws: WebSocket, data: dict):
    page = int(data["page"])
    page_size = int(5)
    df_id = str(data["df_id"])
    table_id = str(data["table_id"])

    df = gs.get_df(df_id)

    if df is None:
        return

    total_rows = (
        df
        .select(pl.len().alias("n_rows"))
        .collect()
        .item(0, 0)
    )
    
    # Pagination

    start = page * page_size
    end = start + page_size
    
    page_df = df.slice(start, page_size)

    # Returning data
    total_pages = math.ceil(total_rows / page_size)

    json_str = page_df.collect().write_json()

    df_data = DataframeUpdate(
        df_data=json_str,
        df_id=df_id,
        page=page,
        total_pages=total_pages,
        table_id=table_id,
        total_entries=total_rows
    )

    await ws.send_json(df_data.to_dict())

__all__ = ["get_df_data"]