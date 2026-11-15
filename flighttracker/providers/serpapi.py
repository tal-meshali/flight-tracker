"""Google Flights results through SerpApi (https://serpapi.com/google-flights-api).

SerpApi is a licensed API, so we never scrape Google directly. Each call = 1 search
from the monthly quota (free plan: 250/month)."""
from __future__ import annotations

import datetime as dt
import json
import urllib.parse
import urllib.request

from ..config import Config, Trip
from . import Quote

URL = "https://serpapi.com/search.json"
CLASSES = {"economy": 1, "premium_economy": 2, "business": 3, "first": 4}
STOPS = {-1: 0, 0: 1, 1: 2, 2: 3}


def build_params(cfg: Config, trip: Trip, api_key: str, market: str | None = None,
                 currency: str | None = None) -> dict:
    p = {
        "engine": "google_flights",
        "departure_id": trip.origin,
        "arrival_id": trip.destination,
        "outbound_date": trip.depart.isoformat(),
        "type": 1 if trip.ret else 2,
        "currency": currency or cfg.currency,
        "gl": market or cfg.market,
        "hl": cfg.language,
        "adults": cfg.adults,
        "travel_class": CLASSES.get(cfg.travel_class, 1),
        "stops": STOPS.get(cfg.max_stops, 0),
        "api_key": api_key,
    }
    if trip.ret:
        p["return_date"] = trip.ret.isoformat()
    return p


def parse(data: dict, trip: Trip, currency: str, now: dt.datetime) -> Quote:
    if data.get("error"):
        # "no results" is a valid answer (e.g. no flights that day), not a crash
        return Quote(trip.key, "google", now, None, currency, error=str(data["error"])[:200])
    flights = (data.get("best_flights") or []) + (data.get("other_flights") or [])
    flights = [f for f in flights if f.get("price")]
    best = min(flights, key=lambda f: f["price"]) if flights else None
    pi = data.get("price_insights") or {}
    lo_hi = pi.get("typical_price_range") or [None, None]
    hist = []
    for ts, price in pi.get("price_history") or []:
        if price:
            hist.append((dt.datetime.fromtimestamp(ts, dt.timezone.utc).date(), float(price)))
    price = float(best["price"]) if best else (float(pi["lowest_price"]) if pi.get("lowest_price") else None)
    q = Quote(trip.key, "google", now, price, currency,
              typical_low=lo_hi[0], typical_high=lo_hi[1],
              price_level=pi.get("price_level", ""), history=hist)
    if best:
        segs = best.get("flights") or []
        q.airline = ", ".join(sorted({s.get("airline", "") for s in segs if s.get("airline")}))
        q.stops = len(best.get("layovers") or [])
        q.duration_min = best.get("total_duration")
    return q


def fetch(cfg: Config, trip: Trip, api_key: str, market: str | None = None,
          currency: str | None = None, timeout: int = 60) -> Quote:
    params = build_params(cfg, trip, api_key, market, currency)
    url = URL + "?" + urllib.parse.urlencode(params)
    now = dt.datetime.now(dt.timezone.utc)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        try:
            data = json.load(e)
        except Exception:
            data = {"error": f"HTTP {e.code}"}
    except Exception as e:  # network problems: record and move on
        return Quote(trip.key, "google", now, None, params["currency"], error=str(e)[:200])
    return parse(data, trip, params["currency"], now)
