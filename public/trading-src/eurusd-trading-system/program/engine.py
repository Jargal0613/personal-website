"""PAPER-ONLY trading research engine (21-day program, 2026-10-07 07:20 UTC to 2026-10-28 07:20 UTC).

- Read-only cTrader Open API on the DEMO host: auth, account list (demo account <DEMO_ACCOUNT_ID> must have isLive=False),
  symbols, M1 trendbars (backfill and restart catch-up) and spot subscriptions. NO order, amend or close messages
  exist in this program (risk.paper_only_ok() refuses to start otherwise).
- Paper fills come from live bid/ask: buy at ask, sell at bid. Slippage, measured news costs, commission and swap
  are always charged. Stop-first, and gaps fill beyond the stop (RISK_LIMITS s7).
- RISK_LIMITS are enforced in code (risk.py), and the engine refuses to start if RISK_LIMITS.md was modified.
- Hypotheses are plug-in modules in program/hypotheses/<ID>.py (META + on_minute(ctx)). They run only while their
  journal status is 'forward' and META.version matches the registered version. New or changed files are
  (re)loaded each minute without a restart.
- Cycle: every 30 min while the FX market is open, every 2 h while closed. Each cycle scans quotes and spreads,
  polls news RSS / X (optional), writes equity, journals the cycle, and runs the kill and promotion checks.
Every signal, entry, exit, skip and cycle goes to journal/decisions.jsonl. State lives in state/engine_state.json.
"""
import glob
import importlib.util
import json
import os
import statistics
import subprocess
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

P = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(P)
sys.path.insert(0, P)
from dotenv import load_dotenv
from ctrader_open_api import Client, TcpProtocol, EndPoints, Protobuf
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq, ProtoOAApplicationAuthRes, ProtoOAGetAccountListByAccessTokenReq,
    ProtoOAGetAccountListByAccessTokenRes, ProtoOAAccountAuthReq, ProtoOAAccountAuthRes, ProtoOASymbolsListReq,
    ProtoOASymbolsListRes, ProtoOASubscribeSpotsReq, ProtoOASubscribeSpotsRes, ProtoOASpotEvent, ProtoOAErrorRes,
    ProtoOAGetTrendbarsReq, ProtoOAGetTrendbarsRes,
)
from twisted.internet import reactor, threads

import journal as J
import news
import risk as R
import stats as ST
import xsent

load_dotenv(os.path.join(ROOT, ".env"))
HOST, PORT = EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "US500", "XAUUSD"]
PROGRAM_START = int(datetime(2026, 10, 7, 7, 20, tzinfo=timezone.utc).timestamp())
PROGRAM_END = PROGRAM_START + 21 * 86400
STATE = os.path.join(P, "state", "engine_state.json")
SPREADS = os.path.join(P, "state", "spreads.json")
HEART = os.path.join(P, "state", "engine.heartbeat")
HALTED = os.path.join(P, "state", "HALTED")
HYPDIR = os.path.join(P, "hypotheses")
NEWS_COST = os.path.join(ROOT, "data", "reference", "news_cost_by_second.csv")
NYC, UTC = ZoneInfo("America/New_York"), timezone.utc

Q = {}              # sym -> dict(bid, ask, t)
BARS = {}           # sym -> list of completed M1 bid bars dict(t,o,h,l,c) (t = bar start, s)
CUR = {}            # sym -> current forming bar
SPR = {}            # sym -> list of [minute_ts, spread]
MODS = {}           # hyp id -> dict(mod, mtime, path)
RT = dict(acct=None, sid2name={}, name2sid={}, backfill_pending=set(), live=False, last_spot=0.0, last_min=0,
          dirty=False, exit=0, news_busy=False)
S = {}
NEWS_SLIP = {}


def log(msg):
    print(f"{datetime.now(UTC):%Y-%m-%dT%H:%M:%SZ} [engine] {msg}", flush=True)


# ------------------------------------------------------------------ state
def default_state():
    return dict(balance=R.START_EQUITY, peak=R.START_EQUITY, day=None, day_start_eq=R.START_EQUITY, day_blocked=False,
                halted=None, promoted=None, positions=[], pending=[], shadows=[], next_id=1, last_cycle=0, hyp_state={},
                last_seen={}, last_rollover=None, created=J.now_iso())


def load_state():
    global S
    try: S = json.load(open(STATE))
    except Exception: S = default_state()
    for k, v in default_state().items(): S.setdefault(k, v)
    try:
        for k, v in json.load(open(SPREADS)).items(): SPR[k] = v
    except Exception: pass


def save_state():
    tmp = STATE + ".tmp"
    json.dump(S, open(tmp, "w")); os.replace(tmp, STATE); RT["dirty"] = False


def save_spreads():
    json.dump(SPR, open(SPREADS + ".tmp", "w")); os.replace(SPREADS + ".tmp", SPREADS)


def decision(kind, **kw):
    kw.setdefault("rule_version", None)
    J.append(J.DEC, dict(kind=kind, **kw))


# ------------------------------------------------------------------ market helpers
def market_closed(t=None):
    d = datetime.fromtimestamp(t or time.time(), UTC)
    return d.weekday() == 5 or (d.weekday() == 4 and d.hour >= 21) or (d.weekday() == 6 and d.hour < 21)


def usdjpy_mid():
    q = Q.get("USDJPY")
    return (q["bid"] + q["ask"]) / 2 if q and q.get("bid") and q.get("ask") else 150.0


def normal_spread(sym):
    xs = [s for t, s in SPR.get(sym, []) if s > 0]
    if len(xs) >= 30: return statistics.median(xs)   # engine quotes (minute samples, last 5 trading days)
    f = R.FACTS[sym].get("spread_sample", {}).get("median", 0.0) or 0.0
    return max(f, R.SPREAD_FLOOR[sym])


def load_news_slip():
    try:
        import csv
        with open(NEWS_COST) as f:
            for r in csv.DictReader(f):
                NEWS_SLIP[int(r["sec"])] = float(r["absmove_1s_p50"] or 0)
    except Exception as e:
        log(f"news cost curve unavailable: {e}")


def slippage(sym, t, kind):
    """kind 'in' or 'out'. Normal values, or inside a news window the measured 1-s latency move (pips)."""
    s_in, s_out = R.slip(sym)
    base = s_in if kind == "in" else s_out
    ev = news.in_news_window(t)
    if ev is None: return base, False
    if sym in ("XAUUSD", "US500"): return 3 * base, True
    pip = 10.0 ** (-R.FACTS[sym]["pipPosition"])
    sec = int(t - ev["t"])
    meas = NEWS_SLIP.get(max(-300, min(1800, sec)), 0.0) * pip
    return max(base, meas + (0 if kind == "in" else 0.2 * pip)), True


def to_usd(sym, amt):
    return R.to_usd(sym, amt, usdjpy_mid())


def acct_view():
    eq = equity()
    return dict(equity=eq, open=[dict(sym=p["sym"], hyp=p["hyp"], risk=p["risk"], units=p["units"]) for p in S["positions"]],
                halted=S["halted"], day_blocked=S["day_blocked"])


def mark(p):
    q = Q.get(p["sym"])
    if not q: return p.get("last_mark", 0.0)
    px = q["bid"] if p["dir"] > 0 else q["ask"]
    v = to_usd(p["sym"], p["dir"] * (px - p["entry"]) * p["units"]) - R.commission_usd(p["sym"], p["units"]) + p.get("swap", 0.0)
    p["last_mark"] = v
    return v


def equity():
    return S["balance"] + sum(mark(p) for p in S["positions"])


def open_risk():
    return sum(p["risk"] for p in S["positions"])


def write_equity(tag):
    import csv
    path = J.EQUITY; new = not os.path.exists(path); eq = equity()
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(["ts_utc", "tag", "balance", "equity", "open_positions", "open_risk", "peak", "drawdown_pct", "day_start_eq"])
        w.writerow([J.now_iso(), tag, round(S["balance"], 4), round(eq, 4), len(S["positions"]), round(open_risk(), 4),
                    round(S["peak"], 4), round(100 * (S["peak"] - eq) / S["peak"], 2) if S["peak"] else 0, round(S["day_start_eq"], 4)])


# ------------------------------------------------------------------ order simulation
def new_id():
    i = S["next_id"]; S["next_id"] += 1; return i


def hyp_version(hid):
    m = MODS.get(hid); return m["mod"].META.get("version") if m else None


def open_position(o, fill, t, why):
    """o: order dict with hyp, sym, dir, sl_dist, tp_dist, exit_by, signal. Runs the risk checks at the fill."""
    sym, d = o["sym"], o["dir"]
    sl = fill - d * o["sl_dist"]; tp = fill + d * o["tp_dist"] if o.get("tp_dist") else None
    s_out, news_win = slippage(sym, t, "out")
    q = Q[sym]
    units, rk, reason = R.check_entry(acct_view(), sym, o["hyp"], fill, sl, s_out, usdjpy_mid(), q["ask"] - q["bid"],
                                      normal_spread(sym), news_hyp=o.get("news_hyp", False))
    base = dict(hyp=o["hyp"], rule_version=o["version"], symbol=sym, side="BUY" if d > 0 else "SELL", signal_source=o["signal"].get("source"),
                signal=o["signal"], would_change_mind=o["signal"].get("would_change_mind"))
    if units is None:
        decision("skip", reason=f"RISK BLOCK: {reason}", entry=round(fill, 6), stop=round(sl, 6), target=tp, **base)
        return None
    exit_by = min(o["exit_by"], friday_flat_ts(t)) if o.get("exit_by") else friday_flat_ts(t)
    pid = new_id()
    p = dict(id=pid, hyp=o["hyp"], version=o["version"], sym=sym, dir=d, units=units, entry=fill, t_in=t, sl=sl, tp=tp,
             exit_by=exit_by, risk=rk, swap=0.0, news_window=news_win, signal=o["signal"])
    S["positions"].append(p)
    for sd in (1, -1):   # shadow long + short with identical brackets (random-direction control)
        q_ = Q[sym]; s_in, _ = slippage(sym, t, "in")
        sf = q_["ask"] + s_in if sd > 0 else q_["bid"] - s_in
        S["shadows"].append(dict(trade_id=pid, hyp=o["hyp"], version=o["version"], sym=sym, dir=sd, units=units, entry=sf, t_in=t,
                                 sl=sf - sd * o["sl_dist"], tp=(sf + sd * o["tp_dist"]) if o.get("tp_dist") else None, exit_by=exit_by, swap=0.0))
    decision("entry", trade_id=pid, entry=round(fill, 6), stop=round(sl, 6), target=round(tp, 6) if tp else None,
             size_units=units, size_lots=units / R.FACTS[sym]["lotSize_units"], risk_usd=round(rk, 4), exit_by=J.now_iso(exit_by),
             spread=round(q["ask"] - q["bid"], 6), news_window=news_win, how=why, equity=round(equity(), 4), **base)
    RT["dirty"] = True
    return p


def friday_flat_ts(t):
    d = datetime.fromtimestamp(t, UTC)
    fri = (d + timedelta(days=(4 - d.weekday()) % 7)).replace(hour=R.FRIDAY_FLAT_UTC[0], minute=R.FRIDAY_FLAT_UTC[1], second=0, microsecond=0)
    if fri.timestamp() <= t: fri += timedelta(days=7)
    return int(fri.timestamp())


def close_position(p, px, t, reason, shadow=False):
    gross = to_usd(p["sym"], p["dir"] * (px - p["entry"]) * p["units"])
    comm = R.commission_usd(p["sym"], p["units"])
    pnl = gross - comm + p.get("swap", 0.0)
    if shadow:
        ST.append_row(ST.SHADOWS, ST.SHADOW_COLS, dict(trade_id=p["trade_id"], hyp=p["hyp"], version=p["version"], sym=p["sym"],
                                                       dir=p["dir"], units=p["units"], t_in=p["t_in"], entry=p["entry"], t_out=t,
                                                       exit=px, reason=reason, pnl_usd=round(pnl, 5)))
        S["shadows"].remove(p); RT["dirty"] = True
        return pnl
    S["balance"] += pnl; S["positions"].remove(p)
    eq = equity(); S["peak"] = max(S["peak"], eq)
    ST.append_row(ST.TRADES, ST.TRADE_COLS, dict(trade_id=p["id"], hyp=p["hyp"], version=p["version"], sym=p["sym"], dir=p["dir"],
                                                 units=p["units"], t_in=p["t_in"], entry=p["entry"], sl=p["sl"], tp=p["tp"], t_out=t,
                                                 exit=px, reason=reason, gross_usd=round(gross, 5), comm_usd=round(comm, 5),
                                                 swap_usd=round(p.get("swap", 0.0), 5), pnl_usd=round(pnl, 5), risk_usd=round(p["risk"], 5),
                                                 equity_after=round(eq, 5)))
    decision("exit", trade_id=p["id"], hyp=p["hyp"], rule_version=p["version"], symbol=p["sym"], side="BUY" if p["dir"] > 0 else "SELL",
             entry=round(p["entry"], 6), stop=round(p["sl"], 6), target=p["tp"], size_units=p["units"], exit=round(px, 6),
             reason=reason, outcome_usd=round(pnl, 4), gross_usd=round(gross, 4), comm_usd=round(comm, 4), swap_usd=round(p.get("swap", 0), 4),
             hold_min=round((t - p["t_in"]) / 60, 1), balance=round(S["balance"], 4), equity=round(eq, 4),
             would_change_mind=p["signal"].get("would_change_mind"))
    write_equity(f"exit#{p['id']}")
    RT["dirty"] = True
    hyp_kill(p["hyp"], p["version"])
    return pnl


def check_exits(sym, t, replay=False):
    q = Q.get(sym)
    if not q: return
    for shadow, book in ((False, S["positions"]), (True, S["shadows"])):
        for p in [x for x in book if x["sym"] == sym]:
            if t < p["t_in"]: continue
            _, slip_out = None, slippage(sym, t, "out")[0]
            d = p["dir"]; tag = " (replayed from M1 bars)" if replay else ""
            if d > 0 and q["bid"] <= p["sl"]: close_position(p, q["bid"] - slip_out, t, "SL" + tag, shadow)
            elif d < 0 and q["ask"] >= p["sl"]: close_position(p, q["ask"] + slip_out, t, "SL" + tag, shadow)
            elif p["tp"] is not None and d > 0 and q["bid"] >= p["tp"]: close_position(p, p["tp"], t, "TP" + tag, shadow)
            elif p["tp"] is not None and d < 0 and q["ask"] <= p["tp"]: close_position(p, p["tp"], t, "TP" + tag, shadow)
            elif t >= p["exit_by"]:
                px = q["bid"] - slip_out if d > 0 else q["ask"] + slip_out
                close_position(p, px, t, ("FRIDAY_FLAT" if p["exit_by"] == friday_flat_ts(p["t_in"]) else "TIME") + tag, shadow)


def check_pending(sym, t, replay=False):
    q = Q.get(sym)
    if not q: return
    for o in [x for x in S["pending"] if x["sym"] == sym]:
        if o not in S["pending"]: continue
        if t >= o["expiry"]:
            S["pending"].remove(o); RT["dirty"] = True
            decision("cancel", hyp=o["hyp"], rule_version=o["version"], symbol=sym, order_id=o["id"], reason="expired", level=o["level"])
            continue
        if t < o["t_placed"]: continue
        hit = (o["dir"] > 0 and q["ask"] >= o["level"]) or (o["dir"] < 0 and q["bid"] <= o["level"])
        if not hit: continue
        s_in, _ = slippage(sym, t, "in")
        fill = max(o["level"], q["ask"]) + s_in if o["dir"] > 0 else min(o["level"], q["bid"]) - s_in
        group = [x for x in S["pending"] if o.get("group") and x.get("group") == o["group"]] or [o]
        for x in group:
            if x in S["pending"]: S["pending"].remove(x)
        for x in group:
            if x is not o:
                decision("cancel", hyp=x["hyp"], rule_version=x["version"], symbol=sym, order_id=x["id"], reason=f"OCO sibling #{o['id']} triggered")
        RT["dirty"] = True
        open_position(o, fill, t, f"stop order #{o['id']} triggered at level {o['level']:.6g}" + (" (replayed from M1 bars)" if replay else ""))


def on_quote(sym, bid, ask, t):
    Q[sym] = dict(bid=bid, ask=ask, t=t)
    S["last_seen"][sym] = t
    m = int(t // 60) * 60
    c = CUR.get(sym)
    if c is None or c["t"] != m:
        if c is not None:
            BARS.setdefault(sym, []).append(c); del BARS[sym][:-5000]
        CUR[sym] = dict(t=m, o=bid, h=bid, l=bid, c=bid)
    else:
        c["h"] = max(c["h"], bid); c["l"] = min(c["l"], bid); c["c"] = bid
    if S["halted"]: return
    check_pending(sym, t)
    check_exits(sym, t)


# ------------------------------------------------------------------ plug-in context
class Ctx:
    def __init__(self, hid, version, now):
        self.hyp_id, self.version, self.now = hid, version, now
        self.state = S["hyp_state"].setdefault(hid, {})
        self.NYC, self.UTC = NYC, UTC

    def quote(self, sym):
        q = Q.get(sym); return (q["bid"], q["ask"]) if q and time.time() - q["t"] < 300 else None

    def bars(self, sym, since=None, until=None):
        b = BARS.get(sym, [])
        return [x for x in b if (since is None or x["t"] >= since) and (until is None or x["t"] < until)]

    def spread_normal(self, sym): return normal_spread(sym)

    def positions(self): return [p for p in S["positions"] if p["hyp"] == self.hyp_id]

    def pending(self): return [o for o in S["pending"] if o["hyp"] == self.hyp_id]

    def log(self, kind, **kw):
        decision(kind, hyp=self.hyp_id, rule_version=self.version, **kw)

    def _order(self, kind, sym, d, sl_dist, tp_dist, exit_by, signal, level=None, expiry=None, group=None, why="", news_hyp=False):
        if S["halted"]: return self.log("skip", symbol=sym, reason="program halted")
        if self.now >= PROGRAM_END: return self.log("skip", symbol=sym, reason="21-day program window is over: no new entries")
        if S["day_blocked"]: return self.log("skip", symbol=sym, reason="daily loss limit: no new entries today")
        if sl_dist is None or sl_dist <= 0: return self.log("skip", symbol=sym, reason="no hard stop -> refused")
        o = dict(id=new_id(), hyp=self.hyp_id, version=self.version, sym=sym, dir=d, sl_dist=sl_dist, tp_dist=tp_dist,
                 exit_by=exit_by, signal=signal, level=level, expiry=expiry, group=group, t_placed=self.now, news_hyp=news_hyp)
        if kind == "market":
            q = Q.get(sym)
            if not q: return self.log("skip", symbol=sym, reason="no quote")
            s_in, _ = slippage(sym, self.now, "in")
            fill = q["ask"] + s_in if d > 0 else q["bid"] - s_in
            decision("signal", hyp=self.hyp_id, rule_version=self.version, symbol=sym, side="BUY" if d > 0 else "SELL",
                     signal_source=signal.get("source"), order="market", why=why, signal=signal)
            return open_position(o, fill, self.now, "market")
        S["pending"].append(o); RT["dirty"] = True
        decision("signal", hyp=self.hyp_id, rule_version=self.version, symbol=sym, side="BUY" if d > 0 else "SELL", order="stop",
                 order_id=o["id"], level=level, stop_dist=sl_dist, target_dist=tp_dist, expiry=J.now_iso(expiry), exit_by=J.now_iso(exit_by),
                 group=group, signal_source=signal.get("source"), why=why, signal=signal, would_change_mind=signal.get("would_change_mind"))
        return o

    def market(self, sym, d, sl_dist, tp_dist, exit_by, signal, why=""):
        return self._order("market", sym, d, sl_dist, tp_dist, exit_by, signal, why=why)

    def stop_order(self, sym, d, level, sl_dist, tp_dist, expiry, exit_by, signal, group=None, why=""):
        return self._order("stop", sym, d, sl_dist, tp_dist, exit_by, signal, level=level, expiry=expiry, group=group, why=why)

    def cancel_group(self, group, why):
        for o in [x for x in S["pending"] if x["hyp"] == self.hyp_id and x.get("group") == group]:
            S["pending"].remove(o); RT["dirty"] = True
            self.log("cancel", symbol=o["sym"], order_id=o["id"], reason=why)


# ------------------------------------------------------------------ plug-ins
def load_plugins():
    status = J.hyp_status()
    for path in sorted(glob.glob(os.path.join(HYPDIR, "*.py"))):
        hid = os.path.basename(path)[:-3]
        if hid.startswith("_"): continue
        mt = os.path.getmtime(path)
        if hid in MODS and MODS[hid]["mtime"] == mt: continue
        try:
            spec = importlib.util.spec_from_file_location(f"hyp_{hid}_{int(mt)}", path)
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            assert mod.META["id"] == hid and callable(mod.on_minute)
            MODS[hid] = dict(mod=mod, mtime=mt, path=path)
            decision("plugin_loaded", hyp=hid, rule_version=mod.META.get("version"), status=status.get(hid, {}).get("status"))
        except Exception as e:
            decision("plugin_error", hyp=hid, error=f"{type(e).__name__}: {e}")
    active = {}
    for hid, m in MODS.items():
        st = status.get(hid, {})
        if st.get("status") == "forward" and int(st.get("version", 1)) == int(m["mod"].META.get("version", 1)):
            active[hid] = m
    return active


def run_plugins(now):
    if S["halted"]: return []
    active = load_plugins()
    for hid, m in active.items():
        try:
            m["mod"].on_minute(Ctx(hid, m["mod"].META["version"], now))
        except Exception as e:
            decision("plugin_error", hyp=hid, error=f"{type(e).__name__}: {e}", tb=traceback.format_exc()[-600:])
    return sorted(active)


# ------------------------------------------------------------------ limits
def hyp_kill(hid, version):
    pn = [t["pnl_usd"] for t in ST.trades(hid, version)]
    why = R.hyp_kill_check(pn)
    if why and J.hyp_status().get(hid, {}).get("status") == "forward":
        J.append(J.HYP, dict(type="status", id=hid, version=version, status="killed", reason=f"RISK_LIMITS s6: {why}"))
        decision("hypothesis_killed", hyp=hid, rule_version=version, reason=why)
        for o in [x for x in S["pending"] if x["hyp"] == hid]:
            S["pending"].remove(o)
        RT["dirty"] = True


def halt(reason, now):
    if S["halted"]: return
    S["halted"] = dict(reason=reason, ts=J.now_iso(now))
    for o in list(S["pending"]): S["pending"].remove(o)
    for p in list(S["positions"]):
        q = Q.get(p["sym"])
        if q:
            so = slippage(p["sym"], now, "out")[0]
            close_position(p, q["bid"] - so if p["dir"] > 0 else q["ask"] + so, now, "KILL_SWITCH")
    open(HALTED, "w").write(json.dumps(S["halted"]))
    decision("KILL_SWITCH", reason=reason, equity=round(equity(), 4), peak=round(S["peak"], 4))
    J.append(J.HYP, dict(type="program", event="HALTED", reason=reason))
    save_state(); write_equity("halt")
    subprocess.Popen([sys.executable, os.path.join(P, "final_report.py"), "--reason", f"kill switch: {reason}"],
                     stdout=open(os.path.join(P, "reports", "final_report.log"), "a"), stderr=subprocess.STDOUT)


def risk_tick(now):
    eq = equity()
    S["peak"] = max(S["peak"], eq)
    day = datetime.fromtimestamp(now, UTC).strftime("%Y-%m-%d")
    if S["day"] != day:
        S["day"] = day; S["day_start_eq"] = eq; S["day_blocked"] = False; RT["dirty"] = True
        decision("day_start", equity=round(eq, 4), day=day); write_equity("day_start")
    if not S["day_blocked"] and eq <= (1 - R.DAILY_LOSS_PCT) * S["day_start_eq"]:
        S["day_blocked"] = True; RT["dirty"] = True
        decision("daily_loss_limit", equity=round(eq, 4), day_start=round(S["day_start_eq"], 4))
        for o in list(S["pending"]): S["pending"].remove(o); decision("cancel", order_id=o["id"], hyp=o["hyp"], reason="daily loss limit")
    k = R.kill_check(eq, S["peak"])
    if k: halt(k, now)


def rollover(now):
    """swap at 17:00 New York, Mon-Fri; triple per broker setting."""
    ny = datetime.fromtimestamp(now, NYC)
    if ny.weekday() >= 5 or ny.hour < 17: return
    key = ny.strftime("%Y-%m-%d")
    if S["last_rollover"] == key: return
    S["last_rollover"] = key
    for book in (S["positions"], S["shadows"]):
        for p in book:
            f = R.FACTS[p["sym"]]; rate = f["swapLong"] if p["dir"] > 0 else f["swapShort"]
            trip = {3: 2, 5: 4}.get(f["swapRollover3Days"], 2); mult = 3 if ny.weekday() == trip else 1
            if f["swapCalculationType"] == 0:
                amt = rate * 10.0 ** (-f["pipPosition"]) * p["units"]
            else:
                amt = p["entry"] * p["units"] * rate / 100.0 / 360.0
            p["swap"] = p.get("swap", 0.0) + mult * to_usd(p["sym"], amt)
    if S["positions"]: decision("swap", note=f"rollover {key}", positions=[(p["id"], round(p["swap"], 4)) for p in S["positions"]])
    RT["dirty"] = True


# ------------------------------------------------------------------ cycle
def cycle(now):
    S["last_cycle"] = now
    scan = {}
    for sym in SYMBOLS:
        q = Q.get(sym); b = BARS.get(sym, [])
        last30 = [x for x in b if x["t"] >= now - 1800]
        day = [x for x in b if x["t"] >= now - 86400]
        scan[sym] = dict(bid=q["bid"] if q else None, ask=q["ask"] if q else None,
                         spread=round(q["ask"] - q["bid"], 6) if q else None, normal_spread=round(normal_spread(sym), 6),
                         chg30m=round(q["bid"] - last30[0]["o"], 6) if q and last30 else None,
                         range24h=round(max(x["h"] for x in day) - min(x["l"] for x in day), 6) if day else None,
                         quote_age_s=round(now - q["t"], 1) if q else None)
    status = J.hyp_status()
    active = sorted(h for h, v in status.items() if v.get("status") == "forward")
    promo = {}
    for h in active:
        pr = ST.promotion(h, int(status[h].get("version", 1)), now)
        promo[h] = dict(n=pr["n"], net=round(pr["net"], 3), pf=pr["pf"], t=pr["t"], days=round(pr["days"], 2),
                        passed=[k for k, v in pr["criteria"].items() if v])
        if pr["promoted"] and not S["promoted"]:
            S["promoted"] = h; RT["dirty"] = True
            J.append(J.HYP, dict(type="status", id=h, version=pr["version"], status="promoted", reason="all RISK_LIMITS s8 criteria met",
                                 stats={k: pr[k] for k in ("n", "net", "pf", "t", "max_dd_pct", "ctrl_p95", "days")}))
            write_promotion_report(pr)
    eq = equity()
    rec = dict(market_open=not market_closed(now), equity=round(eq, 4), balance=round(S["balance"], 4), peak=round(S["peak"], 4),
               open_risk=round(open_risk(), 4), positions=[dict(id=p["id"], hyp=p["hyp"], sym=p["sym"], dir=p["dir"], entry=p["entry"],
               sl=p["sl"], tp=p["tp"], mark_usd=round(p.get("last_mark", 0), 4)) for p in S["positions"]],
               pending=[dict(id=o["id"], hyp=o["hyp"], sym=o["sym"], dir=o["dir"], level=o["level"]) for o in S["pending"]],
               active_hypotheses=active, forward_stats=promo, halted=S["halted"], day_blocked=S["day_blocked"],
               promoted=S["promoted"], scan=scan, upcoming_high_impact=[dict(t=J.now_iso(e["t"]), cur=e["cur"], title=e["title"])
                                                                     for e in news.calendar(ahead_h=24)])
    write_equity("cycle")
    save_state(); save_spreads()
    if not RT["news_busy"]:
        RT["news_busy"] = True
        def work():
            out = {}
            try: out["rss"] = news.poll_rss()
            except Exception as e: out["rss"] = f"error {e}"
            try: out["calendar_logged"] = news.log_calendar_once()
            except Exception as e: out["calendar_logged"] = f"error {e}"
            try: out["x"] = xsent.poll() if not market_closed() else dict(x_status="skipped (market closed)")
            except Exception as e: out["x"] = f"error {e}"
            return out
        def done(out):
            RT["news_busy"] = False
            decision("cycle", news=out, **rec)
        def fail(f):
            RT["news_busy"] = False
            decision("cycle", news=f"error {f.value}", **rec)
        threads.deferToThread(work).addCallbacks(done, fail)
    else:
        decision("cycle", news="previous news poll still running", **rec)
    log(f"cycle: equity {eq:.2f} balance {S['balance']:.2f} positions {len(S['positions'])} pending {len(S['pending'])} active {active}")


def write_promotion_report(pr):
    path = os.path.join(P, "reports", f"promotion_{pr['hyp']}.md")
    with open(path, "w") as f:
        f.write(f"# PROMOTION REPORT: {pr['hyp']} v{pr['version']} ({J.now_iso()})\n\nAll RISK_LIMITS s8 criteria are met on forward paper "
                f"trades. NO live or demo orders follow; the user decides what happens next.\n\n```\n{json.dumps(pr, indent=2, default=str)}\n```\n")
    decision("PROMOTION", hyp=pr["hyp"], rule_version=pr["version"], report=path)


# ------------------------------------------------------------------ clock
def clock():
    try:
        now = time.time()
        if RT["live"]:
            # heartbeat: quotes flowing, or the market is closed
            if market_closed(now) or now - RT["last_spot"] < 300:
                open(HEART, "w").write(str(int(now)))
            m = int(now // 60) * 60
            if m != RT["last_min"]:
                RT["last_min"] = m
                for sym, q in Q.items():
                    SPR.setdefault(sym, []).append([m, q["ask"] - q["bid"]]); del SPR[sym][:-7200]
                    if CUR.get(sym) and CUR[sym]["t"] < m:
                        BARS.setdefault(sym, []).append(CUR.pop(sym)); del BARS[sym][:-5000]
                    if not S["halted"]:
                        check_exits(sym, now); check_pending(sym, now)
                if not S["halted"]:
                    rollover(now); risk_tick(now); run_plugins(now)
                interval = 1800 if not market_closed(now) else 7200
                if now - S["last_cycle"] >= interval or (interval == 1800 and m % 1800 == 0 and now - S["last_cycle"] > 60):
                    cycle(now)
            if RT["dirty"]: save_state()
    except Exception as e:
        log(f"clock error: {e}\n{traceback.format_exc()}")
        decision("engine_error", error=f"{type(e).__name__}: {e}", tb=traceback.format_exc()[-800:])
    reactor.callLater(2, clock)


# ------------------------------------------------------------------ API
def send(c, r, timeout=30):
    d = c.send(r, responseTimeoutInSeconds=timeout)
    d.addErrback(lambda f: log(f"request {type(r).__name__} failed: {f.value}"))


def request_backfill(c):
    now_ms = int(time.time() * 1000)
    for k, (name, sid) in enumerate(RT["name2sid"].items()):
        frm = time.time() - 36 * 3600     # full history for plug-ins; replay() only uses bars after last_seen
        r = ProtoOAGetTrendbarsReq(); r.ctidTraderAccountId = RT["acct"]; r.symbolId = sid; r.period = 1
        r.fromTimestamp = int(frm * 1000); r.toTimestamp = now_ms
        RT["backfill_pending"].add(name); reactor.callLater(0.5 * k, send, c, r, 60)   # historical limit 5 req/s


def replay(name, bars):
    """restart catch-up: replay M1 bid bars after the last seen quote through the order/exit logic (stop-first
    pessimistic path, spread = last known/normal)."""
    since = S["last_seen"].get(name, 0)
    sp = normal_spread(name)
    n = 0
    for b in bars:
        if b["t"] + 60 <= since: continue
        if not any(x["sym"] == name for x in S["positions"] + S["shadows"] + S["pending"]): break
        path = [b["o"], b["h"], b["l"], b["c"]] if b["c"] < b["o"] else [b["o"], b["l"], b["h"], b["c"]]
        for k, px in enumerate(path):
            t = b["t"] + 15 * k
            Q[name] = dict(bid=px, ask=px + sp, t=t)
            check_pending(name, t, replay=True); check_exits(name, t, replay=True)
        n += 1
    if n: decision("restart_replay", symbol=name, bars=n, since=J.now_iso(since))


def on_msg(c, m):
    pt = m.payloadType
    if pt == ProtoOASpotEvent().payloadType:
        e = Protobuf.extract(m); name = RT["sid2name"].get(e.symbolId)
        if not name: return
        q = Q.get(name, {})
        bid = e.bid / 1e5 if e.HasField("bid") else q.get("bid"); ask = e.ask / 1e5 if e.HasField("ask") else q.get("ask")
        if bid is None or ask is None: return
        RT["last_spot"] = time.time()
        on_quote(name, bid, ask, time.time())
        return
    if pt == ProtoOAErrorRes().payloadType:
        e = Protobuf.extract(m); log(f"API error {e.errorCode}: {e.description}")
        if RT["backfill_pending"]: RT["backfill_pending"].clear(); subscribe(c)
        return
    if pt == ProtoOAApplicationAuthRes().payloadType:
        r = ProtoOAGetAccountListByAccessTokenReq(); r.accessToken = os.environ["CTRADER_ACCESS_TOKEN"]; send(c, r)
    elif pt == ProtoOAGetAccountListByAccessTokenRes().payloadType:
        acc = {a.ctidTraderAccountId: a for a in Protobuf.extract(m).ctidTraderAccount}
        a = acc.get(R.DEMO_ACCOUNT)
        if a is None or a.isLive is not False or R.DEMO_ACCOUNT in R.LIVE_ACCOUNTS:
            log("demo account guard failed; exiting"); return stop(3)
        RT["acct"] = R.DEMO_ACCOUNT
        r = ProtoOAAccountAuthReq(); r.ctidTraderAccountId = RT["acct"]; r.accessToken = os.environ["CTRADER_ACCESS_TOKEN"]; send(c, r)
    elif pt == ProtoOAAccountAuthRes().payloadType:
        r = ProtoOASymbolsListReq(); r.ctidTraderAccountId = RT["acct"]; send(c, r)
    elif pt == ProtoOASymbolsListRes().payloadType:
        ids = {s.symbolName: s.symbolId for s in Protobuf.extract(m).symbol}
        RT["name2sid"] = {s: ids[s] for s in SYMBOLS if s in ids}
        RT["sid2name"] = {v: k for k, v in RT["name2sid"].items()}
        missing = [s for s in SYMBOLS if s not in ids]
        if missing: decision("assumption", note=f"symbols not found on demo: {missing}")
        request_backfill(c)
    elif pt == ProtoOAGetTrendbarsRes().payloadType:
        e = Protobuf.extract(m); name = RT["sid2name"].get(e.symbolId)
        bars = []
        for tb in e.trendbar:
            lo = tb.low / 1e5
            bars.append(dict(t=tb.utcTimestampInMinutes * 60, o=lo + tb.deltaOpen / 1e5, h=lo + tb.deltaHigh / 1e5, l=lo, c=lo + tb.deltaClose / 1e5))
        bars.sort(key=lambda x: x["t"])
        if name:
            have = {b["t"] for b in BARS.get(name, [])}
            BARS[name] = sorted(BARS.get(name, []) + [b for b in bars if b["t"] not in have], key=lambda x: x["t"])[-5000:]
            try: replay(name, bars)
            except Exception as ex: decision("engine_error", error=f"replay {name}: {ex}")
            RT["backfill_pending"].discard(name)
        if not RT["backfill_pending"]: subscribe(c)
    elif pt == ProtoOASubscribeSpotsRes().payloadType:
        RT["live"] = True; RT["last_spot"] = time.time()
        log(f"spot subscription OK: {sorted(RT['name2sid'])}; backfilled bars: { {k: len(v) for k, v in BARS.items()} }")
        decision("engine_start", host=f"{HOST}:{PORT}", account_isLive=False, symbols=sorted(RT["name2sid"]),
                 equity=round(equity(), 4), positions=len(S["positions"]), pending=len(S["pending"]))


def subscribe(c):
    if RT.get("subscribed"): return
    RT["subscribed"] = True
    r = ProtoOASubscribeSpotsReq(); r.ctidTraderAccountId = RT["acct"]; r.subscribeToSpotTimestamp = True
    for sid in RT["name2sid"].values(): r.symbolId.append(sid)
    send(c, r)


def stop(code=0):
    RT["exit"] = code
    try: save_state(); save_spreads()
    except Exception: pass
    if reactor.running: reactor.stop()


def main():
    assert HOST == "demo.ctraderapi.com" and PORT == 5035, "demo host only"
    if not R.sha_ok(): log("RISK_LIMITS.md hash mismatch -> refusing to start"); sys.exit(20)
    bad = R.paper_only_ok()
    if bad: log(f"order-capable code found {bad} -> refusing to start"); sys.exit(21)
    for k in ("CTRADER_CLIENT_ID", "CTRADER_CLIENT_SECRET", "CTRADER_ACCESS_TOKEN"):
        if not os.environ.get(k): log(f"{k} missing"); sys.exit(1)
    os.makedirs(os.path.join(P, "state"), exist_ok=True); os.makedirs(os.path.join(P, "reports"), exist_ok=True)
    load_state(); load_news_slip()
    if S["halted"] or os.path.exists(HALTED):
        log(f"program HALTED ({S['halted']}); engine runs idle (no trading)")
    if time.time() > PROGRAM_END and not S.get("ended"):
        S["ended"] = J.now_iso(); decision("program_end", note="21-day window over; no new entries (exits still managed)")
    c = Client(HOST, PORT, TcpProtocol)
    c.setConnectedCallback(lambda cl: (log(f"connected to {HOST}"), cl.send(ProtoOAApplicationAuthReq(
        clientId=os.environ["CTRADER_CLIENT_ID"], clientSecret=os.environ["CTRADER_CLIENT_SECRET"]))))
    c.setDisconnectedCallback(lambda cl, reason: (log("disconnected; exiting for supervisor restart"), stop(4)))
    c.setMessageReceivedCallback(on_msg)
    c.startService()
    reactor.callLater(2, clock)
    reactor.run()
    sys.exit(RT["exit"])


if __name__ == "__main__":
    main()
