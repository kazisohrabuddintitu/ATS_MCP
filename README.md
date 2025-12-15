# ATS Graph MCP Server

Dual-interface graph analysis system for piping/wiring component connectivity analysis.

## Overview

Provides two interfaces for analyzing component connectivity in piping/wiring systems:

- **MCP Server** - Model Context Protocol interface for AI assistants
- **FastAPI REST API** - HTTP API for external applications

Both use shared graph analysis functions to process JSON graph files stored in `json/` directory.

## Core Features

- **Path Finding** - Find shortest path between components using BFS
- **Neighbor Discovery** - Find directly connected components  
- **Component Resolution** - Accept component IDs (`comp_X`) or instance names (`Ball_Valve_4`)
- **Flexible Graph References** - Support multiple formats: `1`, `"graph 1"`, `"Graph_1"`

## Quick Start

### Setup
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run FastAPI Server
```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### Run MCP Server
```bash
python mcp_server.py
```

### Public Access (Development)
```bash
ngrok http 8000
```

## API Endpoints

- `GET /` - Service info
- `POST /find_path` - Find path between components
- `POST /find_neighbors` - Find connected components
- `GET /list_components` - List all components in graph

## Graph Data Format

JSON files in `json/` directory with:
- `components[]` - Components with `id`, `component_id`, `instance_name`
- `connections[]` - Wire connections linking components
- `path_mode` - Analysis mode (e.g., "wire_connectivity")

## Deployment

Configured for Render deployment via `render.yaml`. Also includes Docker and nginx configurations.