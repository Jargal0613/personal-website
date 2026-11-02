"""Backtest of pre-registered NR1 (rules fixed in journal/hypotheses.jsonl before this ran). Data ends 2026-10-06."""
import sys
sys.path.insert(0, "/workspace/projects/ai-trading/research")
import numpy as np, pandas as pd
from engine2 import Sym, simulate, stats
from nf_common import randomize, tstat, OOS0, END
OUT = "/workspace/projects/ai-trading/program/backtests/results"

def gen(S, period):
    step = 300 if period == "m5" else 3600
    df = pd.DataFrame({"o": S.o, "h": S.h, "l": S.l, "c": S.c}, index=S.ts)
    ny = pd.to_datetime(df.index, unit="s", utc=True).tz_convert("America/New_York")
    df["hm"] = ny.hour * 100 + ny.minute; df["date"] = ny.date; df["dow"] = ny.dayofweek
    first_hm, exit_h = (930, 15 * 60 + 55) if period == "m5" else (900, 16 * 60)
    sigs, skipped, doji = [], 0, 0
    for t0, r in df[(df.hm == first_hm) & (df.dow < 5)].iterrows():
        t1 = int(t0) + step
        if t1 not in df.index or t1 >= END: continue
        if r.c == r.o: doji += 1; continue
        d = 1 if r.c > r.o else -1
        o1 = df.at[t1, "o"]
        dist = max((o1 - r.l) if d > 0 else (r.h - o1), 2.0)
        if dist > 10.0: skipped += 1; continue
        day = pd.Timestamp(t1, unit="s", tz="UTC").tz_convert("America/New_York").normalize()
        cut = int((day + pd.Timedelta(minutes=exit_h)).timestamp())
        sigs.append(dict(time=t1, dir=d, sl=dist, tp=None, exit_by=cut))
    return sigs, skipped, doji

def run(period):
    S = Sym("US500", period); sigs, skipped, doji = gen(S, period)
    tr = simulate(S, sigs, 8 * 3600).sort_values("entry_time")
    wk = (END - tr.entry_time.min()) / 604800
    r = stats(tr, weeks=wk); o = tr[tr.entry_time >= OOS0]; ro = stats(o)
    yrs = tr.groupby(pd.to_datetime(tr.entry_time, unit="s").dt.year).pnl_usd.sum()
    r.update(name=f"NR1_{period}", t=tstat(tr.pnl_usd), oos_trades=ro.get("trades"), oos_pf=ro.get("pf"),
             oos_t=tstat(o.pnl_usd), years_pos=f"{(yrs > 0).sum()}/{len(yrs)}", max_risk=tr.risk_usd.max(),
             skipped_wide=skipped, doji=doji, signals=len(sigs))
    rnd = [simulate(S, randomize(sigs, seed=k), 8 * 3600).pnl_usd.sum() for k in range(300)]
    r["rand_p95_total"] = float(np.percentile(rnd, 95)); r["rand_mean_total"] = float(np.mean(rnd))
    tr.to_csv(f"{OUT}/nr1_trades_{period}.csv", index=False)
    print(pd.Series(r).to_string()); print(yrs.round(2).to_string()); print(tr.reason.value_counts().to_string())
    for d, g in tr.groupby("dir"):
        s = stats(g); print(f"  dir {d:+d}: n={s['trades']} PF {s['pf']:.2f} total {s['total_usd']:+.2f} win {s['win_pct']:.0f}%")
    print(); return r
rows = [run("m5"), run("h1")]
pd.DataFrame(rows).to_csv(f"{OUT}/nr1_summary.csv", index=False)
