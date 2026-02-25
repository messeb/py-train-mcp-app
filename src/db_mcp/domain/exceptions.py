from __future__ import annotations


class DBMcpError(Exception):
    """Base exception for all Deutsche Bahn MCP errors."""


class StationNotFoundError(DBMcpError):
    """Raised when a station name resolves to zero results from the API."""


class ApiError(DBMcpError):
    """Raised when the upstream bahn.de API returns an unexpected HTTP error status."""

    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        super().__init__(message or f"Upstream API error ({status_code})")


class ValidationError(DBMcpError):
    """Raised when input parameters fail validation before any network call."""
