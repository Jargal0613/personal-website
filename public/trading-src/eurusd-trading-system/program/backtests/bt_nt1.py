"""Backtest of pre-registered NT1 (rules fixed in journal/hypotheses.jsonl before this ran). Data ends 2026-10-06."""
import json, sys
sys.path.insert(0, "/workspace/projects/ai-trading/research")
import numpy as np, pandas as pd
from engine2 import Sym, simulate, stats, entry_ok
from nf_common import randomize, tstat, OOS0, END
OUT = "/workspace/projects/ai-trading/program/backtests/results"
d = json.load(open(f"{OUT}/treasury_coupon_auctions_2014_2026.json"))["data"]
ev = {}
for r in d:
    if r["floating_rate"] != "No" or r["inflation_index_security"] != "No": continue
    t = pd.Timestamp(f"{r['auction_date']} {r['closing_time_comp']}", tz="America/New_York")
    ev[r["auction_date"]] = max(ev.get(r["auction_date"], t), t)
ev = sorted(ev.values())
def run(period, step):
    S = Sym("USDJPY", period); PIP = S.pip; sigs = []
    for T in ev:
        t0 = int((T + pd.Timedelta(minutes=5)).timestamp())
        if t0 >= END or t0 < S.ts[0]: continue
        i = S.idx(t0)
        if i >= len(S.ts) or S.ts[i] - t0 >= step: continue
        te = int(S.ts[i])
        if not entry_ok(te): continue
        xb = int(T.normalize().replace(hour=16, minute=45).timestamp()) if False else int(pd.Timestamp(T.date()).tz_localize("America/New_York").replace(hour=16, minute=45).timestamp())
        if xb <= te: continue
        sigs.append(dict(time=te, dir=-1, sl=14 * PIP, tp=28 * PIP, exit_by=xb))
    tr = simulate(S, sigs, 6 * 3600)
    wk = (min(END, S.ts[-1]) - S.ts[0]) / 604800
    r = stats(tr, weeks=wk); o = tr[tr.entry_time >= OOS0]; ro = stats(o)
    yrs = tr.groupby(pd.to_datetime(tr.entry_time, unit="s").dt.year).pnl_usd.sum()
    r.update(name=f"NT1_{period}", t=tstat(tr.pnl_usd), oos_trades=ro.get("trades"), oos_pf=ro.get("pf"),
             oos_t=tstat(o.pnl_usd) if len(o) > 2 else np.nan, years_pos=f"{(yrs > 0).sum()}/{len(yrs)}",
             max_risk=tr.risk_usd.max(), total_usd=tr.pnl_usd.sum(), signals=len(sigs))
    rnd = [simulate(S, randomize(sigs, seed=k), 6 * 3600).pnl_usd.sum() for k in range(500)]
    r["rand_p95_total"] = float(np.percentile(rnd, 95)); r["rand_mean_total"] = float(np.mean(rnd))
    tr.to_csv(f"{OUT}/nt1_trades_{period}.csv", index=False)
    print(pd.Series(r).to_string()); print(yrs.round(2).to_string()); print(tr.reason.value_counts().to_string()); print()
    return r
rows = [run("m5", 300), run("h1", 3600)]
pd.DataFrame(rows).to_csv(f"{OUT}/nt1_summary.csv", index=False)
