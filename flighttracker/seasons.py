"""Israeli peak travel periods. Departures from TLV in these windows sell out early,
so prices tend to rise steadily instead of dipping before departure."""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

try:
    from pyluach import dates as _heb
except ImportError:  # pragma: no cover
    _heb = None


def _hd(y: int, m: int, d: int) -> dt.date:
    return _heb.HebrewDate(y, m, d).to_pydate()


@lru_cache(maxsize=None)
def peak_periods(greg_year: int) -> list[tuple[dt.date, dt.date, str]]:
    """Return (start, end, name) windows that affect departures in greg_year."""
    out: list[tuple[dt.date, dt.date, str]] = [
        (dt.date(greg_year, 7, 1), dt.date(greg_year, 8, 31), "Israeli summer school break"),
        (dt.date(greg_year, 12, 20), dt.date(greg_year + 1, 1, 3), "Christmas / New Year in Europe"),
    ]
    if _heb is None:
        return out
    pad = dt.timedelta(days=4)
    for hy in (greg_year + 3760, greg_year + 3761):
        try:
            rh, simchat = _hd(hy, 7, 1), _hd(hy, 7, 22)
            out.append((rh - pad, simchat + dt.timedelta(days=1), "Tishrei holidays (Rosh Hashana to Sukkot)"))
            han = _hd(hy, 9, 25)
            out.append((han - dt.timedelta(days=2), han + dt.timedelta(days=8), "Hanukkah"))
            pesach, pesach7 = _hd(hy, 1, 15), _hd(hy, 1, 21)
            out.append((pesach - dt.timedelta(days=6), pesach7 + dt.timedelta(days=2), "Pesach"))
            shavuot = _hd(hy, 3, 6)
            out.append((shavuot - dt.timedelta(days=2), shavuot + dt.timedelta(days=2), "Shavuot"))
        except ValueError:
            continue
    return [p for p in out if p[1].year >= greg_year - 1]


def peak_name(d: dt.date) -> str | None:
    for y in (d.year - 1, d.year):
        for start, end, name in peak_periods(y):
            if start <= d <= end:
                return name
    return None
