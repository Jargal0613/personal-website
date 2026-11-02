"""Backtest of pre-registered NP1 (rules fixed in journal/hypotheses.jsonl before this ran). Data ends 2026-10-06."""
import os, sys
sys.path.insert(0, "/workspace/projects/ai-trading/research")
import numpy as np, pandas as pd
from engine2 import Sym, simulate, stats
from nf_common import randomize, tstat, OOS0, END
OUT = "/workspace/projects/ai-trading/program/backtests/results"
S = Sym("EURUSD", "m1_12y")
c = pd.read_csv("/workspace/projects/ai-trading/data/reference/econ_calendar.csv")
c = c[(c.impact == "high") & c.currency.isin(["USD", "EUR"]) & (~c.time_masked.astype(bool))]
ev = sorted(set(int(pd.Timestamp(x).timestamp()) for x in c.release_utc))
PIP = 0.0001; sigs = []; nev = 0
for T in ev:
    if T + 16 * 60 >= END: continue
    i0, i1 = S.idx(T - 60), S.idx(T + 16 * 60)
    if i1 >= len(S.ts) or S.ts[i0] != T - 60 or S.ts[i1] != T + 16 * 60: continue
    nev += 1
    m = S.o[i1] - S.o[i0]
    if abs(m) < 10 * PIP: continue
    sigs.append(dict(time=T + 16 * 60, dir=int(np.sign(m)), sl=10 * PIP, tp=20 * PIP, exit_by=T + 16 * 60 + 224 * 60))
tr = simulate(S, sigs, 240 * 60)
span_w = (min(END, S.ts[-1]) - S.ts[0]) / (7 * 86400)
def summ(t, name):
    r = stats(t, weeks=span_w); o = t[t.entry_time >= OOS0]; ro = stats(o)
    yrs = t.groupby(pd.to_datetime(t.entry_time, unit="s").dt.year).pnl_usd.sum()
    r.update(name=name, t=tstat(t.pnl_usd), oos_trades=ro.get("trades"), oos_pf=ro.get("pf"), oos_t=tstat(o.pnl_usd) if len(o) > 2 else np.nan,
             years_pos=f"{(yrs > 0).sum()}/{len(yrs)}", max_risk=t.risk_usd.max())
    return r, yrs
r, yrs = summ(tr, "NP1")
rnd = [simulate(S, randomize(sigs, seed=k), 240 * 60).pnl_usd.sum() for k in range(200)]
r["rand_p95_total"] = float(np.percentile(rnd, 95)); r["rand_mean_total"] = float(np.mean(rnd))
r["events_with_data"] = nev; r["signals"] = len(sigs)
tr.to_csv(f"{OUT}/np1_trades.csv", index=False)
pd.DataFrame([r]).to_csv(f"{OUT}/np1_summary.csv", index=False)
print(pd.Series(r).to_string()); print(yrs.round(2).to_string())
print(tr.reason.value_counts().to_string())
