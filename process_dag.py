from pprint import pprint
import networkx as nx

from events.event_types.node_execution_error import NodeExecutionError
from events.event_types.node_start import NodeExecutionStart
from events.event_types.node_finish import NodeExecutionFinish
from events.event_types.node_skipped import NodeSkipped


from node import NodeOutput, Node

from state import GlobalState

from fastapi import WebSocket

from fs import send_image_to_client
    
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
             
        try:       
            if ws: ## Notify user when node starts
                await ws.send_json(
                    NodeExecutionStart(workflow_id=workflow_id, node_id=item["id"]).to_dict()
                ) 
            res = run_node(item, predecessors, node_list, gs)
        except Exception as  e:
            if ws:
                await ws.send_json(
                    NodeExecutionError(workflow_id=workflow_id, node_id=item["id"], msg=f"{e}").to_dict()
                ) 
            print(f"An error ocurred: {e}. Workflow interrupted")
            
            return
        
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
    