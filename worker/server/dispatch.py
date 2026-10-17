import asyncio
import json
from worker.nodes.base import Node
from worker.messages import Message
from worker.events.event_types.container_specs import ContainerSpecs
from worker.execution.state import GlobalState
from worker.dataframes import get_df_data
from worker.terminal.manager import (
    TerminalManager,
    TerminalMessageError,
    session_id_from_message,
)
from fastapi import WebSocket


async def _run_owned_workflow(message, ws, node_list, gs):
    from worker.events.run_workflow import run_workflow
    from worker.execution.context import (
        ExecutionSocket,
        execution_context,
        owner_context,
        owner_id,
    )

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


async def proccess_message(
    msg: str,
    ws: WebSocket,
    node_list: list[Node],
    gs: GlobalState,
    terminal_manager: TerminalManager | None = None,
):
    from worker.execution.context import ExecutionSocket, cache_lock

    data = json.loads(msg)
    message = Message(name=data["name"], data=data["data"])

    if message.name in {
        "terminal_open",
        "terminal_input",
        "terminal_resize",
        "terminal_close",
    }:
        await _process_terminal_message(message, ws, terminal_manager)
        return

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


async def _process_terminal_message(
    message: Message,
    websocket: WebSocket,
    terminal_manager: TerminalManager | None,
) -> None:
    try:
        session_id = session_id_from_message(message.data)
    except TerminalMessageError:
        return

    if terminal_manager is None:
        await websocket.send_json(
            {
                "name": "terminal_error",
                "data": {
                    "session_id": session_id,
                    "message": "Terminal support is unavailable",
                },
            }
        )
        return

    try:
        if message.name == "terminal_open":
            await terminal_manager.open(message.data)
            return

        if message.name == "terminal_input":
            await terminal_manager.input(message.data)
            return

        if message.name == "terminal_resize":
            await terminal_manager.resize(message.data)
            return

        await terminal_manager.close(session_id)
    except TerminalMessageError as error:
        await terminal_manager.error(session_id, str(error))
