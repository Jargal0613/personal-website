"""Post-hoc NO1 diagnostic (decision rule journaled first): H1 pure-overnight proxy, entry 16:00 NY H1 open, exit 09:00 NY H1 open."""
import sys
sys.path.insert(0, "/workspace/projects/ai-trading/research")
import numpy as np, pandas as pd
from engine2 import Sym, simulate, stats
from nf_common import randomize, tstat, OOS0, END
OUT = "/workspace/projects/ai-trading/program/backtests/results"
def run(period, eh, em, xh, xm):
    S = Sym("US500", period)
    have = set(S.ts.tolist()); sigs = []
    days = pd.date_range(pd.Timestamp(S.ts[0], unit="s").date(), "2026-10-05", freq="D")
    for d in days:
        if d.dayofweek > 3: continue
        te = int(pd.Timestamp(d.date()).tz_localize("America/New_York").replace(hour=eh, minute=em).timestamp())
        nd = d + pd.Timedelta(days=1)
        tx = int(pd.Timestamp(nd.date()).tz_localize("America/New_York").replace(hour=xh, minute=xm).timestamp())
        if te not in have or tx not in have or tx >= END: continue
        sigs.append(dict(time=te, dir=1, sl=10.0, tp=None, exit_by=tx))
    tr = simulate(S, sigs, 20 * 3600, block_hours=(17,))
    wk = (min(END, S.ts[-1]) - S.ts[0]) / 604800
    r = stats(tr, weeks=wk); o = tr[tr.entry_time >= OOS0]; ro = stats(o)
    yrs = tr.groupby(pd.to_datetime(tr.entry_time, unit="s").dt.year).pnl_usd.sum()
    r.update(name=f"NO1_{period}", t=tstat(tr.pnl_usd), oos_trades=ro.get("trades"), oos_pf=ro.get("pf"),
             oos_t=tstat(o.pnl_usd) if len(o) > 2 else np.nan, years_pos=f"{(yrs > 0).sum()}/{len(yrs)}",
             max_risk=tr.risk_usd.max(), total_usd=tr.pnl_usd.sum(), swap_total=tr.swap_usd.sum(), signals=len(sigs),
             gross_ex_swap=(tr.pnl_usd - tr.swap_usd).sum())
    rnd = [simulate(S, randomize(sigs, seed=k), 20 * 3600, block_hours=(17,)).pnl_usd.sum() for k in range(300)]
    r["rand_p95_total"] = float(np.percentile(rnd, 95)); r["rand_mean_total"] = float(np.mean(rnd))
    tr.to_csv(f"{OUT}/no1_diag_trades_{period}.csv", index=False)
    print(pd.Series(r).to_string()); print(yrs.round(2).to_string()); print(tr.reason.value_counts().to_string()); print()
    return r
rows = [run("h1", 16, 0, 9, 0)]
pd.DataFrame(rows).to_csv(f"{OUT}/no1_diag_summary.csv", index=False)
