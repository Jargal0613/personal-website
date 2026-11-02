# Strategy research (2026-10-06): replacement for "Large 5m range"

Research and backtest only. No broker or order code. `fetch_history.py` sends only
read-only Open API requests to the DEMO host.

Pipeline:
- Run `fetch_history.py` with the project venv.
- Run everything else with system `python3`, which has pandas and numpy:

```
.venv/bin/python research/fetch_history.py M1 3.0 /workspace/scratch/history/eurusd_m1.csv   # + symbol facts
.venv/bin/python research/fetch_history.py H1 12  /workspace/scratch/history/eurusd_h1.csv
cd research && python3 run_research.py && python3 monte_carlo.py && python3 long_history_check.py \
            && python3 sanity_checks.py && python3 make_ranking.py
```

Raw bars (55 MB) stay in /workspace/scratch/history/ and are not kept in the project.
Results go to data/reference/research_*.csv, and symbol, margin and commission facts
to data/reference/eurusd_symbol_facts.json.

Method:
- Data: 3 years of M1 BID bars (2023-10 to 2026-10).
- Costs: spread by hour, 0.6 pip commission, slippage and swap (see `engine.py`).
- Walk-forward: train on the previous 12 months and test the next 6 months, 4 times,
  for 2 years of out-of-sample (OOS) data.
- Monte Carlo on a $10 account at minimum volume (1000 units).
- 12-year H1 robustness check.
- Random-entry benchmark: it loses about 1.4 pips per trade, which matches the cost
  model.

Result: none of the 7 candidates is good enough to deploy. See
data/reference/research_candidates_ranked.csv.

## Follow-up: fixed 10/20-pip bracket (`bracket_research.py`)
Every trade uses SL 10 pips and TP 20 pips from the fill (about -$1.09 / +$1.94 net at
0.01 lot). The exact breakeven win rate is 10.9 / (19.4 + 10.9) = 35.97%. I tested 7
pre-declared entry variants, each with 2 parameter values, using the same walk-forward
and Monte Carlo as above. Sizing was tested two ways: fixed 0.01 lot, and
floor(equity / 10) × 0.01 with a minimum of 0.01.

Run: `cd research && python3 bracket_research.py`
Outputs: `data/reference/bracket_10_20_*.csv`

Result: no variant has an edge. Every one has a negative average OOS net and a
profit factor of 0.67–0.93. The random-entry control lost 2.2 pips per trade.

## Round 3: other symbols, timeframes and documented effects
Scripts:
- `fetch_multi.py`: read-only. Pulls symbol details, margin for the minimum volume,
  a live spread sample, and trendbars.
- `engine2.py`: multi-symbol USD P&L at minimum volume, per-symbol costs and swap, and
  a DST-aware rollover.
- `multi_research.py`: the pre-declared hypotheses H1–H5 plus random controls.
- `multi_mc.py`: Monte Carlo and the portfolio test.
- `multi_report.py`: feasibility table, basket aggregates and the ranked table.

Raw data in /workspace/scratch/history/:
- 3 years of M5 for 11 symbols.
- 12 years of H1 (indices from 2014-07).

```
.venv/bin/python research/fetch_multi.py details EURUSD,GBPUSD,... 120
.venv/bin/python research/fetch_multi.py bars US500 M5 3.1      # and H1 12.5
cd research && python3 multi_research.py && python3 multi_mc.py && python3 multi_report.py
python3 multi_mc.py portfolio "ORB GBPUSD London A|ORB GBPJPY London B|ORB US500 NY B"
```

Outputs in data/reference/:
- `symbol_facts_multi.json`, `multi_symbol_feasibility.csv`
- `multi_ranked.csv`, `multi_random_controls.csv`
- `multi_summary_*.csv`, `multi_trades_*.csv`, `multi_mc.csv`, `multi_portfolio.csv`

Result: 44 pre-declared symbol-variant tests. None reaches significance. The best OOS
t-statistic is about 1.5, against about 3.2 needed for 44 tests. The positives are
long-only index/gold effects (bull-market beta), and they need $10–$75 of risk per trade
at minimum volume. A $1/$2 bracket is inside one M5 bar's noise on XAUUSD, NAS100, GER40
and UK100, and costs there are 38–92% of the $1 risk.

## Starting-balance Monte Carlo (`start_balance_mc.py`)
Same trade sets, horizon 3 years and ruin rule as above, starting from $20, $50 and $100.
Sizing is either fixed 0.01 lot or floor(equity / 10) × 0.01.
- P($100) and P($200): the share of runs that touch that equity within 3 years.
- Runs continue until they reach $200 or are ruined.
- P(ruin): the share of runs ruined before reaching $200.

Output: `data/reference/start_balance_mc.csv`.

## Round 4: genuinely different families (`new_families*.py`)
The hypotheses were pre-declared in `research/new_families_hypotheses.md` before any run: 15 tests plus one
addendum (H27), declared after H19 and before it was run. With the 51 earlier tests that makes 67 in total.
Two-sided Bonferroni at α = 0.05 gives t ≥ 3.38. Each hypothesis is one test on the pooled FX7 set (EURUSD,
GBPUSD, AUDUSD, NZDUSD, USDJPY, EURJPY, GBPJPY). Costs and fills come from `engine2.py`. Every test has a
random-direction control on the same entries and exits. The ML tests also have a permuted-label model.

Scripts (system `python3`, except the ML script):
- `nf_common.py`: shared helpers. Adds NZDUSD to `engine2.SPECS`, builds M15 from M5, and has the summary and save
  helpers.
- `new_families.py H14 H15 H20 H21 H22 H23 H24 H25 H26`: the rule-based families. These are prior-day and
  Asian-range sweep fades, z-score reversals, the London fix, the month-end fix, the Monday gap, the
  volatility-regime switch and carry with trend.
- `new_families_pairs.py`: H16 EURUSD/GBPUSD, H17 AUDUSD/NZDUSD and the H18 EURJPY triangle. Uses a rolling
  500-bar OLS hedge (signal only), min-lot legs, and z 2 / 0.5 / 4 with a $2.50 combined stop.
- `new_families_ml.py [H Q KEY SL_ATR]`: pooled LightGBM with 3y-train / 6m-test walk-forward and an
  embargo. Needs the separate venv `/workspace/scratch/mlvenv` (scikit-learn and lightgbm).
  H19 = defaults; H27 = `24 0.05 H27 3`.
- `new_families_mc.py`: $20 start, fixed 0.01 lot, 20k paths over 3 years, on last-3y trades with a
  max-2-open filter. Writes the ranked table.

Data: NZDUSD M5 (3.1y) and H1 (12.5y) were added with `fetch_multi.py`. `*_m15.csv` are resampled from M5 into
/workspace/scratch/history.
Outputs in data/reference/: `new_families_summary.csv` (pooled, per-symbol and controls),
`new_families_trades_<H>.csv`, `new_families_ml_predictions_<H>.csv`, `new_families_mc.csv` and
`new_families_ranked.csv`.

Result: nothing passes. Every family has a negative or about-zero net after costs. The best OOS t-statistic is
+1.19 (H24 Monday gap fill), and over 12 years H24 is flat: PF 1.00, 5 of 13 years positive. The sweep fades
(stop-run) lose more than random direction does. The pairs tests hit the $2.50 stop far more often than they
revert. The triangle cannot beat 3-leg costs. The only real information is H19 (ML, 6h). Its selected signals
hit 52.7% directionally against 49.7% for permuted labels, and it loses $0.12 per trade less than random
direction, but it is still -$0.07 per trade net. Moving to 24h (H27) removed the signal.

## Round 5: news / economic-calendar signal (`news_*.py`)
The hypotheses were pre-declared in `research/news_hypotheses.md` while the calendar was still downloading:
6 strategy tests, so 67 + 6 = 73 tests in total. Two-sided Bonferroni gives t ≥ 3.40.

**Data source.** The ForexFactory public calendar month pages (`/calendar?month=mar.2016`). The JSON embedded in
each page holds actual, forecast (FF consensus), previous and `dateline` (the release time in unix UTC).
- `news_fetch_calendar.py` downloads 154 months (2014-01..2026-10) at one request per 7-8 s, with a gzip cache in
  /workspace/scratch/ff_cache.
- `news_build_calendar.py` writes `data/reference/econ_calendar.csv`: 3,882 releases of 28 target events, with
  coverage in `news_calendar_coverage.csv`. Consensus exists for >99% of releases and none is imputed.
  `z` = (actual − forecast) / the std of that event's past surprises (causal, ≥ 6 past releases), signed for
  EURUSD. `proxy_z_eurusd` (actual − previous) is a labelled proxy and is used only in one event-study row.
- German Prelim CPI is listed by FF as "All Day", so its minute is unknown. It is kept in the CSV but excluded from
  all minute-level work.
- Cross-check (`news_crosscheck_hf.py`): against an independent public FF archive (HuggingFace
  Ehsanrs2/Forex_Factory_Calendar, to 2025-04), the 1,436 rows matched by day have 100% identical actual and
  forecast strings.

**Prices.** EURUSD M1 BID for 2014-04-07..2026-10-06 (4.6M bars), fetched read-only with
`fetch_multi.py bars EURUSD M1 12.5` into /workspace/scratch/history/eurusd_m1_12y.csv. The 3y `eurusd_m1.csv`
was left unchanged.

**Scripts.**
- `news_common.py`: release clusters (target events of one currency at one timestamp, composite z), M1 access,
  the pre-declared news-time cost tiers (+1 min: 3.0 spread + 2.0 slippage, tapering to normal after +15 min,
  plus 0.6 pip commission) and the trade simulator.
- `news_event_study.py`: writes `news_event_moves.csv` (2,122 clusters) and `news_event_study.csv` (aggregates).
- `news_strategies.py`: N1A/N1B surprise momentum, N2 confirmed momentum, N3 fade overreaction, N4A/N4B analog
  kNN. Writes `news_trades_<id>.csv` and `news_strategy_summary.csv`.
- `news_mc.py`: $20 start, fixed 0.01 lot, 20k paths over 3y, bootstrapped from the full 2014-2026 trade set
  because the last 3y hold too few trades. Writes `news_mc.csv` and `news_ranked.csv`.

Run order: `python3 news_fetch_calendar.py 2014-01 2026-10 && python3 news_build_calendar.py &&
python3 news_event_study.py && python3 news_strategies.py && python3 news_mc.py`

**Findings.**
- Surprises do move EURUSD in the expected direction. For abs(z) ≥ 1 the first minute moves about 8 pips the right
  way, with an 80% hit rate. US CPI is about 28 pips (95% hit) and NFP about 18 pips.
- Almost all of the move is done by +1 to +2 minutes. Continuation from +2 to +60 min is only +2.8 pips (t 2.7) for
  1 ≤ abs(z) < 2 and about zero overall. News-time entry costs are about 4 pips at +2 min, so they consume it.
- No strategy is anywhere near significant. The best is N4B (analog kNN with a vol-scaled bracket): +$0.05 per
  trade over 12 years, PF 1.05, t 0.31, 7/12 years positive, OOS 25 trades.
- The headline-sentiment (GDELT) option was not attempted.

## Round 6: measured news-time execution costs
**Historical tick data is available.** `ProtoOAGetTickDataReq` on the demo connection serves EURUSD BID and ASK ticks
back to 2014. A probe with 10-min windows at ages from 1 day to 12.6 years got ticks at every age.
- `news_tick_history.py probe|fetch` (project venv, read-only) pulled -5..+30 min around every unmasked high-impact
  target release in `econ_calendar.csv` from 2014-04 onward: 1,364 releases. It runs as 2 parallel shards
  (`SHARD=k/2`) paced at 0.4 s per request, is resumable, and fetches newest first.
- Output: `data/news_ticks/history/EURUSD_ticks_s*.csv.gz` (216 MB gzip; columns release_dateline, side, ts_ms, price).

**Live recorder.** `trading/news_spread_recorder.py` with the `ops/news_*.sh` scripts (see the main README).
Daily CSVs go to `data/news_ticks/YYYY-MM-DD.csv` and window metadata to `windows.csv`.

**Report.** `news_cost_report.py` (system python3) reads both sources and writes these files to data/reference/:
- `news_cost_by_second.csv`
- `news_cost_by_minute.csv`
- `news_cost_by_group.csv` (by year and by release type)
- `news_cost_live.csv` (once live data exist)
- `news_measured_backtest.csv` and `news_measured_trades_<id>.csv`

The measured cost model, declared in the addendum of `news_hypotheses.md`:
- Spread = p75 across releases of the spread at the exact entry second.
- Slippage = the mean ABSOLUTE 1-s quote change at that second, always charged as adverse.
- Stops pay the same plus 0.2 pip. Commission is 0.6 pip round trip.
- Sensitivity runs use p50 spreads and 2023-26 releases only.

Results:
- Measured spread (pips) at release p50/p75/p90/p99:
  - T+0 s: 0.8/1.7/3.4/12.8
  - T+2 s: 0.9/2.1/4.3/12.9
  - T+10 s: 0.6/1.1/2.2/5.9
  - T+60 s: 0.3/0.4/0.6/2.1
  - T+120 s: 0.2/0.3/0.5/1.3
  - Normal (before release): 0.1-0.2
- 1-s latency move at +60..+120 s: about 0.5 pip on average, 1.0 pip at p90.
- NFP is the worst release type: median spread 2.6 at T+0 s and 1.1 at the p90 of T+60 s. The median abs jump in
  the first 5 s is 18.5 pips for NFP and 12 for CPI.
- The Round 5 assumption (2-3 pip spread + 1-2 pip slippage at +1/+2 min) was about 3x too pessimistic. The measured
  all-in entry at T+1/T+2 min is about 0.9-1.0 pip (spread + slippage), plus 0.6 pip commission.
- Even so, no strategy becomes significant. The 80-test threshold is t ≥ 3.42.
  - N1A/N2/N3/N4A stay negative.
  - N1B is about 0.
  - N4B is +$0.15 per trade (t 0.95, OOS 25 trades, t 1.16, P($100) = 0).
  - E1 (EU flash-PMI continuation) is +$0.69-0.82 per trade, t 1.7-2.1. But it has only 47 trades in 12 years and 2 OOS,
    its random-direction control is also +$0.39-0.46, and P($100) = 0 because it trades about 4 times a year.
