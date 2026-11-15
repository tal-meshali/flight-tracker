import datetime as dt
import json
from pathlib import Path

from flighttracker import advisor
from flighttracker.config import load
from flighttracker.providers import serpapi
from flighttracker.seasons import peak_name
from flighttracker.storage import Store

ROOT = Path(__file__).resolve().parent.parent
CFG = load(ROOT / "config.toml")
TODAY = dt.date(2026, 11, 15)


def test_trips_are_generic_and_land_on_weekday():
    trips = CFG.trips(TODAY)
    assert {t.destination for t in trips} == {"AMS", "BCN", "FCO"}
    assert all(t.depart.weekday() == CFG.depart_weekday for t in trips)
    assert all((t.ret - t.depart).days == CFG.nights for t in trips)


def test_israeli_peaks():
    assert peak_name(dt.date(2027, 4, 23)) == "Pesach"
    assert "Tishrei" in peak_name(dt.date(2027, 10, 18))
    assert peak_name(dt.date(2027, 2, 11)) is None


def test_serpapi_parse():
    trip = CFG.trips(TODAY)[0]
    data = {
        "best_flights": [{"price": 900, "total_duration": 300, "layovers": [],
                          "flights": [{"airline": "KLM"}]}],
        "other_flights": [{"price": 1200, "flights": [{"airline": "X"}], "layovers": [{}]}],
        "price_insights": {"lowest_price": 900, "price_level": "low", "typical_price_range": [950, 1300],
                           "price_history": [[1762992000, 990], [1763078400, 950]]},
    }
    q = serpapi.parse(data, trip, "ILS", dt.datetime(2026, 11, 15, tzinfo=dt.timezone.utc))
    assert q.price == 900 and q.airline == "KLM" and q.stops == 0
    assert q.typical_low == 950 and len(q.history) == 2
    assert serpapi.parse({"error": "no results"}, trip, "ILS", dt.datetime.now()).price is None


def _advise(prices, trip, price):
    series = {TODAY - dt.timedelta(days=len(prices) - i): p for i, p in enumerate(prices)}
    return advisor.advise(CFG, trip, price, series, {}, TODAY, (1000, 1300))


def test_buy_inside_deadline():
    trip = CFG.trips(TODAY)[0]
    near = type(trip)(trip.origin, trip.destination, trip.dest_name, TODAY + dt.timedelta(days=10),
                      TODAY + dt.timedelta(days=14))
    assert _advise([1000] * 20, near, 1000).verdict == "BUY"


def test_cheap_dip_says_buy_and_spike_says_wait():
    far = [t for t in CFG.trips(TODAY) if (t.depart - TODAY).days > 70 and not peak_name(t.depart)][0]
    flat = [1200, 1200, 1250, 1200, 1150, 1200, 1200, 1250, 1200, 1200] * 3
    dip = _advise(flat, far, 950)
    spike = _advise(flat, far, 1500)
    assert dip.buy_score > spike.buy_score
    assert dip.verdict == "BUY"
    assert spike.verdict == "WAIT"


def test_store_roundtrip(tmp_path):
    from flighttracker.providers import demo
    store = Store(tmp_path)
    trip = CFG.trips(TODAY)[0]
    store.add(trip, demo.fetch(CFG, trip, TODAY))
    s = store.daily_series(trip.key)
    assert len(s) == 61 and store.searches_this_month("demo", TODAY) == 1
