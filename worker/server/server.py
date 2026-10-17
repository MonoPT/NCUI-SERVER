import asyncio

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from worker.nodes.base import Node
from worker.nodes.discovery import load_nodes

from worker.server.dispatch import proccess_message
from worker.terminal import TerminalManager
from worker.execution.state import GlobalState

from worker.events.event_types.container_specs import ContainerSpecs

# Import Routes
from worker.server.files import router as filesRouter


# States
node_list: list[Node] = load_nodes()

global_state = GlobalState()

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()

    terminal_manager = TerminalManager(websocket.send_json)

    container_specs = await asyncio.to_thread(ContainerSpecs)
    await websocket.send_json(container_specs.to_dict())

    try:
        while True:
            message = await websocket.receive_text()

            await proccess_message(
                message,
                websocket,
                node_list,
                global_state,
                terminal_manager,
            )
    except WebSocketDisconnect as error:
        print(
            f"Server WebSocket disconnected with code {error.code}.",
            flush=True,
        )
    except Exception:
        import traceback

        traceback.print_exc()
        raise
    finally:
        await terminal_manager.close_all()

# Register extra routes
app.include_router(filesRouter)

# Entrypoint
async def connect_to_server():
    try:
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=3050,
            loop="asyncio",
            log_level="info",
        )
    
        server = uvicorn.Server(config)
    
        await server.serve()
    except Exception:
        import traceback
        traceback.print_exc()

__all__ = ["connect_to_server"]