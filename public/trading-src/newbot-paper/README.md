# newbot-paper — EUR/USD PAPER trading simulator

**Fake money only. No broker, no API keys, no real orders — ever.** Everything is simulated
locally from free public price data.

## Run it

```bash
python3 /workspace/projects/newbot-paper/run.py              # fetch, catch up, save, report
python3 /workspace/projects/newbot-paper/run.py --report-only  # report only, state untouched
/workspace/projects/newbot-paper/run.sh                      # same as run.py (wrapper)
python3 /workspace/projects/newbot-paper/backtest.py 6mo      # sanity backtest (doesn't touch the account)
```

Pure Python 3 standard library (urllib, json, sqlite3) — no venv or pip packages needed.

Exit codes: `0` ok, `1` not initialized (report-only), `2` data fetch failed (state unchanged),
`3` another run in progress, `4` processing error (transaction rolled back, state unchanged).

## Data source

Yahoo Finance chart API, symbol `EURUSD=X`, interval `1h`
(`https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?interval=1h&range=...`, falls back to
`query2`, 3 retries). Verified working from this box on 2026-10-06. Only **closed** bars are used:
the in-progress hour and Yahoo's trailing "live tick" row are dropped, as are rows with missing values.
Times are stored as UTC epoch (bar open time) and shown in UTC+8 (Asia/Ulaanbaatar).

## Strategy (one simple mechanical rule set)

Trend-following EMA crossover on 1-hour bars with ATR-based stop and target:

1. **Signal** at the close of a bar: EMA(20) of closes crosses **above** EMA(50) → go LONG;
   crosses **below** → go SHORT. (Needs ≥150 bars of history first.)
2. **Entry** at the **next bar's open** (never at the signal bar's close).
3. **Stop loss** = 2 × ATR(14, Wilder) from entry; **take profit** = 4 × ATR(14) from entry (2:1 reward/risk).
4. **Exit** at whichever comes first: stop, target, or an opposite crossover (then the position is
   closed at the next open and reversed into the new direction). Max 1 open position.
5. **Size**: target risk 1% of equity per trade: `units = 1% × equity / (stop distance + costs)`,
   rounded down to the 0.01-lot step, **floored at the broker minimum 0.01 lot** (as a real broker
   forces), then capped so required margin fits in equity. With a tiny account this means the
   *actual* risk is far above 1% — the real % risked is logged for every trade.

## Account & broker mechanics (CONFIG section at the top of `engine.py`)

| Setting | Value | Meaning |
|---|---|---|
| `START_BALANCE` | $10 | fake starting balance (account reset to this on 2026-10-06 20:30 UTC+8) |
| `LEVERAGE` | 500 | margin required = units × price / 500 (USD); 0.01 lot ≈ $2.25–2.35 margin |
| `MIN_LOT_UNITS` / `LOT_STEP_UNITS` | 1,000 / 1,000 | min 0.01 lot, 0.01-lot step (1 lot = 100,000 EUR) |
| `RISK_PER_TRADE` | 1% | target risk; the min-lot floor overrides it on small accounts |
| `STOP_OUT_LEVEL` | 50% | position force-closed when margin level (equity / used margin) ≤ 50%, or equity ≤ 0 |
| `STOPOUT_FILL` | `bar_worst` | stop-out fills at that bar's worst price (conservative); `level` = at the stop-out price |
| `NEGATIVE_BALANCE_PROTECTION` | on | a gap can't push the balance below $0 |

- A signal is **skipped** (logged as `SKIPPED` in `trades.csv` and shown in the report) if equity
  can't cover the margin for 0.01 lot.
- Within a bar, adverse exits (stop loss / stop-out) are checked before take profit; whichever
  adverse level is closer to entry fires first.
- The report shows leverage, used margin, free margin and margin level; each trade shows lot size,
  margin, stop-out price, $ risk and % of equity risked.

The previous $10,000 / no-margin-model account (initialized 2026-10-06 20:01, no trades yet) is
preserved in `data_backup_10k/`.

### Cost / fill model
- Yahoo prices are treated as mid. **Spread = 1.0 pip round trip**: buys fill at mid + 0.5 pip,
  sells at mid − 0.5 pip (on entry and exit).
- Stop-loss exits get an extra **0.2 pip slippage**. If a bar opens beyond the stop/target (gap),
  the fill is at the open, not the level.
- If a bar touches both stop and target, the **stop is assumed hit first** (conservative).
- No swap/financing charges modelled.

### No lookahead
Bars are processed strictly in time order, one at a time (`engine.Account.step`). For bar N:
(1) execute any order decided at bar N−1's close at bar N's open, (2) check stop/target against
bar N's high/low, (3) compute the signal from indicators up to and including bar N's close, which can
only be acted on at bar N+1's open. EMAs/ATR at index N only use bars ≤ N. The live paper account
and the backtest use the exact same `step()` code; a test that rewound the account 45 days and
let it catch up produced the same trades (same times and prices) as the backtest.

## Catch-up mode / state

Each run fetches recent hourly bars (range chosen automatically to cover the gap since the last
processed bar: 5d / 1mo / 3mo / …), then processes **every closed bar after the last processed bar**,
in order. If the last bar's signal fires, the order is saved as "pending" and filled at the next
bar's open on a later run.

- **First run** initializes a fresh $10,000 account at the latest closed bar and stores ~3 months of
  history only for indicator warm-up — no backfilled trades.
- `data/paper.db` (SQLite) is the source of truth: bars, account state, trades, runs. Each run is
  one atomic transaction; on any fetch/processing error nothing is written.
- `data/trades.csv` — every trade (OPEN / CLOSED) plus every SKIPPED signal, with lots, margin,
  stop-out price, $ risk and % of equity risked; rewritten from the DB after each run.
- `data/state.json` — human-readable mirror of the account state.
- `data/run.log` — one line per run / failure.
- A lock file prevents two runs at once.

To reset the account (start over): move/delete the `data/` folder and run `run.py` again
(the start balance etc. come from CONFIG at that moment).

## Sanity backtest (BACKTEST — not the paper account)

Run on 2026-10-06 with `backtest.py` using the CONFIG above ($10 start, 1:500, 0.01 min lot,
1% target risk, 50% stop-out; same strategy and costs). Yahoo EURUSD=X 1h, data to 2026-10-06 19:00 UTC+8.

| Window | Trades | Win rate | Final balance | Return | Max drawdown | Wiped out / stop-out | Actual risk per trade (median, range) |
|---|---|---|---|---|---|---|---|
| 3 months  | 5  | 0%    | **$1.59**  | **−84.1%** | 84.1% | wiped out 2026-07-28 23:00 UTC+8 (5 straight losses); 12 later signals skipped; 0 stop-outs | 23.9% (15–55%) |
| 6 months  | 22 | 27.3% | **$1.34**  | **−86.6%** | 92.3% | wiped out 2026-06-05 20:00 UTC+8; 29 later signals skipped; 0 stop-outs | 22.0% (11–66%) |
| 12 months | 98 | 32.7% | **$14.83** | **+48.3%** | 82.7% (peak $54.49 → ~$10) | not wiped out; 0 stop-outs | 7.6% (3.5–27%) |

"Wiped out" = balance below the ~$2.3 margin needed for one 0.01 lot, so no further trades possible.

Plain-terms read:
- The 1% risk target is **not achievable** at $10: the smallest allowed trade (0.01 lot = $0.10/pip)
  with the typical ~20-pip stop risks about **$2 = ~20% of a $10 account** per trade (median stop
  19.8 pips, $ risk $1.26–$5.60). True 1% risk needs roughly **$200+** of equity. Every backtest
  trade was floored to the minimum lot.
- So results are dominated by luck of sequence: 4–5 losses in a row wipe the account. The 3- and
  6-month windows both died within weeks; the 12-month window survived only because its first
  trades won, grew to $54, then gave most of it back.
- Margin stop-out never triggered: with 0.01 lot the stop loss (~20 pips) is always hit long before
  the 50% margin level (~60–90 pips away), and once the balance is tiny the margin check simply
  blocks new trades.
- For reference, the earlier $10,000 / 1%-risk version of the same strategy: 3mo −5.1%, 6mo −13.1%,
  12mo −1.0% (strategy itself is roughly break-even-to-losing after costs recently).

Raw output: `backtest_results.txt`. Backtests are not predictions.

## Files
- `engine.py` — data fetch/validation, indicators, account and bar-by-bar logic
- `run.py` / `run.sh` — catch-up runner + report
- `backtest.py` — sanity backtest
