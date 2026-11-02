"""LBO v1: GBPUSD London opening-range breakout with a $1/$2 bracket. This is the Round-3 H1-A rule, unchanged.
Pre-registered in journal/hypotheses.jsonl, and forward-tested as a MARGINAL candidate (backtest: full PF 0.99,
OOS PF 1.04, 1/4 years positive).
Rule: range = high/low of the M1 bid bars 08:00-08:29 London time. At 08:30 London, place OCO stop entries: buy at
range high + spread (ask), sell at range low - spread (bid), live 3 h. Stop $1.00 / target $2.00 at 0.01 lot
(10 / 20 pips) from the fill. Exit at min(08:00 London + 8 h, 20:00 UTC). One trade per day.
If the engine was not running at 08:30 and the range was already broken by the time it places the orders, the day is
skipped. That matches the backtest, where the first touch after 08:30 is the entry."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

META = dict(id="LBO", version=1, symbols=["GBPUSD"], title="GBPUSD London ORB $1/$2")
LDN = ZoneInfo("Europe/London")
SYM = "GBPUSD"
SL, TP = 0.0010, 0.0020
MIND = ("Kill if >=15 forward trades with PF<0.8 or 8 straight losses. Would also lose confidence if the "
        "random-direction shadow control matches it, since that means no directional edge beyond the bracket.")


def on_minute(ctx):
    now = ctx.now
    lt = datetime.fromtimestamp(now, LDN)
    if lt.weekday() >= 5: return
    day = lt.strftime("%Y-%m-%d")
    days = ctx.state.setdefault("days", {})
    if day in days: return
    op = datetime(lt.year, lt.month, lt.day, 8, 0, tzinfo=LDN).timestamp()
    r_end = op + 1800
    if now < r_end: return
    if now >= r_end + 3 * 3600:
        days[day] = "missed (engine not running in the entry window)"; return
    bars = ctx.bars(SYM, since=op, until=r_end)
    q = ctx.quote(SYM)
    if len(bars) < 20 or q is None:
        days[day] = f"skip: only {len(bars)} range bars / quote {'ok' if q else 'missing'}"
        ctx.log("skip", symbol=SYM, reason=days[day], signal_source="price: London 08:00-08:30 range"); return
    hi = max(b["h"] for b in bars); lo = min(b["l"] for b in bars)
    spread = q[1] - q[0]
    up, dn = hi + spread, lo - spread
    after = ctx.bars(SYM, since=r_end)
    if after and (max(b["h"] for b in after) + spread >= up or min(b["l"] for b in after) <= dn) or q[1] >= up or q[0] <= dn:
        days[day] = "skip: range already broken before the orders could be placed"
        ctx.log("skip", symbol=SYM, reason=days[day], range_high=hi, range_low=lo); return
    expiry = r_end + 3 * 3600
    d_utc = datetime.fromtimestamp(now, timezone.utc)
    exit_by = min(op + 8 * 3600, datetime(d_utc.year, d_utc.month, d_utc.day, 20, 0, tzinfo=timezone.utc).timestamp())
    sig = dict(source="price: GBPUSD London 08:00-08:30 opening range (M1 bid bars, live cTrader demo quotes)",
               range_high=hi, range_low=lo, range_pips=round((hi - lo) / 0.0001, 1), spread_pips=round(spread / 0.0001, 2),
               invalidation="price returns through the stop ($1); time exit at min(16:00 London, 20:00 UTC)",
               expected_hold="1-6 h", why_survives_costs="20-pip target vs ~1.2-pip round-trip cost; break-even win rate ~36.6%",
               would_change_mind=MIND)
    g = f"LBO-{day}"
    ctx.stop_order(SYM, 1, up, SL, TP, expiry, exit_by, sig, group=g, why="buy stop above the London opening range")
    ctx.stop_order(SYM, -1, dn, SL, TP, expiry, exit_by, sig, group=g, why="sell stop below the London opening range")
    days[day] = f"orders placed: buy {up:.5f} / sell {dn:.5f}"
