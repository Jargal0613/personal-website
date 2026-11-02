"""Forward-test statistics for the paper program: per-hypothesis stats, the promotion test (RISK_LIMITS s8) and
the kill status. Reads journal/trades.csv and journal/shadows.csv (both written by engine.py)."""
import csv
import math
import os
import random

import risk as R

P = os.path.dirname(os.path.abspath(__file__))
TRADES = os.path.join(P, "journal", "trades.csv")
SHADOWS = os.path.join(P, "journal", "shadows.csv")
TRADE_COLS = ["trade_id", "hyp", "version", "sym", "dir", "units", "t_in", "entry", "sl", "tp", "t_out", "exit", "reason",
              "gross_usd", "comm_usd", "swap_usd", "pnl_usd", "risk_usd", "equity_after"]
SHADOW_COLS = ["trade_id", "hyp", "version", "sym", "dir", "units", "t_in", "entry", "t_out", "exit", "reason", "pnl_usd"]


def _read(path):
    if not os.path.exists(path): return []
    with open(path) as f: return list(csv.DictReader(f))


def append_row(path, cols, row):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new: w.writeheader()
        w.writerow({k: row.get(k) for k in cols})


def trades(hyp=None, version=None):
    out = []
    for r in _read(TRADES):
        if hyp and r["hyp"] != hyp: continue
        if version is not None and int(r["version"]) != int(version): continue
        for k in ("t_in", "t_out", "units", "pnl_usd", "risk_usd", "gross_usd", "comm_usd", "swap_usd", "equity_after"):
            r[k] = float(r[k]) if r.get(k) not in (None, "") else None
        out.append(r)
    return out


def shadows():
    d = {}
    for r in _read(SHADOWS):
        d.setdefault(r["trade_id"], {})[int(r["dir"])] = float(r["pnl_usd"])
    return d


def summary(pnls):
    n = len(pnls)
    if n == 0: return dict(n=0, net=0.0, pf=None, win=None, t=None, avg=None, max_dd_pct=0.0)
    w = sum(x for x in pnls if x > 0); l = -sum(x for x in pnls if x < 0)
    mean = sum(pnls) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in pnls) / (n - 1)) if n > 1 else 0.0
    eq = R.START_EQUITY; peak = eq; mdd = 0.0
    for x in pnls:
        eq += x; peak = max(peak, eq); mdd = max(mdd, (peak - eq) / peak if peak > 0 else 0)
    return dict(n=n, net=sum(pnls), pf=(w / l if l > 0 else (float("inf") if w > 0 else None)), win=sum(1 for x in pnls if x > 0) / n,
                t=(mean / (sd / math.sqrt(n)) if sd > 0 else None), avg=mean, max_dd_pct=mdd)


def promotion(hyp, version, now):
    tr = trades(hyp, version)
    pn = [t["pnl_usd"] for t in tr]
    s = summary(pn)
    days = (now - min(t["t_in"] for t in tr)) / 86400 if tr else 0.0
    sh = shadows(); pairs = [(sh.get(t["trade_id"], {}).get(1), sh.get(t["trade_id"], {}).get(-1)) for t in tr]
    complete = [p for p in pairs if p[0] is not None and p[1] is not None]
    ctrl_p95 = None
    if len(complete) == len(tr) and tr:
        rng = random.Random(8); tot = []
        for _ in range(R.PROMO["ctrl_draws"]):
            tot.append(sum(p[0] if rng.random() < 0.5 else p[1] for p in complete))
        tot.sort(); ctrl_p95 = tot[int(0.95 * len(tot)) - 1]
    P_ = R.PROMO
    crit = {
        "trades>=30": s["n"] >= P_["min_trades"],
        "days>=14": days >= P_["min_days"],
        "net>0": s["net"] > 0,
        "PF>=1.3": (s["pf"] or 0) >= P_["min_pf"],
        "beats_random_dir_p95": ctrl_p95 is not None and s["net"] > ctrl_p95,
        "t>=2": (s["t"] or -9) >= P_["min_t"],
        "maxDD<35%": s["max_dd_pct"] < P_["max_dd_pct"],
    }
    return dict(hyp=hyp, version=version, days=days, ctrl_p95=ctrl_p95, criteria=crit, promoted=all(crit.values()), **s)
