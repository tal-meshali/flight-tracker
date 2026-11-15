from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


@dataclass
class Quote:
    """The cheapest itinerary found for one trip at one moment, plus any context the source gives."""
    trip_key: str
    source: str
    observed_at: dt.datetime
    price: float | None
    currency: str
    airline: str = ""
    stops: int | None = None
    duration_min: int | None = None
    typical_low: float | None = None
    typical_high: float | None = None
    price_level: str = ""
    # (date, price) points of the source's own price history for this exact trip
    history: list[tuple[dt.date, float]] = field(default_factory=list)
    error: str = ""
