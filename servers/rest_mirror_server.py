"""
REST-mirror MCP server — auto-generated from mlops_backend/openapi.json
via FastMCP OpenAPIProvider.

Every tool, its name, parameter schema, and docstring is derived
mechanically from the OpenAPI document at mlops_backend/openapi.json.
Nothing in this file is hand-authored. This represents the real token
cost of an OpenAPI-to-MCP gateway approach: one tool per REST primitive,
verbose schemas, pagination envelopes, and stub write tools that exist
because the spec defines them — not because any agentic scenario calls them.
That full schema ships as part of the tools context on every API turn,
regardless of which tools the agent actually uses.
"""
import json
import os
from pathlib import Path

import httpx
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import OpenAPIProvider

_SPEC_PATH = Path(__file__).parent.parent / "mlops_backend" / "openapi.json"
_BASE_URL = os.environ.get("MLOPS_API_URL", "http://127.0.0.1:7319")

_spec = json.loads(_SPEC_PATH.read_text())
_client = httpx.AsyncClient(base_url=_BASE_URL)
_provider = OpenAPIProvider(openapi_spec=_spec, client=_client)

mcp = FastMCP("mlops-rest-mirror", providers=[_provider])

if __name__ == "__main__":
    mcp.run()
