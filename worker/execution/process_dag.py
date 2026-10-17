import contextlib
import io
from pprint import pprint

import networkx as nx

from worker.events.event_types.node_execution_error import NodeExecutionError
from worker.events.event_types.node_start import NodeExecutionStart
from worker.events.event_types.node_finish import NodeExecutionFinish
from worker.events.event_types.node_skipped import NodeSkipped
from worker.events.event_types.workflow_log import WorkflowLog


from worker.nodes.base import NodeOutput, Node

from worker.execution.state import GlobalState

from fastapi import WebSocket

from worker.storage.files import send_image_to_client


MAX_LOG_CHUNK_BYTES = 16 * 1024


async def send_python_output(
    websocket: WebSocket | None,
    workflow_id: str,
    node_id: str,
    stdout: io.StringIO,
    stderr: io.StringIO,
) -> None:
    """Relay bounded node stdout/stderr through the execution-scoped socket."""

    if websocket is None:
        return

    for stream, captured in (("stdout", stdout), ("stderr", stderr)):
        text = captured.getvalue()
        if not text:
            continue

        encoded = text.encode("utf-8", errors="replace")
        for start in range(0, len(encoded), MAX_LOG_CHUNK_BYTES):
            chunk = encoded[start : start + MAX_LOG_CHUNK_BYTES]
            await websocket.send_json(
                WorkflowLog(
                    workflow_id=workflow_id,
                    node_id=node_id,
                    stream=stream,
                    text=chunk.decode("utf-8", errors="replace"),
                ).to_dict()
            )


async def proccess_dag(G: nx.DiGraph, data: dict, ws: None | WebSocket, workflow_id: str, node_list: list[Node], gs: GlobalState):
    import json
    results = {}
         
    #pyrefly:ignore                                            
    for node in nx.topological_sort(G):
        
        #pyrefly:ignore
        item: dict = next((i for i in data["nodes"] if i["id"] == node), None)
        
        if not G.nodes[node]["executable"]: # Skips nodes that must be skipped
            if ws:
                await ws.send_json(
                    NodeSkipped(workflow_id=workflow_id, node_id=item["id"]).to_dict()
                ) 
            continue
        
                                            
        #pyrefly:ignore 
        predecessors: list[tuple[dict, dict]] = [
            (
                edge_data := G.get_edge_data(pred, node),
                results.get(edge_data["source"]) if edge_data else None
            )
            for pred in G.predecessors(node)
        ]
             
        return_data = None ## Data to be sent to client on finish
             
        stdout = io.StringIO()
        stderr = io.StringIO()

        try:
            if ws: ## Notify user when node starts
                await ws.send_json(
                    NodeExecutionStart(workflow_id=workflow_id, node_id=item["id"]).to_dict()
                )

            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                res = run_node(item, predecessors, node_list, gs)
        except Exception as error:
            print(
                f"An error occurred: {error}. Workflow interrupted",
                file=stderr,
            )
            await send_python_output(
                ws,
                workflow_id,
                item["id"],
                stdout,
                stderr,
            )

            if ws:
                await ws.send_json(
                    NodeExecutionError(
                        workflow_id=workflow_id,
                        node_id=item["id"],
                        msg=f"{error}",
                    ).to_dict()
                )

            return

        await send_python_output(
            ws,
            workflow_id,
            item["id"],
            stdout,
            stderr,
        )
        
        if res:
            #pyrefly:ignore
            results[res.node_id] = res
            
            return_data = res.return_data
            
            if res.disable_nodes_after_handle:                
                direct_after_nodes = [i for i in data["edges"] if i["source"] == item["id"] and i["sourceHandle"] == res.disable_nodes_after_handle]
                                
                for node in direct_after_nodes:
                    disable_node_exectuion(G, node["target"])

            if len(res.files_to_upload) > 0 and ws:
                await send_image_to_client(ws, res.files_to_upload)
        
        if ws: ## Notify user when node finishes running
            
            await ws.send_json(
                NodeExecutionFinish(workflow_id=workflow_id, node_id=item["id"], return_data=return_data).to_dict()
            ) 
                        
        #await asyncio.sleep(4)
            
        
def run_node(node: dict, predecessors: list[tuple[dict, dict]], node_list: list[Node],  gs: GlobalState) -> NodeOutput | None:
    node_type = node["type"]
        
    for n in node_list:
        if n.node_identifier == node_type:
            return n.node_fn(node, predecessors, gs)
          
    print(f"Node of type {node_type} not found.")  
    return None
    
def disable_node_exectuion(G: nx.DiGraph, target_id: str):
    nodes_after_including_self = {target_id} | nx.descendants(G, target_id)
    
    for node in nodes_after_including_self:
        G.nodes[node]["executable"] = False
    