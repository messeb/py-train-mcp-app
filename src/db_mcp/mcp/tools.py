from __future__ import annotations

import dataclasses
import json
import logging
from datetime import datetime

import httpx
from mcp import types
from mcp.server.fastmcp import FastMCP

from db_mcp.application.departure_service import DepartureService
from db_mcp.domain.exceptions import ApiError, StationNotFoundError
from db_mcp.domain.value_objects import TransportMode
from db_mcp.infrastructure.time_utils import BERLIN_TZ

logger = logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

_RESULT_URI = "mcp://db-mcp/result"


def _as_resource(json_str: str) -> list[types.EmbeddedResource]:
    """Wrap a JSON string as an embedded resource so the LLM does not narrate it."""
    return [
        types.EmbeddedResource(
            type="resource",
            resource=types.TextResourceContents(
                uri=_RESULT_URI,  # type: ignore[arg-type]
                mimeType="application/json",
                text=json_str,
            ),
        )
    ]


def _error_json(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


def _handle_exception(exc: Exception) -> list[types.EmbeddedResource]:
    if isinstance(exc, StationNotFoundError):
        return _as_resource(_error_json(str(exc)))
    if isinstance(exc, ApiError):
        if exc.status_code == 400:
            return _as_resource(_error_json("Invalid request. Please check your inputs."))
        if exc.status_code == 404:
            return _as_resource(_error_json("Resource not found."))
        if exc.status_code >= 500:
            return _as_resource(
                _error_json(f"Upstream API error ({exc.status_code}). Please try again later.")
            )
        return _as_resource(_error_json(str(exc)))
    if isinstance(exc, httpx.TimeoutException):
        return _as_resource(_error_json("Request timed out. Please try again."))
    if isinstance(exc, ValueError):
        return _as_resource(_error_json(str(exc)))
    logger.exception("Unexpected error in MCP tool: %s", exc)
    return _as_resource(_error_json("An unexpected error occurred."))


def _parse_datetime_str(datetime_str: str | None) -> datetime | None:
    if datetime_str is None:
        return None
    try:
        dt_naive = datetime.strptime(datetime_str, DATETIME_FORMAT)
        return dt_naive.replace(tzinfo=BERLIN_TZ)
    except ValueError:
        raise ValueError("Invalid datetime format, expected YYYY-MM-DDTHH:MM:SS")


def _validate_modes(transport_modes: list[str] | None) -> list[TransportMode] | None:
    if transport_modes is None:
        return None
    result: list[TransportMode] = []
    valid_values = {m.value for m in TransportMode}
    for mode in transport_modes:
        upper = mode.upper()
        if upper not in valid_values:
            raise ValueError(f"Unknown transport mode: {mode}")
        result.append(TransportMode(upper))
    return result


def register_tools(mcp: FastMCP, departure_svc: DepartureService) -> None:
    """Bind all @mcp.tool decorators. Called once during server setup."""

    @mcp.tool()
    async def get_journey(
        journey_id: str,
    ) -> list[types.EmbeddedResource]:
        """Get all stops for a train journey (origin to destination with real-time data).

        Args:
            journey_id: Journey ID obtained from a departure entry.
        """
        try:
            if not journey_id.strip():
                return _as_resource(_error_json("journey_id cannot be empty"))
            result = await departure_svc.get_journey(journey_id)
            return _as_resource(json.dumps(result, default=str, ensure_ascii=False))
        except Exception as exc:
            return _handle_exception(exc)

    @mcp.tool(
        meta={
            "ui": {"resourceUri": "ui://db-mcp/departures-view.html"},
            "ui/resourceUri": "ui://db-mcp/departures-view.html",
        }
    )
    async def get_departures(
        station_name: str,
        datetime_str: str | None = None,
        transport_modes: list[str] | None = None,
        destination_filter: str | None = None,
        max_results: int = 20,
    ) -> list[types.EmbeddedResource]:
        """Get departures from a station.

        Results are rendered in the embedded UI view.

        Args:
            station_name: Station name (free text, resolved via location search).
            datetime_str: Board start time as ISO 8601 in Europe/Berlin, e.g.
                          "2026-02-24T14:00:00". Defaults to current time when omitted.
            transport_modes: Optional list of transport modes to include, e.g.
                             ["ICE", "REGIONAL"]. All modes included when omitted.
            destination_filter: Optional destination name substring filter
                                (case-insensitive). All destinations included when omitted.
            max_results: Maximum number of departures to return (default 20).
        """
        try:
            if not station_name.strip():
                return _as_resource(_error_json("Station name cannot be empty"))
            dt = _parse_datetime_str(datetime_str)
            modes = _validate_modes(transport_modes)

            station, departures = await departure_svc.get_departures(
                station_name=station_name.strip(),
                dt=dt,
                modes=modes,
                destination_filter=destination_filter,
                max_results=max_results,
            )

            result = {
                "station": dataclasses.asdict(station),
                "boardTime": datetime_str or dt.isoformat() if dt else None,
                "departures": [dataclasses.asdict(d) for d in departures],
                "count": len(departures),
            }
            return _as_resource(json.dumps(result, default=str, ensure_ascii=False))
        except Exception as exc:
            return _handle_exception(exc)
