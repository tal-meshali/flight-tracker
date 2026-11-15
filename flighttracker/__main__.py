"""Command line entry point.

    python -m flighttracker run            # collect prices, then write the report (what the daily job does)
    python -m flighttracker collect        # only collect
    python -m flighttracker advise         # only (re)write the report from stored data
    python -m flighttracker demo           # try everything on synthetic data, no API key needed
    python -m flighttracker market-test BCN  # compare the same trip across countries (the honest "VPN test")
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

from . import advisor, report
from .config import Trip, load
from .providers import demo, serpapi, travelpayouts
from .storage import Store


def collect(cfg, store: Store, use_demo: bool = False, today: dt.date | None = None) -> None:
    serp_key = os.environ.get("SERPAPI_KEY", "").strip()
    tp_token = os.environ.get("TRAVELPAYOUTS_TOKEN", "").strip()
    trips = cfg.trips(today)
    if not use_demo and not serp_key and not tp_token:
        sys.exit("No data source configured. Set SERPAPI_KEY and/or TRAVELPAYOUTS_TOKEN, or run `demo`.")
    used = store.searches_this_month("google", today)
    for trip in trips:
        if use_demo:
            q = demo.fetch(cfg, trip, today)
            store.add(trip, q)
            continue
        if serp_key:
            if used >= cfg.monthly_search_budget:
                print(f"SerpApi budget reached ({used}/{cfg.monthly_search_budget}); skipping {trip.key}")
            else:
                q = serpapi.fetch(cfg, trip, serp_key)
                used += 1
                store.add(trip, q)
                print(f"google    {trip.key}: {q.price} {q.currency} {q.error}")
        if tp_token:
            q = travelpayouts.fetch(cfg, trip, tp_token)
            store.add(trip, q)
            print(f"aviasales {trip.key}: {q.price} {q.currency} {q.error}")


def advise(cfg, store: Store, out_dir: str, sample: bool = False, today: dt.date | None = None):
    today = today or dt.date.today()
    latest = store.latest()
    trips = {t.key: t for t in cfg.trips(today)}
    # also keep advising on any stored trip that hasn't departed (e.g. older watch dates)
    for key, by_src in latest.items():
        r = next(iter(by_src.values()))
        dep = dt.date.fromisoformat(r["depart"])
        if key not in trips and dep > today and r["destination"] in cfg.destinations:
            # only keep older watch trips if checked within the last week
            last = max(dt.date.fromisoformat(x["observed_at"][:10]) for x in by_src.values())
            if (today - last).days <= 7:
                trips[key] = Trip(r["origin"], r["destination"], cfg.destinations[r["destination"]], dep,
                                  dt.date.fromisoformat(r["return"]) if r["return"] else None, r["label"])
    series = {k: store.daily_series(k) for k in trips}
    curve = advisor.learn_curve({t: series[k] for k, t in trips.items()})
    out = []
    for key, trip in sorted(trips.items(), key=lambda kv: (kv[1].destination, kv[1].depart)):
        by_src = latest.get(key, {})
        g, av = by_src.get("google") or by_src.get("demo"), by_src.get("aviasales")
        prices = [(float(r["price"]), r) for r in (g, av) if r and r["price"]]
        price, row = min(prices, key=lambda x: x[0]) if prices else (None, g or av or {})
        typical = (g.get("typical_low") or None, g.get("typical_high") or None) if g else (None, None)
        out.append(advisor.advise(cfg, trip, price, series[key], curve, today, typical,
                                  airline=(row or {}).get("airline", ""), currency=cfg.currency))
    used = store.searches_this_month("google", today)
    notes = [f"\n_SerpApi searches used this month: {used}/{cfg.monthly_search_budget}._"] if not sample else []
    path = report.write(out, series, out_dir, sample=sample, extra_notes=notes)
    print(f"Report written to {path}")
    for a in out:
        print(f"{a.trip.key:40s} {a.price!s:>8} {a.verdict:7s} conf {a.confidence}%")
    return out


def market_test(cfg, code: str, weeks: int = 8) -> None:
    key = os.environ.get("SERPAPI_KEY", "").strip()
    if not key:
        sys.exit("market-test needs SERPAPI_KEY")
    start = dt.date.today() + dt.timedelta(weeks=weeks)
    dep = start + dt.timedelta(days=(cfg.depart_weekday - start.weekday()) % 7)
    trip = Trip(cfg.origin, code.upper(), cfg.destinations.get(code.upper(), code), dep,
                dep + dt.timedelta(days=cfg.nights))
    print(f"Same trip ({trip.key}), priced in USD from different countries:")
    for gl in ["il", "us", "gb", "de", "in", "tr"]:
        q = serpapi.fetch(cfg, trip, key, market=gl, currency="USD")
        print(f"  {gl}: {q.price} USD {q.airline} {q.error}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="flighttracker")
    ap.add_argument("command", choices=["run", "collect", "advise", "demo", "market-test"])
    ap.add_argument("dest", nargs="?")
    ap.add_argument("--config", default="config.toml")
    args = ap.parse_args(argv)
    cfg = load(args.config)
    if args.command == "demo":
        store = Store("data-demo")
        collect(cfg, store, use_demo=True)
        advise(cfg, store, "reports-demo", sample=True)
        return
    if args.command == "market-test":
        market_test(cfg, args.dest or next(iter(cfg.destinations)))
        return
    store = Store("data")
    if args.command in ("run", "collect"):
        collect(cfg, store)
    if args.command in ("run", "advise"):
        advise(cfg, store, "reports")


if __name__ == "__main__":
    main()
