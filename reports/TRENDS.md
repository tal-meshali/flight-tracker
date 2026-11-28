# Price trends

Built from every price the tracker has saved (`data/observations.csv`) plus Google's own daily history for each tracked trip (`data/source_history.csv`). Prices are round trip, in ILS. The charts grow every day the job runs.

## All cities

Each day, the lowest price among the trips being tracked for that city. Jumps can happen when the tracker switches to a new watch date.

![cheapest per city](trends/cities.svg)

## Each trip over time

One line per departure date. A line that climbs means that trip got more expensive the longer you waited.

### Amsterdam

![Amsterdam trips](trends/AMS.svg)

### Barcelona

![Barcelona trips](trends/BCN.svg)

### Rome

![Rome trips](trends/FCO.svg)

### Brussels

![Brussels trips](trends/BRU.svg)

## Price vs. time before departure

Every trip's price divided by its own lowest price (= 100), grouped by weeks before departure. Read left to right: further out on the left, departure on the right. Where the line turns up is when waiting starts to cost you. This is the curve the buy-timing algorithm learns from.

![lead time](trends/lead-time.svg)

## Latest checks

| City | Departure | Return | Price | Checked |
|---|---|---|---:|---|
| Amsterdam | 2026-12-24 | 2026-12-28 | 1,079 ILS | 2026-11-19 |
| Amsterdam | 2026-12-31 | 2027-01-04 | 1,258 ILS | 2026-11-26 |
| Amsterdam | 2027-01-07 | 2027-01-11 | 1,364 ILS | 2026-11-28 |
| Amsterdam | 2027-02-11 | 2027-02-15 | 1,074 ILS | 2026-11-19 |
| Amsterdam | 2027-02-18 | 2027-02-22 | 1,017 ILS | 2026-11-26 |
| Amsterdam | 2027-02-25 | 2027-03-01 | 1,084 ILS | 2026-11-28 |
| Barcelona | 2026-12-24 | 2026-12-28 | 1,104 ILS | 2026-11-19 |
| Barcelona | 2026-12-31 | 2027-01-04 | 989 ILS | 2026-11-26 |
| Barcelona | 2027-01-07 | 2027-01-11 | 842 ILS | 2026-11-28 |
| Barcelona | 2027-02-11 | 2027-02-15 | 1,083 ILS | 2026-11-19 |
| Barcelona | 2027-02-18 | 2027-02-22 | 877 ILS | 2026-11-26 |
| Barcelona | 2027-02-25 | 2027-03-01 | 918 ILS | 2026-11-28 |
| Brussels | 2026-12-24 | 2026-12-28 | 1,101 ILS | 2026-11-19 |
| Brussels | 2026-12-31 | 2027-01-04 | 1,259 ILS | 2026-11-26 |
| Brussels | 2027-01-07 | 2027-01-11 | 1,027 ILS | 2026-11-28 |
| Brussels | 2027-02-11 | 2027-02-15 | 883 ILS | 2026-11-19 |
| Brussels | 2027-02-18 | 2027-02-22 | 859 ILS | 2026-11-26 |
| Brussels | 2027-02-25 | 2027-03-01 | 928 ILS | 2026-11-28 |
| Rome | 2026-12-24 | 2026-12-28 | 440 ILS | 2026-11-19 |
| Rome | 2026-12-31 | 2027-01-04 | 461 ILS | 2026-11-26 |
| Rome | 2027-01-07 | 2027-01-11 | 423 ILS | 2026-11-28 |
| Rome | 2027-02-11 | 2027-02-15 | 405 ILS | 2026-11-19 |
| Rome | 2027-02-18 | 2027-02-22 | 424 ILS | 2026-11-26 |
| Rome | 2027-02-25 | 2027-03-01 | 423 ILS | 2026-11-28 |
