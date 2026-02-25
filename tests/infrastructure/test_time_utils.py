"""Tests for time utility functions."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from db_mcp.infrastructure.time_utils import (
    format_datum,
    format_formation_time,
    format_zeit,
    parse_bahn_datetime,
    to_utc,
)


def test_parse_bahn_datetime_with_offset() -> None:
    result = parse_bahn_datetime("2026-02-24T14:30:00+01:00")
    assert result.tzinfo is not None
    # Should be in Berlin tz
    berlin_tz = ZoneInfo("Europe/Berlin")
    result_berlin = result.astimezone(berlin_tz)
    assert result_berlin.hour == 14
    assert result_berlin.minute == 30


def test_parse_bahn_datetime_naive() -> None:
    result = parse_bahn_datetime("2026-02-24T14:30:00")
    assert result.tzinfo is not None
    # Naive input is treated as Berlin time
    assert result.hour == 14
    assert result.minute == 30


def test_parse_bahn_datetime_summer_time() -> None:
    result = parse_bahn_datetime("2026-07-15T14:30:00+02:00")
    assert result.tzinfo is not None
    result_berlin = result.astimezone(ZoneInfo("Europe/Berlin"))
    assert result_berlin.hour == 14


def test_parse_bahn_datetime_empty_raises() -> None:
    with pytest.raises(ValueError):
        parse_bahn_datetime("")


def test_parse_bahn_datetime_invalid_raises() -> None:
    with pytest.raises(ValueError):
        parse_bahn_datetime("not-a-date")


def test_format_datum() -> None:
    dt = datetime(2026, 2, 24, 14, 0, 0)
    assert format_datum(dt) == "2026-02-24"


def test_format_zeit() -> None:
    dt = datetime(2026, 2, 24, 14, 0, 0)
    assert format_zeit(dt) == "14:00:00"


def test_format_formation_time_is_utc() -> None:
    """Berlin 15:30 (UTC+1 in winter) -> 14:30:00.000Z."""
    berlin_tz = ZoneInfo("Europe/Berlin")
    dt = datetime(2026, 2, 24, 15, 30, 0, tzinfo=berlin_tz)
    result = format_formation_time(dt)
    assert result == "2026-02-24T14:30:00.000Z"


def test_format_formation_time_utc() -> None:
    """Alias test for formation time formatting."""
    berlin_tz = ZoneInfo("Europe/Berlin")
    # In winter (CET = UTC+1), 15:30 Berlin = 14:30 UTC
    dt = datetime(2026, 2, 24, 15, 30, 0, tzinfo=berlin_tz)
    result = format_formation_time(dt)
    assert result.endswith("Z")
    assert "14:30:00" in result


def test_to_utc() -> None:
    berlin_tz = ZoneInfo("Europe/Berlin")
    dt = datetime(2026, 2, 24, 15, 30, 0, tzinfo=berlin_tz)
    utc_dt = to_utc(dt)
    assert utc_dt.hour == 14
    assert utc_dt.minute == 30
    assert str(utc_dt.tzinfo) == "UTC"
