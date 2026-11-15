# What actually gets you a cheaper flight from Israel

Research notes behind the buy-timing algorithm. Researched November 2026.

## Bottom line

1. **When you buy matters a lot. How you search barely matters.** Booking lead time and
   avoiding Israeli peak dates move the price by tens of percent. Incognito mode does nothing
   measurable, and a VPN rarely helps on the routes from TLV to Europe.
2. **For ordinary dates to Europe, the cheapest window is roughly 3 weeks to 2 months before
   departure.** Fares tend to drift down slowly from 6 months out, flatten around 2 months out,
   then climb. In the last 2 to 3 weeks they climb steeply.
3. **For Israeli holiday dates the rule flips: buy early.** Pesach, the Tishrei holidays
   (Rosh Hashana to Sukkot), Hanukkah, and the July–August school break sell out, so fares
   mostly rise from the moment they're published.
4. **Short sales happen and only show up if you check often.** That's why the tracker checks
   every day and gives a target price to buy at immediately.

## Booking lead time

- Expedia's 2026 Air Hacks report (millions of bookings) found that for international flights,
  booking **15–30 days ahead** saved about €112 on average versus booking 6+ months ahead, and
  **31–45 days** ahead saved about €102. Domestic trips were cheapest at 31–45 days.
  ([Euronews summary](https://www.euronews.com/2026/02/18/when-to-fly-and-when-to-book-top-air-travel-hacks-for-flight-bargains-in-2026))
- Booking too early is not a win on normal dates: airlines open with conservative fares and adjust
  as demand becomes clear.
- In the last ~14 days the cheap fare buckets are gone and fares rise quickly. The tracker
  always says **BUY** inside 14 days.

**In the algorithm:** the lead-time prior (`advisor.prior_drift`) has fares easing slightly beyond
60 days, flat from 45–60, rising from 21–45, and rising steeply inside 21 days. As the tracker
collects data, the curve it learns from your own routes gradually replaces this prior
(`advisor.learn_curve`).

## Israel-specific seasonality

- **Peak and sell-out periods from TLV:** Tishrei holidays, Pesach, Hanukkah (overlapping with
  Christmas/New Year in Europe), Shavuot, and the summer school break (July–August). For the
  Tishrei 2025 holidays, starting round-trip fares were about $515 to Rome and $618 to London on
  Wizz Air, and some El Al routes had no economy seats left.
  ([Globes](https://en.globes.co.il/en/article-1001519907))
- **Cheaper shoulder periods:** winter outside the holidays, the weeks between Pesach and summer,
  and November. ([Ynet, 2026 outlook](https://www.ynetnews.com/travel/article/hk0rmnlm11e))
- **2026 market:** capacity is coming back. Nearly 60 foreign airlines fly to Ben Gurion again,
  Wizz Air plans an Israeli base, Israir and Arkia are roughly tripling their fleets, and
  Israel–Italy is projected at 40–50 flights a week, up from about 10 at the wartime low.
  Travel agencies expect fares to fall in 2026 for the first time in years. More competition
  usually means more frequent sales, so watching daily pays off more.

**In the algorithm:** `seasons.py` computes the Israeli holiday windows from the Hebrew calendar
for any year. Trips departing in those windows get an upward drift at every lead time, so the
tracker leans toward buying early.

## Day of the week

- Expedia found **Friday** the cheapest day to fly in economy, 18% below Saturday, and **Sunday**
  the cheapest day to book. Both are global averages, and the booking-day effect is small.
- For TLV routes, Thursday and Sunday are popular with Israeli travellers, so mid-week departures
  (Monday to Wednesday) are often cheaper. The tracker's departure weekday and trip length are
  set in `config.toml`, so it's easy to compare.

## Incognito mode and cookies: no effect

- Consumer Reports ran 372 paired searches in normal and incognito browsers. Prices were the
  **same 88%** of the time, incognito was cheaper 7% of the time, and it was more expensive 5% of
  the time. That's noise, not a pattern.
- Economists from Berkeley, Yale and the University of Chicago studied a large airline's actual
  pricing algorithm. Prices respond to **total bookings on the flight**, not to an individual's
  searches: "Your search behavior almost surely does not affect anything."
  ([Gizmodo](https://gizmodo.com/incognito-mode-does-not-help-you-find-cheap-flights-1851360398))
- Why it *feels* like prices go up when you search again: fares really do change several times a
  day as seats sell, and some sites show cached prices that update when you click.

## VPN / country of purchase: rarely worth it from TLV

- Prices can differ by point of sale, mostly on **long-haul legacy carriers** (Emirates, Qatar,
  etc.) and premium cabins. **Low-cost carriers** like Wizz Air, Ryanair and easyJet, which
  carry much of TLV–Europe traffic, price the same everywhere.
- In a Tom's Guide test across many countries, the biggest saving was **$9**, and most VPN
  locations *raised* the price by up to $36.
- Real costs eat any gap: a 1.5–3% foreign-transaction fee, FX spread, and 6–7% if you accept
  dynamic currency conversion. Airlines also check card country against booking country, and
  can reprice, flag or void a ticket bought at another market's price, which may also break
  their terms. ([Windscribe overview, VPN vendor](https://windscribe.com/blog/vpn-for-cheaper-flights/))

**In the tracker:** instead of guessing, `python -m flighttracker market-test BCN` prices the
same trip as if searched from Israel, the US, the UK, Germany, India and Turkey, through the API
and not a VPN. It uses 6 searches, so run it occasionally.

## Data sources: what's legitimate

| Source | Status | Used? |
|---|---|---|
| Scraping Google Flights / Skyscanner / airline sites directly | Against their terms of service, and blocked often | No |
| Amadeus Self-Service API | Shut down in 2026 (enterprise only now) ([PhocusWire](https://www.phocuswire.com/amadeus-shut-down-self-service-apis-portal-developers)) | No |
| Kiwi Tequila, Skyscanner API | Partner-only, closed to individuals | No |
| **SerpApi Google Flights API** | Licensed access to Google Flights results, including Google's own price history and "typical price" range per trip. Free: 250 searches/month. | **Main source** |
| **Travelpayouts / Aviasales Data API** | Free with a partner token. Cached prices from real searches in the last 48h, good as a second opinion but not always bookable. | Optional |

## How the buy-timing algorithm decides

For each trip, the algorithm answers: *"Is a price at least 5% lower likely to show up before
the 14-day deadline, or should I lock this in?"*

1. Builds the trip's daily price history from our own checks plus Google's history for that
   exact itinerary, so there's useful history from the first run.
2. Separates the underlying fare level (rolling median) from short-lived noise, and measures how
   much each one moves.
3. Simulates thousands of possible price paths until the deadline, using the lead-time curve
   (prior or learned), the holiday adjustment, the recent trend, and the measured volatility.
4. **P(cheaper later)** = share of paths that hit a price at least 5% below today.
5. Adjusts for where today's price sits against Google's typical range.
6. Verdict: **BUY** (score ≥ 0.6), **WAIT** (≤ 0.4), otherwise **WATCH**. Confidence grows with
   how decisive the score is and how much data exists for the trip.
7. Gives a **target price**: if the fare drops to it, buy immediately.

**Limits:** this is a probabilistic estimate, not a guarantee. Airlines can add or cut flights
and wars can close airspace. The learned curve needs a few weeks of daily data per route before
it outweighs the research-based prior.
