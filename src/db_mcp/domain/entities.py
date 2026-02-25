from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """A service alert or informational message attached to a departure."""

    type: str  # e.g. "DELAY", "HALT_AUSFALL"
    text: str


@dataclass
class Location:
    """A resolved Deutsche Bahn station or stop."""

    eva: int  # EVA number (int64) — used as ortExtId in API calls
    hafas_id: str  # Hafas station ID string — used as ortId in API calls
    name: str  # Human-readable station name
    lat: float
    lon: float
    location_type: str  # "ST" = station, "POI", "ADR"
    transport_modes: list[str] = field(default_factory=list)


@dataclass
class Departure:
    """A single departure entry from a station departure board."""

    journey_id: str
    train_name: str  # Full name, e.g. "ICE 619"
    train_type: str  # Short type, e.g. "ICE"
    destination: str  # Final terminus name
    via_stations: list[str]  # ueber[1:] — first entry (origin) is always skipped
    platform: str  # Scheduled platform (gleis)
    rt_platform: str  # Real-time platform (ezGleis); empty string if unchanged
    scheduled_departure: datetime
    rt_departure: datetime | None  # None when on time (ezZeit empty)
    effective_departure: datetime  # rt_departure if set, else scheduled_departure
    delay_minutes: int  # 0 when on time; clamped to 0 for early trains
    is_cancelled: bool  # True when any meldungen[].type == "HALT_AUSFALL"
    messages: list[Message] = field(default_factory=list)
