from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

_CSP_DOMAINS = ["https://unpkg.com"]

_UI_DIR = Path(__file__).parent / "ui"


def _load(filename: str) -> str:
    return (_UI_DIR / filename).read_text(encoding="utf-8")


def register_resources(mcp: FastMCP) -> None:
    """Register all HTML UI resources. Called once during server setup."""

    @mcp.resource(
        "ui://db-mcp/departures-view.html",
        mime_type="text/html;profile=mcp-app",
        meta={"ui": {"csp": {"resourceDomains": _CSP_DOMAINS}}},
    )
    def departures_view() -> str:
        """HTML view for get_departures tool results."""
        return _load("departures-view.html")
