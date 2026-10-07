from pprint import pprint
import networkx as nx
import matplotlib.pyplot as plt

from process_dag import proccess_dag
from server import connect_to_server

VISUALIZE_DAG = False # Debug dag visualization - saves image to dag_prev

def build_dag(data: dict) -> list[nx.DiGraph] | None:
    G = nx.DiGraph()
    
    for node in data["nodes"]:
        node["executable"] = True
        
    for node in data["nodes"]:
        G.add_node(node["id"], **node)
        
    for edge in data["edges"]:
        G.add_edge(edge["source"], edge["target"], **edge)
       
    if not validate_dag(G):
        print("Graph is not valid.")
        return

    if VISUALIZE_DAG:
        visualize_dag(G, "full")
         
    components = nx.connected_components(G.to_undirected())
    
    subgraphs: list[nx.DiGraph] = []
    for i, nodes in enumerate(components):
        sub = G.subgraph(nodes).copy()
        
        subgraphs.append(sub)

    if VISUALIZE_DAG:
        for i, G in enumerate(subgraphs):
            visualize_dag(G, f"{i}")
    
    return subgraphs

def visualize_dag(G: nx.DiGraph, name: str):
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_size=2000, node_color="lightblue")
    
    plt.savefig(f"./dag_prev/graph_{name}.png", dpi=300, bbox_inches="tight")
    plt.close()

def validate_dag(G: nx.DiGraph) -> bool:
    if not nx.is_directed_acyclic_graph(G):
        return False
        
    return True


__all__ = ["build_dag"]