from __future__ import annotations

from typing import Any

import httpx

from db_mcp.domain.exceptions import ApiError
from db_mcp.infrastructure.cache import TTLCache
from db_mcp.infrastructure.headers import make_headers

BASE_URL = "https://www.bahn.de/web/api"
DEFAULT_TIMEOUT = 15.0  # seconds

# TTL values per endpoint (in seconds)
TTL_STATIONS = 300  # Station data changes rarely
TTL_DEPARTURES = 90
TTL_JOURNEY = 30  # Short TTL — live positions change frequently


class BahnClient:
    """HTTP client for the bahn.de API.

    A single httpx.AsyncClient instance is used throughout the process lifetime
    so that session cookies persist across requests.
    """

    def __init__(self, cache: TTLCache, http_client: httpx.AsyncClient) -> None:
        self._cache = cache
        self._http = http_client  # Shared client; cookie jar persists across calls

    async def search_stations(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """GET /reiseloesung/orte — cache TTL 300 s (station data changes rarely)."""
        url = f"{BASE_URL}/reiseloesung/orte"
        params: dict[str, Any] = {"suchbegriff": query, "typ": "ALL", "limit": limit}
        result = await self._get(url, params, ttl=TTL_STATIONS)
        # The API returns a list directly
        if isinstance(result, list):
            return result
        items: list[dict[str, Any]] = result.get("items", result.get("orte", []))
        return items

    async def get_nearby_stations(
        self, lat: float, lon: float, radius: int = 9999, max_no: int = 100
    ) -> list[dict[str, Any]]:
        """GET /reiseloesung/orte/nearby — cache TTL 300 s."""
        url = f"{BASE_URL}/reiseloesung/orte/nearby"
        params: dict[str, Any] = {"lat": lat, "long": lon, "radius": radius, "maxNo": max_no}
        result = await self._get(url, params, ttl=TTL_STATIONS)
        if isinstance(result, list):
            return result
        items: list[dict[str, Any]] = result.get("items", [])
        return items

    async def get_departures(
        self,
        eva: int,
        hafas_id: str,
        datum: str,  # YYYY-MM-DD (Europe/Berlin)
        zeit: str,  # HH:MM:SS (Europe/Berlin)
        modes: list[str],  # [] means all modes (no filter)
    ) -> dict[str, Any]:
        """GET /reiseloesung/abfahrten — cache TTL 90 s.

        Always sends mitVias=true and maxVias=5.
        """
        url = f"{BASE_URL}/reiseloesung/abfahrten"
        base_params: dict[str, Any] = {
            "datum": datum,
            "zeit": zeit,
            "ortExtId": eva,
            "ortId": hafas_id,
            "mitVias": "true",
            "maxVias": 5,
        }
        # Build a stable cache key including sorted modes
        modes_key = ",".join(sorted(modes)) if modes else ""
        cache_key = (
            url
            + "?"
            + "&".join(f"{k}={v}" for k, v in sorted(base_params.items()))
            + f"&modes={modes_key}"
        )

        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        # Build httpx params with repeatable verkehrsmittel[]
        httpx_params: list[tuple[str, str]] = [
            (str(k), str(v)) for k, v in base_params.items()
        ]
        for mode in modes:
            httpx_params.append(("verkehrsmittel[]", mode))

        headers = make_headers()
        response = await self._http.get(
            url,
            params=httpx_params,  # type: ignore[arg-type]
            headers=headers,
        )
        self._raise_for_status(response)
        data: dict[str, Any] = response.json()
        self._cache.set(cache_key, data, ttl=TTL_DEPARTURES)
        return data

    async def get_journey(self, journey_id: str) -> dict[str, Any]:
        """GET /reiseloesung/fahrt — all stops for a journey, cache TTL 30 s."""
        url = f"{BASE_URL}/reiseloesung/fahrt"
        params: dict[str, Any] = {"journeyId": journey_id, "poly": "false"}
        return await self._get(url, params, ttl=TTL_JOURNEY)

    async def _get(
        self,
        url: str,
        params: dict[str, Any],
        ttl: int | None = None,
    ) -> dict[str, Any]:
        """Internal GET helper.

        1. Build cache key from (url, sorted params).
        2. Return cached value if present.
        3. Otherwise call httpx with make_headers() and DEFAULT_TIMEOUT.
        4. Raise ApiError on non-2xx status.
        5. Store result in cache and return.
        """
        cache_key = url + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))

        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        headers = make_headers()
        response = await self._http.get(url, params=params, headers=headers)
        self._raise_for_status(response)
        data: dict[str, Any] = response.json()
        self._cache.set(cache_key, data, ttl=ttl)
        return data

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Raise ApiError for non-2xx responses."""
        if response.status_code == 404:
            raise ApiError(404, f"Resource not found (404): {response.url}")
        if response.status_code >= 400:
            raise ApiError(response.status_code)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
