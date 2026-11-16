"""Markdown report + small SVG price charts, readable straight on GitHub."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from .advisor import Advice

ICON = {"BUY": "🟢 BUY", "WAIT": "🔵 WAIT", "WATCH": "🟡 WATCH", "NO DATA": "⚪ NO DATA"}


def _money(v, cur):
    return "–" if v is None else f"{v:,.0f} {cur}"


def svg_chart(series: dict[dt.date, float], depart: dt.date, w: int = 520, h: int = 140) -> str:
    pts = [(d, p) for d, p in series.items() if p]
    if len(pts) < 2:
        return ""
    x0, x1 = pts[0][0].toordinal(), max(pts[-1][0].toordinal(), pts[0][0].toordinal() + 1)
    lo, hi = min(p for _, p in pts), max(p for _, p in pts)
    span = (hi - lo) or 1
    pad = 28

    def X(d):
        return pad + (d.toordinal() - x0) / (x1 - x0) * (w - 2 * pad)

    def Y(p):
        return h - pad + 8 - (p - lo) / span * (h - 2 * pad)

    path = " ".join(f"{'M' if i == 0 else 'L'}{X(d):.1f},{Y(p):.1f}" for i, (d, p) in enumerate(pts))
    last_d, last_p = pts[-1]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="sans-serif" font-size="11">
<rect width="100%" height="100%" fill="#ffffff"/>
<path d="{path}" fill="none" stroke="#2563eb" stroke-width="2"/>
<circle cx="{X(last_d):.1f}" cy="{Y(last_p):.1f}" r="3.5" fill="#2563eb"/>
<text x="{pad}" y="14" fill="#555">high {hi:,.0f}</text>
<text x="{pad}" y="{h - 4}" fill="#555">low {lo:,.0f} · {pts[0][0]:%d %b} → {last_d:%d %b} · departs {depart:%d %b %Y}</text>
</svg>"""


def write(advice: list[Advice], series: dict[str, dict], out_dir: str | Path, sample: bool = False,
          now: dt.datetime | None = None, extra_notes: list[str] | None = None) -> Path:
    out = Path(out_dir)
    (out / "charts").mkdir(parents=True, exist_ok=True)
    now = now or dt.datetime.now(dt.timezone.utc)
    L = []
    if sample:
        L.append("> ⚠️ **SAMPLE DATA.** These prices are synthetic, generated to demo the tracker. They are not real fares.\n")
    L.append(f"# Flight price tracker: buy-timing report\n\nUpdated {now:%Y-%m-%d %H:%M} UTC. 📈 [Price trends over time](TRENDS.md)\n")
    L.append("| Trip | Dates | Days out | Price now | Typical range | Advice | Confidence | Chance cheaper later |")
    L.append("|---|---|---:|---:|---|---|---|---:|")
    for a in advice:
        t = a.trip
        dates = f"{t.depart:%a %d %b}" + (f" → {t.ret:%a %d %b %Y}" if t.ret else " (one way)")
        typ = "–" if not a.typical[0] else f"{a.typical[0]:,.0f}–{a.typical[1]:,.0f}"
        pc = "–" if a.p_cheaper is None else f"{a.p_cheaper:.0%}"
        conf = "–" if not a.confidence else f"{a.confidence_label} ({a.confidence}%)"
        L.append(f"| TLV → {t.dest_name} ({t.destination}) | {dates} | {a.days_out} | {_money(a.price, a.currency)} "
                 f"| {typ} | {ICON[a.verdict]} | {conf} | {pc} |")
    L.append("\n**BUY** = unlikely to get meaningfully cheaper before the deadline. **WAIT** = good odds of a lower "
             "price; keep watching. **WATCH** = roughly a coin flip; buy if it hits the target price.\n")
    for a in advice:
        t = a.trip
        L.append(f"## TLV → {t.dest_name}: {t.depart:%d %b}" + (f" – {t.ret:%d %b %Y}" if t.ret else "")
                 + f" · {ICON[a.verdict]}\n")
        meta = [f"Trip: {t.label}" if t.label else "", f"Cheapest airline now: {a.airline}" if a.airline else "",
                f"Data points: {a.n_points}"]
        if a.target_price and a.verdict != "BUY":
            meta.append(f"Target price: {_money(a.target_price, a.currency)}")
        if a.expected_low:
            meta.append(f"Likely lowest before deadline: ~{_money(a.expected_low, a.currency)}")
        L.append(" · ".join(m for m in meta if m) + "\n")
        for r in a.reasons:
            L.append(f"- {r}")
        svg = svg_chart(series.get(t.key, {}), t.depart)
        if svg:
            name = f"charts/{t.key}.svg"
            (out / name).write_text(svg)
            L.append(f"\n![price history]({name})")
        L.append("")
    for n in extra_notes or []:
        L.append(n)
    path = out / "README.md"
    path.write_text("\n".join(L))

    buys = [a for a in advice if a.verdict == "BUY"]
    alert = ""
    if buys:
        alert = "Good time to buy:\n\n" + "\n".join(
            f"- TLV → {a.trip.dest_name}, {a.trip.depart:%d %b}" + (f"–{a.trip.ret:%d %b %Y}" if a.trip.ret else "")
            + f": {_money(a.price, a.currency)} ({a.confidence_label} confidence, {a.confidence}%)"
            for a in buys)
    (out / "alerts.md").write_text(alert)
    (out / "advice.json").write_text(json.dumps([{
        "trip": a.trip.key, "destination": a.trip.dest_name, "depart": a.trip.depart.isoformat(),
        "return": a.trip.ret.isoformat() if a.trip.ret else None, "price": a.price, "currency": a.currency,
        "verdict": a.verdict, "confidence": a.confidence, "p_cheaper_later": a.p_cheaper,
        "target_price": a.target_price, "best_day": a.best_day.isoformat() if a.best_day else None,
        "reasons": a.reasons} for a in advice], indent=2, ensure_ascii=False))
    return path
