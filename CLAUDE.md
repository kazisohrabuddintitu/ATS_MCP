# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ATS Graph MCP Server - A dual-interface graph analysis system for piping/wiring component connectivity analysis. Provides both:
1. **MCP Server** (`mcp_server.py`) - Model Context Protocol server for AI assistant integration
2. **FastAPI REST API** (`api_server.py`) - HTTP API for external applications

Both interfaces use shared graph analysis functions from `graph_functions.py` to analyze component connectivity in piping/wiring systems stored as JSON graph files in the `json/` directory.

## Architecture

### Core Components

- **`graph_functions.py`** - Shared graph analysis logic
  - `load_graph()` - Loads JSON graph files
  - `build_adjacency_graph()` - Builds adjacency list from wire-based connections
  - `find_path_bfs()` - BFS shortest path between components
  - `find_neighbors()` - Finds directly connected components
  - `get_component_name()` / `get_component_id_by_name()` - ID/name conversion
  - Accepts either component IDs (`comp_X`) or instance names (e.g., `Ball_Valve_4`, `pump_1`)

- **`mcp_server.py`** - MCP protocol server for AI integration
  - Runs via stdio transport
  - Tools: `find_path`, `find_neighbors`
  - Requires `graph` argument in all tool calls (e.g., "graph 1", "2")

- **`api_server.py`** - FastAPI REST API
  - Endpoints: `/find_path`, `/find_neighbors`, `/list_components`, `/`
  - Uses Pydantic request models
  - `resolve_graph_file()` - Converts graph references (1, "1", "graph 1", "Graph_1") to file paths

### Graph Data Structure

Graph JSON files in `json/` directory contain:
- `components[]` - List of components with `id` (comp_X), `component_id` (numeric), `instance_name`
- `connections[]` - Wire connections with `component`, `wire` fields
- `path_mode` - Metadata field (e.g., "wire_connectivity")

Components are connected via shared wires. The adjacency graph treats components sharing any wire as neighbors.

## Development Commands

### Running the Services

**FastAPI API Server:**
```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

For public access during development:
```bash
ngrok http 8000
```

**MCP Server:**
```bash
python mcp_server.py
```

### Environment Setup

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Deployment

Configured for Render deployment via `render.yaml`:
- Service type: web
- Build: `pip install -r requirements.txt`
- Start: `uvicorn api_server:app --host 0.0.0.0 --port $PORT`

## Graph Reference Format

Both servers accept flexible graph references:
- Integers: `1`, `2`, `3`
- Strings: `"1"`, `"graph 1"`, `"Graph_1"`, `"graph 2"`

These are resolved to `json/graph_X.json` files using regex extraction of the first number.
