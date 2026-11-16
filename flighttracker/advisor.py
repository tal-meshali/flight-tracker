"""Buy-timing advisor.

For each trip it answers: "Is it more likely that I'll see a meaningfully lower price
before it's too late, or should I buy now?" and puts a confidence on the answer.

How it works (see RESEARCH.md for where the numbers come from):
1. Lead-time prior: how fares on short-haul routes typically move as departure gets
   closer. Normal dates drift down slowly until ~2 months out, then rise, and rise
   steeply in the last 3 weeks. Israeli holiday / summer dates rise the whole time.
2. Learned curve: the same thing measured from this route's own collected history.
   Once there are enough observations it gradually replaces the prior.
3. Recent trend: slope of the last 3 weeks of prices for this exact trip.
4. Volatility: how much this trip's price jumps day to day.
These drive a Monte Carlo simulation of the price until the buy deadline (default 14
days before departure). The share of simulated futures that reach a price at least
`min_saving_pct` lower is P(cheaper later). That is then nudged by where today's price
sits within its own history and within Google's "typical price" range.
"""
from __future__ import annotations

import datetime as dt
import math
import random
import statistics
from dataclasses import dataclass, field

from .config import Config, Trip
from .seasons import peak_name

BUCKETS = [(0, 14), (15, 21), (22, 45), (46, 60), (61, 120), (121, 10_000)]


def bucket_of(days_out: int) -> tuple[int, int]:
    for b in BUCKETS:
        if b[0] <= days_out <= b[1]:
            return b
    return BUCKETS[-1]


def prior_drift(days_out: int, peak: bool) -> float:
    """Expected change in log-price for one day passing, at a given days-to-departure."""
    if peak:
        return 0.012 if days_out <= 21 else 0.003
    if days_out <= 14:
        return 0.020
    if days_out <= 21:
        return 0.010
    if days_out <= 45:
        return 0.004
    if days_out <= 60:
        return 0.0
    return -0.0006


def learn_curve(series_by_trip: dict[Trip, dict[dt.date, float]]) -> dict[tuple[str, bool, tuple[int, int]], tuple[float, int]]:
    """Average daily log-price change per (destination, is_peak, days-out bucket) from all history."""
    acc: dict[tuple, list[float]] = {}
    for trip, series in series_by_trip.items():
        peak = peak_name(trip.depart) is not None
        pts = list(series.items())
        for (d0, p0), (d1, p1) in zip(pts, pts[1:]):
            gap = (d1 - d0).days
            if gap <= 0 or gap > 7 or p0 <= 0 or p1 <= 0:
                continue
            per_day = math.log(p1 / p0) / gap
            key = (trip.destination, peak, bucket_of((trip.depart - d0).days))
            acc.setdefault(key, []).append(per_day)
    return {k: (statistics.fmean(v), len(v)) for k, v in acc.items()}


@dataclass
class Advice:
    trip: Trip
    price: float | None
    currency: str
    days_out: int
    verdict: str = "NO DATA"      # BUY / WAIT / WATCH / NO DATA
    confidence: int = 0            # percent
    confidence_label: str = ""
    p_cheaper: float | None = None
    buy_score: float | None = None
    expected_low: float | None = None
    best_day: dt.date | None = None
    target_price: float | None = None
    typical: tuple[float | None, float | None] = (None, None)
    trend_pct_week: float | None = None
    percentile: float | None = None
    n_points: int = 0
    peak: str | None = None
    airline: str = ""
    reasons: list[str] = field(default_factory=list)


def _trend_and_vol(series: dict[dt.date, float], today: dt.date):
    """Return (slope of log price per day over last 3 weeks, current smoothed log level,
    sigma of the day-to-day 'noise' around that level, sigma of the level's random walk)."""
    pts = [(d, math.log(p)) for d, p in series.items() if p > 0]
    recent = [(d, y) for d, y in pts if (today - d).days <= 21]
    slope = None
    if len(recent) >= 5:
        xs = [(d - today).days for d, _ in recent]
        ys = [y for _, y in recent]
        mx, my = statistics.fmean(xs), statistics.fmean(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        if sxx > 0:
            slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    if len(pts) < 7:
        return slope, None, None, None
    # rolling median (7 obs) = the underlying fare level; residuals = short-lived noise
    ys = [y for _, y in pts]
    med = [statistics.median(ys[max(0, i - 3): i + 4]) for i in range(len(ys))]
    resid = [y - m for y, m in zip(ys, med)]
    noise = statistics.pstdev(resid)
    steps = []
    for i in range(1, len(pts)):
        gap = (pts[i][0] - pts[i - 1][0]).days
        if 0 < gap <= 7:
            steps.append((med[i] - med[i - 1]) / math.sqrt(gap))
    level_sd = statistics.pstdev(steps) if len(steps) >= 5 else None
    level_now = statistics.median(ys[-4:])
    return slope, level_now, noise, level_sd


def advise(cfg: Config, trip: Trip, price: float | None, series: dict[dt.date, float],
           curve: dict, today: dt.date | None = None, typical: tuple = (None, None),
           airline: str = "", currency: str | None = None, seed: int = 7) -> Advice:
    today = today or dt.date.today()
    d = (trip.depart - today).days
    peak = peak_name(trip.depart)
    a = Advice(trip, price, currency or cfg.currency, d, peak=peak, airline=airline,
               typical=(float(typical[0]) if typical[0] else None, float(typical[1]) if typical[1] else None))
    hist = {k: v for k, v in series.items() if (today - k).days <= 90}
    a.n_points = len(hist)
    if price is None:
        a.reasons.append("No price found on the last check.")
        return a

    lo, hi = a.typical
    vals = list(hist.values())
    if len(vals) >= 5:
        a.percentile = sum(1 for v in vals if v < price) / len(vals)
    slope, level_now, noise, level_sd = _trend_and_vol(hist, today)
    if slope is not None:
        a.trend_pct_week = (math.exp(slope * 7) - 1) * 100
    noise = min(max(noise if noise is not None else 0.03, 0.005), 0.08)
    level_sd = min(max(level_sd if level_sd is not None else 0.008, 0.003), 0.03)
    # start from the underlying level, not today's (possibly lucky or unlucky) quote
    x0 = (level_now - math.log(price)) if level_now is not None else 0.0
    saving = cfg.min_saving_pct / 100
    a.target_price = round(price * (1 - saving))

    horizon = d - cfg.buy_deadline_days
    if horizon <= 0:
        a.verdict, a.confidence, a.buy_score, a.p_cheaper = "BUY", 85, 1.0, 0.05
        a.best_day = today
        a.reasons.append(f"Only {d} days to departure. Inside the last {cfg.buy_deadline_days} days fares almost always climb.")
        _label(a)
        return a

    # ---- Monte Carlo over the remaining days ----
    def drift(days_out: int) -> float:
        prior = prior_drift(days_out, peak is not None)
        learned, n = curve.get((trip.destination, peak is not None, bucket_of(days_out)), (0.0, 0))
        w = min(0.7, n / 60)  # trust our own data more as it accumulates
        return (1 - w) * prior + w * learned

    drifts = [drift(d - t) for t in range(1, horizon + 1)]
    rng = random.Random(seed)
    n_sims = cfg.simulations
    threshold = math.log(1 - saving)
    hits, mins = 0, []
    path_sum = [0.0] * (horizon + 1)
    trend_w = 0.5 if slope is not None else 0.0
    for _ in range(n_sims):
        x, m = x0, 0.0
        for t in range(1, horizon + 1):
            x += drifts[t - 1] + trend_w * (slope or 0.0) * math.exp(-t / 7) + rng.gauss(0, level_sd)
            seen = x + rng.gauss(0, noise)
            path_sum[t] += seen
            m = min(m, seen)
        mins.append(m)
        hits += m <= threshold
    p_cheaper = hits / n_sims
    mean_path = [s / n_sims for s in path_sum]
    best_t = min(range(horizon + 1), key=lambda t: mean_path[t])
    a.best_day = today + dt.timedelta(days=best_t)
    a.p_cheaper = p_cheaper
    a.expected_low = round(price * math.exp(statistics.median(mins)))

    # ---- combine into a buy score ----
    score = 1 - p_cheaper
    if lo and price <= lo:
        score += 0.15
        a.reasons.append(f"Price is at or below Google's typical low ({lo:,.0f}).")
    elif lo and hi and price <= lo + 0.25 * (hi - lo):
        a.reasons.append(f"Price is in the cheapest quarter of Google's typical range ({lo:,.0f}-{hi:,.0f}).")
    elif hi and price >= hi:
        score -= 0.10
        a.reasons.append(f"Price is above Google's typical range ({lo:,.0f}-{hi:,.0f}).")
    if a.percentile is not None:
        a.reasons.append(f"Lower than {100 * (1 - a.percentile):.0f}% of the {len(vals)} daily prices seen for this trip in the last 90 days.")
    if level_now is not None and abs(x0) >= 0.03:
        a.reasons.append("Today's price is " + ("below" if x0 > 0 else "above") +
                         f" this trip's recent level by {abs(math.exp(x0) - 1):.0%}" +
                         (", a dip worth taking." if x0 > 0 else ", likely a temporary spike."))
    score = max(0.0, min(1.0, score))
    a.buy_score = score

    if score >= 0.6:
        a.verdict = "BUY"
    elif score <= 0.4:
        a.verdict = "WAIT"
    else:
        a.verdict = "WATCH"

    quality = min(1.0, 0.35 + a.n_points / 40) * (1.0 if lo else 0.85)
    # never claim certainty: airlines can always launch a sale or add flights
    a.confidence = min(95, round(100 * (0.5 + abs(score - 0.5) * quality)))

    a.reasons.insert(0, f"{p_cheaper:.0%} chance of a fare at least {cfg.min_saving_pct:.0f}% cheaper before "
                        f"{(trip.depart - dt.timedelta(days=cfg.buy_deadline_days)).isoformat()}.")
    if peak:
        a.reasons.append(f"Departure falls in a peak period ({peak}); these fares usually rise steadily.")
    if a.trend_pct_week is not None and abs(a.trend_pct_week) >= 2:
        a.reasons.append(f"Trend over the last 3 weeks: {a.trend_pct_week:+.1f}% per week.")
    if a.verdict != "BUY" and best_t > 0:
        a.reasons.append(f"Expected cheapest around {a.best_day.isoformat()}; buy right away if it drops to {a.target_price:,.0f} or less.")
    _label(a)
    return a


def _label(a: Advice) -> None:
    a.confidence_label = "High" if a.confidence >= 75 else "Medium" if a.confidence >= 60 else "Low"
