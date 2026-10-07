import uvicorn
from fastapi import FastAPI, WebSocket

from node import Node
from load_nodes import load_nodes

from app import proccess_message
from state import GlobalState

from events.event_types.container_specs import ContainerSpecs

# Import Routes
from apis import router as filesRouter


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

    await websocket.send_json(
        ContainerSpecs().to_dict()
    )

    while True:
        message = await websocket.receive_text()

        await proccess_message(
            message,
            websocket,
            node_list,
            global_state
        )

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