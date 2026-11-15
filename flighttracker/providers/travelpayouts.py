"""Aviasales / Travelpayouts Data API (free with a partner token).

Prices come from a cache of real user searches in the last ~48h, so they are a useful
free second opinion but not guaranteed bookable. Docs:
https://support.travelpayouts.com/hc/en-us/articles/203956163"""
from __future__ import annotations

import datetime as dt
import json
import urllib.parse
import urllib.request

from ..config import Config, Trip
from . import Quote

URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"


def fetch(cfg: Config, trip: Trip, token: str, timeout: int = 30) -> Quote:
    params = {
        "origin": trip.origin, "destination": trip.destination,
        "departure_at": trip.depart.isoformat(),
        "one_way": "false" if trip.ret else "true",
        "currency": cfg.currency.lower(), "sorting": "price", "limit": 5,
        "direct": "true" if cfg.max_stops == 0 else "false",
    }
    if trip.ret:
        params["return_at"] = trip.ret.isoformat()
    now = dt.datetime.now(dt.timezone.utc)
    req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(params),
                                 headers={"X-Access-Token": token, "Accept-Encoding": "identity"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except Exception as e:
        return Quote(trip.key, "aviasales", now, None, cfg.currency, error=str(e)[:200])
    rows = [x for x in data.get("data") or [] if x.get("price")]
    if not rows:
        return Quote(trip.key, "aviasales", now, None, cfg.currency,
                     error=data.get("error") or "no cached fares")
    best = min(rows, key=lambda x: x["price"])
    stops = best.get("transfers")
    if best.get("return_transfers") is not None and stops is not None:
        stops = max(stops, best["return_transfers"])
    return Quote(trip.key, "aviasales", now, float(best["price"]), cfg.currency,
                 airline=best.get("airline", ""), stops=stops, duration_min=best.get("duration"))
