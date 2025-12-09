# api_server.py
"""
HTTP API wrapper for graph_functions so it can be used via ngrok / n8n.
Exposes:
- POST /find_path
- POST /find_neighbors
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import re
from typing import Union



from graph_functions import (
    load_graph,
    get_component_name,
    find_path_bfs,
    find_neighbors,
)

DEFAULT_GRAPH_FILE = "json/graph_1.json"

app = FastAPI(title="Graph Analyzer API")


# ---------- Request models ----------



class FindPathRequest(BaseModel):
    start_component: str
    end_component: str
    graph: Union[int, str]   # required now, no default


class FindNeighborsRequest(BaseModel):
    component: str
    graph: Union[int, str]   # required now, no default



# ---------- Helper ----------

def resolve_graph_file(graph_ref) -> str:
    """
    Convert things like:
      - 1
      - "1"
      - "graph 1"
      - "Graph_1"
    into: "json/graph_1.json"
    and ensure the file exists.
    """
    if isinstance(graph_ref, int):
        number = graph_ref
    else:
        s = str(graph_ref).strip().lower()
        # extract first number in the string
        match = re.search(r'\d+', s)
        if not match:
            raise ValueError(f"Could not find a graph number in '{graph_ref}'")
        number = int(match.group(0))

    path = Path("json") / f"graph_{number}.json"
    if not path.exists():
        raise FileNotFoundError(f"Graph file not found for graph {number}: {path}")

    return str(path)



def load_graph_safe(graph_ref) -> Any:
    """
    graph_ref is required (int or string).
    """
    try:
        path = resolve_graph_file(graph_ref)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "FileNotFoundError",
                "message": str(e),
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "InvalidGraph",
                "message": str(e),
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": type(e).__name__,
                "message": f"Error resolving graph: {str(e)}",
            },
        )

    try:
        return load_graph(path), path
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": type(e).__name__,
                "message": f"Error loading graph from '{path}': {str(e)}",
            },
        )


# ---------- Routes ----------

@app.post("/find_path")
def find_path(req: FindPathRequest) -> Dict[str, Any]:
    graph, path = load_graph_safe(req.graph)

    try:
        path_nodes = find_path_bfs(req.start_component, req.end_component, graph)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": type(e).__name__,
                "message": f"Error finding path: {str(e)}",
            },
        )

    if path_nodes is None:
        return {
            "success": False,
            "message": (
                f"No path found between '{req.start_component}' and '{req.end_component}'. "
                f"Components may not be connected or one/both components don't exist."
            ),
            "start_component": req.start_component,
            "end_component": req.end_component,
            "graph_file": path,
            "path": None,
        }

    path_details = []
    for i, comp_id in enumerate(path_nodes):
        comp_name = get_component_name(comp_id, graph)
        path_details.append(
            {
                "position": i + 1,
                "component_id": comp_id,
                "component_name": comp_name,
            }
        )

    return {
        "success": True,
        "message": f"Found shortest path with {len(path_nodes)} components",
        "start_component": req.start_component,
        "end_component": req.end_component,
        "graph_file": path,
        "path_length": len(path_nodes),
        "path": path_details,
    }


@app.post("/find_neighbors")
def neighbors(req: FindNeighborsRequest) -> Dict[str, Any]:
    graph, path = load_graph_safe(req.graph)

    try:
        neighbor_ids = find_neighbors(req.component, graph)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": type(e).__name__,
                "message": f"Error finding neighbors: {str(e)}",
            },
        )

    neighbor_details = []
    for nid in neighbor_ids:
        neighbor_details.append(
            {
                "component_id": nid,
                "component_name": get_component_name(nid, graph),
            }
        )

    return {
        "success": True,
        "message": f"Found {len(neighbor_ids)} neighbor(s) for '{req.component}'",
        "component": req.component,
        "graph_file": path,
        "neighbor_count": len(neighbor_ids),
        "neighbors": neighbor_details,
    }


@app.get("/")
def root():
    return {
        "service": "graph-analyzer-api",
        "endpoints": ["/find_path", "/find_neighbors"],
    }
