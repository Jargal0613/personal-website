# 21-day PAPER-ONLY trading research program (2026-10-07 07:20 UTC to 2026-10-28 07:20 UTC)

Goal: find and validate a repeatable, net-positive process, judged only by forward paper results after costs, starting
from a $10 paper account. **No orders of any kind** (no live, no demo). Read-only cTrader demo API. No profit is promised.

| path | what |
|---|---|
| `RISK_LIMITS.md` (+ `.sha256`) | immutable hard limits; the engine refuses to start if the hash changes |
| `risk.py` | the limits in code (`python3 program/risk.py --selftest`) |
| `engine.py` | the long-running paper engine: quotes, fill simulation, limits, plug-ins, cycles |
| `hypotheses/<ID>.py` | plug-in rule modules (`META` + `on_minute(ctx)`), active only while journal status = `forward` |
| `journal/hypotheses.jsonl` | append-only: risk-limit hash, screen, hypothesis pre-registrations, status changes |
| `journal/decisions.jsonl` | append-only: every signal / entry / exit / skip / cancel / cycle / kill event |
| `journal/trades.csv`, `journal/shadows.csv` | closed paper trades, plus the long/short shadow outcomes per entry (random-direction control) |
| `journal/equity.csv` | equity marks (each cycle, each exit, day start) |
| `journal/news.jsonl` | RSS headlines (title/link/tags), FF calendar events, X aggregates (when available) |
| `journal/assumptions.jsonl` | logged assumptions (instrument list, cost model, X availability, ...) |
| `news.py`, `xsent.py` | news / calendar inputs; optional X recent-search sentiment (backs off 6 h on 402/429) |
| `stats.py` | forward stats and the promotion test |
| `daily_summary.py`, `final_report.py` | reports (`python3 program/daily_summary.py`) |
| `backtests/` | pre-registration (`register_v1.py`), backtests, `screen_v1.py`, `results/` |
| `state/` | engine state, spreads, heartbeat, logs, `HALTED` (kill switch) |

Ops: `ops/program_start.sh`, `ops/program_stop.sh`, `ops/program_status.sh`. The supervisor `ops/run_program.sh`
(flock singleton, crash restart, 10-min heartbeat watchdog) is auto-started by `ops/program_ensure_running.sh` from
~/.bashrc and ~/.profile. It does not restart the engine if the RISK_LIMITS hash or the paper-only guard fails.

To add a hypothesis without a restart:
1. Append a `type=hypothesis` record (rules, invalidation, expected hold, cost rationale) to `journal/hypotheses.jsonl`.
2. Backtest it on data ending <= 2026-10-06 and append the screen result as a `type=status` record.
3. Drop `hypotheses/<ID>.py` with `META = dict(id=..., version=...)` and `on_minute(ctx)`, using `ctx.market(...)`,
   `ctx.stop_order(...)`, `ctx.bars(...)`, `ctx.quote(...)`, `ctx.state` and `ctx.log(...)`. Every order needs a stop.
4. Append `status=forward`. The engine loads the module within a minute.
A rule change gets a new `version`, and forward stats restart for it.
- 2026-10-17: window extended to 31 days (ends 2026-11-07 07:20 UTC) at B's request to make up outage days (Oct 9-12 DNS stall, Oct 16-17 missing venv). RISK_LIMITS unchanged.
- 2026-10-18: program STOPPED at B's request after LBO v1 failed the 2022-2026 history backtest (program/backtests/lbo_history_100plus.md). New rule: paper trade only strategies that pass a historical backtest first.
