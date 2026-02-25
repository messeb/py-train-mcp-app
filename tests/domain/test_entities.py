"""Tests for domain entities (dataclasses)."""
from __future__ import annotations

from datetime import datetime, timezone

from db_mcp.domain.entities import Departure, Location, Message


def test_message_creation() -> None:
    msg = Message(type="DELAY", text="Verspätung wegen Baustelle")
    assert msg.type == "DELAY"
    assert msg.text == "Verspätung wegen Baustelle"


def test_location_creation() -> None:
    loc = Location(
        eva=8000105,
        hafas_id="A=1@O=Frankfurt(Main)Hbf@X=8663785@Y=50107149@",
        name="Frankfurt(Main)Hbf",
        lat=50.107149,
        lon=8.663785,
        location_type="ST",
        transport_modes=["ICE", "EC_IC", "REGIONAL", "SBAHN"],
    )
    assert loc.eva == 8000105
    assert loc.name == "Frankfurt(Main)Hbf"
    assert loc.location_type == "ST"
    assert "ICE" in loc.transport_modes


def test_location_default_transport_modes() -> None:
    loc = Location(
        eva=8000105,
        hafas_id="A=1@O=Test@X=0@Y=0@",
        name="Test",
        lat=0.0,
        lon=0.0,
        location_type="ST",
    )
    assert loc.transport_modes == []


def test_departure_via_stations_default() -> None:
    dt = datetime(2026, 2, 24, 14, 30, tzinfo=timezone.utc)
    dep = Departure(
        journey_id="j1",
        train_name="ICE 619",
        train_type="ICE",
        destination="München Hbf",
        via_stations=[],
        platform="7",
        rt_platform="",
        scheduled_departure=dt,
        rt_departure=None,
        effective_departure=dt,
        delay_minutes=0,
        is_cancelled=False,
    )
    assert dep.via_stations == []
    assert dep.messages == []


def test_departure_with_messages() -> None:
    dt = datetime(2026, 2, 24, 14, 30, tzinfo=timezone.utc)
    msg = Message(type="HALT_AUSFALL", text="Zug fällt aus")
    dep = Departure(
        journey_id="j1",
        train_name="ICE 619",
        train_type="ICE",
        destination="München Hbf",
        via_stations=["Mannheim Hbf", "Stuttgart Hbf"],
        platform="7",
        rt_platform="7A",
        scheduled_departure=dt,
        rt_departure=None,
        effective_departure=dt,
        delay_minutes=0,
        is_cancelled=True,
        messages=[msg],
    )
    assert dep.is_cancelled is True
    assert len(dep.messages) == 1
    assert dep.messages[0].type == "HALT_AUSFALL"
