# Flight tracker ✈️ from TLV

Checks flight prices from Tel Aviv every day, keeps the full price history in this repo, and
tells you whether **now** is a good time to buy, with a confidence level.

- **Latest advice:** [reports/README.md](reports/README.md)
- **Why it works this way:** [RESEARCH.md](RESEARCH.md) covers booking lead time, Israeli
  holidays, and whether incognito mode or a VPN helps.
- **What it looks like on sample data:** [reports-demo/README.md](reports-demo/README.md)

When a trip turns into a **BUY**, the daily job opens (or comments on) a GitHub issue labelled
`buy-signal`, so you get an email from GitHub.

## Setup (one time)

1. Get a free API key at [serpapi.com](https://serpapi.com/users/sign_up) (250 searches/month).
2. In this repo: **Settings → Secrets and variables → Actions → New repository secret**,
   name `SERPAPI_KEY`.
3. Optional second source: a free [Travelpayouts](https://www.travelpayouts.com/) token as
   secret `TRAVELPAYOUTS_TOKEN`.
4. **Actions → Track flight prices → Run workflow** to run it now. After that it runs daily at
   04:15 UTC.

## Adding destinations or your real trip dates

Everything is in [config.toml](config.toml):

```toml
[[destinations]]       # watch a new city
code = "LIS"
name = "Lisbon"

[[trips]]              # track the exact dates you want to fly
destination = "BCN"
depart = "2027-04-25"
return = "2027-04-30"
label = "Barcelona after Pesach"
```

By default each destination is checked for a Thursday-to-Monday trip about 5 and 12 weeks out.
Change `weeks_ahead`, `depart_weekday` and `nights` to suit you.

**Search budget:** each trip check uses 1 SerpApi search. With 4 destinations × 2 trips daily,
that's about 240 a month. The collector stops at `monthly_search_budget` (248). If you add more
destinations, reduce `weeks_ahead` to one entry or upgrade the SerpApi plan.

## Running locally

```bash
pip install -r requirements.txt
python -m flighttracker demo                 # synthetic data, no key needed
SERPAPI_KEY=... python -m flighttracker run  # real collection + report
python -m flighttracker market-test BCN      # same trip priced from 6 countries (the "VPN test")
python -m pytest tests
```

## Layout

| Path | What |
|---|---|
| `flighttracker/providers/` | Data sources: SerpApi (Google Flights), Travelpayouts, demo |
| `flighttracker/advisor.py` | Buy-timing algorithm |
| `flighttracker/seasons.py` | Israeli holiday and peak windows, from the Hebrew calendar |
| `data/observations.csv` | Every price check |
| `data/source_history.csv` | Google's own daily price history per trip |
| `reports/` | Latest report, charts, `advice.json`, `alerts.md` |
