"""Load config.toml and expand it into the concrete list of trips to check."""
from __future__ import annotations

import datetime as dt
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


@dataclass(frozen=True)
class Trip:
    origin: str
    destination: str
    dest_name: str
    depart: dt.date
    ret: dt.date | None
    label: str = ""

    @property
    def key(self) -> str:
        r = self.ret.isoformat() if self.ret else "oneway"
        return f"{self.origin}-{self.destination}-{self.depart.isoformat()}-{r}"


@dataclass
class Config:
    origin: str
    currency: str
    market: str
    language: str
    adults: int
    travel_class: str
    max_stops: int
    weeks_ahead: list[int]
    depart_weekday: int
    nights: int
    monthly_search_budget: int
    buy_deadline_days: int
    min_saving_pct: float
    simulations: int
    destinations: dict[str, str]
    fixed_trips: list[Trip] = field(default_factory=list)

    def trips(self, today: dt.date | None = None) -> list[Trip]:
        today = today or dt.date.today()
        out: dict[str, Trip] = {}
        for code, name in self.destinations.items():
            for w in self.weeks_ahead:
                start = today + dt.timedelta(weeks=w)
                depart = start + dt.timedelta(days=(self.depart_weekday - start.weekday()) % 7)
                t = Trip(self.origin, code, name, depart, depart + dt.timedelta(days=self.nights),
                         f"watch +{w}w")
                out[t.key] = t
        for t in self.fixed_trips:
            if t.depart > today:
                out[t.key] = t
        return sorted(out.values(), key=lambda t: (t.destination, t.depart))


def load(path: str | Path = "config.toml") -> Config:
    raw = tomllib.loads(Path(path).read_text())
    s, a = raw["search"], raw.get("advisor", {})
    dests = {d["code"].upper(): d.get("name", d["code"]) for d in raw.get("destinations", [])}
    fixed = []
    for t in raw.get("trips", []):
        code = t["destination"].upper()
        fixed.append(Trip(
            s["origin"], code, dests.get(code, code),
            dt.date.fromisoformat(str(t["depart"])),
            dt.date.fromisoformat(str(t["return"])) if t.get("return") else None,
            t.get("label", "planned trip"),
        ))
    return Config(
        origin=s["origin"], currency=s.get("currency", "ILS"), market=s.get("market", "il"),
        language=s.get("language", "en"), adults=int(s.get("adults", 1)),
        travel_class=s.get("travel_class", "economy"), max_stops=int(s.get("max_stops", 1)),
        weeks_ahead=list(s.get("weeks_ahead", [5, 12])),
        depart_weekday=WEEKDAYS[s.get("depart_weekday", "thu")[:3].lower()],
        nights=int(s.get("nights", 4)),
        monthly_search_budget=int(s.get("monthly_search_budget", 240)),
        buy_deadline_days=int(a.get("buy_deadline_days", 14)),
        min_saving_pct=float(a.get("min_saving_pct", 5)),
        simulations=int(a.get("simulations", 4000)),
        destinations=dests, fixed_trips=fixed,
    )
