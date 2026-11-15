"""Synthetic prices for trying the tracker without an API key. Never mixed with real data:
demo runs write to data-demo/ and reports are labelled SAMPLE."""
from __future__ import annotations

import datetime as dt
import hashlib
import math
import random

from ..config import Config, Trip
from ..seasons import peak_name
from . import Quote

BASE = {"AMS": 1150, "BCN": 980, "FCO": 820}


def _curve(days_out: int, peak: bool) -> float:
    """Typical shape: falls gently until ~2 months out, then climbs; peaks climb all along."""
    if peak:
        return 1.35 + 0.004 * max(0, 150 - days_out) + (0.03 * (21 - days_out) if days_out < 21 else 0)
    base = 1.0 + 0.0006 * max(0, days_out - 60)
    if days_out < 45:
        base += 0.006 * (45 - days_out)
    if days_out < 14:
        base += 0.03 * (14 - days_out)
    return base


def _price(trip: Trip, on: dt.date) -> float:
    """Fares move in steps (fare buckets) and sometimes drop briefly during sales."""
    days_out = (trip.depart - on).days
    peak = peak_name(trip.depart) is not None
    base = BASE.get(trip.destination, 1000)
    level = base * _curve(days_out, peak)
    step = 0.04  # fares jump between buckets about 4% apart
    level = math.exp(round(math.log(level) / step) * step)
    week = int(hashlib.md5(f"{trip.key}{on.toordinal() // 5}".encode()).hexdigest()[:8], 16)
    rnd = random.Random(week)
    if rnd.random() < 0.12:  # short sale / competitor match
        level *= 0.88
    level *= 1 + random.Random(week + 1).choice([-0.04, 0, 0, 0.04])
    return float(round(level))


def fetch(cfg: Config, trip: Trip, today: dt.date | None = None) -> Quote:
    today = today or dt.date.today()
    now = dt.datetime.combine(today, dt.time(6, 0), dt.timezone.utc)
    hist = [(today - dt.timedelta(days=i), _price(trip, today - dt.timedelta(days=i))) for i in range(60, 0, -1)]
    base = BASE.get(trip.destination, 1000)
    return Quote(trip.key, "demo", now, _price(trip, today), cfg.currency, airline="Demo Air",
                 stops=0, duration_min=290, typical_low=round(base * 0.95), typical_high=round(base * 1.3),
                 history=hist)
