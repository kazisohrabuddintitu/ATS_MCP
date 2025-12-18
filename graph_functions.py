from collections import defaultdict, deque
import json
import re
from typing import Optional


COMPONENT_ALIASES = {
    "valve": "Ball_Valve",
    "ball_valve": "Ball_Valve",
    "boiler": "BOILER",
    "pump": "pump",
    "3_way_valve": "3_Way_Ball_Valve_T",
    "three_way_valve": "3_Way_Ball_Valve_T",
}


def _norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"[\s\-]+", "_", s)
    return s


def resolve_component_id(user_input: str, graph_data) -> Optional[str]:
    """
    Accepts:
      - comp_7 / COMP_7 / Comp_7
      - exact instance name (Ball_Valve_2)
      - partial/alias like: "valve", "valve 2", "ball valve 2", "pump 1", "boiler"
    Returns:
      - component_id like "comp_7" or None
    """
    if not user_input:
        return None

    s_raw = str(user_input).strip()

    # If user provided component id, normalize to lowercase so it matches JSON ids
    if s_raw.lower().startswith("comp_"):
        return s_raw.lower()

    s = _norm(s_raw)

    # exact instance match
    for comp in graph_data.get("components", []):
        if _norm(comp.get("instance_name", "")) == s:
            return comp.get("id")

    # extract trailing number if present (e.g., "valve_2" / "pump_1")
    m = re.search(r"(?:\s|_)(\d+)$", s)
    idx = m.group(1) if m else None

    # remove trailing number for alias lookup
    base = re.sub(r"(?:\s|_)\d+$", "", s).strip()

    # alias lookup
    canonical = COMPONENT_ALIASES.get(base)
    if canonical is None:
        canonical = base

    # idx exists => exact canonical_idx match
    if idx is not None:
        wanted = _norm(f"{canonical}_{idx}")
        for comp in graph_data.get("components", []):
            if _norm(comp.get("instance_name", "")) == wanted:
                return comp.get("id")
        return None

    # no idx: unique match by prefix
    prefix = _norm(canonical + "_")
    matches = [
        comp for comp in graph_data.get("components", [])
        if _norm(comp.get("instance_name", "")).startswith(prefix)
    ]

    if len(matches) == 1:
        return matches[0].get("id")

    return None


def load_graph(json_file):
    """Load the graph from JSON file"""
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_component_name(component_id, graph_data):
    """Get the instance name of a component by its ID"""
    for comp in graph_data.get("components", []):
        if comp.get("id") == component_id:
            return comp.get("instance_name")
    return None


def get_component_id_by_name(instance_name, graph_data):
    """Get the component ID by its instance name (case-insensitive)"""
    if not instance_name:
        return None

    target = str(instance_name).strip().lower()

    for comp in graph_data.get("components", []):
        name = str(comp.get("instance_name", "")).strip().lower()
        if name == target:
            return comp.get("id")

    return None


def build_adjacency_graph(graph_data):
    """
    Build an adjacency list from the graph data.
    Components are connected if they share a wire.
    """
    adjacency = defaultdict(set)

    wire_components = defaultdict(set)
    for conn in graph_data.get("connections", []):
        wire_components[conn["wire"]].add(conn["component"])

    for _, components in wire_components.items():
        components_list = list(components)
        for i, comp1 in enumerate(components_list):
            for comp2 in components_list[i + 1:]:
                adjacency[comp1].add(comp2)
                adjacency[comp2].add(comp1)

    return adjacency


def find_path_bfs(start_component, end_component, graph_data):
    """
    Find the shortest path between two components using BFS.
    Accepts either component IDs (comp_X) or instance names.
    """
    if not str(start_component).lower().startswith("comp_"):
        start_component = resolve_component_id(start_component, graph_data)
        if not start_component:
            return None
    else:
        start_component = str(start_component).lower()

    if not str(end_component).lower().startswith("comp_"):
        end_component = resolve_component_id(end_component, graph_data)
        if not end_component:
            return None
    else:
        end_component = str(end_component).lower()

    if start_component == end_component:
        return [start_component]

    adjacency = build_adjacency_graph(graph_data)

    queue = deque([(start_component, [start_component])])
    visited = {start_component}

    while queue:
        current, path = queue.popleft()

        neighbors = adjacency.get(current, set())
        for neighbor in neighbors:
            if neighbor == end_component:
                return path + [neighbor]

            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return None


def find_neighbors(component_id, graph_data):
    """
    Find all neighboring components connected to the given component.
    Accepts either component ID (comp_X) or instance name.
    """
    if not str(component_id).lower().startswith("comp_"):
        component_id = resolve_component_id(component_id, graph_data)
        if not component_id:
            return []
    else:
        component_id = str(component_id).lower()

    component_wires = set()

    for conn in graph_data.get("connections", []):
        if conn["component"] == component_id:
            component_wires.add(conn["wire"])

    neighbors = set()
    for conn in graph_data.get("connections", []):
        if conn["wire"] in component_wires and conn["component"] != component_id:
            neighbors.add(conn["component"])

    return list(neighbors)
