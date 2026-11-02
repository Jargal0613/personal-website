"""Daily summary of the paper program (read-only; safe to run any time). Usage: python3 program/daily_summary.py"""
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

P = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(P)
sys.path.insert(0, P)
import journal as J
import risk as R
import stats as ST

UB = timezone(timedelta(hours=8))


def t2s(t):
    d = datetime.fromtimestamp(t, timezone.utc)
    return f"{d:%Y-%m-%d %H:%M} UTC ({d.astimezone(UB):%m-%d %H:%M} UB)"


def age(path):
    return int(time.time() - os.path.getmtime(path)) if os.path.exists(path) else None


def proc_ok(pidfile):
    try:
        os.kill(int(open(pidfile).read().strip()), 0); return True
    except Exception: return False


def main():
    now = time.time()
    try: S = json.load(open(os.path.join(P, "state", "engine_state.json")))
    except Exception: S = {}
    eqrows = list(csv.DictReader(open(J.EQUITY))) if os.path.exists(J.EQUITY) else []
    last = eqrows[-1] if eqrows else {}
    start = int(datetime(2026, 10, 7, 7, 20, tzinfo=timezone.utc).timestamp()); end = start + 31 * 86400
    print(f"=== PAPER PROGRAM DAILY SUMMARY: {t2s(now)} ===")
    print(f"program day {int((now - start) // 86400) + 1}/31 (extended from 21 for outages; window {t2s(start)} -> {t2s(end)}). PAPER ONLY, no orders.")
    eq = float(last.get("equity", R.START_EQUITY)) if last else R.START_EQUITY
    print(f"equity ${eq:.2f} (last mark {last.get('ts_utc', '-')}) | balance ${S.get('balance', 10):.2f} | peak ${S.get('peak', 10):.2f} | "
          f"drawdown {100 * (S.get('peak', 10) - eq) / max(1e-9, S.get('peak', 10)):.1f}% | start-of-day ${S.get('day_start_eq', 10):.2f}")
    pos = S.get("positions", [])
    print(f"open positions {len(pos)} | open risk ${sum(p['risk'] for p in pos):.2f} ({100 * sum(p['risk'] for p in pos) / max(eq, 1e-9):.1f}% of equity; cap 15%) "
          f"| pending orders {len(S.get('pending', []))}")
    for p in pos:
        print(f"   #{p['id']} {p['hyp']} {p['sym']} {'BUY' if p['dir'] > 0 else 'SELL'} {p['units']:g}u @ {p['entry']:.5f} SL {p['sl']:.5f} "
              f"TP {p['tp'] if p['tp'] is None else round(p['tp'], 5)} risk ${p['risk']:.2f} mark ${p.get('last_mark', 0):+.2f} opened {t2s(p['t_in'])}")
    tr = ST.trades()
    d24 = [t for t in tr if t["t_out"] and t["t_out"] >= now - 86400]
    print(f"closed trades: last 24h {len(d24)} (net ${sum(t['pnl_usd'] for t in d24):+.2f}) | total {len(tr)} (net ${sum(t['pnl_usd'] for t in tr):+.2f})")
    for t in d24:
        print(f"   #{t['trade_id']} {t['hyp']} {t['sym']} {'BUY' if int(t['dir']) > 0 else 'SELL'} {float(t['entry']):.5f} -> {float(t['exit']):.5f} "
              f"{t['reason']} ${t['pnl_usd']:+.2f} (closed {t2s(t['t_out'])})")
    dec = J.read(J.DEC)
    cut = datetime.fromtimestamp(now - 86400, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    d24d = [r for r in dec if r.get("ts_utc", "") >= cut]
    kinds = {}
    for r in d24d: kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print(f"decisions last 24h: {dict(sorted(kinds.items()))}")
    st = J.hyp_status()
    groups = {}
    for k, v in st.items(): groups.setdefault(v.get("status"), []).append(k)
    print(f"hypotheses: forward-testing {sorted(groups.get('forward', []))} | killed {sorted(groups.get('killed', []))} | "
          f"promoted {sorted(groups.get('promoted', []))} | rejected {len(groups.get('rejected', []))} | proposed/backtested "
          f"{sorted(groups.get('proposed', []) + groups.get('backtested', []))}")
    for h in sorted(groups.get("forward", []) + groups.get("killed", []) + groups.get("promoted", [])):
        pr = ST.promotion(h, int(st[h].get("version", 1)), now)
        pf = "-" if pr["pf"] is None else f"{pr['pf']:.2f}"; tt = "-" if pr["t"] is None else f"{pr['t']:+.2f}"
        print(f"   {h} v{st[h].get('version', 1)} [{st[h]['status']}]: n={pr['n']} net ${pr['net']:+.2f} PF {pf} t {tt} maxDD {100 * pr['max_dd_pct']:.0f}% "
              f"days {pr['days']:.1f} | promotion criteria met: {sum(pr['criteria'].values())}/7 "
              f"(missing: {', '.join(k for k, v in pr['criteria'].items() if not v) or 'none'})")
    halted = S.get("halted")
    print(f"kill switch: {'HALTED: ' + json.dumps(halted) if halted else 'armed, not triggered'} (halts at equity < $4.00 or drawdown > 50%) | "
          f"daily loss limit: {'HIT, no new entries today' if S.get('day_blocked') else 'ok'}")
    ha, ra = age(os.path.join(P, "state", "engine.heartbeat")), age(os.path.join(ROOT, "data", "news_recorder.heartbeat"))
    print(f"engine: {'running' if proc_ok(os.path.join(P, 'state', 'engine.pid')) else 'NOT RUNNING'} (heartbeat {ha}s ago) | "
          f"news recorder: {'running' if proc_ok(os.path.join(ROOT, 'data', 'news_recorder.pid')) else 'NOT RUNNING'} (heartbeat {ra}s ago)")
    cyc = [r for r in dec if r["kind"] == "cycle"]
    if cyc:
        c = cyc[-1]; n24 = sum(1 for r in d24d if r["kind"] == "cycle")
        x = c.get("news", {}).get("x", {}) if isinstance(c.get("news"), dict) else {}
        print(f"last cycle {c['ts_utc']} ({n24} cycles in 24h) | X sentiment: {x.get('x_status', '-') if isinstance(x, dict) else x} | "
              f"headlines logged 24h: {sum(1 for r in J.read(J.NEWS) if r.get('type') == 'headline' and r['ts_utc'] >= cut)}")
        up = c.get("upcoming_high_impact", [])
        if up: print("upcoming high-impact (24h): " + "; ".join(f"{u['t']} {u['cur']} {u['title']}" for u in up))


if __name__ == "__main__":
    main()
