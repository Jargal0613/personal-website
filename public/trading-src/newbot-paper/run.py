#!/usr/bin/env python3
"""EUR/USD PAPER trading simulator - fake money only, never places real orders.

  python3 run.py               fetch new hourly bars, catch up bar-by-bar, save, report
  python3 run.py --report-only show report from saved state (no processing, state untouched)
"""
import argparse
import csv
import fcntl
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E  # noqa: E402

DATA_DIR = os.path.join(HERE, "data")
DB_PATH = os.path.join(DATA_DIR, "paper.db")
CSV_PATH = os.path.join(DATA_DIR, "trades.csv")
STATE_JSON = os.path.join(DATA_DIR, "state.json")
LOG_PATH = os.path.join(DATA_DIR, "run.log")
LOCK_PATH = os.path.join(DATA_DIR, ".lock")

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS bars (ts INTEGER PRIMARY KEY, o REAL, h REAL, l REAL, c REAL);
CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, run_ts REAL, mode TEXT,
  bars_processed INTEGER, last_bar_ts INTEGER, price REAL, balance REAL, equity REAL);
CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY, side TEXT, units INTEGER,
  entry_ts INTEGER, entry REAL, stop REAL, target REAL, entry_reason TEXT, open_run INTEGER,
  exit_ts INTEGER, exit REAL, pips REAL, pnl REAL, exit_reason TEXT, close_run INTEGER,
  balance_after REAL, margin REAL, stopout_px REAL, risk_usd REAL, risk_pct REAL,
  balance_before REAL, sizing_note TEXT);
CREATE TABLE IF NOT EXISTS skipped (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, side TEXT,
  reason TEXT, detail TEXT, balance REAL, run_id INTEGER);
"""
TRADE_COLS = ["id", "side", "units", "entry_ts", "entry", "stop", "target", "entry_reason",
              "open_run", "exit_ts", "exit", "pips", "pnl", "exit_reason", "close_run", "balance_after",
              "margin", "stopout_px", "risk_usd", "risk_pct", "balance_before", "sizing_note"]


def log(msg):
    with open(LOG_PATH, "a") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}\n")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def get_meta(conn, key, default=None):
    r = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(r["value"]) if r else default


def set_meta(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, json.dumps(value)))


def upsert_trade(conn, t):
    row = [t.get(c) for c in TRADE_COLS]
    conn.execute(f"INSERT OR REPLACE INTO trades({','.join(TRADE_COLS)}) "
                 f"VALUES({','.join('?' * len(TRADE_COLS))})", row)


def choose_range(last_ts):
    gap_days = (time.time() - last_ts) / 86400
    for limit, r in ((4, "5d"), (25, "1mo"), (85, "3mo"), (175, "6mo"), (360, "1y")):
        if gap_days < limit:
            return r
    return "2y"


def export_files(conn):
    """Rewrite trades.csv and state.json atomically from the DB (DB is the source of truth)."""
    rows = conn.execute("SELECT * FROM trades ORDER BY id").fetchall()
    skips = conn.execute("SELECT * FROM skipped ORDER BY id").fetchall()
    tmp = CSV_PATH + ".tmp"
    hdr = ["id", "status", "side", "units", "lots", "entry_time_utc8", "entry_price", "stop", "target",
           "stopout_price", "margin_usd", "balance_before", "risk_usd", "risk_pct_of_equity", "sizing_note",
           "exit_time_utc8", "exit_price", "pips", "pnl_usd", "entry_reason", "exit_reason", "balance_after"]
    events = []
    for r in rows:
        closed = r["exit_ts"] is not None
        events.append((r["entry_ts"], [
            r["id"], "CLOSED" if closed else "OPEN", r["side"], r["units"], f"{E.lots(r['units']):.2f}",
            E.fmt_ts(r["entry_ts"]), f"{r['entry']:.5f}", f"{r['stop']:.5f}", f"{r['target']:.5f}",
            f"{r['stopout_px']:.5f}", f"{r['margin']:.2f}", f"{r['balance_before']:.2f}",
            f"{r['risk_usd']:.2f}", f"{r['risk_pct']:.1f}", r["sizing_note"] or "",
            E.fmt_ts(r["exit_ts"]) if closed else "", f"{r['exit']:.5f}" if closed else "",
            f"{r['pips']:.1f}" if closed else "", f"{r['pnl']:.2f}" if closed else "",
            r["entry_reason"], r["exit_reason"] or "", f"{r['balance_after']:.2f}" if closed else ""]))
    for k in skips:
        events.append((k["ts"], ["", "SKIPPED", k["side"], "", "", E.fmt_ts(k["ts"]), "", "", "", "", "",
                                 f"{k['balance']:.2f}", "", "", "", "", "", "", "", k["reason"], k["detail"], ""]))
    events.sort(key=lambda e: e[0])
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(hdr)
        for _, row in events:
            w.writerow(row)
    os.replace(tmp, CSV_PATH)
    snap = {k: get_meta(conn, k) for k in ("state", "last_bar_ts", "start_ts", "start_balance")}
    snap["last_bar_utc8"] = E.fmt_ts(snap["last_bar_ts"]) if snap["last_bar_ts"] else None
    tmp = STATE_JSON + ".tmp"
    with open(tmp, "w") as f:
        json.dump(snap, f, indent=2)
    os.replace(tmp, STATE_JSON)


# ------------------------------------------------------------------ report
def money(x, sign=True):
    return f"{'+' if sign and x >= 0 else '-' if x < 0 else ''}${abs(x):,.2f}"


def trade_line(t):
    s = (f"  #{t['id']} {t['side']} {E.lots(t['units']):.2f} lot ({t['units']:,} EUR)  risk {t['risk_pct']:.1f}%  entry {t['entry']:.5f} @ {E.fmt_ts(t['entry_ts'])}")
    if t.get("exit_ts") is not None:
        s += (f"\n      exit {t['exit']:.5f} @ {E.fmt_ts(t['exit_ts'])}  {t['pips']:+.1f} pips  "
              f"{money(t['pnl'])}  [{t['exit_reason']}]")
    else:
        s += f"  stop {t['stop']:.5f} target {t['target']:.5f}  [{t['entry_reason']}]"
    return s


def report(conn, price, price_note, run_id, prev_run, bars_processed, header_note=""):
    st = get_meta(conn, "state")
    acct = E.Account(st)
    start_bal = get_meta(conn, "start_balance")
    start_ts = get_meta(conn, "start_ts")
    last_bar_ts = get_meta(conn, "last_bar_ts")
    last_bar = conn.execute("SELECT * FROM bars WHERE ts=?", (last_bar_ts,)).fetchone()
    unreal = acct.unrealized(price)
    equity = acct.balance + unreal
    now = time.time()
    out = []
    out.append(f"=== EUR/USD PAPER account (fake money, no real orders) — {E.fmt_ts(now)} ===")
    if header_note:
        out.append(header_note)
    out.append(f"Data: Yahoo Finance {E.SYMBOL} 1h | last processed closed bar: {E.fmt_ts(last_bar_ts)} "
               f"(close {last_bar['c']:.5f})"
               + ("" if bars_processed is None else f" | new bars processed this run: {bars_processed}"))
    age_h = (now - (last_bar_ts + E.BAR_SECONDS)) / 3600
    if age_h > 3:
        out.append(f"  note: no new closed bar for {age_h:.0f}h (weekend/holiday or data delay)")
    out.append(f"Current price: {price:.5f}{price_note}")
    eq_, used, free, level = acct.margin_info(price)
    out.append(f"Balance: {money(acct.balance, False)}   Equity: {money(equity, False)}   "
               f"Leverage: 1:{E.LEVERAGE}")
    out.append(f"Used margin: {money(used, False)}   Free margin: {money(free, False)}   Margin level: "
               + (f"{level * 100:,.0f}% (stop-out at {E.STOP_OUT_LEVEL:.0%})" if level else "n/a (no position)"))
    out.append(f"P&L since start ({E.fmt_ts(start_ts)}, {money(start_bal, False)}): "
               f"{money(equity - start_bal)} ({(equity / start_bal - 1) * 100:+.2f}%)")
    if prev_run:
        out.append(f"P&L since previous run ({E.fmt_ts(prev_run['run_ts'])}): "
                   f"{money(equity - prev_run['equity'])}")
    if run_id is not None:
        closed = conn.execute("SELECT * FROM trades WHERE close_run=? ORDER BY id", (run_id,)).fetchall()
        opened = conn.execute("SELECT * FROM trades WHERE open_run=? ORDER BY id", (run_id,)).fetchall()
        label = "last engine run" if bars_processed is None else "this run"
        out.append(f"Trades {label}: {len(opened)} opened, {len(closed)} closed")
        for t in closed:
            out.append(trade_line(dict(t)))
        skips = conn.execute("SELECT * FROM skipped WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        for k in skips:
            out.append(f"  SKIPPED {k['side']} signal @ {E.fmt_ts(k['ts'])}: {k['reason']} ({k['detail']})")
        still_open = [t for t in opened if t["exit_ts"] is None]
        if still_open:
            out.append("  opened and still open:")
            out += [trade_line(dict(t)) for t in still_open]
    p = st["position"]
    if p:
        sgn = 1 if p["side"] == "LONG" else -1
        exit_px = price - E.HALF_SPREAD if sgn > 0 else price + E.HALF_SPREAD
        out.append(f"Open position: #{p['id']} {p['side']} {p['units']:,} EUR @ {p['entry']:.5f} "
                   f"since {E.fmt_ts(p['entry_ts'])}")
        out.append(f"  {E.lots(p['units']):.2f} lot | stop {p['stop']:.5f}  target {p['target']:.5f}  "
                   f"margin stop-out ~{p['stopout_px']:.5f} | risk at entry {money(p['risk_usd'], False)} "
                   f"({p['risk_pct']:.1f}% of equity){' [' + p['sizing_note'].strip() + ']' if p.get('sizing_note') else ''}")
        out.append(f"  unrealized {money(unreal)} ({sgn * (exit_px - p['entry']) / E.PIP:+.1f} pips, after spread)")
    else:
        out.append("Open position: none (flat)")
    if st.get("pending"):
        pd = st["pending"]
        out.append(f"Pending order: {pd['side']} at next bar open ({pd['reason']}, "
                   f"signal bar {E.fmt_ts(pd['signal_ts'])})")
    allc = conn.execute("SELECT pnl FROM trades WHERE exit_ts IS NOT NULL").fetchall()
    wins = sum(1 for r in allc if r["pnl"] > 0)
    nskip = conn.execute("SELECT COUNT(*) FROM skipped").fetchone()[0]
    out.append(f"All-time: {len(allc)} closed trades, {wins} wins"
               + (f" ({wins / len(allc) * 100:.0f}%)" if allc else "") + f", {nskip} signals skipped (margin)")
    if acct.balance - E.MIN_LOT_UNITS * E.HALF_SPREAD < E.margin_required(E.MIN_LOT_UNITS, price) and not p:
        out.append("WARNING: balance too small to open even the minimum 0.01 lot — account effectively wiped out.")
    print("\n".join(out))
    return equity


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report-only", action="store_true", help="print report, do not process bars")
    args = ap.parse_args()
    os.makedirs(DATA_DIR, exist_ok=True)

    lockf = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("ERROR: another run.py instance is running; try again shortly.")
        return 3

    conn = connect()
    initialized = get_meta(conn, "state") is not None
    last_ts = get_meta(conn, "last_bar_ts")

    if args.report_only:
        if not initialized:
            print("Paper account not initialized yet. Run: python3 run.py")
            return 1
        try:
            _, price, _ = E.fetch_yahoo_hourly("5d")
            note = " (live, Yahoo)"
        except E.DataError as e:
            price = conn.execute("SELECT c FROM bars WHERE ts=?", (last_ts,)).fetchone()["c"]
            note = f" (last stored close; live fetch failed: {e})"
        last_run = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        report(conn, price, note, last_run["id"], None, None,
               header_note=f"(report-only; showing trades from last engine run at {E.fmt_ts(last_run['run_ts'])})")
        return 0

    rng = "3mo" if not initialized else choose_range(last_ts)
    try:
        bars, price, fetched_at = E.fetch_yahoo_hourly(rng)
    except E.DataError as e:
        log(f"FETCH FAILED: {e}")
        print(f"DATA FETCH FAILED — no bars processed, saved state left unchanged.\n  reason: {e}")
        if initialized:
            print("Last saved state:")
            price = conn.execute("SELECT c FROM bars WHERE ts=?", (last_ts,)).fetchone()["c"]
            report(conn, price, " (last stored close — NOT live)", None, None, None)
        return 2

    prev_run = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    try:
        with conn:  # single atomic transaction: all-or-nothing
            if not initialized:
                acct = E.Account()
                for b in bars:
                    conn.execute("INSERT OR IGNORE INTO bars VALUES(?,?,?,?,?)",
                                 (b["ts"], b["o"], b["h"], b["l"], b["c"]))
                last = bars[-1]["ts"]
                set_meta(conn, "state", acct.state)
                set_meta(conn, "last_bar_ts", last)
                set_meta(conn, "start_ts", last + E.BAR_SECONDS)
                set_meta(conn, "start_balance", E.START_BALANCE)
                cur = conn.execute("INSERT INTO runs(run_ts,mode,bars_processed,last_bar_ts,price,balance,equity)"
                                   " VALUES(?,?,?,?,?,?,?)", (fetched_at, "init", 0, last, price,
                                                              E.START_BALANCE, E.START_BALANCE))
                run_id, n_new, note = cur.lastrowid, 0, ""
                hdr = (f"INITIALIZED fresh paper account at latest closed bar {E.fmt_ts(last)}; "
                       f"stored {len(bars)} bars of history for indicators (no backfilled trades).")
            else:
                new = [b for b in bars if b["ts"] > last_ts]
                hdr = ""
                if bars[0]["ts"] > last_ts + E.BAR_SECONDS:
                    hdr = "WARNING: fetched data starts after last processed bar — possible data gap."
                cur = conn.execute("INSERT INTO runs(run_ts,mode,bars_processed,last_bar_ts,price,balance,equity)"
                                   " VALUES(?,?,?,?,?,?,?)", (fetched_at, "run", len(new), last_ts, price, 0, 0))
                run_id = cur.lastrowid
                acct = E.Account(get_meta(conn, "state"))
                for b in new:
                    conn.execute("INSERT INTO bars VALUES(?,?,?,?,?)", (b["ts"], b["o"], b["h"], b["l"], b["c"]))
                allbars = [dict(r) for r in conn.execute("SELECT ts,o,h,l,c FROM bars ORDER BY ts")]
                ind = E.indicators(allbars)
                first_new = len(allbars) - len(new)
                for i in range(first_new, len(allbars)):
                    acct.step(allbars, ind, i, run_id)
                for t in acct.opened:
                    upsert_trade(conn, t)
                for t in acct.closed:
                    upsert_trade(conn, t)
                for k in acct.skipped:
                    conn.execute("INSERT INTO skipped(ts,side,reason,detail,balance,run_id) VALUES(?,?,?,?,?,?)",
                                 (k["ts"], k["side"], k["reason"], k["detail"], k["balance"], run_id))
                new_last = new[-1]["ts"] if new else last_ts
                set_meta(conn, "state", acct.state)
                set_meta(conn, "last_bar_ts", new_last)
                eq = acct.balance + acct.unrealized(price)
                conn.execute("UPDATE runs SET last_bar_ts=?, balance=?, equity=? WHERE id=?",
                             (new_last, acct.balance, eq, run_id))
                n_new = len(new)
                log(f"run {run_id}: {n_new} bars, opened {len(acct.opened)}, closed {len(acct.closed)}, "
                    f"skipped {len(acct.skipped)}, balance {acct.balance:.2f}, equity {eq:.2f}")
    except Exception as e:
        log(f"RUN FAILED (rolled back): {e!r}")
        print(f"ERROR during processing — transaction rolled back, saved state unchanged.\n  {e!r}")
        return 4

    export_files(conn)
    if not initialized:
        log(f"initialized at bar {E.utc_iso(get_meta(conn, 'last_bar_ts'))}")
    report(conn, price, " (live, Yahoo)", run_id, prev_run, n_new, header_note=hdr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
