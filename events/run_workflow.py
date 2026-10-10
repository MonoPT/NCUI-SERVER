import json
from message import Message
from dag import build_dag, proccess_dag
from events.event_types.started_workflow import WorkflowStarted

from node import Node
from state import GlobalState
from fastapi import WebSocket

async def run_workflow(message: Message, ws: WebSocket, node_list: list[Node], gs: GlobalState):
    workflow = json.loads(message.data["workflow_data"])
    workflow_id = workflow["workflow_id"]
    await ws.send_json(WorkflowStarted(workflow_id=workflow_id).to_dict())
    for dag in build_dag(workflow) or []:
        await proccess_dag(dag, workflow, ws, workflow_id, node_list, gs)
