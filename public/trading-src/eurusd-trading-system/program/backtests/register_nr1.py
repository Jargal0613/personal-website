"""Pre-registration of NR1 (2026-10-08 05:3x UTC review cycle). Appended BEFORE its backtest is run."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal as J
if any(r.get("id") == "NR1" and r.get("type") == "hypothesis" for r in J.read(J.HYP)):
    sys.exit("NR1 already registered")
J.append(J.HYP, dict(
    type="hypothesis", id="NR1", version=1, status="proposed",
    title="US500 5-minute opening-range breakout: trade the direction of the first cash-session 5-min candle, stop at its opposite extreme, flat before the close (Zarattini & Aziz 2023)",
    symbols=["US500"], source="program/backtests/bt_nr1.py",
    origin="review cycle 2026-10-08 05:3x UTC; news flow: hawkish FOMC minutes, US yields near 24-year highs, 'higher rates splitting the market', "
           "Iran-strike headlines, oil up: US equity opens are driven by overnight macro/geopolitical news, which is the premise of opening-range momentum. "
           "LBO (London FX ORB) is the only forward process; this is the US-equity session analog, a family not yet tested (NH1 was last-half-hour momentum, NO1 overnight drift).",
    rules=dict(
        session="US cash-session days Mon-Fri (DST-correct America/New_York); skip if the 09:30 or 09:35 M5 bar is missing",
        signal="first candle = the 09:30-09:35 NY M5 bid bar (o0,h0,l0,c0). dir = +1 if c0 > o0, -1 if c0 < o0, skip if c0 == o0",
        entry="market at the open of the 09:35 NY M5 bar in direction dir (buy at ask, sell at bid)",
        stop="opposite extreme of the first candle: distance = o1 - l0 for longs, h0 - o1 for shorts (o1 = 09:35 bid open), floored at 2.0 points; "
             "SKIP the day if distance > 10.0 points (RISK_LIMITS s2: 0.1 units x (10 + 0.5 slip) = $1.05 <= $1.10; US500 is spread-only)",
        target="none (the paper's 10R target is effectively never reached intraday)",
        exit="open of the 15:55 NY M5 bar, or the stop first",
        expected_hold="minutes to ~6.3 h",
        data_primary="M5 bid bars 2023-08..2026-10-06 (US500)",
        data_secondary="H1 bid bars 2014..2026-10-06 coarse proxy: first candle = the 09:00-10:00 NY H1 bar (includes 30 min pre-open), entry 10:00 NY H1 open, "
                       "stop at that bar's opposite extreme with the same 2-pt floor and 10-pt skip, exit at the 16:00 NY H1 open"),
    costs="engine2 costs: 1.5x live median spread with a 0.4-pt floor, 0.25 pt entry / 0.5 pt stop-or-time slippage, no commission (spread-only), no swap (flat intraday)",
    invalidation="screen v1: full PF < 1.05 or OOS (2024-10-06..) PF < 1.0, < 2 calendar years positive, < 30 trades, or not beating the random-direction p95 "
                 "on the same entries/stops; H1 12y secondary PF < 1.0 counts against it (single-regime); < 1.5 trades/week fails the marginal tier; forward kill per RISK_LIMITS s6",
    why_survives_costs="round trip ~1-1.5 index points vs a stop of 2-10 points and an intraday hold; if the open-direction day move averages a few points it clears costs. "
                       "Caveat registered up front: the 10-pt skip removes the widest (most volatile) opens, which the paper's results lean on; this tests the cap-compatible subset only",
    rationale="opening-range momentum: the first minutes of the cash session aggregate overnight news and order imbalance; dealer hedging and slow institutional "
              "execution can extend the opening direction (Zarattini & Aziz 2023, 'Can Day Trading Really Be Profitable?', SSRN 4416622, on QQQ)",
    would_change_mind="random-direction control matching it; edge only in long trades in a bull tape; the H1 12y proxy losing; OOS block worse than in-sample",
    forward_kill=">=15 forward trades with PF<0.8, or 8 consecutive losses (RISK_LIMITS s6)"))
print("NR1 registered")
