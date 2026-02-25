#!/usr/bin/env python3
"""Train MCP Server — repository root entry point.

Usage:
    uv run server.py           # HTTP mode (default)
    uv run server.py --stdio   # stdio mode for Claude Desktop
"""
from __future__ import annotations

import logging
import os
import sys

import uvicorn
from starlette.middleware.cors import CORSMiddleware

from src.db_mcp.mcp import create_mcp_app

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "3001"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

if __name__ == "__main__":
    mcp = create_mcp_app()
    if "--stdio" in sys.argv:
        # Claude Desktop mode
        mcp.run(transport="stdio")
    else:
        # HTTP mode with CORS
        app = mcp.streamable_http_app()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        print(f"Train MCP Server listening on http://{HOST}:{PORT}/mcp")
        uvicorn.run(app, host=HOST, port=PORT)
