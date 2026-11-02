"""Backtest of pre-registered NA1 (rules fixed in journal/hypotheses.jsonl before this ran). Data ends 2026-10-06."""
import sys
sys.path.insert(0, "/workspace/projects/ai-trading/research")
import numpy as np, pandas as pd
from engine2 import Sym, simulate, stats
from nf_common import randomize, tstat, daily_atr_at, OOS0, END
OUT = "/workspace/projects/ai-trading/program/backtests/results"
SYMS = ["EURUSD", "GBPUSD", "AUDUSD", "USDJPY"]
def gen(S, period):
    hr = (S.ts // 3600) % 24
    S.sp = np.where(hr < 7, S.sp * 2.0, S.sp)       # pre-registered Asian spread x2
    step = 300 if period == "m5" else 3600
    atr = daily_atr_at(S, 20); sigs = []
    day = S.ts // 86400
    for dd in np.unique(day):
        t0 = int(dd * 86400); dow = (dd + 3) % 7
        if dow >= 5 or t0 >= END: continue
        i0 = S.idx(t0)
        if i0 >= len(S.ts) or S.ts[i0] != t0: continue
        A = S.o[i0]; k = 0.15 * atr(t0)
        if not np.isfinite(k) or k <= 0: continue
        sl = (15 if S.sym == "USDJPY" else 10) * S.pip
        lo_close, hi_close = (t0 + 1800, t0 + 4 * 3600 + 3300) if period == "m5" else (t0 + 3600, t0 + 4 * 3600)
        prev_in = True
        j = i0
        while j < len(S.ts) - 1 and S.ts[j] < t0 + 7 * 3600:
            tclose = int(S.ts[j]) + step                    # bar j closes at its open + step
            c = S.c[j]; inside = (A - k) < c < (A + k)
            if lo_close <= tclose <= hi_close and prev_in and not inside and S.ts[j + 1] == tclose:
                d = -1 if c >= A + k else 1
                o = S.o[j + 1]
                if abs(o - A) >= 0.5 * k and np.sign(A - o) == d:
                    fill = o + S.sp[j + 1] + S.slip_in if d > 0 else o - S.slip_in
                    tp = d * (A - fill)
                    if tp > S.pip:
                        sigs.append(dict(time=tclose, dir=d, sl=sl, tp=tp, exit_by=t0 + 6 * 3600 + 3300 if period == "m5" else t0 + 7 * 3600))
            prev_in = inside; j += 1
    return sigs
def run(period):
    rows, alltr, allsig = [], [], {}
    for sym in SYMS:
        S = Sym(sym, period); sigs = gen(S, period); allsig[sym] = (S, sigs)
        tr = simulate(S, sigs, 7 * 3600); alltr.append(tr)
    tr = pd.concat(alltr, ignore_index=True).sort_values("entry_time")
    wk = (END - tr.entry_time.min()) / 604800
    r = stats(tr, weeks=wk); o = tr[tr.entry_time >= OOS0]; ro = stats(o)
    yrs = tr.groupby(pd.to_datetime(tr.entry_time, unit="s").dt.year).pnl_usd.sum()
    r.update(name=f"NA1_{period}", t=tstat(tr.pnl_usd), oos_trades=ro.get("trades"), oos_pf=ro.get("pf"),
             oos_t=tstat(o.pnl_usd), years_pos=f"{(yrs > 0).sum()}/{len(yrs)}", max_risk=tr.risk_usd.max())
    rnd = []
    for k in range(200):
        rnd.append(sum(simulate(S, randomize(sg, seed=k), 7 * 3600).pnl_usd.sum() for S, sg in allsig.values()))
    r["rand_p95_total"] = float(np.percentile(rnd, 95)); r["rand_mean_total"] = float(np.mean(rnd))
    tr.to_csv(f"{OUT}/na1_trades_{period}.csv", index=False)
    print(pd.Series(r).to_string()); print(yrs.round(2).to_string()); print(tr.reason.value_counts().to_string())
    for sym, g in tr.groupby("symbol"):
        s = stats(g); print(f"  {sym}: n={s['trades']} PF {s['pf']:.2f} total {s['total_usd']:+.2f} win {s['win_pct']:.0f}%")
    print(); return r
rows = [run("m5"), run("h1")]
pd.DataFrame(rows).to_csv(f"{OUT}/na1_summary.csv", index=False)
