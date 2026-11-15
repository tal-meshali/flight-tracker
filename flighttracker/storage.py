"""Plain CSV storage so the history is readable on GitHub and diffs cleanly."""
from __future__ import annotations

import csv
import datetime as dt
from collections import defaultdict
from pathlib import Path

from .config import Trip
from .providers import Quote

OBS_FIELDS = ["observed_at", "trip_key", "origin", "destination", "depart", "return", "label",
              "source", "price", "currency", "airline", "stops", "duration_min",
              "typical_low", "typical_high", "price_level", "error"]
HIST_FIELDS = ["trip_key", "source", "date", "price"]


class Store:
    def __init__(self, root: str | Path = "data"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.obs_path = self.root / "observations.csv"
        self.hist_path = self.root / "source_history.csv"

    # ---------- writing ----------
    def add(self, trip: Trip, q: Quote) -> None:
        new = not self.obs_path.exists()
        with self.obs_path.open("a", newline="") as f:
            w = csv.DictWriter(f, OBS_FIELDS)
            if new:
                w.writeheader()
            w.writerow({
                "observed_at": q.observed_at.isoformat(timespec="seconds"), "trip_key": trip.key,
                "origin": trip.origin, "destination": trip.destination,
                "depart": trip.depart.isoformat(), "return": trip.ret.isoformat() if trip.ret else "",
                "label": trip.label, "source": q.source,
                "price": "" if q.price is None else q.price, "currency": q.currency,
                "airline": q.airline, "stops": "" if q.stops is None else q.stops,
                "duration_min": q.duration_min or "", "typical_low": q.typical_low or "",
                "typical_high": q.typical_high or "", "price_level": q.price_level, "error": q.error,
            })
        if q.history:
            self._merge_history(trip.key, q.source, q.history)

    def _merge_history(self, key: str, source: str, points: list[tuple[dt.date, float]]) -> None:
        rows = {}
        if self.hist_path.exists():
            with self.hist_path.open(newline="") as f:
                for r in csv.DictReader(f):
                    rows[(r["trip_key"], r["source"], r["date"])] = r["price"]
        for d, p in points:
            rows[(key, source, d.isoformat())] = p
        with self.hist_path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(HIST_FIELDS)
            for (k, s, d), p in sorted(rows.items()):
                w.writerow([k, s, d, p])

    # ---------- reading ----------
    def observations(self) -> list[dict]:
        if not self.obs_path.exists():
            return []
        with self.obs_path.open(newline="") as f:
            return list(csv.DictReader(f))

    def searches_this_month(self, source: str = "google", today: dt.date | None = None) -> int:
        m = (today or dt.date.today()).strftime("%Y-%m")
        return sum(1 for r in self.observations() if r["source"] == source and r["observed_at"].startswith(m))

    def daily_series(self, key: str) -> dict[dt.date, float]:
        """Cheapest known price per calendar day for one trip, from our own checks plus
        the price history the source reported for that same itinerary."""
        series: dict[dt.date, float] = {}

        def put(d: dt.date, p: float):
            series[d] = min(p, series.get(d, p))

        if self.hist_path.exists():
            with self.hist_path.open(newline="") as f:
                for r in csv.DictReader(f):
                    if r["trip_key"] == key and r["price"]:
                        put(dt.date.fromisoformat(r["date"]), float(r["price"]))
        for r in self.observations():
            if r["trip_key"] == key and r["price"]:
                put(dt.date.fromisoformat(r["observed_at"][:10]), float(r["price"]))
        return dict(sorted(series.items()))

    def latest(self) -> dict[str, dict[str, dict]]:
        """trip_key -> source -> most recent observation row."""
        out: dict[str, dict[str, dict]] = defaultdict(dict)
        for r in self.observations():
            out[r["trip_key"]][r["source"]] = r
        return out
