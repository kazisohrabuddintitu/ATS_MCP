from collections import defaultdict, deque
import json
import re
from typing import Optional, List, Set


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
    if not user_input:
        return None

    s_raw = str(user_input).strip()

    if s_raw.lower().startswith("comp_"):
        return s_raw.lower()

    s = _norm(s_raw)

    for comp in graph_data.get("components", []):
        if _norm(comp.get("instance_name", "")) == s:
            return comp.get("id")

    m = re.search(r"(?:\s|_)(\d+)$", s)
    idx = m.group(1) if m else None

    base = re.sub(r"(?:\s|_)\d+$", "", s).strip()
    canonical = COMPONENT_ALIASES.get(base, base)

    if idx is not None:
        wanted = _norm(f"{canonical}_{idx}")
        for comp in graph_data.get("components", []):
            if _norm(comp.get("instance_name", "")) == wanted:
                return comp.get("id")
        return None

    prefix = _norm(canonical + "_")
    matches = [
        comp for comp in graph_data.get("components", [])
        if _norm(comp.get("instance_name", "")).startswith(prefix)
    ]

    if len(matches) == 1:
        return matches[0].get("id")

    return None


def load_graph(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_component_name(component_id, graph_data):
    for comp in graph_data.get("components", []):
        if comp.get("id") == component_id:
            return comp.get("instance_name")
    return None


def build_adjacency_graph(graph_data):
    adjacency = defaultdict(set)

    wire_components = defaultdict(set)
    for conn in graph_data.get("connections", []):
        wire_components[conn["wire"]].add(conn["component"])

    for components in wire_components.values():
        lst = list(components)
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                adjacency[lst[i]].add(lst[j])
                adjacency[lst[j]].add(lst[i])

    return adjacency


# -------------------------
# SHORTEST PATH (BFS)
# -------------------------
def find_path_bfs(start_component, end_component, graph_data):
    if not str(start_component).lower().startswith("comp_"):
        start_component = resolve_component_id(start_component, graph_data)
    else:
        start_component = str(start_component).lower()

    if not str(end_component).lower().startswith("comp_"):
        end_component = resolve_component_id(end_component, graph_data)
    else:
        end_component = str(end_component).lower()

    if not start_component or not end_component:
        return None

    adjacency = build_adjacency_graph(graph_data)

    queue = deque([(start_component, [start_component])])
    visited = {start_component}

    while queue:
        current, path = queue.popleft()
        for neighbor in adjacency.get(current, []):
            if neighbor == end_component:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return None


# -------------------------
# ALL PATHS (DFS)
# -------------------------
MAX_DEPTH = 20
MAX_PATHS = 50


def find_all_paths(start_component, end_component, graph_data) -> List[List[str]]:
    if not str(start_component).lower().startswith("comp_"):
        start_component = resolve_component_id(start_component, graph_data)
    else:
        start_component = str(start_component).lower()

    if not str(end_component).lower().startswith("comp_"):
        end_component = resolve_component_id(end_component, graph_data)
    else:
        end_component = str(end_component).lower()

    if not start_component or not end_component:
        return []

    adjacency = build_adjacency_graph(graph_data)
    paths: List[List[str]] = []

    def dfs(current: str, target: str, visited: Set[str], path: List[str]):
        if len(paths) >= MAX_PATHS:
            return
        if len(path) > MAX_DEPTH:
            return
        if current == target:
            paths.append(path.copy())
            return

        for neighbor in adjacency.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                dfs(neighbor, target, visited, path + [neighbor])
                visited.remove(neighbor)

    dfs(start_component, end_component, {start_component}, [start_component])
    return paths


def find_neighbors(component_id, graph_data):
    if not str(component_id).lower().startswith("comp_"):
        component_id = resolve_component_id(component_id, graph_data)
    else:
        component_id = str(component_id).lower()

    if not component_id:
        return []

    adjacency = build_adjacency_graph(graph_data)
    return list(adjacency.get(component_id, []))
