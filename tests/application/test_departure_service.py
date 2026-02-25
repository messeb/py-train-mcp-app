"""Tests for DepartureService."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from db_mcp.application.departure_service import DepartureService
from db_mcp.domain.exceptions import StationNotFoundError
from db_mcp.domain.value_objects import TransportMode


def make_station_raw(
    name: str = "Frankfurt(Main)Hbf",
    eva: int = 8000105,
    station_type: str = "ST",
) -> dict:  # type: ignore[type-arg]
    return {
        "evaNumber": eva,
        "id": f"A=1@O={name}@X=8663785@Y=50107149@",
        "name": name,
        "lat": 50.107149,
        "lon": 8.663785,
        "type": station_type,
        "products": ["ICE"],
    }


def make_departure_raw(
    journey_id: str = "j1",
    terminus: str = "München Hbf",
    zeit: str = "2026-02-24T14:30:00",
    ez_zeit: str = "",
    ueber: list | None = None,
    gleis: str = "7",
    ez_gleis: str = "",
    meldungen: list | None = None,
    train_name: str = "ICE 619",
    train_type: str = "ICE",
) -> dict:  # type: ignore[type-arg]
    return {
        "journeyId": journey_id,
        "terminus": terminus,
        "zeit": zeit,
        "ezZeit": ez_zeit,
        "ueber": ueber if ueber is not None else ["Frankfurt(Main)Hbf", "Mannheim Hbf", "Stuttgart Hbf"],
        "gleis": gleis,
        "ezGleis": ez_gleis,
        "meldungen": meldungen if meldungen is not None else [],
        "verkehrmittel": {
            "kurzText": train_type,
            "mittelText": train_name,
            "langText": train_name,
        },
    }


def make_mock_client(
    stations: list | None = None,
    departures_entries: list | None = None,
) -> MagicMock:
    client = MagicMock()
    client.search_stations = AsyncMock(
        return_value=stations if stations is not None else [make_station_raw()]
    )
    client.get_departures = AsyncMock(
        return_value={"entries": departures_entries if departures_entries is not None else [make_departure_raw()]}
    )
    return client


async def test_ueber_index_0_skipped() -> None:
    """via_stations must NOT contain ueber[0] (the origin station)."""
    ueber = ["Frankfurt(Main)Hbf", "Mannheim Hbf", "Stuttgart Hbf"]
    client = make_mock_client(departures_entries=[make_departure_raw(ueber=ueber)])
    service = DepartureService(client)

    _, departures = await service.get_departures(
        station_name="Frankfurt",
        dt=datetime(2026, 2, 24, 14, 0, tzinfo=timezone.utc),
        modes=None,
        destination_filter=None,
    )

    assert len(departures) == 1
    dep = departures[0]
    # Origin "Frankfurt(Main)Hbf" at index 0 should be skipped
    assert "Frankfurt(Main)Hbf" not in dep.via_stations
    assert "Mannheim Hbf" in dep.via_stations
    assert "Stuttgart Hbf" in dep.via_stations


async def test_halt_ausfall_is_cancelled() -> None:
    """Departure with HALT_AUSFALL meldung should have is_cancelled=True."""
    meldungen = [{"type": "HALT_AUSFALL", "text": "Zug fällt aus"}]
    client = make_mock_client(
        departures_entries=[make_departure_raw(meldungen=meldungen)]
    )
    service = DepartureService(client)

    _, departures = await service.get_departures(
        station_name="Frankfurt",
        dt=None,
        modes=None,
        destination_filter=None,
    )

    assert departures[0].is_cancelled is True


def test_mode_filter() -> None:
    """Only specified modes should be passed to client."""
    client = make_mock_client()
    service = DepartureService(client)

    # Run synchronously for verification of the call — we just check what gets passed
    import asyncio

    asyncio.get_event_loop().run_until_complete(
        service.get_departures(
            station_name="Frankfurt",
            dt=None,
            modes=[TransportMode.ICE],
            destination_filter=None,
        )
    )

    call_kwargs = client.get_departures.call_args
    # modes should only contain "ICE"
    passed_modes = call_kwargs[1].get("modes") or call_kwargs[0][4]
    assert passed_modes == ["ICE"]


async def test_destination_filter() -> None:
    """Only departures matching destination filter are returned."""
    entries = [
        make_departure_raw(journey_id="j1", terminus="München Hbf"),
        make_departure_raw(journey_id="j2", terminus="Hamburg Hbf"),
    ]
    client = make_mock_client(departures_entries=entries)
    service = DepartureService(client)

    _, departures = await service.get_departures(
        station_name="Frankfurt",
        dt=None,
        modes=None,
        destination_filter="München",
    )

    assert len(departures) == 1
    assert departures[0].journey_id == "j1"


async def test_station_not_found() -> None:
    """Empty station search results should raise StationNotFoundError."""
    client = make_mock_client(stations=[])
    service = DepartureService(client)

    with pytest.raises(StationNotFoundError):
        await service.get_departures(
            station_name="ZZZUNKNOWN999",
            dt=None,
            modes=None,
            destination_filter=None,
        )


async def test_delay_computed_correctly() -> None:
    """Delay minutes should be computed from scheduled vs real-time departure."""
    entries = [make_departure_raw(zeit="2026-02-24T14:30:00", ez_zeit="2026-02-24T14:38:00")]
    client = make_mock_client(departures_entries=entries)
    service = DepartureService(client)

    _, departures = await service.get_departures(
        station_name="Frankfurt",
        dt=None,
        modes=None,
        destination_filter=None,
    )

    assert departures[0].delay_minutes == 8


async def test_on_time_departure() -> None:
    """Departure with no ezZeit should have delay_minutes=0 and rt_departure=None."""
    entries = [make_departure_raw(ez_zeit="")]
    client = make_mock_client(departures_entries=entries)
    service = DepartureService(client)

    _, departures = await service.get_departures(
        station_name="Frankfurt",
        dt=None,
        modes=None,
        destination_filter=None,
    )

    assert departures[0].delay_minutes == 0
    assert departures[0].rt_departure is None


async def test_prefers_st_type_station() -> None:
    """resolve_station should prefer type 'ST' over other types."""
    stations = [
        {"evaNumber": 1, "id": "@X=0@Y=0@", "name": "Frankfurt POI", "lat": 0.0, "lon": 0.0, "type": "POI", "products": []},
        {"evaNumber": 8000105, "id": "@X=8663785@Y=50107149@", "name": "Frankfurt Hbf", "lat": 50.0, "lon": 8.0, "type": "ST", "products": ["ICE"]},
    ]
    client = MagicMock()
    client.search_stations = AsyncMock(return_value=stations)
    client.get_departures = AsyncMock(return_value={"entries": []})
    service = DepartureService(client)

    location = await service.resolve_station("Frankfurt")
    assert location.eva == 8000105
    assert location.name == "Frankfurt Hbf"
