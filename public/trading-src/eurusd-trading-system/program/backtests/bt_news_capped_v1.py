"""Backtest N4C / E1C (risk-cap-compatible variants of N4B / E1) with the Round-6 measured news cost model.
Research only. Output: program/backtests/results/news_capped_v1.csv + trades."""
import os
import sys

R = "/workspace/projects/ai-trading/research"
sys.path.insert(0, R); os.chdir(R)
import numpy as np
import pandas as pd
import news_cost_report as NC
import news_strategies as NS
from news_common import M1

OUT = "/workspace/projects/ai-trading/program/backtests/results"; os.makedirs(OUT, exist_ok=True)
OOS0 = pd.Timestamp("2024-10-06", tz="UTC").timestamp()
CAP = 9.0


def st(x):
    x = np.asarray(x, float)
    if len(x) < 3: return dict(n=len(x))
    w, l = x[x > 0].sum(), -x[x < 0].sum()
    return dict(n=len(x), avg=x.mean(), pf=w / l if l > 0 else np.inf, t=x.mean() / x.std(ddof=1) * np.sqrt(len(x)))


hist = NC.per_release_hist()
_, _, _, arr = NC.analyse(hist, "history")
keys, SP, SLB, SLS = arr
tier = NC.make_tier(keys, SP, SLB, SLS, 75)[0]
m = M1(); ev = pd.read_csv(os.path.join(NC.REF, "news_event_moves.csv"))
S = NC.strategies_with(m, ev, tier)
sigs = {"N4C": [dict(s, sl=min(s["sl"], CAP), tp=2 * min(s["sl"], CAP)) for s in S["N4B"]],
        "E1C": [dict(s, sl=min(s["sl"], CAP)) for s in S["E1"]]}
rows = []
for sid, sig in sigs.items():
    tr = NS.run(m, sig)
    tr.to_csv(f"{OUT}/news_capped_trades_{sid}.csv", index=False)
    y = pd.to_datetime(tr.entry_time, unit="s").dt.year; by = tr.groupby(y).pnl_usd.sum()
    a = st(tr.pnl_usd); o = st(tr[tr.entry_time >= OOS0].pnl_usd)
    rnd = [NS.run(m, sig, seed=s).pnl_usd.mean() for s in range(20)]
    r = dict(id=sid, trades=a.get("n"), avg_usd=a.get("avg"), pf=a.get("pf"), t=a.get("t"), oos_trades=o.get("n"),
             oos_avg=o.get("avg"), oos_pf=o.get("pf"), oos_t=o.get("t"), max_risk_usd=tr.risk_usd.max(), avg_risk_usd=tr.risk_usd.mean(),
             years_pos=f"{(by > 0).sum()}/{len(by)}", rnd_avg_mean20=np.mean(rnd), rnd_avg_p95=np.percentile(rnd, 95),
             pnl_by_year=" ".join(f"{k}:{v:+.1f}" for k, v in by.items()))
    rows.append(r); print(r, flush=True)
pd.DataFrame(rows).to_csv(f"{OUT}/news_capped_v1.csv", index=False)
