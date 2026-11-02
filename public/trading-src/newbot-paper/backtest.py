"""Sanity backtest of the exact same engine (same CONFIG) on historical Yahoo hourly bars.

Usage: python3 backtest.py [range]   (range: 3mo, 6mo, 1y ... default 6mo)
This does NOT touch the paper account state.
"""
import statistics
import sys
import engine as E


def backtest(range_="6mo", bars=None, quiet=False):
    if bars is None:
        bars, _, _ = E.fetch_yahoo_hourly(range_)
    ind = E.indicators(bars)
    acct = E.Account()
    peak, maxdd, wiped_ts = E.START_BALANCE, 0.0, None
    for i in range(len(bars)):
        acct.step(bars, ind, i)
        eq = acct.balance + acct.unrealized(bars[i]["c"])
        peak = max(peak, eq)
        maxdd = max(maxdd, (peak - eq) / peak if peak > 0 else 0)
        if wiped_ts is None and not acct.state["position"] and \
                acct.balance - E.MIN_LOT_UNITS * E.HALF_SPREAD < E.margin_required(E.MIN_LOT_UNITS, bars[i]["c"]):
            wiped_ts = bars[i]["ts"]
    trades = acct.closed
    final_eq = acct.balance + acct.unrealized(bars[-1]["c"])
    wins = [t for t in trades if t["pnl"] > 0]
    gross_w = sum(t["pnl"] for t in wins)
    gross_l = -sum(t["pnl"] for t in trades if t["pnl"] <= 0)
    stopouts = [t for t in trades if t["exit_reason"].startswith("STOP-OUT")]
    risk = [t["risk_pct"] for t in trades]
    floored = sum(1 for t in trades if "floored" in t["sizing_note"])
    reasons = {}
    for t in trades:
        k = t["exit_reason"].split(" (")[0]
        reasons[k] = reasons.get(k, 0) + 1
    res = {
        "range": range_, "start": bars[0]["ts"], "end": bars[-1]["ts"], "bars": len(bars),
        "trades": len(trades), "wins": len(wins), "final_eq": final_eq,
        "ret": (final_eq / E.START_BALANCE - 1) * 100, "maxdd": maxdd * 100,
        "pf": gross_w / gross_l if gross_l else float("inf"),
        "stopouts": [E.fmt_ts(t["exit_ts"]) for t in stopouts], "wiped": wiped_ts,
        "skipped": len(acct.skipped), "risk": risk, "floored": floored, "reasons": reasons,
    }
    if not quiet:
        print(f"BACKTEST {E.SYMBOL} 1h, range={range_}: {E.fmt_ts(res['start'])} -> {E.fmt_ts(res['end'])}, "
              f"{len(bars)} bars (first {E.WARMUP_BARS} = warm-up)")
        print(f"  config: start ${E.START_BALANCE:,.2f}, 1:{E.LEVERAGE}, min lot {E.lots(E.MIN_LOT_UNITS):.2f}, "
              f"step {E.lots(E.LOT_STEP_UNITS):.2f}, target risk {E.RISK_PER_TRADE:.1%}, stop-out {E.STOP_OUT_LEVEL:.0%}")
        print(f"  closed trades: {len(trades)}  wins: {len(wins)}  win rate: "
              f"{(len(wins) / len(trades) * 100 if trades else 0):.1f}%  profit factor: {res['pf']:.2f}")
        print(f"  final equity: ${final_eq:,.2f}  ({res['ret']:+.2f}%)   max drawdown (bar closes): {res['maxdd']:.2f}%")
        if risk:
            print(f"  actual risk per trade (% of equity at entry): median {statistics.median(risk):.1f}%, "
                  f"min {min(risk):.1f}%, max {max(risk):.1f}%;  {floored}/{len(trades)} trades floored to min lot")
        print(f"  margin stop-outs: {len(stopouts)} {res['stopouts']}")
        print(f"  wiped out (can't afford min lot): {E.fmt_ts(wiped_ts) if wiped_ts else 'no'};  "
              f"signals skipped for margin: {len(acct.skipped)}")
        print(f"  exits: {reasons}   open at end: {bool(acct.state['position'])}")
    return res


if __name__ == "__main__":
    backtest(sys.argv[1] if len(sys.argv) > 1 else "6mo")
