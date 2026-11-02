"""Backtests of the pre-registered NH1/NH2/NH3 (rules fixed in journal/hypotheses.jsonl before this ran).
Uses research/engine2.py (costs: spread model, commission, slippage, swap; SL-first). Data ends 2026-10-06.
Research only. Output: program/backtests/results/new_v1_summary.csv + trades."""
import calendar
import os
import sys
from zoneinfo import ZoneInfo

R = "/workspace/projects/ai-trading/research"
sys.path.insert(0, R)
import numpy as np
import pandas as pd
import engine2
from nf_common import get_sym, summarize, randomize, local_ts

OUT = "/workspace/projects/ai-trading/program/backtests/results"
NYC = ZoneInfo("America/New_York"); UTC = ZoneInfo("UTC")
STD_OK = engine2.entry_ok


def allow_weekdays(t, block_hours=()):
    return pd.Timestamp(t, unit="s", tz="UTC").dayofweek < 5


def trading_days(S):
    d = np.unique(S.ts // 86400)
    return [int(x) for x in d if (x + 3) % 7 < 5]


def price_at(S, t):
    i = S.idx(t)
    return S.o[i] if i < len(S.ts) and abs(int(S.ts[i]) - t) <= 600 else np.nan


# ---------------- NH1 ----------------
def nh1_gen(period):
    def gen(S):
        sig = []; days = trading_days(S)
        for k in range(1, len(days)):
            day, prev = days[k], days[k - 1]
            p_prev = price_at(S, local_ts(prev, NYC, 16, 0)); p10 = price_at(S, local_ts(day, NYC, 10, 0))
            if np.isnan(p_prev) or np.isnan(p10): continue
            r1 = p10 / p_prev - 1
            if abs(r1) < 0.0005: continue
            t_in = local_ts(day, NYC, 15, 30) if period == "m5" else local_ts(day, NYC, 15, 0)
            sig.append(dict(time=t_in, dir=int(np.sign(r1)), sl=8.0, tp=None, exit_by=local_ts(day, NYC, 16, 0)))
        return sig
    return gen


# ---------------- NH2 ----------------
LEGS = [("EURUSD", -1, 7, 12, 0.0010), ("GBPUSD", -1, 7, 12, 0.0010), ("EURUSD", 1, 13, 17, 0.0010),
        ("GBPUSD", 1, 13, 17, 0.0010), ("AUDUSD", -1, 23, 5, 0.0010), ("USDJPY", 1, 0, 6, 0.14)]


def nh2_gen(sym):
    def gen(S):
        sig = []
        for (s_, d, h0, h1, sl) in LEGS:
            if s_ != sym: continue
            for day in range(int(S.ts[0] // 86400), int(S.ts[-1] // 86400) + 1):
                t0 = day * 86400 + h0 * 3600
                t1 = (day + (1 if h1 < h0 else 0)) * 86400 + h1 * 3600
                sig.append(dict(time=t0, dir=d, sl=sl, tp=None, exit_by=t1))
        return sig
    return gen


# ---------------- NH3 ----------------
def gotobi_dates(y0, y1):
    out = []
    for y in range(y0, y1 + 1):
        for mth in range(1, 13):
            last = calendar.monthrange(y, mth)[1]
            for dd in sorted({5, 10, 15, 20, 25, last}):
                t = pd.Timestamp(y, mth, dd)
                while t.dayofweek >= 5: t -= pd.Timedelta(days=1)
                out.append(t)
    return sorted(set(out))


def nh3_gen(S):
    y0 = pd.Timestamp(S.ts[0], unit="s").year; y1 = pd.Timestamp(S.ts[-1], unit="s").year
    sig = []
    for t in gotobi_dates(y0, y1):
        t0 = int(pd.Timestamp(t, tz="UTC").timestamp())
        sig.append(dict(time=t0, dir=1, sl=0.12, tp=None, exit_by=t0 + 55 * 60))
    return sig


def run(hyp, variant, sym, period, gen, max_hold, ok, block=(16, 17, 18), seeds=10):
    engine2.entry_ok = ok
    S = get_sym(sym, period); sig = gen(S)
    tr = engine2.simulate(S, sig, max_hold, weekend_flat=True, block_hours=block)
    ctrl = []
    for sd in range(seeds):
        c = engine2.simulate(S, randomize(sig, seed=sd), max_hold, weekend_flat=True, block_hours=block)
        ctrl.append(c.pnl_usd.mean() if len(c) else np.nan)
    engine2.entry_ok = STD_OK
    if len(tr): tr["hyp"] = hyp; tr["variant"] = variant
    r = summarize(hyp, variant, sym, tr, period)
    r["rnd_avg_mean"] = float(np.nanmean(ctrl)); r["rnd_avg_p95"] = float(np.nanpercentile(ctrl, 95))
    r["max_risk_usd"] = float(tr.risk_usd.max()) if len(tr) else np.nan
    return r, tr


def main():
    rows, trades = [], []
    for period, span in [("m5", "3y M5"), ("h1", "12y H1")]:
        r, tr = run("NH1", f"US500 intraday momentum {span}", "US500", period, nh1_gen(period), 3600, allow_weekdays)
        rows.append(r); trades.append(tr)
    for period, span in [("h1", "12y H1"), ("m5", "3y M5")]:
        pool = []
        for sym in ["EURUSD", "GBPUSD", "AUDUSD", "USDJPY"]:
            r, tr = run("NH2", f"local-hours depreciation {span}", sym, period, nh2_gen(sym), 7 * 3600, STD_OK, block=(17,))
            rows.append(r); pool.append(tr)
        allt = pd.concat(pool, ignore_index=True); trades.append(allt)
        rp = summarize("NH2", f"local-hours depreciation {span}", "POOLED", allt, period); rows.append(rp)
        # per-leg breakdown
        allt["leg"] = allt.symbol + np.where(allt.dir > 0, " L ", " S ") + pd.to_datetime(allt.entry_time, unit="s").dt.hour.astype(str)
        for leg, g in allt.groupby("leg"):
            x = g.pnl_usd; print(f"   leg {leg:16s} n={len(g):5d} avg {x.mean():+.3f} PF {x[x>0].sum()/max(1e-9,-x[x<0].sum()):.2f}")
    for period, span in [("h1", "12y H1"), ("m5", "3y M5")]:
        r, tr = run("NH3", f"Gotobi USDJPY {span}", "USDJPY", period, nh3_gen, 3600, allow_weekdays)
        rows.append(r); trades.append(tr)
    pd.DataFrame(rows).to_csv(f"{OUT}/new_v1_summary.csv", index=False)
    pd.concat([t for t in trades if len(t)], ignore_index=True).to_csv(f"{OUT}/new_v1_trades.csv", index=False)


if __name__ == "__main__":
    main()
