from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

BERLIN_TZ: ZoneInfo = ZoneInfo("Europe/Berlin")
UTC_TZ: ZoneInfo = ZoneInfo("UTC")


def now_berlin() -> datetime:
    """Return the current moment as a timezone-aware datetime in Europe/Berlin."""
    return datetime.now(tz=BERLIN_TZ)


def parse_bahn_datetime(s: str) -> datetime:
    """Parse a datetime string from bahn.de API responses.

    Handles formats:
    - "2026-02-24T14:30:00"         (naive — assumed Berlin)
    - "2026-02-24T14:30:00+01:00"   (offset-aware)
    - "2026-02-24T14:30:00+02:00"   (summer time)

    Always returns a timezone-aware datetime in Europe/Berlin.
    Raises ValueError on empty or unparseable input.
    """
    if not s or not s.strip():
        raise ValueError("Empty datetime string")

    s = s.strip()

    # Try parsing with timezone offset first
    if "+" in s or (s.count("-") > 2):  # has timezone offset like +01:00 or -01:00
        try:
            # Python 3.7+ fromisoformat handles +HH:MM offsets
            dt = datetime.fromisoformat(s)
            # Convert to Berlin timezone
            return dt.astimezone(BERLIN_TZ)
        except ValueError:
            pass

    # Try naive format (no timezone info)
    try:
        dt_naive = datetime.fromisoformat(s)
        # Treat as Berlin local time
        return dt_naive.replace(tzinfo=BERLIN_TZ)
    except ValueError:
        raise ValueError(f"Cannot parse datetime string: {s!r}")


def format_datum(dt: datetime) -> str:
    """Return date string in YYYY-MM-DD format (for datum API parameter)."""
    return dt.strftime("%Y-%m-%d")


def format_zeit(dt: datetime) -> str:
    """Return time string in HH:MM:SS format (for zeit API parameter)."""
    return dt.strftime("%H:%M:%S")


def to_utc(dt: datetime) -> datetime:
    """Convert a timezone-aware datetime to UTC."""
    return dt.astimezone(UTC_TZ)


def format_formation_time(dt: datetime) -> str:
    """Format datetime as YYYY-MM-DDT15:04:05.000Z (UTC) for the formation endpoint.

    Converts to UTC internally before formatting.
    """
    utc_dt = to_utc(dt)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
