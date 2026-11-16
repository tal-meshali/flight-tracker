"""Long-term trend charts built from every price ever saved in data/.

Writes reports/TRENDS.md plus SVG charts:
  trends/cities.svg      cheapest tracked fare per city, day by day
  trends/<CODE>.svg      every tracked trip for one city, as its own line
  trends/lead-time.svg   how fares move as departure gets closer (indexed, per city)
"""
from __future__ import annotations

import datetime as dt
import statistics
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

from .config import Config
from .storage import Store

# Fixed categorical order: a city keeps its colour as long as its place in config.toml stays.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8f6ad8", "#c94a4a"]
INK, INK2, GRID, SURFACE = "#1f1f1e", "#5f5e58", "#e6e5e0", "#ffffff"


def _nice_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    """Round tick values that fully cover [lo, hi]."""
    import math
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start, end = math.floor(lo / step) * step, math.ceil(hi / step) * step
    return [start + i * step for i in range(int(round((end - start) / step)) + 1)]


def line_chart(series: list[dict], title: str, y_label: str, x_is_date: bool = True,
               x_reversed: bool = False, w: int = 760, h: int = 340) -> str:
    """series: [{name, color, points: [(x, y)], label?}] -> SVG string (light surface)."""
    series = [s for s in series if len(s["points"]) >= 1]
    if not series:
        return ""
    xs = [x.toordinal() if x_is_date else x for s in series for x, _ in s["points"]]
    ys = [y for s in series for _, y in s["points"]]
    x0, x1 = min(xs), max(xs)
    if x1 == x0:
        x1 = x0 + 1
    yt = _nice_ticks(min(ys) * 0.97, max(ys) * 1.03)
    y0, y1 = yt[0], yt[-1]
    L, R, T, B = 64, 130, 66, 40
    pw, ph = w - L - R, h - T - B

    def X(x):
        v = x.toordinal() if x_is_date else x
        f = (v - x0) / (x1 - x0)
        return L + (1 - f if x_reversed else f) * pw

    def Y(y):
        return T + (1 - (y - y0) / (y1 - y0)) * ph

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
         f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif" font-size="12">',
         f'<rect width="100%" height="100%" fill="{SURFACE}"/>',
         f'<text x="{L}" y="22" font-size="15" font-weight="600" fill="{INK}">{escape(title)}</text>']
    # legend row
    lx = L
    for s in series:
        o.append(f'<rect x="{lx}" y="38" width="14" height="4" rx="2" fill="{s["color"]}" '
                 f'fill-opacity="{s.get('opacity', 1):.2f}"/>')
        o.append(f'<text x="{lx + 19}" y="44" fill="{INK2}">{escape(s["name"])}</text>')
        lx += 36 + 7.5 * len(s["name"])
    # grid + y axis
    for t in yt:
        o.append(f'<line x1="{L}" x2="{L + pw}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="{GRID}"/>')
        o.append(f'<text x="{L - 8}" y="{Y(t) + 4:.1f}" text-anchor="end" fill="{INK2}">{t:,.0f}</text>')
    o.append(f'<text x="14" y="{T + ph / 2}" fill="{INK2}" transform="rotate(-90 14 {T + ph / 2})" '
             f'text-anchor="middle">{escape(y_label)}</text>')
    # x ticks
    n = 6
    for i in range(n + 1):
        v = x0 + (x1 - x0) * i / n
        xv = dt.date.fromordinal(int(round(v))) if x_is_date else round(v)
        lab = xv.strftime("%d %b") if x_is_date else f"{xv} days"
        o.append(f'<text x="{X(xv):.1f}" y="{T + ph + 18}" text-anchor="middle" fill="{INK2}">{lab}</text>')
    o.append(f'<line x1="{L}" x2="{L + pw}" y1="{T + ph}" y2="{T + ph}" stroke="#b9b8b0"/>')
    # lines, with a surface halo so crossings stay readable
    ends = []
    for s in series:
        pts = sorted(s["points"], key=lambda p: p[0])
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(x):.1f},{Y(y):.1f}" for i, (x, y) in enumerate(pts))
        if len(pts) > 1:
            o.append(f'<path d="{d}" fill="none" stroke="{SURFACE}" stroke-width="5" stroke-linejoin="round"/>')
            o.append(f'<path d="{d}" fill="none" stroke="{s["color"]}" stroke-opacity="{s.get('opacity', 1):.2f}" stroke-width="2" stroke-linejoin="round"/>')
        end = pts[0] if x_reversed else pts[-1]  # the point drawn furthest right
        lx_, ly_ = X(end[0]), Y(end[1])
        o.append(f'<circle cx="{lx_:.1f}" cy="{ly_:.1f}" r="4" fill="{s["color"]}" fill-opacity="{s.get('opacity', 1):.2f}" stroke="{SURFACE}" stroke-width="2"/>')
        ends.append([ly_, lx_, s.get("label") or s["name"], end[1]])
    # direct end labels, nudged apart vertically so they don't collide
    ends.sort()
    for i in range(1, len(ends)):
        if ends[i][0] - ends[i - 1][0] < 14:
            ends[i][0] = ends[i - 1][0] + 14
    for ly_, lx_, lab, val in ends:
        o.append(f'<text x="{L + pw + 8}" y="{ly_ + 4:.1f}" fill="{INK}">{escape(lab)} '
                 f'<tspan fill="{INK2}">{val:,.0f}</tspan></text>')
    o.append("</svg>")
    return "\n".join(o)


def write(cfg: Config, store: Store, out_dir: str | Path, sample: bool = False) -> Path:
    out = Path(out_dir)
    (out / "trends").mkdir(parents=True, exist_ok=True)
    obs = store.observations()
    trips: dict[str, dict] = {}
    for r in obs:
        if r["destination"] in cfg.destinations:
            trips[r["trip_key"]] = r
    by_city: dict[str, list[str]] = defaultdict(list)
    for k, r in trips.items():
        by_city[r["destination"]].append(k)
    series = {k: store.daily_series(k) for k in trips}
    colors = {c: SERIES[i % len(SERIES)] for i, c in enumerate(cfg.destinations)}
    today = dt.date.today()
    lines = []
    if sample:
        lines.append("> ⚠️ **SAMPLE DATA.** Synthetic prices for demonstration only.\n")
    lines.append("# Price trends\n")
    lines.append("Built from every price the tracker has saved (`data/observations.csv`) plus Google's "
                 "own daily history for each tracked trip (`data/source_history.csv`). Prices are "
                 f"round trip, in {cfg.currency}. The charts grow every day the job runs.\n")

    # 1. cheapest tracked fare per city per day
    city_series = []
    for code, name in cfg.destinations.items():
        daily: dict[dt.date, float] = {}
        for k in by_city.get(code, []):
            for d, p in series[k].items():
                daily[d] = min(p, daily.get(d, p))
        if daily:
            city_series.append({"name": name, "color": colors[code], "points": sorted(daily.items())})
    svg = line_chart(city_series, "Cheapest tracked round trip per city", f"Price ({cfg.currency})")
    if svg:
        (out / "trends/cities.svg").write_text(svg)
        lines.append("## All cities\n\nEach day, the lowest price among the trips being tracked for that "
                     "city. Jumps can happen when the tracker switches to a new watch date.\n")
        lines.append("![cheapest per city](trends/cities.svg)\n")

    # 2. every trip, per city
    lines.append("## Each trip over time\n\nOne line per departure date. A line that climbs means that "
                 "trip got more expensive the longer you waited.\n")
    for code, name in cfg.destinations.items():
        keys = [k for k in by_city.get(code, []) if dt.date.fromisoformat(trips[k]["depart"]) >= today - dt.timedelta(days=60)]
        keys.sort(key=lambda k: trips[k]["depart"])
        keys = keys[-8:]
        trip_series = []
        for i, k in enumerate(keys):
            dep = dt.date.fromisoformat(trips[k]["depart"])
            ret = trips[k]["return"]
            lab = f"{dep:%d %b}" + (f"–{dt.date.fromisoformat(ret):%d %b}" if ret else "")
            # newest departures darkest: same hue, stepped opacity keeps the city's identity
            op = 0.45 + 0.55 * (i + 1) / len(keys)
            color = colors[code]
            trip_series.append({"name": lab, "label": lab, "points": sorted(series[k].items()),
                                "color": color, "opacity": op})
        svg = line_chart(trip_series, f"TLV → {name}: price of each tracked trip", f"Price ({cfg.currency})")
        if svg:
            (out / f"trends/{code}.svg").write_text(svg)
            lines.append(f"### {name}\n\n![{name} trips](trends/{code}.svg)\n")

    # 3. price vs days before departure, indexed to each trip's own lowest price
    lead_series = []
    for code, name in cfg.destinations.items():
        buckets: dict[int, list[float]] = defaultdict(list)
        for k in by_city.get(code, []):
            s = series[k]
            if len(s) < 5:
                continue
            base = min(s.values())
            dep = dt.date.fromisoformat(trips[k]["depart"])
            for d, p in s.items():
                days = (dep - d).days
                if days >= 0:
                    buckets[days // 7 * 7].append(100 * p / base)
        pts = [(b, statistics.median(v)) for b, v in sorted(buckets.items()) if len(v) >= 2]
        if len(pts) >= 2:
            lead_series.append({"name": name, "color": colors[code], "points": pts})
    svg = line_chart(lead_series, "How fares change as departure gets closer",
                     "Price index (trip's lowest = 100)", x_is_date=False, x_reversed=True)
    if svg:
        (out / "trends/lead-time.svg").write_text(svg)
        lines.append("## Price vs. time before departure\n\nEvery trip's price divided by its own lowest "
                     "price (= 100), grouped by weeks before departure. Read left to right: further out "
                     "on the left, departure on the right. Where the line turns up is when waiting starts "
                     "to cost you. This is the curve the buy-timing algorithm learns from.\n")
        lines.append("![lead time](trends/lead-time.svg)\n")

    # small table of the raw numbers for accessibility
    lines.append("## Latest checks\n\n| City | Departure | Return | Price | Checked |\n|---|---|---|---:|---|")
    latest: dict[str, dict] = {}
    for r in obs:
        if r["price"]:
            latest[r["trip_key"]] = r
    for r in sorted(latest.values(), key=lambda r: (r["destination"], r["depart"])):
        if r["destination"] in cfg.destinations and r["depart"] >= today.isoformat():
            lines.append(f"| {cfg.destinations[r['destination']]} | {r['depart']} | {r['return'] or '–'} "
                         f"| {float(r['price']):,.0f} {r['currency']} | {r['observed_at'][:10]} |")
    path = out / "TRENDS.md"
    path.write_text("\n".join(lines) + "\n")
    return path
