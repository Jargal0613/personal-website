"""Read-only daily report: live PAPER results vs frozen backtest.

Usage:  .venv/bin/python trading/daily_report.py      (run from project root or anywhere)

Reads only. Never writes files, never connects to cTrader.
"""
import csv
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
TRADES = os.path.join(DATA, "live_paper_trades.csv")
SIGNALS = os.path.join(DATA, "live_paper_signals.csv")
BACKTEST = os.path.join(DATA, "reference", "nonoverlap_frozen_results.csv")
# Frozen backtest dataset facts (data/market_structure_features.csv, now in
# /workspace/projects/ai-trading-archive-20261006.tar.gz): 50000 M1 bars,
# 2026-08-14 -> 2026-10-02 UTC, mean open price 1.15425.
BT_BARS = 50000
BT_DAYS = 48.94
BT_MEAN_PRICE = 1.15425
LOG = os.path.join(DATA, "live_paper.log")
PID = os.path.join(DATA, "live_paper.pid")
SUP_PID = os.path.join(DATA, "live_paper_supervisor.pid")

STRATEGY = "Large 5m range"      # live_paper.py: range_5m > 0.000326, SHORT
INITIAL_EQUITY = 10.00           # live_paper.py INITIAL_EQUITY
PIP = 0.0001
REALISTIC_COST_PCT = 0.005       # ~0.56 pip round trip at 1.13 (spread ~0.1 + commission ~0.6)
EST_COMMISSION_PIPS = 0.6        # Pepperstone demo EURUSD: $3/lot/side (Open API symbol info) -> 0.6 pip RT
UB = timezone(timedelta(hours=8))  # Asia/Ulaanbaatar


def parse_ts(s):
    s = s.strip()
    if re.fullmatch(r"\d+", s):
        return datetime.fromtimestamp(int(s), timezone.utc)
    return datetime.fromisoformat(s)


def fmt(dt):
    if dt is None:
        return "n/a"
    return f"{dt.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC ({dt.astimezone(UB):%m-%d %H:%M} UB)"


def pid_alive(path):
    try:
        pid = int(open(path).read().strip())
        os.kill(pid, 0)
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmd = f.read().replace(b"\0", b" ").decode(errors="replace").strip()
        start_ticks = int(open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[19])
        boot = float(open("/proc/uptime").read().split()[0])
        age = boot - start_ticks / os.sysconf("SC_CLK_TCK")
        return pid, cmd, timedelta(seconds=int(age))
    except Exception:
        return None


def load_trades():
    rows = []
    with open(TRADES, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["n"] = int(r["trade"])
            r["exit_dt"] = parse_ts(r["exit_time"])
            r["entry_dt"] = parse_ts(r["entry_time"])
            r["net"] = float(r["net_pips"])
            r["gross"] = float(r["gross_pips"])
            r["pnl"] = float(r["pnl_usd"])
            r["spread_pips"] = float(r["spread_entry"] or 0) / PIP
            rows.append(r)
    # Session = run of the script. live_paper.py restarts numbering at 1 and
    # equity at $10 on every start, so detect resets and chain equity.
    session, prev, eq = 1, None, INITIAL_EQUITY
    for r in rows:
        if prev is not None and r["n"] <= prev:
            session += 1
        r["session"] = session
        prev = r["n"]
        eq += r["pnl"]
        r["chained_equity"] = eq
    return rows


def metrics(rows, start_equity):
    if not rows:
        return None
    nets = [r["net"] for r in rows]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x < 0]
    pf = (sum(wins) / -sum(losses)) if losses else float("inf")
    eq, peak, mdd_usd, mdd_pips, cum, cpeak = start_equity, start_equity, 0.0, 0.0, 0.0, 0.0
    for r in rows:
        eq += r["pnl"]; peak = max(peak, eq); mdd_usd = min(mdd_usd, eq - peak)
        cum += r["net"]; cpeak = max(cpeak, cum); mdd_pips = min(mdd_pips, cum - cpeak)
    after_comm = [x - EST_COMMISSION_PIPS for x in nets]
    aw = sum(x for x in after_comm if x > 0); al = -sum(x for x in after_comm if x < 0)
    return {
        "trades": len(rows),
        "win_rate": 100 * len(wins) / len(rows),
        "net_pips": sum(nets),
        "gross_pips": sum(r["gross"] for r in rows),
        "avg_pips": sum(nets) / len(rows),
        "pf": pf,
        "start_equity": start_equity,
        "equity": eq,
        "mdd_usd": mdd_usd,
        "mdd_pips": mdd_pips,
        "exits": Counter(r["exit_reason"] for r in rows),
        "avg_spread": sum(r["spread_pips"] for r in rows) / len(rows),
        "net_after_comm": sum(after_comm),
        "pf_after_comm": (aw / al) if al else float("inf"),
        "first": min(r["entry_dt"] for r in rows),
        "last": max(r["exit_dt"] for r in rows),
    }


def print_metrics(title, m):
    print(f"\n--- {title}")
    if m is None:
        print("  no closed trades")
        return
    pf = "inf" if m["pf"] == float("inf") else f"{m['pf']:.2f}"
    pfc = "inf" if m["pf_after_comm"] == float("inf") else f"{m['pf_after_comm']:.2f}"
    print(f"  trades        {m['trades']}   ({fmt(m['first'])} -> {fmt(m['last'])})")
    print(f"  win rate      {m['win_rate']:.1f}%")
    print(f"  net pips      {m['net_pips']:+.1f}  (gross {m['gross_pips']:+.1f}, avg {m['avg_pips']:+.2f}/trade, avg logged spread {m['avg_spread']:.2f} pip)")
    print(f"  profit factor {pf}")
    print(f"  equity        ${m['start_equity']:.3f} -> ${m['equity']:.3f}  ({m['equity'] - m['start_equity']:+.3f})")
    print(f"  max drawdown  ${m['mdd_usd']:.3f}  ({m['mdd_pips']:.1f} pips)")
    print(f"  exit reasons  " + ", ".join(f"{k}={v}" for k, v in m["exits"].most_common()))
    print(f"  after est. commission ({EST_COMMISSION_PIPS} pip/trade, NOT modelled by live_paper.py): "
          f"net {m['net_after_comm']:+.1f} pips, PF {pfc}")


def backtest_section():
    rows = [r for r in csv.DictReader(open(BACKTEST, newline="")) if r["strategy"] == STRATEGY]
    n, days, price = BT_BARS, BT_DAYS, BT_MEAN_PRICE
    pct_to_pips = price / 100 / PIP
    print(f"\n=== FROZEN BACKTEST: {STRATEGY} (data/reference/nonoverlap_frozen_results.csv)")
    print("  rules: SHORT next-bar open when range_5m > 0.000326, exit at open after 120 min, "
          "one position at a time, NO stop loss")
    print("  NOTE: live_paper.py adds a 5-pip stop -> not like-for-like; compare direction/size of edge only.")
    if days:
        print(f"  dataset: {n} M1 bars over {days:.1f} calendar days; mean price {price:.5f} "
              f"(1% return ~= {pct_to_pips:.0f} pips)")
    for r in rows:
        c = float(r["cost_percent"])
        if c not in (0.0, REALISTIC_COST_PCT, 0.01):
            continue
        label = {0.0: "0% cost", REALISTIC_COST_PCT: "realistic", 0.01: "pessimistic"}[c]
        t = int(r["trades"])
        tpd = f", {t / days:.1f} trades/cal-day" if days else ""
        print(f"  cost {c:.3f}% (~{c * pct_to_pips:.2f} pip, {label}): trades {t}{tpd}, "
              f"win {float(r['win_rate']):.1f}%, avg {float(r['avg_return']) * pct_to_pips:+.2f} pips/trade, "
              f"total {float(r['total_return']) * pct_to_pips:+.0f} pips, PF {float(r['profit_factor']):.2f}, "
              f"maxDD {float(r['max_drawdown']) * pct_to_pips:.0f} pips")
    return days


def signals_section(now):
    with open(SIGNALS, newline="", encoding="utf-8") as f:
        lines = list(csv.reader(f))
    data = []
    for r in lines[1:]:
        if not r:
            continue
        # old rows: ts,range,bid,ask,spread,signal ; current: ts,range,threshold,bid,ask,spread,signal
        if len(r) == 7:
            ts, rng, _, bid, ask, spr, sig = r
        else:
            ts, rng, bid, ask, spr, sig = r
        data.append((parse_ts(ts), float(rng), bid, ask, spr, sig))
    last = data[-1] if data else None
    mtime = datetime.fromtimestamp(os.path.getmtime(SIGNALS), timezone.utc)
    print("\n=== SIGNALS (data/live_paper_signals.csv)")
    if lines and len(lines[0]) != 7:
        print(f"  note: header has {len(lines[0])} columns but current rows have 7 (extra 'threshold' column "
              "after range_5m); header predates that change")
    if last:
        age = now - mtime
        print(f"  last row: candle {fmt(last[0])}, bid {last[2]}, ask {last[3]}, spread {last[4]}, {last[5]}")
        print(f"  file last written: {fmt(mtime)}  ({int(age.total_seconds() // 60)} min ago)")
    recent = [d for d in data if d[0] >= now - timedelta(hours=24)]
    for title, sub in (("all", data), ("last 24h", recent)):
        if not sub:
            print(f"  {title}: 0 rows"); continue
        spreads = []
        for d in sub:
            try:
                spreads.append(float(d[4]))
            except ValueError:
                pass
        zero = sum(1 for x in spreads if x == 0)
        shorts = sum(1 for d in sub if d[5] == "SHORT")
        print(f"  {title}: {len(sub)} rows, SHORT {100 * shorts / len(sub):.0f}%, "
              f"spread==0 in {100 * zero / max(1, len(spreads)):.0f}%, "
              f"median spread {sorted(spreads)[len(spreads) // 2] / PIP:.1f} pip")


def open_position_from_log():
    if not os.path.exists(LOG):
        return None
    txt = open(LOG, encoding="utf-8", errors="replace").read()
    idx = txt.rfind("starting trading/live_paper.py")
    seg = txt[idx:] if idx >= 0 else txt
    opened = [m.start() for m in re.finditer("PAPER SHORT OPENED", seg)]
    closed = [m.start() for m in re.finditer("PAPER SHORT CLOSED", seg)]
    if opened and (not closed or opened[-1] > closed[-1]):
        block = seg[opened[-1]: opened[-1] + 600]
        get = lambda k: (re.search(k + r":\s*(\S+)", block) or [None, "?"])[1]
        return (f"{get('Trade')} entry {get('Entry price')} at {get('Entry time')}, stop {get('Stop')} "
                "(in memory only; lost if the process restarts)")
    return None


def main():
    now = datetime.now(timezone.utc)
    print("=" * 78)
    print(f"EURUSD LIVE PAPER REPORT  -  {fmt(now)}")
    print("=" * 78)

    sup, tr = pid_alive(SUP_PID), pid_alive(PID)
    print(f"supervisor: {'ALIVE pid %d, up %s' % (sup[0], sup[2]) if sup else 'NOT RUNNING'}")
    print(f"trader:     {'ALIVE pid %d, up %s' % (tr[0], tr[2]) if tr else 'NOT RUNNING'}")
    op = open_position_from_log()
    print(f"open virtual position (current run, from log): {op or 'none'}")

    signals_section(now)

    rows = load_trades()
    sessions = sorted(set(r["session"] for r in rows))
    print(f"\n=== LIVE PAPER TRADES (data/live_paper_trades.csv): {len(rows)} closed, {len(sessions)} run(s)")
    if len(sessions) > 1:
        print("  NOTE: runs before 2026-10-06 11:13 UTC restarted numbering at #1 / equity $10;")
        print("  live_paper.py now resumes from the log. Equity below is chained from $10.00 using pnl_usd.")
    if rows:
        print(f"  last logged row: trade #{rows[-1]['n']}, logged equity ${float(rows[-1]['equity']):.3f}, "
              f"chained equity ${rows[-1]['chained_equity']:.3f}")
    print_metrics("OVERALL", metrics(rows, INITIAL_EQUITY))
    cutoff = now - timedelta(hours=24)
    before = [r for r in rows if r["exit_dt"] < cutoff]
    recent = [r for r in rows if r["exit_dt"] >= cutoff]
    start_eq = before[-1]["chained_equity"] if before else INITIAL_EQUITY
    print_metrics("LAST 24H (by exit time)", metrics(recent, start_eq))
    if rows:
        span_days = (now - min(r["entry_dt"] for r in rows)).total_seconds() / 86400
        print(f"\n  live trade frequency: {len(rows) / span_days:.1f} trades/cal-day over {span_days:.1f} days")

    backtest_section()
    print()


if __name__ == "__main__":
    main()
