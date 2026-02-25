from __future__ import annotations

import re
from datetime import datetime


def delay_minutes(sched: datetime, rt: datetime | None) -> int:
    """Return delay in whole minutes between sched and rt.

    Returns 0 when rt is None (on time) or when rt is earlier than sched
    (early arrival/departure — clamped to 0 per requirements).
    """
    if rt is None:
        return 0
    delta = int((rt - sched).total_seconds() / 60)
    return max(0, delta)


def is_cancelled(messages: list[dict[str, str]]) -> bool:
    """Return True when any message dict has type == "HALT_AUSFALL".

    Accepts the raw meldungen list from the API response.
    """
    return any(m.get("type") == "HALT_AUSFALL" for m in messages)


def effective_time(sched: datetime, rt: datetime | None) -> datetime:
    """Return rt if provided, otherwise return sched."""
    return rt if rt is not None else sched


def parse_coords_from_hafas_id(hafas_id: str) -> tuple[float, float]:
    """Extract (lat, lon) from a Hafas station ID string.

    The ID encodes coordinates as: @X=<lon_times_1e6>@Y=<lat_times_1e6>
    Example: "A=1@O=Frankfurt(Main)Hbf@X=8663785@Y=50107149@"
    Returns (lat, lon) as floats divided by 1_000_000.

    Raises ValueError when the expected @X= / @Y= tokens are absent.
    """
    x_match = re.search(r"@X=(-?\d+)", hafas_id)
    y_match = re.search(r"@Y=(-?\d+)", hafas_id)

    if x_match is None or y_match is None:
        raise ValueError(
            f"Could not parse coordinates from Hafas ID: {hafas_id!r}. "
            "Expected @X=<lon*1e6> and @Y=<lat*1e6> tokens."
        )

    lon = int(x_match.group(1)) / 1_000_000
    lat = int(y_match.group(1)) / 1_000_000
    return lat, lon
