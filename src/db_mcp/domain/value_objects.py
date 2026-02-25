from __future__ import annotations

from enum import Enum


class TransportMode(str, Enum):
    """Valid transport mode values accepted by the bahn.de API verkehrsmittel[] parameter.

    Using (str, Enum) for Python 3.10 compatibility (StrEnum requires 3.11+).
    """

    ICE = "ICE"
    EC_IC = "EC_IC"
    IR = "IR"
    REGIONAL = "REGIONAL"
    SBAHN = "SBAHN"
    BUS = "BUS"
    SCHIFF = "SCHIFF"
    UBAHN = "UBAHN"
    TRAM = "TRAM"
    ANRUFPFLICHTIG = "ANRUFPFLICHTIG"
