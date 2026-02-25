"""Shared pytest fixtures for the Deutsche Bahn MCP Server test suite."""
from __future__ import annotations

from datetime import datetime

import pytest

from db_mcp.infrastructure.time_utils import BERLIN_TZ


@pytest.fixture
def sample_departure_raw() -> dict:  # type: ignore[type-arg]
    """Sample raw departure entry matching the bahn.de API response schema."""
    return {
        "journeyId": "2|#VN#1#ST#1234",
        "terminus": "München Hbf",
        "gleis": "7",
        "ezGleis": "7A",
        "zeit": "2026-02-24T14:30:00",
        "ezZeit": "2026-02-24T14:32:00",
        "ueber": ["Frankfurt(Main)Hbf", "Mannheim Hbf", "Stuttgart Hbf"],
        "verkehrmittel": {
            "kurzText": "ICE",
            "mittelText": "ICE 619",
            "langText": "ICE 619",
            "name": "ICE 619",
        },
        "meldungen": [
            {"type": "DELAY", "text": "Delay due to operational reasons"}
        ],
    }


@pytest.fixture
def sample_journey_raw() -> dict:  # type: ignore[type-arg]
    """Sample raw journey entry matching the bahn.de API response schema."""
    return {
        "reisetag": "2026-02-24",
        "zugName": "ICE 619",
        "cancelled": False,
        "halte": [
            {
                "name": "Frankfurt(Main)Hbf",
                "extId": "8000105",
                "evaNumber": 8000105,
                "id": "A=1@O=Frankfurt(Main)Hbf@X=8663785@Y=50107149@",
                "gleis": "7",
                "ezGleis": "7A",
                "abfahrtsZeitpunkt": "2026-02-24T14:30:00",
                "ezAbfahrtsZeitpunkt": "2026-02-24T14:32:00",
                "ankunftsZeitpunkt": None,
                "ezAnkunftsZeitpunkt": None,
                "adminID": "80____",
                "nummer": "619",
                "kategorie": "ICE",
                "canceled": False,
                "additional": False,
                "priorisierteMeldungen": [],
                "risMeldungen": [],
            },
            {
                "name": "München Hbf",
                "extId": "8000261",
                "evaNumber": 8000261,
                "id": "A=1@O=München Hbf@X=11558339@Y=48140229@",
                "gleis": "18",
                "ezGleis": "",
                "abfahrtsZeitpunkt": None,
                "ezAbfahrtsZeitpunkt": None,
                "ankunftsZeitpunkt": "2026-02-24T16:30:00",
                "ezAnkunftsZeitpunkt": None,
                "adminID": "80____",
                "nummer": "619",
                "kategorie": "ICE",
                "canceled": False,
                "additional": False,
                "priorisierteMeldungen": [],
                "risMeldungen": [],
            },
        ],
        "himMeldungen": [],
        "priorisierteMeldungen": [],
    }


@pytest.fixture
def sample_location_raw() -> dict:  # type: ignore[type-arg]
    """Sample raw location entry matching the bahn.de /reiseloesung/orte response schema."""
    return {
        "extId": "8000105",
        "evaNumber": 8000105,
        "id": "A=1@O=Frankfurt(Main)Hbf@X=8663785@Y=50107149@",
        "name": "Frankfurt(Main)Hbf",
        "lat": 50.107149,
        "lon": 8.663785,
        "type": "ST",
        "products": ["ICE", "EC_IC", "REGIONAL", "SBAHN"],
    }


@pytest.fixture
def frozen_berlin_time(freezer):  # type: ignore[no-untyped-def]
    """Freeze time to 2026-02-24T14:00:00 in Europe/Berlin.

    Requires freezegun to be installed. Use with freezegun.freeze_time.
    """
    return datetime(2026, 2, 24, 14, 0, 0, tzinfo=BERLIN_TZ)
