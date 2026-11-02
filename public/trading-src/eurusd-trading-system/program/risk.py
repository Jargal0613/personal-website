"""Hard risk limits for the paper program. These mirror RISK_LIMITS.md (immutable; sha256-checked) and are enforced
in code by engine.py. No function here can be configured looser at runtime. Run `python3 risk.py --selftest`."""
import hashlib
import json
import os
import sys

P = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(P)
RISK_FILE = os.path.join(P, "RISK_LIMITS.md")
EXPECTED_SHA = open(os.path.join(P, "RISK_LIMITS.sha256")).read().split()[0]

START_EQUITY = 10.00
SIZE_UP_EQUITY = 20.0          # min volume only until equity >= $20
MAX_RISK_ABS = 1.10            # $ per trade
MAX_RISK_PCT_ABOVE_11 = 0.10   # once equity > $11: min($1.10, 10% equity)
MAX_POSITIONS = 2
MAX_OPEN_RISK_PCT = 0.15
MAX_PER_HYP_SYMBOL = 1
MAX_SPREAD_MULT = 3.0
MAX_MARGIN_PCT = 0.70
DAILY_LOSS_PCT = 0.20
KILL_EQUITY = 4.00
KILL_DD_PCT = 0.50
FRIDAY_FLAT_UTC = (20, 45)
HYP_KILL_MIN_TRADES, HYP_KILL_PF, HYP_KILL_CONSEC = 15, 0.8, 8
PROMO = dict(min_trades=30, min_days=14, min_pf=1.3, min_t=2.0, max_dd_pct=0.35, ctrl_pct=95, ctrl_draws=10000)
FORBIDDEN = ["ProtoOANewOrderReq", "ProtoOAAmendPositionSLTPReq", "ProtoOAClosePositionReq", "ProtoOACancelOrderReq",
             "ProtoOAAmendOrderReq"]
# Account ids come from the environment (see .env.example); the real ids were removed from this public copy.
LIVE_ACCOUNTS = {int(x) for x in os.environ.get("CTRADER_LIVE_ACCOUNT_IDS", "").split(",") if x.strip()}
DEMO_ACCOUNT = int(os.environ.get("CTRADER_DEMO_ACCOUNT_ID", "0"))

FACTS = json.load(open(os.path.join(ROOT, "data", "reference", "symbol_facts_multi.json")))
# normal-condition slippage (price units): (entry, stop exit)
SLIP = {"FX5": (0.00002, 0.00003), "FX3": (0.002, 0.003), "XAUUSD": (0.05, 0.10), "US500": (0.25, 0.5)}
SPREAD_FLOOR = {"EURUSD": 0.00002, "GBPUSD": 0.00002, "AUDUSD": 0.00002, "USDJPY": 0.002, "XAUUSD": 0.12, "US500": 0.4}
QUOTE = {"EURUSD": "USD", "GBPUSD": "USD", "AUDUSD": "USD", "USDJPY": "JPY", "XAUUSD": "USD", "US500": "USD"}


def sha_ok():
    return hashlib.sha256(open(RISK_FILE, "rb").read()).hexdigest() == EXPECTED_SHA


def paper_only_ok():
    """refuse to run if any program file references an order/amend/close API message."""
    bad = []
    for dp, _, fs in os.walk(P):
        for f in fs:
            if f.endswith(".py") and f != "risk.py":
                txt = open(os.path.join(dp, f), errors="ignore").read()
                bad += [f"{f}:{w}" for w in FORBIDDEN if w in txt]
    return bad


def slip(sym):
    if sym in ("XAUUSD", "US500"): return SLIP[sym]
    return SLIP["FX3"] if FACTS[sym]["digits"] == 3 else SLIP["FX5"]


def min_units(sym):
    return FACTS[sym]["minVolume_units"]


def commission_usd(sym, units):
    """round trip. FX $3/lot/side, XAUUSD $3.5/lot/side (broker figures), US500 spread-only."""
    f = FACTS[sym]
    if f["commissionType"] != 2: return 0.0
    return 2 * f["commission"] * units / f["lotSize_units"]


def to_usd(sym, quote_amount, usdjpy_mid):
    return quote_amount / usdjpy_mid if QUOTE[sym] == "JPY" else quote_amount


def margin_usd(sym, units):
    return FACTS[sym]["margin_min_volume"] * units / min_units(sym)


def max_risk(equity):
    return MAX_RISK_ABS if equity <= 11.0 else min(MAX_RISK_ABS, MAX_RISK_PCT_ABOVE_11 * equity)


def size_multiples(equity):
    return 1 if equity < SIZE_UP_EQUITY else max(1, int(equity // 10))


def trade_risk_usd(sym, units, fill, stop, stop_slip, usdjpy_mid):
    return to_usd(sym, abs(fill - stop) * units + stop_slip * units, usdjpy_mid) + commission_usd(sym, units)


def check_entry(acct, sym, hyp_id, fill, stop, stop_slip, usdjpy_mid, spread, normal_spread, news_hyp=False):
    """returns (units, risk_usd, None) or (None, None, reason). acct: dict(equity, open:list of dict(sym,hyp,risk,units),
    day_start, halted, day_blocked)."""
    if acct.get("halted"): return None, None, "kill switch: program halted"
    if acct.get("day_blocked"): return None, None, "daily loss limit hit: no new entries until next UTC day"
    if stop is None or stop == fill: return None, None, "no hard stop"
    eq = acct["equity"]
    if len(acct["open"]) >= MAX_POSITIONS: return None, None, f"max {MAX_POSITIONS} concurrent positions"
    if sum(1 for p in acct["open"] if p["sym"] == sym and p["hyp"] == hyp_id) >= MAX_PER_HYP_SYMBOL:
        return None, None, "already 1 position for this hypothesis/symbol"
    if not news_hyp and normal_spread and spread > MAX_SPREAD_MULT * normal_spread:
        return None, None, f"spread {spread:.5g} > {MAX_SPREAD_MULT}x normal {normal_spread:.5g}"
    open_risk = sum(p["risk"] for p in acct["open"])
    budget = min(max_risk(eq), MAX_OPEN_RISK_PCT * eq - open_risk)
    used_margin = sum(margin_usd(p["sym"], p["units"]) for p in acct["open"])
    mu = min_units(sym)
    for k in range(size_multiples(eq), 0, -1):
        units = k * mu
        r = trade_risk_usd(sym, units, fill, stop, stop_slip, usdjpy_mid)
        if r <= budget + 1e-9 and used_margin + margin_usd(sym, units) <= MAX_MARGIN_PCT * eq:
            return units, r, None
    r1 = trade_risk_usd(sym, mu, fill, stop, stop_slip, usdjpy_mid)
    return None, None, (f"risk ${r1:.2f} at min volume > budget ${max(budget, 0):.2f} (cap ${max_risk(eq):.2f}, "
                        f"open risk ${open_risk:.2f}, 15% equity ${MAX_OPEN_RISK_PCT * eq:.2f}) or margin "
                        f"${used_margin + margin_usd(sym, mu):.2f} > 70% equity")


def kill_check(equity, peak):
    if equity < KILL_EQUITY: return f"equity ${equity:.2f} < ${KILL_EQUITY:.2f}"
    if peak > 0 and (peak - equity) / peak > KILL_DD_PCT: return f"drawdown {(peak - equity) / peak:.0%} from peak ${peak:.2f} > 50%"
    return None


def hyp_kill_check(pnls):
    n = len(pnls)
    w = sum(x for x in pnls if x > 0); l = -sum(x for x in pnls if x < 0)
    pf = w / l if l > 0 else float("inf")
    if n >= HYP_KILL_MIN_TRADES and pf < HYP_KILL_PF: return f"{n} forward trades, PF {pf:.2f} < {HYP_KILL_PF}"
    c = 0
    for x in reversed(pnls):
        if x < 0: c += 1
        else: break
    if c >= HYP_KILL_CONSEC: return f"{c} consecutive losses"
    return None


if __name__ == "__main__" and "--selftest" in sys.argv:
    txt = open(RISK_FILE).read()
    checks = {"sha256": sha_ok(), "paper_only": not paper_only_ok()}
    for needle in ["$10.00", "$1.10", "10% of equity", "**2**", "15% of equity", "80% of start-of-day", "$4.00", "50%",
                   ">= 15 forward trades with PF < 0.8", "8 consecutive losses", "70% of equity", "3x", "PF >= 1.3"]:
        checks[needle] = needle.replace("PF >= 1.3", "profit factor >= 1.3") in txt or needle in txt
    a = dict(equity=10.0, open=[], halted=False, day_blocked=False)
    checks["10pip GBPUSD fits"] = check_entry(a, "GBPUSD", "T", 1.3000, 1.2990, 0.00003, 150, 0.00008, 0.00008)[0] == 1000
    checks["11pip GBPUSD blocked"] = check_entry(a, "GBPUSD", "T", 1.3000, 1.2989, 0.00003, 150, 0.00008, 0.00008)[0] is None
    checks["XAU margin blocked at $10"] = check_entry(a, "XAUUSD", "T", 3800.0, 3799.5, 0.1, 150, 0.2, 0.2)[0] is None
    checks["kill at 3.99"] = kill_check(3.99, 10) is not None and kill_check(9, 10) is None
    checks["hyp kill 8 losses"] = hyp_kill_check([1] + [-1] * 8) is not None
    for k, v in checks.items(): print(f"{'OK ' if v else 'FAIL'} {k}")
    sys.exit(0 if all(checks.values()) else 1)
