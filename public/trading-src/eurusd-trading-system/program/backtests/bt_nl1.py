"""Backtest of pre-registered NL1 (rules fixed in journal/hypotheses.jsonl before this ran). Data ends 2026-10-06."""
import sys
sys.path.insert(0, "/workspace/projects/ai-trading/research")
import numpy as np, pandas as pd
from engine2 import Sym, simulate, stats
from nf_common import randomize, tstat, OOS0, END
OUT = "/workspace/projects/ai-trading/program/backtests/results"
FXS = ["AUDUSD", "USDJPY"]

def zframe(S, period):
    step = 300 if period == "m5" else 3600
    lag = 3 if period == "m5" else 1
    df = pd.DataFrame({"c": S.c}, index=S.ts)
    prev_t = df.index - lag * step
    prev_c = df.c.reindex(prev_t).to_numpy()
    df["r"] = np.log(df.c.to_numpy() / prev_c)
    close_ny = pd.to_datetime(df.index + step, unit="s", utc=True).tz_convert("America/New_York")
    mins = close_ny.hour * 60 + close_ny.minute
    lo, hi = (9 * 60 + 45, 15 * 60 + 30) if period == "m5" else (11 * 60, 15 * 60)
    df["win"] = (mins >= lo) & (mins <= hi) & (close_ny.dayofweek < 5)
    df["date"] = close_ny.date
    w = df[df.win & df.r.notna()]
    g = w.groupby("date").r.agg(n="count", s="sum", ss=lambda x: (x ** 2).sum())
    roll = g.rolling(20, min_periods=20).sum().shift(1)
    sd = np.sqrt((roll.ss - roll.s ** 2 / roll.n) / (roll.n - 1))
    df["sd"] = df.date.map(sd)
    df["z"] = df.r / df.sd
    return df

def gen(U, X, period):
    step = 300 if period == "m5" else 3600
    zu, zx = zframe(U, period), zframe(X, period)
    j = zu[["z", "win"]].join(zx[["z"]], rsuffix="x", how="inner").rename(columns={"z": "zu", "zx": "zx"})
    q = j.win & (j.zu.abs() >= 2.0) & (j.zx * np.sign(j.zu) <= 0.5)
    q = q & ~q.shift(1, fill_value=False) if period == "m5" else q
    xts = set(X.ts.tolist()); sigs = []
    pip = X.pip; sl = (15 if X.sym == "USDJPY" else 10) * pip
    for t, row in j[q].iterrows():
        te = int(t) + step
        if te not in xts or te >= END: continue
        ny = pd.Timestamp(te, unit="s", tz="UTC").tz_convert("America/New_York")
        cut = int(ny.normalize().replace(hour=15, minute=55).timestamp()) if period == "m5" else int(ny.normalize().replace(hour=16).timestamp())
        sigs.append(dict(time=te, dir=int(np.sign(row.zu)), sl=sl, tp=None, exit_by=min(te + 3600, cut)))
    return sigs

def run(period):
    U = Sym("US500", period); alltr, allsig = [], {}
    for sym in FXS:
        X = Sym(sym, period); sigs = gen(U, X, period); allsig[sym] = (X, sigs)
        alltr.append(simulate(X, sigs, 3600))
    tr = pd.concat(alltr, ignore_index=True).sort_values("entry_time")
    wk = (END - tr.entry_time.min()) / 604800
    r = stats(tr, weeks=wk); o = tr[tr.entry_time >= OOS0]; ro = stats(o)
    yrs = tr.groupby(pd.to_datetime(tr.entry_time, unit="s").dt.year).pnl_usd.sum()
    r.update(name=f"NL1_{period}", t=tstat(tr.pnl_usd), oos_trades=ro.get("trades"), oos_pf=ro.get("pf"),
             oos_t=tstat(o.pnl_usd), years_pos=f"{(yrs > 0).sum()}/{len(yrs)}", max_risk=tr.risk_usd.max())
    rnd = [sum(simulate(X, randomize(sg, seed=k), 3600).pnl_usd.sum() for X, sg in allsig.values()) for k in range(200)]
    r["rand_p95_total"] = float(np.percentile(rnd, 95)); r["rand_mean_total"] = float(np.mean(rnd))
    tr.to_csv(f"{OUT}/nl1_trades_{period}.csv", index=False)
    print(pd.Series(r).to_string()); print(yrs.round(2).to_string()); print(tr.reason.value_counts().to_string())
    for sym, g in tr.groupby("symbol"):
        s = stats(g); print(f"  {sym}: n={s['trades']} PF {s['pf']:.2f} total {s['total_usd']:+.2f} win {s['win_pct']:.0f}%")
    print(); return r
rows = [run("m5"), run("h1")]
pd.DataFrame(rows).to_csv(f"{OUT}/nl1_summary.csv", index=False)
