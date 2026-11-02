"""Backtest of pre-registered NF1 (rules fixed in journal/hypotheses.jsonl before this ran). Data ends 2026-10-06."""
import sys
sys.path.insert(0, "/workspace/projects/ai-trading/research")
import numpy as np, pandas as pd
from engine2 import Sym, simulate, stats
from nf_common import randomize, tstat, OOS0, END
OUT = "/workspace/projects/ai-trading/program/backtests/results"
PAIRS = {"EURUSD": (1, 10), "USDJPY": (-1, 15)}

def frame(S):
    df = pd.DataFrame({"o": S.o}, index=S.ts)
    ld = pd.to_datetime(df.index, unit="s", utc=True).tz_convert("Europe/London")
    df["hm"] = ld.hour * 100 + ld.minute; df["dow"] = ld.dayofweek; df["date"] = ld.date
    return df

def gen(S, period, d):
    pip_stop = PAIRS[S.sym][1] * S.pip
    df = frame(S); step = 300 if period == "m5" else 3600
    ehm = 1605 if period == "m5" else 1600
    sigs = []
    for t, r in df[(df.hm == ehm) & (df.dow < 5)].iterrows():
        t = int(t)
        if t >= END: continue
        sigs.append(dict(time=t, dir=d, sl=pip_stop, tp=None, exit_by=t + 3600))
    return sigs

def prefix_diag(S, d):
    df = frame(S)
    a = df[(df.hm == 1500) & (df.dow < 5)]; b = df[(df.hm == 1600) & (df.dow < 5)]
    j = pd.Series(a.o.values, index=a.date.values).to_frame("o15").join(pd.Series(b.o.values, index=b.date.values).to_frame("o16"), how="inner")
    usd = -d * (j.o16 - j.o15) / S.pip  # positive = USD appreciated (pips)
    return dict(n=len(usd), mean_pips=usd.mean(), t=tstat(usd))

def run(period):
    alltr, allsig = [], {}
    for sym, (d, _) in PAIRS.items():
        S = Sym(sym, period); sg = gen(S, period, d); allsig[sym] = (S, sg)
        alltr.append(simulate(S, sg, 3600))
        print(period, sym, "pre-fix USD leg 15:00->16:00 London:", prefix_diag(S, d))
    tr = pd.concat(alltr, ignore_index=True).sort_values("entry_time")
    wk = (END - tr.entry_time.min()) / 604800
    r = stats(tr, weeks=wk); o = tr[tr.entry_time >= OOS0]; ro = stats(o)
    yrs = tr.groupby(pd.to_datetime(tr.entry_time, unit="s").dt.year).pnl_usd.sum()
    r.update(name=f"NF1_{period}", t=tstat(tr.pnl_usd), oos_trades=ro.get("trades"), oos_pf=ro.get("pf"),
             oos_t=tstat(o.pnl_usd), years_pos=f"{(yrs > 0).sum()}/{len(yrs)}", max_risk=tr.risk_usd.max())
    rnd = [sum(simulate(S, randomize(sg, seed=k), 3600).pnl_usd.sum() for S, sg in allsig.values()) for k in range(200)]
    r["rand_p95_total"] = float(np.percentile(rnd, 95)); r["rand_mean_total"] = float(np.mean(rnd))
    tr.to_csv(f"{OUT}/nf1_trades_{period}.csv", index=False)
    print(pd.Series(r).to_string()); print(yrs.round(2).to_string()); print(tr.reason.value_counts().to_string())
    for sym, g in tr.groupby("symbol"):
        s = stats(g); print(f"  {sym}: n={s['trades']} PF {s['pf']:.2f} total {s['total_usd']:+.2f} win {s['win_pct']:.0f}% avg_gross_pips n/a")
    print(); return r
rows = [run("m5"), run("h1")]
pd.DataFrame(rows).to_csv(f"{OUT}/nf1_summary.csv", index=False)
