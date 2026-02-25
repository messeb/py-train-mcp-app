"""Tests for domain service pure functions."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from db_mcp.domain.services import (
    delay_minutes,
    effective_time,
    is_cancelled,
    parse_coords_from_hafas_id,
)

# ---------------------------------------------------------------------------
# delay_minutes
# ---------------------------------------------------------------------------

def test_delay_minutes_on_time() -> None:
    sched = datetime(2026, 2, 24, 14, 30, tzinfo=timezone.utc)
    assert delay_minutes(sched, None) == 0


def test_delay_minutes_positive() -> None:
    sched = datetime(2026, 2, 24, 14, 30, tzinfo=timezone.utc)
    rt = datetime(2026, 2, 24, 14, 35, tzinfo=timezone.utc)
    assert delay_minutes(sched, rt) == 5


def test_delay_minutes_early_clamped() -> None:
    """Negative delay (early train) is clamped to 0."""
    sched = datetime(2026, 2, 24, 14, 30, tzinfo=timezone.utc)
    rt = datetime(2026, 2, 24, 14, 28, tzinfo=timezone.utc)
    assert delay_minutes(sched, rt) == 0


def test_delay_minutes_with_rt() -> None:
    sched = datetime(2026, 2, 24, 14, 0, tzinfo=timezone.utc)
    rt = datetime(2026, 2, 24, 14, 8, tzinfo=timezone.utc)
    assert delay_minutes(sched, rt) == 8


def test_delay_minutes_no_rt() -> None:
    sched = datetime(2026, 2, 24, 14, 0, tzinfo=timezone.utc)
    assert delay_minutes(sched, None) == 0


def test_delay_minutes_fractional_rounds_down() -> None:
    sched = datetime(2026, 2, 24, 14, 0, 0, tzinfo=timezone.utc)
    rt = datetime(2026, 2, 24, 14, 2, 30, tzinfo=timezone.utc)  # 2.5 minutes late
    assert delay_minutes(sched, rt) == 2


# ---------------------------------------------------------------------------
# is_cancelled
# ---------------------------------------------------------------------------

def test_is_cancelled_halt_ausfall() -> None:
    messages = [{"type": "HALT_AUSFALL", "text": "Zug fällt aus"}]
    assert is_cancelled(messages) is True


def test_is_cancelled_no_halt_ausfall() -> None:
    messages = [{"type": "DELAY", "text": "Verspätung"}]
    assert is_cancelled(messages) is False


def test_is_cancelled_true() -> None:
    assert is_cancelled([{"type": "HALT_AUSFALL"}]) is True


def test_is_cancelled_false_other_type() -> None:
    assert is_cancelled([{"type": "DELAY"}]) is False


def test_is_cancelled_empty() -> None:
    assert is_cancelled([]) is False


def test_is_cancelled_mixed_messages() -> None:
    messages = [
        {"type": "DELAY", "text": "Late"},
        {"type": "HALT_AUSFALL", "text": "Cancelled"},
    ]
    assert is_cancelled(messages) is True


# ---------------------------------------------------------------------------
# effective_time
# ---------------------------------------------------------------------------

def test_effective_time_uses_rt_when_present() -> None:
    sched = datetime(2026, 2, 24, 14, 30, tzinfo=timezone.utc)
    rt = datetime(2026, 2, 24, 14, 32, tzinfo=timezone.utc)
    assert effective_time(sched, rt) == rt


def test_effective_time_falls_back_to_sched() -> None:
    sched = datetime(2026, 2, 24, 14, 30, tzinfo=timezone.utc)
    assert effective_time(sched, None) == sched


def test_effective_time_uses_rt() -> None:
    sched = datetime(2026, 2, 24, 14, 30, tzinfo=timezone.utc)
    rt = datetime(2026, 2, 24, 14, 35, tzinfo=timezone.utc)
    assert effective_time(sched, rt) == rt


def test_effective_time_uses_sched() -> None:
    sched = datetime(2026, 2, 24, 14, 30, tzinfo=timezone.utc)
    assert effective_time(sched, None) == sched


# ---------------------------------------------------------------------------
# parse_coords_from_hafas_id
# ---------------------------------------------------------------------------

def test_parse_coords_valid() -> None:
    hafas_id = "A=1@O=Frankfurt(Main)Hbf@X=8663785@Y=50107149@"
    lat, lon = parse_coords_from_hafas_id(hafas_id)
    assert abs(lat - 50.107149) < 1e-6
    assert abs(lon - 8.663785) < 1e-6


def test_parse_coords_negative_lon() -> None:
    hafas_id = "A=1@O=SomeStation@X=-8663785@Y=50107149@"
    lat, lon = parse_coords_from_hafas_id(hafas_id)
    assert abs(lat - 50.107149) < 1e-6
    assert abs(lon - (-8.663785)) < 1e-6


def test_parse_coords_missing_tokens() -> None:
    with pytest.raises(ValueError):
        parse_coords_from_hafas_id("no-coordinates-here")


def test_parse_coords_missing_x() -> None:
    with pytest.raises(ValueError):
        parse_coords_from_hafas_id("@Y=50107149@")


def test_parse_coords_missing_y() -> None:
    with pytest.raises(ValueError):
        parse_coords_from_hafas_id("@X=8663785@")
