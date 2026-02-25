"""Tests for the header factory."""
from __future__ import annotations

import re

from db_mcp.infrastructure.headers import make_headers

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def test_correlation_id_present() -> None:
    headers = make_headers()
    assert "x-correlation-id" in headers


def test_correlation_id_format() -> None:
    headers = make_headers()
    cid = headers["x-correlation-id"]
    assert "_" in cid, "Correlation ID should contain underscore separator"
    assert UUID_PATTERN.match(cid), f"Correlation ID {cid!r} does not match expected pattern"


def test_different_each_call() -> None:
    h1 = make_headers()
    h2 = make_headers()
    assert h1["x-correlation-id"] != h2["x-correlation-id"]


def test_make_headers_required_keys() -> None:
    headers = make_headers()
    required_keys = [
        "Accept",
        "Accept-Language",
        "Cache-Control",
        "Pragma",
        "Origin",
        "Referer",
        "User-Agent",
        "Sec-Fetch-Dest",
        "Sec-Fetch-Mode",
        "Sec-Fetch-Site",
        "sec-ch-ua",
        "sec-ch-ua-mobile",
        "x-correlation-id",
    ]
    for key in required_keys:
        assert key in headers, f"Missing required header: {key}"


def test_user_agent_non_empty() -> None:
    headers = make_headers()
    assert headers["User-Agent"], "User-Agent should be a non-empty string"


def test_origin_is_bahn_de() -> None:
    headers = make_headers()
    assert headers["Origin"] == "https://www.bahn.de"


def test_accept_includes_json() -> None:
    headers = make_headers()
    assert "application/json" in headers["Accept"]
