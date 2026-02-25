"""Tests for MCP tool functions — input validation, success and error paths."""
from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from db_mcp.application.departure_service import DepartureService
from db_mcp.domain.entities import Departure, Location
from db_mcp.domain.exceptions import ApiError, StationNotFoundError
from db_mcp.infrastructure.time_utils import BERLIN_TZ
from db_mcp.mcp.tools import (
    _parse_datetime_str,
    _validate_modes,
    register_tools,
)


def make_location(name: str = "Frankfurt(Main)Hbf") -> Location:
    return Location(
        eva=8000105,
        hafas_id="A=1@O=Frankfurt(Main)Hbf@X=8663785@Y=50107149@",
        name=name,
        lat=50.107149,
        lon=8.663785,
        location_type="ST",
        transport_modes=["ICE"],
    )


def make_departure(journey_id: str = "j1", destination: str = "München Hbf") -> Departure:
    dt = datetime(2026, 2, 24, 14, 30, tzinfo=BERLIN_TZ)
    return Departure(
        journey_id=journey_id,
        train_name="ICE 619",
        train_type="ICE",
        destination=destination,
        via_stations=["Mannheim Hbf"],
        platform="7",
        rt_platform="",
        scheduled_departure=dt,
        rt_departure=None,
        effective_departure=dt,
        delay_minutes=0,
        is_cancelled=False,
    )


def build_tool_functions(departure_svc: MagicMock) -> dict:  # type: ignore[type-arg]
    """Register tools on a mock MCP and extract the tool functions."""
    registered: dict = {}  # type: ignore[type-arg]

    class MockMcp:
        def tool(self, meta: dict | None = None):  # type: ignore[type-arg]
            def decorator(fn):  # type: ignore[type-arg]
                registered[fn.__name__] = fn
                return fn
            return decorator

        def resource(self, *args, **kwargs):  # type: ignore[type-arg]
            def decorator(fn):  # type: ignore[type-arg]
                return fn
            return decorator

    mock_mcp = MockMcp()
    register_tools(mock_mcp, departure_svc)  # type: ignore[arg-type]
    return registered


# ---------------------------------------------------------------------------
# _parse_datetime_str
# ---------------------------------------------------------------------------

def test_parse_datetime_str_none_returns_none() -> None:
    assert _parse_datetime_str(None) is None


def test_parse_datetime_str_valid() -> None:
    result = _parse_datetime_str("2026-02-24T14:00:00")
    assert result is not None
    assert result.year == 2026
    assert result.hour == 14


def test_parse_datetime_str_invalid_raises() -> None:
    with pytest.raises(ValueError, match="Invalid datetime format"):
        _parse_datetime_str("24.02.2026 14:00")


# ---------------------------------------------------------------------------
# _validate_modes
# ---------------------------------------------------------------------------

def test_validate_modes_none_returns_none() -> None:
    assert _validate_modes(None) is None


def test_validate_modes_valid() -> None:
    result = _validate_modes(["ICE", "REGIONAL"])
    assert result is not None
    assert len(result) == 2


def test_validate_modes_case_insensitive() -> None:
    result = _validate_modes(["ice", "regional"])
    assert result is not None
    assert all(m.value.isupper() for m in result)


def test_validate_modes_invalid_raises() -> None:
    with pytest.raises(ValueError, match="Unknown transport mode: HELICOPTER"):
        _validate_modes(["HELICOPTER"])


# ---------------------------------------------------------------------------
# get_departures tool
# ---------------------------------------------------------------------------

async def test_get_departures_returns_resource() -> None:
    departure_svc = MagicMock(spec=DepartureService)
    location = make_location()
    departure = make_departure()
    departure_svc.get_departures = AsyncMock(return_value=(location, [departure]))

    tools = build_tool_functions(departure_svc)
    result = await tools["get_departures"]("Frankfurt")

    parsed = json.loads(result[0].resource.text)
    assert "departures" in parsed
    assert "station" in parsed
    assert parsed["count"] == 1


async def test_get_departures_empty_station_returns_error() -> None:
    departure_svc = MagicMock(spec=DepartureService)
    tools = build_tool_functions(departure_svc)

    result = await tools["get_departures"]("")
    parsed = json.loads(result[0].resource.text)
    assert "error" in parsed


async def test_get_departures_invalid_datetime_returns_error() -> None:
    departure_svc = MagicMock(spec=DepartureService)
    tools = build_tool_functions(departure_svc)

    result = await tools["get_departures"]("Frankfurt", "today at 2pm")
    parsed = json.loads(result[0].resource.text)
    assert "error" in parsed
    assert "datetime" in parsed["error"].lower() or "format" in parsed["error"].lower()


async def test_get_departures_unknown_mode_returns_error() -> None:
    departure_svc = MagicMock(spec=DepartureService)
    tools = build_tool_functions(departure_svc)

    result = await tools["get_departures"]("Frankfurt", None, ["MAGLEV"])
    parsed = json.loads(result[0].resource.text)
    assert "error" in parsed
    assert "MAGLEV" in parsed["error"]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

async def test_tool_service_exception_returns_resource_not_exception() -> None:
    """Exception from service must NOT propagate — must return error resource."""
    departure_svc = MagicMock(spec=DepartureService)
    departure_svc.get_departures = AsyncMock(
        side_effect=RuntimeError("Unexpected internal error")
    )

    tools = build_tool_functions(departure_svc)
    result = await tools["get_departures"]("Frankfurt")

    assert isinstance(result, list)
    parsed = json.loads(result[0].resource.text)
    assert "error" in parsed


async def test_station_not_found_returns_error() -> None:
    departure_svc = MagicMock(spec=DepartureService)
    departure_svc.get_departures = AsyncMock(
        side_effect=StationNotFoundError("Station not found: ZZZUNKNOWN")
    )

    tools = build_tool_functions(departure_svc)
    result = await tools["get_departures"]("ZZZUNKNOWN")
    parsed = json.loads(result[0].resource.text)
    assert "error" in parsed
    assert "Station not found" in parsed["error"]


async def test_api_error_5xx_returns_friendly_message() -> None:
    departure_svc = MagicMock(spec=DepartureService)
    departure_svc.get_departures = AsyncMock(side_effect=ApiError(500))

    tools = build_tool_functions(departure_svc)
    result = await tools["get_departures"]("Frankfurt")
    parsed = json.loads(result[0].resource.text)
    assert "error" in parsed
    assert "500" in parsed["error"]
