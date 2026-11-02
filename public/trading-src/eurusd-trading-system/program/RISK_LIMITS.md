# RISK_LIMITS: IMMUTABLE

Written 2026-10-07 07:25 UTC, before any program code, backtest or paper trade. The SHA-256 of this file is stored in
`RISK_LIMITS.sha256` and in `journal/hypotheses.jsonl` (record `RISK_LIMITS_REGISTERED`). `engine.py` refuses to
start if the hash differs. The numbers below are hard-coded in `risk.py` and checked against this file by
`risk.py --selftest`. Nothing here may be loosened by any agent, hypothesis module, review or "temporary" exception.
A rule may only be made stricter. That takes a NEW file `RISK_LIMITS_v2.md`, with the reason written down and a
journal record. This file is never edited.

Program window: 2026-10-07 07:20 UTC to 2026-10-28 07:20 UTC (21 days). PAPER ONLY.

## 0. Paper only
- No orders of any kind: no live orders and no demo orders. The program code contains no order-, amend- or
  close-position API messages. The engine refuses to start if any file under `program/` references
  `ProtoOANewOrderReq`, `ProtoOAAmendPositionSLTPReq`, `ProtoOAClosePositionReq`, `ProtoOACancelOrderReq` or
  `ProtoOAAmendOrderReq`.
- Allowed Open API calls (read-only, DEMO host `demo.ctraderapi.com:5035` only): auth, account list, symbols, symbol
  details, spot subscriptions, trendbars, tick data. Never touch the live accounts <LIVE_ACCOUNT_1>, <LIVE_ACCOUNT_2> or <LIVE_ACCOUNT_3>.
- `ops/demo_test_order.py` is retired and is never run again.
- Credentials are never printed or logged.
- Even if a hypothesis is promoted, NO live or demo orders follow. The engine writes a promotion report, stops
  opening trades for new hypotheses, and a human decides what happens next.

## 1. Account and sizing
- Paper equity starts at **$10.00 USD**.
- Size is the symbol's minimum volume (0.01 lot FX, 1 oz XAUUSD, 0.1 US500) while equity < $20.
- Once equity >= $20, size is at most floor(equity / 10) x min volume. It is then reduced, in min-volume steps, until
  §2 is satisfied. If even 1 x min volume breaks §2 or §3, the trade is SKIPPED and the skip is journaled.

## 2. Per-trade risk
- Every trade has a hard stop that is set at entry and never moved further from entry. Moving it toward profit is
  allowed only if the hypothesis' pre-registered rules say so.
- Risk at entry = |fill - stop| x units, converted to USD
  + round-trip commission
  + expected stop slippage (normal: 0.3 pip FX / $0.10 XAU / 0.5 pt US500; inside a news window: the measured
    1-s latency move from `data/reference/news_cost_by_second.csv`).
- Max risk per trade:
  - **$1.10** while equity <= $11.00;
  - **min($1.10, 10% of equity)** once equity > $11.00.
  - In every case, also <= the remaining open-risk budget in §3.
- (Stricter addition) Max spread at entry: no entry if the live spread is > 3x the symbol's normal spread. Normal
  spread = the median of the engine's own quotes over the last 5 trading days, or `symbol_facts_multi.json` before
  that. The one exception is a news-window hypothesis whose rules use the measured news cost curve; its cost is then
  charged from that curve or the live quote, whichever is worse.
- (Stricter addition) Margin: used margin after entry must be <= 70% of equity, using the min-volume margin in
  `data/reference/symbol_facts_multi.json` scaled by size.

## 3. Portfolio
- At most **2** concurrent open paper positions (all hypotheses combined).
- Total open risk (the sum of §2 risk over open positions) <= **15% of equity**.
- (Stricter addition) At most 1 open position per hypothesis per symbol.
- (Stricter addition) Flat by Friday 20:45 UTC, unless the hypothesis' pre-registered rules hold through the weekend.
  None do in v1.

## 4. Daily loss limit
- If equity (realized + unrealized) falls to <= **80% of start-of-day equity** (00:00 UTC snapshot), there are no new
  entries until the next UTC day. Open positions keep their stops and targets.

## 5. Kill switch (program level)
- If equity < **$4.00**, OR drawdown from peak equity > **50%**:
  - halt all paper trading;
  - close any open paper positions at the current executable price, with costs;
  - write `program/state/HALTED` with the reason;
  - generate `program/final_report.py` output.
- The program never resumes after a halt.

## 6. Per-hypothesis kill
- A hypothesis is killed (status `killed`, no new entries) after **>= 15 forward trades with PF < 0.8**, OR after
  **8 consecutive losses**.
- A killed hypothesis may come back only as a NEW id with materially different, pre-registered rules. It is never
  "re-tuned" under the same id.

## 7. Costs (always applied, never optional)
- Fills come from live bid/ask: buy at ask, sell at bid; longs exit on bid, shorts on ask.
- Slippage on market/stop entries and stop exits:
  - normal: 0.2 pip FX entry / 0.3 pip stop; $0.05 / $0.10 XAU; 0.25 / 0.5 pt US500;
  - news windows: the measured curve.
  Targets are limit fills with no positive slippage.
- Stop-first: if a stop and a target are both crossed by the same quote update, the stop wins.
- Gaps: a stop crossed by a gap fills at the first executable quote beyond it, not at the stop.
- Commission: $3.00 per lot per side on FX (0.01 lot = $0.03 per side) and $3.50 per lot per side on XAUUSD
  (the broker's figures); US500 is spread-only.
- Swap: charged from the broker's symbol swap rates for every rollover held (triple day as reported).

## 8. Promotion rule (forward paper trades only)
A process (hypothesis id + version) is "validated" only if ALL of the following hold on its own forward paper trades:
1. >= 30 closed trades AND >= 14 calendar days since its first forward trade;
2. net P&L > 0 after all costs;
3. profit factor >= 1.3;
4. it beats the random-direction control on the same entries: total net P&L > the 95th percentile of 10,000
   random-direction resamples of its shadow long/short outcomes. The engine simulates both directions with
   identical brackets at every entry;
5. forward t-stat >= 2.0, where t = mean / (sd / sqrt(n)) of per-trade net USD P&L at actual size;
6. max drawdown of its own forward equity curve < 35% (on a $10 start).

On promotion: no live or demo orders. Write `reports/promotion_<id>.md`, stop testing new hypotheses, and leave the
decision to the user.

## 9. Process rules
- Every hypothesis is pre-registered in `journal/hypotheses.jsonl`, with entry, exit, invalidation, expected hold
  and cost rationale, BEFORE its backtest results are seen.
- Backtests use only data that ends before the forward window (<= 2026-10-06).
- Hypothesis modules are versioned. A rule change creates a new version, and forward stats restart for it.
- Every signal, entry, exit, skip, risk block and cycle is appended to `journal/decisions.jsonl`. Journals are
  append-only; corrections are new records.
- No non-public information, no manipulation, no pump-call following. X/social posts may be used only as noisy
  sentiment, and only if legally and freely readable without logging in.
- No promise of profit is ever made.
