from collections import defaultdict, deque
import json


def load_graph(json_file):
    """Load the graph from JSON file"""
    with open(json_file, 'r') as f:
        return json.load(f)


def get_component_name(component_id, graph_data):
    """Get the instance name of a component by its ID"""
    for comp in graph_data['components']:
        if comp['id'] == component_id:
            return comp['instance_name']
    return None


def get_component_id_by_name(instance_name, graph_data):
    """Get the component ID by its instance name (case-insensitive)"""
    if not instance_name:
        return None

    target = instance_name.strip().lower()

    for comp in graph_data['components']:
        name = str(comp.get('instance_name', '')).strip().lower()
        if name == target:
            return comp['id']

    return None



def build_adjacency_graph(graph_data):
    """
    Build an adjacency list from the graph data.
    Components are connected if they share a wire.
    """
    adjacency = defaultdict(set)

    # Group connections by wire
    wire_components = defaultdict(set)
    for conn in graph_data['connections']:
        wire_components[conn['wire']].add(conn['component'])

    # Build adjacency list: components sharing a wire are neighbors
    for wire, components in wire_components.items():
        components_list = list(components)
        for i, comp1 in enumerate(components_list):
            for comp2 in components_list[i+1:]:
                adjacency[comp1].add(comp2)
                adjacency[comp2].add(comp1)

    return adjacency


def find_path_bfs(start_component, end_component, graph_data):
    """
    Find the shortest path between two components using BFS.
    Returns the path as a list of component IDs from start to end.
    Accepts either component IDs (comp_X) or instance names.
    """
    # Convert instance names to component IDs if needed
    if not start_component.startswith('comp_'):
        start_component = get_component_id_by_name(start_component, graph_data)
        if not start_component:
            return None

    if not end_component.startswith('comp_'):
        end_component = get_component_id_by_name(end_component, graph_data)
        if not end_component:
            return None

    if start_component == end_component:
        return [start_component]

    adjacency = build_adjacency_graph(graph_data)

    # BFS to find shortest path
    queue = deque([(start_component, [start_component])])
    visited = {start_component}

    while queue:
        current, path = queue.popleft()

        # Check all neighbors
        neighbors = adjacency.get(current, set())
        for neighbor in neighbors:
            if neighbor == end_component:
                return path + [neighbor]

            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    # No path found
    return None


def find_neighbors(component_id, graph_data):
    """
    Find all neighboring components connected to the given component
    through any shared wire.
    Accepts either component ID (comp_X) or instance name.
    """
    # Convert instance name to component ID if needed
    if not component_id.startswith('comp_'):
        component_id = get_component_id_by_name(component_id, graph_data)
        if not component_id:
            return []

    component_wires = set()

    for conn in graph_data['connections']:
        if conn['component'] == component_id:
            component_wires.add(conn['wire'])

    neighbors = set()

    for conn in graph_data['connections']:
        if conn['wire'] in component_wires and conn['component'] != component_id:
            neighbors.add(conn['component'])

    return list(neighbors)