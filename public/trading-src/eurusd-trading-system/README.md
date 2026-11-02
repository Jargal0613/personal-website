# ai-trading: EUR/USD research + news-cost recorder

**Status (2026-10-06):** the old short-only paper trader is STOPPED. `ops/DISABLED` is present, auto-start is off and
its daily report was deleted. The only running service is the read-only **news spread recorder** (see below).

## News spread recorder (read-only, DEMO)
`trading/news_spread_recorder.py` subscribes to EURUSD, GBPUSD and USDJPY spot quotes on `demo.ctraderapi.com`.
It sends only these requests: app auth, account list, account auth, symbol list, subscribe spots. It never sends
order code or order requests.
- Every quote (UTC ms, bid, ask) is written to `data/news_ticks/YYYY-MM-DD.csv`, but only inside these windows:
  - -10..+30 min around high-impact USD/EUR releases and the EUR flash PMIs
  - one pseudo-random 40-min baseline window per weekday
- Window metadata goes to `data/news_ticks/windows.csv`.
- Schedule: the ForexFactory month page (daily) plus the weekly JSON feed (every 6h, with a 1h retry after a
  failure), cached in `data/news_schedule.json`.
- Supervision works the same way as the old trader. `ops/run_news_recorder.sh` holds a flock singleton, restarts
  on crash with backoff, and restarts when `data/news_recorder.heartbeat` is more than 10 min stale.
  `ops/news_ensure_running.sh` is called from `~/.bashrc` and `~/.profile` (there is no systemd or cron). The log is
  `data/news_recorder.log`.

```
ops/news_status.sh   # supervisor/recorder state, heartbeat, tick rows, upcoming releases (UB time and UTC)
ops/news_stop.sh     # stop + disable auto-start (creates ops/NEWS_DISABLED)
ops/news_start.sh    # re-enable + start
```
Analysis: `python3 research/news_cost_report.py` (see research/README.md, Round 6).

---
## (Stopped) EUR/USD live PAPER trader. Historical notes below


A virtual (paper) trader for EUR/USD. It reads live quotes from a **cTrader DEMO**
account through the Open API, simulates trades in memory, and logs them to CSV.

**DEMO only. No order code.** The bot connects only to `demo.ctraderapi.com`
(`EndPoints.PROTOBUF_DEMO_HOST`), picks the first account with `isLive == false`,
and sends only read-only requests (application auth, account list, account auth,
symbol list and details, spot subscription). Nothing in this project sends
`ProtoOANewOrderReq`, `ProtoOAAmendPositionSLTPReq`, `ProtoOAClosePositionReq`
or any other trading request. Keep it that way.

## Strategy (frozen; do not change the parameters)
"Large 5m range": on each completed M1 candle, if `range_5m` (high-low of the
last 5 candles) > 0.000326, go SHORT at the next candle's open. 0.01 lot,
5-pip stop, 120-minute maximum hold, one position at a time, $10 virtual account.
Spread is taken from quotes; commission (~0.6 pip round trip on this
Pepperstone raw demo) is **not** modelled.

## Layout
```
trading/live_paper.py               live paper trader (entry point)
trading/daily_report.py             read-only report: live vs frozen backtest
trading/nonoverlap_frozen_backtest.py  reproduces the frozen reference (needs archive data + pandas)
ctrader/market.py                   M1 candle builder from spot quotes (used by live_paper.py)
ops/                                supervisor + start/stop/status/restart, demo connection test
data/live_paper_trades.csv          closed virtual trades (appended)
data/live_paper_signals.csv         one row per completed M1 candle (appended)
data/live_paper.log                 trader stdout/stderr + supervisor events
data/live_paper_supervisor.log      supervisor events only
data/reference/nonoverlap_frozen_results.csv  frozen backtest results
data/backups/                       CSV backups
.env                                credentials fallback (chmod 600, never commit or print)
.venv/                              Python 3.13 venv from requirements.txt
```
Research scripts, research CSVs, historical M1 data and old tests are archived in
`/workspace/projects/ai-trading-archive-20261006.tar.gz`.

## Run / supervise
There is no systemd or cron on this box. `ops/run_live_paper.sh` is a supervisor:
- only one copy runs at a time
- it restarts the trader on crash (5s backoff, doubling up to 300s)
- it restarts the trader if no new signal row appears for 20 minutes during
  market hours

`ops/ensure_running.sh` is called from `~/.bashrc` and `~/.profile`, so after a
box restart the supervisor comes back as soon as any shell starts.

```
ops/status.sh     # is the supervisor/trader alive, last signal row
ops/stop.sh       # stop and turn off auto-start (creates ops/DISABLED)
ops/start.sh      # turn auto-start back on and start
ops/restart.sh    # stop + start
.venv/bin/python ops/demo_connection_test.py   # read-only demo check (account, isLive, quotes)
```
Credentials come from the environment variables `CTRADER_CLIENT_ID`,
`CTRADER_CLIENT_SECRET` and `CTRADER_ACCESS_TOKEN`. Any that are missing are
filled in from `.env`. Never echo them.

Notes:
- An open virtual position lives only in memory. Any restart drops it.
- On startup the trader continues trade numbering and equity from
  `data/live_paper_trades.csv`.
- The signals CSV header has 6 columns (written before the `threshold` column was
  added). Rows have 7 columns, except the first 7 rows. The report handles both.

## Report
```
.venv/bin/python trading/daily_report.py
```
The report shows:
- whether the trader is alive, the last signal time, and any open virtual position
- live trades, win rate, net pips, profit factor, equity, max drawdown and exit
  reasons, both overall and for the last 24h
- the frozen backtest at 0%, 0.005% (realistic) and 0.010% cost

## 21-day paper program (2026-10-07 to 2026-10-28)
PAPER ONLY (no orders of any kind; `ops/demo_test_order.py` is retired and refuses to run again because its marker
file exists). See `program/README.md`. Engine ops: `ops/program_start.sh`, `ops/program_stop.sh`,
`ops/program_status.sh`. Summary: `python3 program/daily_summary.py`. Final report: `python3 program/final_report.py`.
