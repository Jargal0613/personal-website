# LBO v1 history backtest, 100+ trades (GBPUSD London ORB, $1 SL / $2 TP, 0.01 lot, $10 account)

Generated 2026-10-18 ~03:20 (Asia/Ulaanbaatar, UTC+8). This is a **historical backtest** and paper research only. It is not forward-trade evidence, nothing was written to `journal/` or `state/`, and no orders were placed.

## What was tested

- **Rule:** `program/hypotheses/LBO.py` v1, **unchanged**, with no parameter changes and no search. Range = M1 bid high/low 08:00-08:29 London (DST-aware). At 08:30:01 London, place OCO stops at range high + spread (buy) and range low - spread (sell), live for 3 h. SL 10 pips / TP 20 pips from the fill at 0.01 lot (1,000 units). Time exit at min(16:00 London, 20:00 UTC). One trade per day.
- **Simulator:** the validated replica `/workspace/scratch/lbo_gapfill/bt_lbo_gapfill.py` (`run_day` unchanged: tick-level bid/ask quote merge plus a 1-minute clock pass, fill at max(level, ask) + 0.2 pip / min(level, bid) - 0.2 pip, stop-first exits with 0.3 pip stop slippage, measured news slippage inside news windows, $0.06 commission per trade, `risk.check_entry` per trade incl. the 3x-normal-spread block). The driver is `/workspace/scratch/lbo_hist/run_hist.py`. It only changes data plumbing: it reads gzipped history, takes news windows from `data/reference/econ_calendar.csv` (high impact, unmasked; same -120/+900 s window), and sets "normal spread" = median of minute-sampled tick spreads over the previous 5 trading days.
- **Plumbing check:** on the 8 gap-fill/live days 2026-10-07..16 the history driver reproduces every trade (direction, entry, exit reason, net $) of the validated replica, which matched the two live trades. One shadow-control P&L differed by $0.07 (news-slippage source).
- **Data:** cTrader **DEMO** account <DEMO_ACCOUNT_ID> (isLive=False checked on every connection). Read-only requests only: GBPUSD M1 bid trendbars plus **real BID and ASK ticks** for every weekday 2022-01-03..2026-10-06, in `/workspace/scratch/lbo_hist/raw/` (1,242 weekdays x 3 files). Because actual bid/ask ticks were available for every day, **no M1-plus-spread-estimate assumption was needed**. Spreads are the recorded tick spreads.
- **Sizing:** every trade is 0.01 lot from a $10 start at a fixed lot, so the equity curve can go below $0 on paper. The "real $10 account" line below applies RISK_LIMITS sequentially.

## Where LBO was designed: the IS / OOS split

- LBO = Round-3 hypothesis **H1-A** from `research/multi_research.py` ("ORB GBPUSD London A", `data/reference/multi_ranked.csv`). It was pre-registered in `journal/hypotheses.jsonl` on 2026-10-07 and admitted by `program/backtests/register_v1.py` / `screen_v1.py` as MARGINAL (798 trades, PF 0.99; research-"OOS" 2024-10-06..2026-10-06: 513 trades, PF 1.04, t 0.44; 1/4 years positive).
- That research used `/workspace/scratch/history/gbpusd_m5.csv`, which starts **2023-08-31** and runs to 2026-10-06. The screen used the whole window, its 2024-10-06+ "OOS" block included, to admit LBO. So **2023-08-31..2026-10-06 is IN-SAMPLE** (design and selection data).
- **OUT-OF-SAMPLE = 2022-01-03..2023-08-30.** No LBO or GBPUSD-ORB research touched this period. The GBPUSD 12y H1 file was used only for the TSMOM/Donchian hypotheses, and the 12y London-breakout check in `research/long_history_check.py` was EURUSD with different rules.
- Replication check: this IS run gives 714 trades, PF 0.96, and on the research-"OOS" sub-block 454 trades, PF 1.03, t +0.26. That is in line with the original M5 research (PF 0.99 / 1.04, t 0.44).
- Random-direction control: on each traded day a coin picks the long or short shadow trade (market entry at the trigger moment, same bracket, costs and exits). There are 10,000 draws, seed 8. "Percentile" is the share of random draws whose net is below the real net.


## Results (each trade sized 0.01 lot, $10 start, fixed lot; equity may go negative on paper)

| set | trades | win % | net $ | avg $/trade | PF | t | max DD $ (from peak) | max DD as % of $10 start | lowest equity from $10 | random-dir mean $ | random-dir p95 $ | real net percentile vs random |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **OUT-OF-SAMPLE** 2022-01-03 to 2023-08-30 (untouched) | 416 | 29.6 | -86.35 | -0.208 | 0.73 | -3.04 | 88.17 | 882% | -78.17 | -73.25 | -33.44 | 29.4 |
| IN-SAMPLE 2023-08-31 to 2026-10-06 (design data, all) | 714 | 36.3 | -18.07 | -0.025 | 0.96 | -0.46 | 43.94 | 439% | -29.12 | -98.82 | -45.46 | 99.5 |
|   IS part 1: 2023-08-31 to 2024-10-05 (research 'train') | 260 | 33.8 | -26.38 | -0.101 | 0.86 | -1.15 | 42.69 | 427% | -29.12 | -47.01 | -15.33 | 86.0 |
|   IS part 2: 2024-10-06 to 2026-10-06 (research 'OOS', used for selection) | 454 | 37.7 | +8.31 | +0.018 | 1.03 | +0.26 | 43.94 | 439% | +5.68 | -52.20 | -9.10 | 98.9 |
| ALL 2022-01-03 to 2026-10-06 | 1130 | 33.8 | -104.42 | -0.092 | 0.87 | -2.15 | 125.47 | 1255% | -115.47 | -172.43 | -105.23 | 95.2 |

## By calendar year

| set | trades | win % | net $ | avg $/trade | PF | t | max DD $ (from peak) | max DD as % of $10 start | lowest equity from $10 | random-dir mean $ | random-dir p95 $ | real net percentile vs random |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022 (OOS) | 250 | 28.8 | -58.06 | -0.232 | 0.71 | -2.65 | 58.10 | 581% | -48.10 | -38.50 | -7.07 | 15.2 |
| 2023 (OOS) | 166 | 30.7 | -28.29 | -0.170 | 0.78 | -1.55 | 30.11 | 301% | -20.11 | -34.90 | -10.24 | 67.6 |
| 2023 (IS) | 80 | 32.5 | -9.14 | -0.114 | 0.85 | -0.71 | 16.93 | 169% | -3.36 | -24.48 | -9.16 | 95.2 |
| 2024 (IS) | 234 | 35.9 | -9.96 | -0.043 | 0.94 | -0.45 | 42.16 | 422% | -19.98 | -29.57 | +1.37 | 84.6 |
| 2025 (IS) | 223 | 37.7 | +3.08 | +0.014 | 1.02 | +0.14 | 29.26 | 293% | +8.65 | -22.05 | +8.38 | 91.1 |
| 2026 (IS) | 177 | 36.7 | -2.05 | -0.012 | 0.98 | -0.11 | 15.83 | 158% | -4.68 | -23.18 | +2.71 | 90.8 |

## Day outcomes, exits, and the real-account path

- **OOS**: 433 weekdays -> {'trade': 416, 'skip': 9, 'RISK BLOCK': 8}. Exits TP 123 / SL 292 / TIME 1; longs 212, shorts 204; avg spread at entry 0.41 pip; 4 entries inside a news window; observed break-even win rate 36.4% vs actual 29.6%.
- **OOS as one real $10 account under RISK_LIMITS** (risk budget blocks entries once equity is too low; kill switch halts): first blocked entry ['2022-01-06', 3, 6.62] (date, trades taken, equity); per-hypothesis kill (s6) None; account kill None; trades taken 3, final equity $6.62.
- **IS**: 809 weekdays -> {'skip': 32, 'trade': 714, 'RISK BLOCK': 58, 'no trigger': 5}. Exits TP 249 / SL 455 / TIME 10; longs 358, shorts 356; avg spread at entry 0.26 pip; 5 entries inside a news window; observed break-even win rate 37.1% vs actual 36.3%.
- **IS as one real $10 account under RISK_LIMITS** (risk budget blocks entries once equity is too low; kill switch halts): first blocked entry ['2023-09-11', 6, 6.39] (date, trades taken, equity); per-hypothesis kill (s6) None; account kill None; trades taken 6, final equity $6.39.

## Verdict

**LBO v1 does NOT survive the backtest.**

- **Out-of-sample (2022-01..2023-08, 416 trades):** clearly negative. Win rate 29.6% vs a 36.4% break-even, PF 0.73, net -$86.35, t = **-3.04**. Both years are negative (2022 PF 0.71, 2023 PF 0.78). The real result sits at the **29th percentile** of random-direction entries, so it shows no directional edge at all and is not even better than a coin flip with the same bracket.
- **In-sample (2023-08..2026-10, 714 trades):** about break-even after costs (PF 0.96, net -$18.07, t -0.46). Only 2025 was positive (+$3.08). It beats random direction (99.5th percentile), but random direction loses heavily with this bracket, so "better than random" here still means "losing slowly". The in-sample advantage over random did not carry into the untouched period.
- The pass bar was edge clearly beyond costs and random with t >= 2 out-of-sample. Actual: OOS t = -3.04, PF < 1, and below the random median. **Fail.**
- On a real $10 account, a fixed $1.09-1.17 risk per trade breaks the 15% open-risk budget once equity falls below ~$7.3. In both periods the account freezes after its first 3-6 trades (from $10 to ~$6.4-6.6), so it could not even trade its way back.

## Files

- `program/backtests/lbo_history_100plus.csv`: one row per weekday: period, status, range, levels, direction, UTC entry/exit times, prices, exit reason, net $, risk $, entry spread, news flag, shadow long/short $.
- Scripts and raw data (new files only): `/workspace/scratch/lbo_hist/{fetch_hist.py, fetch_loop.sh, run_hist.py}`, `/workspace/scratch/lbo_hist/out/{all_2022_2026.json, analysis_final.json, lbo_final.py, lbo_md.py, check_gapfill_days.py}`, `/workspace/scratch/lbo_hist/raw/`.

