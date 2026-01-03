from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from pathlib import Path
import re

from graph_functions import (
    load_graph,
    get_component_name,
    find_all_paths,
    find_path_bfs,  
    find_neighbors,
)


app = FastAPI(title="Graph Analyzer API")


# ---------- Request models ----------
class FindPathRequest(BaseModel):
    start_component: str
    end_component: str
    graph: str


class FindShortestPathRequest(BaseModel):
    start_component: str
    end_component: str
    graph: str


class FindNeighborsRequest(BaseModel):
    component: str
    graph: str


class ListComponentsRequest(BaseModel):
    graph: str


# ---------- Helpers ----------
def extract_component_type(component_name: str) -> str:
    """
    Extracts component type from instance-like names.
    Examples:
      Ball_Valve_1              -> Ball_Valve
      3_Way_Ball_Valve_T_1      -> 3_Way_Ball_Valve_T
      pump_1                    -> pump
    """
    if not component_name:
        return None

    base = re.sub(r"_\d+$", "", component_name)
    return base


def _norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"[\s\-]+", "_", s)
    return s


def resolve_graph_file(graph_ref) -> str:
    json_dir = Path("json")
    if graph_ref is None:
        raise ValueError("Missing graph reference")

    raw = str(graph_ref).strip()
    raw_norm = _norm(raw)

    if raw_norm.endswith(".json"):
        raw_norm = raw_norm[:-5].strip()

    candidates = list(json_dir.glob("*.json"))
    if not candidates:
        raise FileNotFoundError(f"No .json graphs found in: {json_dir}")

    for p in candidates:
        if _norm(p.stem) == raw_norm:
            return str(p)

    matches = [p for p in candidates if raw_norm in _norm(p.stem)]

    if len(matches) == 1:
        return str(matches[0])

    if len(matches) == 0:
        available = ", ".join(sorted([p.stem for p in candidates]))
        raise FileNotFoundError(
            f"Graph not found for '{raw}'. Available graphs: {available}"
        )

    opts = ", ".join(sorted([p.stem for p in matches]))
    raise ValueError(
        f"Graph name '{raw}' is ambiguous. Matches: {opts}. Please be more specific."
    )


def load_graph_safe(graph_ref) -> Any:
    """
    graph_ref is required (string).
    """
    try:
        path = resolve_graph_file(graph_ref)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": "FileNotFoundError", "message": str(e)},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "InvalidGraph", "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": type(e).__name__, "message": f"Error resolving graph: {str(e)}"},
        )

    try:
        return load_graph(path), path
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": type(e).__name__, "message": f"Error loading graph from '{path}': {str(e)}"},
        )

# Predefined component descriptions
COMPONENT_DESCRIPTIONS = {
    "Ball_Valve": "Rappresenta il simbolo di una valvola a sfera.Una valvola che controlla il flusso mediante una sfera forata che ruota all'interno del corpo valvola.È molto usata perché consente un'apertura/chiusura rapida e garantisce una buona tenuta.",
    "3_Way_Ball_Valve_T": "A valve that modulates flow, pressure, or temperature in response to a control signal.",
    "BOILER": "A closed vessel that heats water or other fluid to generate steam or hot fluid for downstream use.",
    "pump": "A mechanical device that moves fluid by converting mechanical energy into hydraulic energy.",
    "Straight_sdnr_Valve": "Rappresenta il simbolo di una valvola di ritegno a chiusura diretta.Permette il passaggio del fluido in una sola direzione (come una valvola di non ritorno). Inoltre può essere manuale: si può agire su una vite per chiudere o aprire il flusso, indipendentemente dal senso di circolazione. È usata quando si vuole bloccare manualmente il flusso, oltre a proteggerlo automaticamente contro il riflusso.",
    "box": "This is coming from the box of the schema",

}


# ---------- Routes ----------
@app.post("/find_path")
def find_path(req: FindPathRequest):
    graph, path = load_graph_safe(req.graph)

    paths = find_all_paths(req.start_component, req.end_component, graph)
    truncated = len(paths) >= 50  # MUST match MAX_PATHS

    if not paths:
        return {
            "success": False,
            "message": "No path found",
            "paths": [],
            "path_count": 0,
            "truncated": False,
        }

    all_paths = []
    for p in paths:
        details = []
        for i, cid in enumerate(p):
            details.append({
                "position": i + 1,
                "component_id": cid,
                "component_name": get_component_name(cid, graph),
            })
        all_paths.append(details)

    return {
        "success": True,
        "message": f"Found {len(all_paths)} path(s)",
        "graph_file": path,
        "path_count": len(all_paths),
        "paths": all_paths,
        "truncated": truncated,
    }


@app.post("/find_shortest_path")
def find_shortest_path(req: FindPathRequest) -> Dict[str, Any]:
    graph, path = load_graph_safe(req.graph)

    try:
        path_nodes = find_path_bfs(req.start_component, req.end_component, graph)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": type(e).__name__,
                "message": f"Error finding shortest path: {str(e)}",
            },
        )

    if path_nodes is None:
        return {
            "success": False,
            "message": (
                f"No path found between '{req.start_component}' and '{req.end_component}'."
            ),
            "start_component": req.start_component,
            "end_component": req.end_component,
            "graph_file": path,
            "path": None,
            "path_length": 0,
        }

    path_details = []
    for i, comp_id in enumerate(path_nodes):
        path_details.append(
            {
                "position": i + 1,
                "component_id": comp_id,
                "component_name": get_component_name(comp_id, graph),
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


@app.post("/list_components")
def list_components(req: ListComponentsRequest) -> Dict[str, Any]:
    graph, path = load_graph_safe(req.graph)

    components_raw = graph.get("components", [])
    components = []

    for comp in components_raw:
        component_id = comp.get("id")               # comp_1
        component_name = comp.get("instance_name") # Ball_Valve_1

        component_type = extract_component_type(component_name)

        components.append(
            {
                "component_id": component_id,
                "component_name": component_name,
                "component_type": component_type,
                "description": COMPONENT_DESCRIPTIONS.get(
                    component_type,
                    "No description available."
                ),
            }
        )

    return {
        "success": True,
        "graph_file": path,
        "component_count": len(components),
        "components": components,
    }


@app.get("/")
def root():
    return {
        "service": "graph-analyzer-api",
        "endpoints": ["/find_path", "/find_shortest_path", "/find_neighbors", "/list_components"],
    }
