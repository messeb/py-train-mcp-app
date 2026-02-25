from __future__ import annotations

from datetime import datetime

from db_mcp.domain.entities import Departure, Location, Message
from db_mcp.domain.exceptions import StationNotFoundError
from db_mcp.domain.services import delay_minutes, effective_time, is_cancelled
from db_mcp.domain.value_objects import TransportMode
from db_mcp.infrastructure.bahn_client import BahnClient
from db_mcp.infrastructure.time_utils import (
    format_datum,
    format_zeit,
    now_berlin,
    parse_bahn_datetime,
)


class DepartureService:
    """Orchestrates station resolution, departure fetching, and result mapping."""

    def __init__(self, client: BahnClient) -> None:
        self._client = client

    async def resolve_station(self, name: str) -> Location:
        """Search for station by name, return the best match.

        Selection rule: prefer the first result with location_type == "ST";
        fall back to the first result of any type.
        Raises StationNotFoundError when results are empty.
        """
        results = await self._client.search_stations(name, limit=10)
        if not results:
            raise StationNotFoundError(f"Station not found: {name}")

        # Prefer type "ST" (station) over other types
        for raw in results:
            if raw.get("type") == "ST":
                return self._map_location(raw)

        # Fall back to first result regardless of type
        return self._map_location(results[0])

    async def get_departures(
        self,
        station_name: str,
        dt: datetime | None,  # None → use now_berlin()
        modes: list[TransportMode] | None,  # None → all modes
        destination_filter: str | None,  # case-insensitive substring match
        max_results: int = 20,
    ) -> tuple[Location, list[Departure]]:
        """Resolve station, fetch departures, apply filters, return (station, departures).

        Steps:
        1. Resolve station_name → Location (raises StationNotFoundError if not found)
        2. Call BahnClient.get_departures with eva, hafas_id, datum, zeit, modes
        3. Map raw API entries → Departure domain objects
        4. Apply destination_filter (case-insensitive substring on Departure.destination)
        5. Truncate to max_results
        6. Return (location, departures)
        """
        location = await self.resolve_station(station_name)

        effective_dt = dt if dt is not None else now_berlin()
        datum = format_datum(effective_dt)
        zeit = format_zeit(effective_dt)

        mode_strings: list[str] = [m.value for m in modes] if modes is not None else []

        raw_data = await self._client.get_departures(
            eva=location.eva,
            hafas_id=location.hafas_id,
            datum=datum,
            zeit=zeit,
            modes=mode_strings,
        )

        entries: list[dict] = raw_data.get("entries", [])  # type: ignore[type-arg]
        departures = [self._map_departure(entry) for entry in entries]

        # Apply destination filter
        if destination_filter:
            dest_lower = destination_filter.lower()
            departures = [
                d
                for d in departures
                if dest_lower in d.destination.lower()
                or any(dest_lower in via.lower() for via in d.via_stations)
            ]

        return location, departures[:max_results]

    async def get_journey(self, journey_id: str) -> dict:  # type: ignore[type-arg]
        """Fetch all stops for a journey and return structured stop data."""
        raw = await self._client.get_journey(journey_id)
        halte: list[dict] = raw.get("halte", [])  # type: ignore[type-arg]
        stops = []
        for h in halte:
            rt_dep = h.get("ezAbfahrtsZeitpunkt") or None
            rt_arr = h.get("ezAnkunftsZeitpunkt") or None
            meldungen: list[dict] = (  # type: ignore[type-arg]
                h.get("priorisierteMeldungen", []) + h.get("risMeldungen", [])
            )
            is_stop_cancelled = h.get("canceled", False) or any(
                m.get("type") == "HALT_AUSFALL"
                or m.get("key") == "text.realtime.stop.cancelled"
                for m in meldungen
            )
            stops.append(
                {
                    "name": h.get("name", ""),
                    "eva": h.get("evaNumber") or h.get("extId", ""),
                    "platform": h.get("gleis", ""),
                    "rt_platform": h.get("ezGleis", ""),
                    "sched_dep": h.get("abfahrtsZeitpunkt"),
                    "rt_dep": rt_dep,
                    "sched_arr": h.get("ankunftsZeitpunkt"),
                    "rt_arr": rt_arr,
                    "is_cancelled": is_stop_cancelled,
                    "is_additional": h.get("additional", False),
                }
            )
        return {
            "journey_id": journey_id,
            "train_name": raw.get("zugName", ""),
            "date": raw.get("reisetag", ""),
            "is_cancelled": raw.get("cancelled", False),
            "stops": stops,
        }

    def _map_departure(self, raw: dict) -> Departure:  # type: ignore[type-arg]
        """Map a single raw API departure entry to the Departure domain entity.

        Key mappings:
        - raw["ueber"] → via_stations = ueber[1:]  (skip index 0, which is origin)
        - raw["zeit"] → scheduled_departure (parse_bahn_datetime)
        - raw["ezZeit"] → rt_departure (None when empty string or missing)
        - raw["meldungen"] → is_cancelled via domain.services.is_cancelled
        - raw["verkehrmittel"]["mittelText"] → train_name
        - raw["verkehrmittel"]["kurzText"] → train_type
        - raw["terminus"] → destination
        - raw["gleis"] → platform
        - raw["ezGleis"] → rt_platform (empty string when unchanged)
        """
        verkehrmittel = raw.get("verkehrmittel", {})
        # Use langText or mittelText for the train name, fall back to kurzText
        train_name = (
            verkehrmittel.get("langText")
            or verkehrmittel.get("mittelText")
            or verkehrmittel.get("kurzText", "")
        )
        train_type = verkehrmittel.get("kurzText", "")

        # via_stations: skip ueber[0] which is the origin station
        ueber: list[str] = raw.get("ueber", [])
        via_stations = ueber[1:]  # CRITICAL: skip index 0

        sched_dt = parse_bahn_datetime(raw.get("zeit", ""))

        ez_zeit_str = raw.get("ezZeit", "")
        rt_dt: datetime | None = None
        if ez_zeit_str:
            try:
                rt_dt = parse_bahn_datetime(ez_zeit_str)
            except ValueError:
                rt_dt = None

        eff_dt = effective_time(sched_dt, rt_dt)
        delay = delay_minutes(sched_dt, rt_dt)

        meldungen: list[dict] = raw.get("meldungen", [])  # type: ignore[type-arg]
        cancelled = is_cancelled(meldungen)

        # Map messages
        messages = [
            Message(type=m.get("type", ""), text=m.get("text", ""))
            for m in meldungen
        ]

        return Departure(
            journey_id=raw.get("journeyId", ""),
            train_name=train_name,
            train_type=train_type,
            destination=raw.get("terminus", ""),
            via_stations=via_stations,
            platform=raw.get("gleis", ""),
            rt_platform=raw.get("ezGleis", ""),
            scheduled_departure=sched_dt,
            rt_departure=rt_dt,
            effective_departure=eff_dt,
            delay_minutes=delay,
            is_cancelled=cancelled,
            messages=messages,
        )

    def _map_location(self, raw: dict) -> Location:  # type: ignore[type-arg]
        """Map a raw station API response to a Location entity."""
        eva = int(raw.get("evaNumber", raw.get("extId", 0)))
        return Location(
            eva=eva,
            hafas_id=raw.get("id", ""),
            name=raw.get("name", ""),
            lat=float(raw.get("lat", 0.0)),
            lon=float(raw.get("lon", 0.0)),
            location_type=raw.get("type", "ST"),
            transport_modes=raw.get("products", []),
        )
