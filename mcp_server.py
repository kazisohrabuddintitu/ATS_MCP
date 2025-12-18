import asyncio
import json
import sys
import logging
from pathlib import Path
import re

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

from graph_functions import (
    load_graph,
    get_component_name,
    find_path_bfs,
    find_neighbors as graph_find_neighbors,  # renamed to avoid confusion
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

app = Server("graph-analyzer")


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

    # remove optional ".json" for matching
    if raw_norm.endswith(".json"):
        raw_norm = raw_norm[:-5].strip()

    candidates = list(json_dir.glob("*.json"))
    if not candidates:
        raise FileNotFoundError(f"No .json graphs found in: {json_dir}")

    # 1) exact stem match (case-insensitive)
    for p in candidates:
        if _norm(p.stem) == raw_norm:
            return str(p)

    # 2) partial match (substring)
    matches = [p for p in candidates if raw_norm in _norm(p.stem)]

    if len(matches) == 1:
        return str(matches[0])

    if len(matches) == 0:
        available = ", ".join(sorted([p.stem for p in candidates]))
        raise FileNotFoundError(
            f"Graph not found for '{raw}'. Available graphs: {available}"
        )

    # ambiguous
    opts = ", ".join(sorted([p.stem for p in matches]))
    raise ValueError(
        f"Graph name '{raw}' is ambiguous. Matches: {opts}. Please be more specific."
    )


# ---------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------
@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools for the MCP client"""
    logger.info("Listing available tools")

    return [
        Tool(
            name="find_path",
            description=(
                "Find the shortest path between two components in the graph. "
                "This uses BFS (Breadth-First Search) to find the shortest connection path "
                "through shared wires. You can use either component IDs (like 'comp_1') or "
                "instance names (like 'Ball_Valve_4', 'pump_1', 'BOILER_1'). "
                "Returns detailed information about each component in the path including "
                "position, component ID, and component name."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "start_component": {
                        "type": "string",
                        "description": "Starting component ID (comp_X) or instance name (e.g., 'Ball_Valve_4', 'pump_1')",
                    },
                    "end_component": {
                        "type": "string",
                        "description": "Ending component ID (comp_X) or instance name (e.g., '3_Way_Ball_Valve_T_2', 'BOILER_1')",
                    },
                    "graph": {
                        "type": "string",
                        "description": "Graph filename to use, e.g. 'gasolio' or 'schema completo' (with or without .json).",
                    },
                },
                "required": ["start_component", "end_component", "graph"],
            },
        ),
        Tool(
            name="find_neighbors",
            description=(
                "Find all neighboring components that are directly connected to a given component "
                "through shared wires. This shows what components are immediately adjacent in the "
                "piping/wiring system. You can use either component ID (comp_X) or instance name. "
                "Returns a list of all neighbors with their IDs and names."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "description": "Component ID (comp_X) or instance name (e.g., 'pump_1', 'BOILER_1') to find neighbors for",
                    },
                    "graph": {
                        "type": "string",
                        "description": "Graph filename to use, e.g. 'gasolio' or 'schema completo' (with or without .json).",
                    },
                },
                "required": ["component", "graph"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution requests from MCP client"""

    logger.info(f"Tool called: {name} with arguments: {arguments}")

    # Get graph reference (required now)
    graph_ref = arguments.get("graph")
    if graph_ref is None:
        error_response = {
            "error": "MissingGraph",
            "message": "You must provide a 'graph' argument like 'gasolio' or 'schema completo' (with or without .json).",
            "success": False,
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    # Resolve graph path
    try:
        graph_file = resolve_graph_file(graph_ref)
    except FileNotFoundError as e:
        logger.error(str(e))
        error_response = {
            "error": "FileNotFoundError",
            "message": str(e),
            "success": False,
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    except ValueError as e:
        logger.error(str(e))
        error_response = {
            "error": "InvalidGraph",
            "message": str(e),
            "success": False,
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    except Exception as e:
        logger.error(f"Unexpected error resolving graph: {str(e)}")
        error_response = {
            "error": type(e).__name__,
            "message": f"Error resolving graph: {str(e)}",
            "success": False,
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    # Load graph data
    try:
        graph = load_graph(graph_file)
        logger.info(f"Successfully loaded graph from {graph_file}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        error_response = {
            "error": "JSONDecodeError",
            "message": f"Invalid JSON in '{graph_file}': {str(e)}",
            "success": False,
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    except Exception as e:
        logger.error(f"Unexpected error loading graph: {str(e)}")
        error_response = {
            "error": type(e).__name__,
            "message": f"Error loading graph: {str(e)}",
            "success": False,
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    if name == "find_path":
        start = arguments["start_component"]
        end = arguments["end_component"]

        logger.info(f"Finding path from {start} to {end}")

        try:
            path = find_path_bfs(start, end, graph)

            if path is None:
                logger.info(f"No path found between {start} and {end}")
                result = {
                    "success": False,
                    "message": (
                        f"No path found between '{start}' and '{end}'. "
                        f"Components may not be connected or one/both components don't exist."
                    ),
                    "start_component": start,
                    "end_component": end,
                    "graph_file": graph_file,
                    "path": None,
                }
            else:
                logger.info(f"Path found with {len(path)} components")
                path_details = []
                for i, comp_id in enumerate(path):
                    comp_name = get_component_name(comp_id, graph)
                    path_details.append(
                        {
                            "position": i + 1,
                            "component_id": comp_id,
                            "component_name": comp_name,
                        }
                    )

                result = {
                    "success": True,
                    "message": f"Found shortest path with {len(path)} components",
                    "start_component": start,
                    "end_component": end,
                    "graph_file": graph_file,
                    "path_length": len(path),
                    "path": path_details,
                }

        except Exception as e:
            logger.error(f"Error finding path: {str(e)}")
            result = {
                "success": False,
                "error": type(e).__name__,
                "message": f"Error finding path: {str(e)}",
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "find_neighbors":
        component = arguments["component"]

        logger.info(f"Finding neighbors of {component}")

        try:
            neighbors = graph_find_neighbors(component, graph)  # ✅ renamed call
            logger.info(f"Found {len(neighbors)} neighbors")

            neighbor_details = []
            for neighbor_id in neighbors:
                neighbor_name = get_component_name(neighbor_id, graph)
                neighbor_details.append(
                    {
                        "component_id": neighbor_id,
                        "component_name": neighbor_name,
                    }
                )

            result = {
                "success": True,
                "message": f"Found {len(neighbors)} neighbor(s) for '{component}'",
                "component": component,
                "graph_file": graph_file,
                "neighbor_count": len(neighbors),
                "neighbors": neighbor_details,
            }

        except Exception as e:
            logger.error(f"Error finding neighbors: {str(e)}")
            result = {
                "success": False,
                "error": type(e).__name__,
                "message": f"Error finding neighbors: {str(e)}",
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    else:
        logger.warning(f"Unknown tool requested: {name}")
        error_response = {
            "success": False,
            "error": "UnknownTool",
            "message": f"Tool '{name}' is not recognized. Available tools: find_path, find_neighbors",
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


async def main():
    """Run the MCP server using stdio transport"""
    logger.info("=" * 70)
    logger.info("Starting Graph Analyzer MCP Server")
    logger.info("No default graph. Clients must provide a 'graph' argument.")
    logger.info("=" * 70)

    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("Server initialized, waiting for connections...")
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
