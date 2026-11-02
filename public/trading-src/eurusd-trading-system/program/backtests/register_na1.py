"""Pre-registration of NA1 (2026-10-07 21:3x UTC review cycle). Appended BEFORE its backtest is run."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal as J
if any(r.get("id") == "NA1" and r.get("type") == "hypothesis" for r in J.read(J.HYP)):
    sys.exit("NA1 already registered")
J.append(J.HYP, dict(
    type="hypothesis", id="NA1", version=1, status="proposed",
    title="Asian-session mean reversion: fade moves away from the 00:00 UTC open back toward it, flat before London",
    symbols=["EURUSD", "GBPUSD", "AUDUSD", "USDJPY"], source="program/backtests/bt_na1.py",
    origin="review cycle 2026-10-07 21:3x UTC; news flow after the FOMC minutes (hawkish, 'another hike in sight'), US 10y off a 24-year high, "
           "30y gilts > 6%: big moves are concentrated in London/NY data hours, and the Asian session is the thin, news-light part of the day. "
           "Also a structural note: promotion needs >= 30 forward trades in the 21-day window, so only a multi-symbol, near-daily process can ever qualify; "
           "this family is chosen partly for frequency. Not a duplicate of H15 (Asian-range sweep fade in London hours) or NH2 (time-of-day drift).",
    rules=dict(
        anchor="A = open of the 00:00 UTC bar, Monday-Friday UTC days",
        band="k = 0.15 x ATR20(D1, completed 22:00-UTC-boundary days strictly before 00:00 UTC)",
        entry="on a bar CLOSE between 00:30 and 04:55 UTC: close >= A + k -> SELL at the next bar open; close <= A - k -> BUY at the next bar open; "
              "only on a fresh crossing (previous close inside the band); skip if the next open is already back within 0.5 k of A; "
              "one position per symbol at a time, re-entry allowed after the previous one closes and a new crossing occurs",
        stop="$1.00 at min volume: 10 pips EURUSD/GBPUSD/AUDUSD, 15 pips USDJPY (~$0.95)",
        target="limit at A (the 00:00 UTC open), executable side (longs exit on bid >= A, shorts on ask <= A)",
        exit="06:55 UTC bar open (before London) if neither stop nor target hit",
        expected_hold="minutes to ~6 h",
        data_primary="M5 bid bars 2023-08..2026-10-06, 4 symbols",
        data_secondary="H1 bid bars 2014..2026-10-06 (coarse proxy: signals on H1 closes 01:00-04:00 UTC bars, entry next H1 open, exit 07:00 UTC open)"),
    costs="engine2 costs (1.5x live median spread, floor, 0.2/0.3 pip slippage, $0.06 round-trip commission at 0.01 lot, swap if held over 21:00 UTC: never), "
          "PLUS a pre-registered x2 spread multiplier on every bar 00:00-06:59 UTC because Asian-session spreads are wider than the all-day median",
    invalidation="screen v1: full PF < 1.05 or OOS (2024-10-06..) PF < 1.0, < 2 calendar years positive, < 30 trades, or not beating the random-direction p95 on the same entries/brackets; "
                 "H1 12y secondary PF < 1.0 counts against it (single-regime); forward kill per RISK_LIMITS s6",
    why_survives_costs="a winner earns |entry - A| >= ~0.5 k (EURUSD ~5-10 pips) vs ~1.5-2 pips round-trip cost at doubled Asian spreads; it needs a win rate "
                       "well above ~55-60% because the 10-pip stop is about as big as the typical target, so prior odds are LOW",
    rationale="thin-liquidity Asian hours: moves without news are more often order-flow imbalances that mean-revert (liquidity-provision story); "
              "widely used retail 'Asian night scalper' style; low prior, tested because it is frequent enough to be resolvable in 21 days",
    would_change_mind="random-direction control matching it; profit only in one year; PF < 1 on H1 12y; the doubled-spread cost wiping it out",
    forward_kill=">=15 forward trades with PF<0.8, or 8 consecutive losses (RISK_LIMITS s6)"))
print("registered NA1")
