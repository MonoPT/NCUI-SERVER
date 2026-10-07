from typing import Any
import polars as pl


class GlobalState:
    """
        App global stated that is passed on every node execution context. 
        Can be used to store data that should be acessible after the workflow finished. e.g: Models, Dataframes, etc...
    """
        
    models: dict[str, Any]
    dataframes: dict[str, pl.LazyFrame]

    def __init__(self):
        self.models = {}
        self.dataframes = {}

    def push_df(self, node_id: str, df: pl.LazyFrame):
        self.dataframes[node_id] = df

    def get_df(self, node_id: str):
        return self.dataframes.get(node_id)