"""Core of the EUR/USD paper-trading simulator (fake money only, no broker).

Pure standard library: urllib + json + sqlite3. No real orders are ever sent anywhere.
"""
import json
import math
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# ================================================================ CONFIG
# All account / broker / strategy settings live here.
SYMBOL = "EURUSD=X"
BAR_SECONDS = 3600
PIP = 0.0001

# --- account & broker mechanics
START_BALANCE = 10.0         # USD, fake money
LEVERAGE = 500               # 1:500 -> margin required = units * price / 500 (USD)
MIN_LOT_UNITS = 1000         # broker minimum 0.01 lot (1 standard lot = 100,000 EUR)
LOT_STEP_UNITS = 1000        # 0.01-lot step
STOP_OUT_LEVEL = 0.50        # forced close when margin level (equity / used margin) <= 50%, or equity <= 0
STOPOUT_FILL = "bar_worst"  # "bar_worst": stop-out fills at the bar's worst price (conservative);
                             # "level": fills at the computed stop-out price (or the open if gapped through)
NEGATIVE_BALANCE_PROTECTION = True   # balance can't go below 0 after a gap (typical retail broker)
STANDARD_LOT = 100_000

# --- costs
HALF_SPREAD = 0.5 * PIP      # 1.0 pip round trip: buy at mid+0.5, sell at mid-0.5
STOP_SLIPPAGE = 0.2 * PIP    # extra adverse slippage on stop-loss fills

# --- risk / sizing
RISK_PER_TRADE = 0.01        # target risk 1% of equity per trade (rounded to lot step, floored at min lot)

# --- strategy
FAST_EMA = 20
SLOW_EMA = 50
ATR_LEN = 14
STOP_ATR = 2.0               # stop  = 2 x ATR(14) from entry
TARGET_ATR = 4.0             # target = 4 x ATR(14) from entry (2R)
WARMUP_BARS = 150            # no signals until this many bars of history exist
# ================================================================

LOCAL_TZ = ZoneInfo("Asia/Ulaanbaatar")


class DataError(Exception):
    pass


# ---------------------------------------------------------------- data
def fetch_yahoo_hourly(range_="1mo", retries=3, timeout=20):
    """Return (closed_bars, current_price, fetched_at_epoch).

    closed_bars: list of dicts {ts,o,h,l,c} (ts = bar OPEN time, UTC epoch seconds),
    only bars whose hour has fully ended, sorted, de-duplicated, validated.
    """
    last_err = None
    for attempt in range(retries):
        for host in ("query1", "query2"):
            url = (f"https://{host}.finance.yahoo.com/v8/finance/chart/{SYMBOL}"
                   f"?interval=1h&range={range_}&includePrePost=false")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    payload = json.loads(r.read().decode())
                return _parse_chart(payload)
            except Exception as e:  # network, HTTP, JSON, parse
                last_err = e
        time.sleep(2 * (attempt + 1))
    raise DataError(f"Yahoo Finance fetch failed after {retries} attempts: {last_err}")


def _parse_chart(payload):
    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise DataError(f"Yahoo error: {chart['error']}")
    res = (chart.get("result") or [None])[0]
    if not res or "timestamp" not in res:
        raise DataError("Yahoo response has no data")
    now = time.time()
    q = res["indicators"]["quote"][0]
    bars = {}
    for i, ts in enumerate(res["timestamp"]):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None in (o, h, l, c):
            continue
        if ts % BAR_SECONDS != 0:          # live tick row, not a real bar
            continue
        if ts + BAR_SECONDS > now:         # bar still forming -> not closed
            continue
        if not all(0.5 < x < 2.5 for x in (o, h, l, c)):
            continue
        h, l = max(o, h, l, c), min(o, h, l, c)
        bars[ts] = {"ts": int(ts), "o": o, "h": h, "l": l, "c": c}
    if not bars:
        raise DataError("Yahoo returned no closed hourly bars")
    price = res.get("meta", {}).get("regularMarketPrice")
    closed = [bars[k] for k in sorted(bars)]
    if not price:
        price = closed[-1]["c"]
    return closed, float(price), now


# ---------------------------------------------------------------- indicators
def ema(values, n):
    out, k, prev = [], 2 / (n + 1), None
    for v in values:
        prev = v if prev is None else prev + k * (v - prev)
        out.append(prev)
    return out


def atr(bars, n):
    out, prev_c, a = [], None, None
    for i, b in enumerate(bars):
        tr = b["h"] - b["l"] if prev_c is None else max(
            b["h"] - b["l"], abs(b["h"] - prev_c), abs(b["l"] - prev_c))
        a = tr if a is None else (a * (n - 1) + tr) / n   # Wilder smoothing
        out.append(a)
        prev_c = b["c"]
    return out


def indicators(bars):
    closes = [b["c"] for b in bars]
    return {"fast": ema(closes, FAST_EMA), "slow": ema(closes, SLOW_EMA), "atr": atr(bars, ATR_LEN)}


# ---------------------------------------------------------------- account / engine
def margin_required(units, price):
    return units * price / LEVERAGE


def lots(units):
    return units / STANDARD_LOT


class Account:
    """Paper account. state is a plain JSON-serialisable dict."""

    def __init__(self, state=None):
        self.state = state or {
            "balance": START_BALANCE, "position": None, "pending": None, "next_trade_id": 1}
        self.closed = []   # trades closed during this session (dicts)
        self.opened = []   # trades opened during this session (dicts)
        self.skipped = []  # signals not traded (dicts with reason)

    # -- helpers
    @property
    def balance(self):
        return self.state["balance"]

    def unrealized(self, mid):
        p = self.state["position"]
        if not p:
            return 0.0
        exit_px = mid - HALF_SPREAD if p["side"] == "LONG" else mid + HALF_SPREAD
        return _pnl(p, exit_px)

    def margin_info(self, mid):
        """(equity, used_margin, free_margin, margin_level or None) at a mid price."""
        eq = self.balance + self.unrealized(mid)
        p = self.state["position"]
        used = margin_required(p["units"], mid) if p else 0.0
        return eq, used, eq - used, (eq / used if used else None)

    def _skip(self, side, ts, reason, detail):
        self.skipped.append({"ts": ts, "side": side, "reason": reason, "detail": detail,
                             "balance": self.state["balance"]})

    def _open(self, side, ts, mid_open, sig_atr, reason, run_id):
        bal = self.state["balance"]          # flat at entry -> equity == balance
        sgn = 1 if side == "LONG" else -1
        entry = mid_open + sgn * HALF_SPREAD
        stop_dist = STOP_ATR * sig_atr
        risk_per_unit = stop_dist + HALF_SPREAD + STOP_SLIPPAGE
        # 1% risk sizing, rounded down to lot step, floored at broker minimum
        units = math.floor(RISK_PER_TRADE * bal / risk_per_unit / LOT_STEP_UNITS) * LOT_STEP_UNITS
        floored = units < MIN_LOT_UNITS
        units = max(units, MIN_LOT_UNITS)
        # cap by available margin (equity after paying the entry spread must cover required margin)
        def affordable(u):
            return bal - u * HALF_SPREAD >= margin_required(u, entry)
        if not affordable(MIN_LOT_UNITS) or bal <= 0:
            self._skip(side, ts, "insufficient margin for minimum lot",
                       f"balance ${bal:.2f}, need ${margin_required(MIN_LOT_UNITS, entry):.2f} for "
                       f"{lots(MIN_LOT_UNITS):.2f} lot")
            return None
        capped = False
        while not affordable(units):
            units -= LOT_STEP_UNITS
            capped = True
        risk_usd = units * risk_per_unit
        # price at which margin level would hit the stop-out level
        k = STOP_OUT_LEVEL / LEVERAGE
        if side == "LONG":
            stopout_px = (entry + HALF_SPREAD - bal / units) / (1 - k)
        else:
            stopout_px = (bal / units + entry - HALF_SPREAD) / (1 + k)
        pos = {
            "id": self.state["next_trade_id"], "side": side, "units": units,
            "entry_ts": ts, "entry": entry,
            "stop": entry - sgn * stop_dist, "target": entry + sgn * TARGET_ATR * sig_atr,
            "stopout_px": stopout_px, "margin": margin_required(units, entry),
            "risk_usd": risk_usd, "risk_pct": 100 * risk_usd / bal, "balance_before": bal,
            "sizing_note": ("floored to min lot" if floored else "") + (" capped by margin" if capped else ""),
            "entry_reason": reason, "open_run": run_id,
        }
        self.state["next_trade_id"] += 1
        self.state["position"] = pos
        self.opened.append(dict(pos))
        return pos

    def _close(self, ts, exit_px, reason, run_id):
        p = self.state["position"]
        pnl = _pnl(p, exit_px)
        note = ""
        if NEGATIVE_BALANCE_PROTECTION and self.state["balance"] + pnl < 0:
            note = f" (loss capped by negative-balance protection; raw P&L {pnl:.2f})"
            pnl = -self.state["balance"]
        self.state["balance"] += pnl
        t = dict(p)
        sgn = 1 if p["side"] == "LONG" else -1
        t.update({"exit_ts": ts, "exit": exit_px, "pips": sgn * (exit_px - p["entry"]) / PIP,
                  "pnl": pnl, "exit_reason": reason + note, "close_run": run_id,
                  "balance_after": self.state["balance"]})
        self.state["position"] = None
        self.closed.append(t)
        return t

    # -- the one function that advances the simulation by exactly one closed bar
    def step(self, bars, ind, i, run_id=None):
        """Process bar i. Uses only bars[0..i] and indicators at index <= i."""
        b = bars[i]
        st = self.state

        # 1) execute order decided at the previous bar's close, at THIS bar's open
        pend = st.get("pending")
        if pend:
            st["pending"] = None
            pos = st["position"]
            if pos and pos["side"] != pend["side"]:
                px = b["o"] - HALF_SPREAD if pos["side"] == "LONG" else b["o"] + HALF_SPREAD
                self._close(b["ts"], px, "opposite EMA crossover", run_id)
            if st["position"] is None:
                self._open(pend["side"], b["ts"], b["o"], pend["atr"], pend["reason"], run_id)

        # 2) adverse exits first (stop loss / margin stop-out), then take profit.
        #    Stop-out is filled at the bar's worst price (conservative).
        pos = st["position"]
        if pos:
            so = pos["stopout_px"]
            if pos["side"] == "LONG":
                worst = b["l"] - HALF_SPREAD if STOPOUT_FILL == "bar_worst" else min(so, b["o"]) - HALF_SPREAD
                adverse = max(pos["stop"], so)
                if b["l"] <= adverse:
                    if so >= pos["stop"] or b["o"] <= so:
                        self._close(b["ts"], worst, "STOP-OUT (margin level <= "
                                    f"{STOP_OUT_LEVEL:.0%})", run_id)
                    else:
                        px = min(pos["stop"], b["o"]) - HALF_SPREAD - STOP_SLIPPAGE
                        self._close(b["ts"], px, "stop loss", run_id)
                elif b["h"] >= pos["target"]:
                    px = max(pos["target"], b["o"]) - HALF_SPREAD
                    self._close(b["ts"], px, "take profit", run_id)
            else:
                worst = b["h"] + HALF_SPREAD if STOPOUT_FILL == "bar_worst" else max(so, b["o"]) + HALF_SPREAD
                adverse = min(pos["stop"], so)
                if b["h"] >= adverse:
                    if so <= pos["stop"] or b["o"] >= so:
                        self._close(b["ts"], worst, "STOP-OUT (margin level <= "
                                    f"{STOP_OUT_LEVEL:.0%})", run_id)
                    else:
                        px = max(pos["stop"], b["o"]) + HALF_SPREAD + STOP_SLIPPAGE
                        self._close(b["ts"], px, "stop loss", run_id)
                elif b["l"] <= pos["target"]:
                    px = min(pos["target"], b["o"]) + HALF_SPREAD
                    self._close(b["ts"], px, "take profit", run_id)

        # 3) signal at this bar's close -> order for next bar's open
        if i >= WARMUP_BARS:
            f0, s0, f1, s1 = ind["fast"][i - 1], ind["slow"][i - 1], ind["fast"][i], ind["slow"][i]
            side = None
            if f0 <= s0 and f1 > s1:
                side = "LONG"
            elif f0 >= s0 and f1 < s1:
                side = "SHORT"
            pos = st["position"]
            if side and (pos is None or pos["side"] != side):
                st["pending"] = {"side": side, "atr": ind["atr"][i], "signal_ts": b["ts"],
                                 "reason": f"EMA{FAST_EMA} crossed {'above' if side == 'LONG' else 'below'} EMA{SLOW_EMA}"}


def _pnl(p, exit_px):
    sgn = 1 if p["side"] == "LONG" else -1
    return sgn * (exit_px - p["entry"]) * p["units"]   # EURUSD: P&L already in USD


# ---------------------------------------------------------------- formatting
def fmt_ts(ts):
    return datetime.fromtimestamp(ts, LOCAL_TZ).strftime("%Y-%m-%d %H:%M UTC+8")


def utc_iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
