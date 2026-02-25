from __future__ import annotations

from uuid import uuid4

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]
_ua_index = 0


def make_headers() -> dict[str, str]:
    """Return a complete set of browser-like headers required by bahn.de.

    x-correlation-id is freshly generated on every call: str(uuid4()) + "_" + str(uuid4()).
    User-Agent rotates through _USER_AGENTS to reduce bot-detection risk.
    """
    global _ua_index
    ua = _USER_AGENTS[_ua_index % len(_USER_AGENTS)]
    _ua_index += 1
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Origin": "https://www.bahn.de",
        "Referer": "https://www.bahn.de/buchung/fahrplan/suche",
        "User-Agent": ua,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "sec-ch-ua": '"Chromium";v="131", "Not?A_Brand";v="24", "Google Chrome";v="131"',
        "sec-ch-ua-mobile": "?0",
        "x-correlation-id": f"{uuid4()}_{uuid4()}",
    }
