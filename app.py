import asyncio
import json
from node import Node
from message import Message
from events.event_types.container_specs import ContainerSpecs
from state import GlobalState
from dataframes import get_df_data
from fastapi import WebSocket


async def _run_owned_workflow(message, ws, node_list, gs):
    from events.run_workflow import run_workflow
    from execution_context import owner_context, execution_context, owner_id, ExecutionSocket

    scoped_ws = ExecutionSocket(ws, message.data["execution_id"])
    owner_token = owner_context.set(message.data.get("owner_id", ""))
    execution_token = execution_context.set(message.data["execution_id"])
    workflow_id = ""
    terminal = "WorkflowFinished"
    terminal_data = {}
    try:
        workflow_id = json.loads(message.data["workflow_data"]).get("workflow_id", "")
        owner_id()
        await run_workflow(message, scoped_ws, node_list, gs.for_owner(owner_id()))
    except asyncio.CancelledError:
        terminal = "WorkflowError"
        terminal_data["msg"] = "Execution cancelled"
        raise
    except Exception as error:
        terminal = "WorkflowError"
        terminal_data["msg"] = str(error)
    finally:
        # Exactly one terminal acknowledgement, including parse/build/owner errors.
        # NodeExecutionError is not terminal: other DAGs can still be running.
        try:
            await scoped_ws.send_json({"name": terminal, "data": {"workflow_id": workflow_id, **terminal_data}})
        finally:
            execution_context.reset(execution_token)
            owner_context.reset(owner_token)


async def proccess_message(msg: str, ws: WebSocket, node_list: list[Node], gs: GlobalState):
    from execution_context import cache_lock, ExecutionSocket

    data = json.loads(msg)
    message = Message(name=data["name"], data=data["data"])
    if message.name == "run_workflow":
        async with cache_lock:
            await _run_owned_workflow(message, ws, node_list, gs)
        return

    if message.name == "ping_machine_perf":
        await ws.send_json(ContainerSpecs().to_dict())
        return

    if message.name == "dataframe_get_data":
        scoped_ws = ExecutionSocket(ws, message.data["execution_id"])
        try:
            owner = message.data["owner_id"]
            await get_df_data(gs.for_owner(owner), scoped_ws, json.loads(message.data["dataframe_get_data"]))
        except Exception as error:
            print(f"Error occurred getting dataframe: {error}")
        finally:
            # Missing dataframe and error paths must also release server authority.
            await scoped_ws.send_json({"name": "ExecutionComplete", "data": {}})
        return

    print(f"Action for {message.name} not implemented")
    await ws.send_text(f"Action {message.name} not implemented")
