from node import Node
import json

from load_nodes import load_nodes

from message import Message

from events.event_types.container_specs import ContainerSpecs

from state import GlobalState
from dataframes import get_df_data

from fastapi import WebSocket

async def proccess_message(msg: str, ws: WebSocket, node_list: list[Node], gs: GlobalState):
    import json
    from events.run_workflow import run_workflow
    
    data = json.loads(msg)
    
    message = Message(name=data["name"], data=data["data"])

    if message.name == "run_workflow":
        await run_workflow(message, ws, node_list, gs)
        return

    if message.name == "ping_machine_perf": # Sends container specs
        await ws.send_json(
            ContainerSpecs().to_dict()
        ) 
        return

    if message.name == "dataframe_get_data": # Handle the dynamic dfs data fetching
        try:
            parsed_data = json.loads(msg)
            await get_df_data(gs, ws, json.loads(parsed_data["data"]["dataframe_get_data"]))
        except Exception as  e:
            print(f"Error ocurred get dataframe: {e}")
        return

    ## No action found for message
    print(f"Action for {message.name} not implemented")
    await ws.send_text(f"Action {message.name} not implemented")
