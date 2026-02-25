from __future__ import annotations

import httpx
from mcp.server.fastmcp import FastMCP

from db_mcp.application.departure_service import DepartureService
from db_mcp.infrastructure.bahn_client import DEFAULT_TIMEOUT, BahnClient
from db_mcp.infrastructure.cache import TTLCache
from db_mcp.mcp.resources import register_resources
from db_mcp.mcp.tools import register_tools


def create_mcp_app() -> FastMCP:
    """Create and configure the FastMCP application with all services wired."""
    cache = TTLCache(default_ttl=90)
    http_client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True)
    bahn_client = BahnClient(cache=cache, http_client=http_client)

    departure_svc = DepartureService(bahn_client)

    mcp = FastMCP("Deutsche Bahn MCP", stateless_http=True)
    register_tools(mcp, departure_svc)
    register_resources(mcp)
    return mcp
