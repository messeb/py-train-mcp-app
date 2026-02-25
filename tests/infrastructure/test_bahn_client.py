"""Tests for BahnClient using respx to mock HTTP calls."""
from __future__ import annotations

import httpx
import pytest
import respx

from db_mcp.domain.exceptions import ApiError
from db_mcp.infrastructure.bahn_client import BASE_URL, BahnClient
from db_mcp.infrastructure.cache import TTLCache


def make_client() -> tuple[BahnClient, TTLCache]:
    """Create a BahnClient with a fresh TTLCache and httpx client."""
    cache = TTLCache()
    http_client = httpx.AsyncClient()
    client = BahnClient(cache=cache, http_client=http_client)
    return client, cache


@respx.mock
async def test_search_stations_calls_correct_url() -> None:
    """search_stations should call /reiseloesung/orte with correct query params."""
    stations_data = [
        {
            "extId": "8000105",
            "evaNumber": 8000105,
            "id": "A=1@O=Frankfurt(Main)Hbf@X=8663785@Y=50107149@",
            "name": "Frankfurt(Main)Hbf",
            "lat": 50.107149,
            "lon": 8.663785,
            "type": "ST",
            "products": ["ICE"],
        }
    ]
    respx.get(f"{BASE_URL}/reiseloesung/orte").mock(
        return_value=httpx.Response(200, json=stations_data)
    )

    client, _ = make_client()
    result = await client.search_stations("Frankfurt")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "Frankfurt(Main)Hbf"
    await client.close()


@respx.mock
async def test_get_departures_includes_modes() -> None:
    """get_departures should pass verkehrsmittel[] params for each mode."""
    dep_data = {"entries": []}
    route = respx.get(f"{BASE_URL}/reiseloesung/abfahrten").mock(
        return_value=httpx.Response(200, json=dep_data)
    )

    client, _ = make_client()
    await client.get_departures(
        eva=8000105,
        hafas_id="A=1@O=Frankfurt@X=8663785@Y=50107149@",
        datum="2026-02-24",
        zeit="14:00:00",
        modes=["ICE", "REGIONAL"],
    )

    assert route.called
    # Verify the request URL contains the modes
    request = route.calls[0].request
    url_str = str(request.url)
    assert "ICE" in url_str or "verkehrsmittel" in url_str
    await client.close()


@respx.mock
async def test_cache_used_on_second_call() -> None:
    """Second call with same params should use cache, not make another HTTP request."""
    stations_data = [{"name": "Frankfurt(Main)Hbf", "evaNumber": 8000105}]
    route = respx.get(f"{BASE_URL}/reiseloesung/orte").mock(
        return_value=httpx.Response(200, json=stations_data)
    )

    client, _ = make_client()
    result1 = await client.search_stations("Frankfurt")
    result2 = await client.search_stations("Frankfurt")

    # HTTP should only have been called once
    assert route.call_count == 1
    assert result1 == result2
    await client.close()


@respx.mock
async def test_api_error_on_non_2xx() -> None:
    """ApiError should be raised when server returns 500."""
    respx.get(f"{BASE_URL}/reiseloesung/orte").mock(
        return_value=httpx.Response(500)
    )

    client, _ = make_client()
    with pytest.raises(ApiError) as exc_info:
        await client.search_stations("Frankfurt")

    assert exc_info.value.status_code == 500
    await client.close()


@respx.mock
async def test_get_departures_no_modes_no_filter() -> None:
    """get_departures with empty modes list should work."""
    dep_data = {"entries": [{"terminus": "München Hbf"}]}
    respx.get(f"{BASE_URL}/reiseloesung/abfahrten").mock(
        return_value=httpx.Response(200, json=dep_data)
    )

    client, _ = make_client()
    result = await client.get_departures(
        eva=8000105,
        hafas_id="A=1@O=Frankfurt@X=8663785@Y=50107149@",
        datum="2026-02-24",
        zeit="14:00:00",
        modes=[],
    )

    assert result["entries"][0]["terminus"] == "München Hbf"
    await client.close()


