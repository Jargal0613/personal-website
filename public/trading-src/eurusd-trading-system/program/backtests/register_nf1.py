"""Pre-registration of NF1 (2026-10-08 09:2x UTC review cycle). Appended BEFORE its backtest is run."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal as J
if any(r.get("id") == "NF1" and r.get("type") == "hypothesis" for r in J.read(J.HYP)):
    sys.exit("NF1 already registered")
J.append(J.HYP, dict(
    type="hypothesis", id="NF1", version=1, status="proposed",
    title="Post-London-4pm-fix USD reversal: sell USD (long EURUSD, short USDJPY) just after the WM/Reuters 16:00 London fix, hold 60 min (Krohn, Mueller & Whelan, 'Foreign Exchange Fixings and Returns Around the Clock', JF 2024)",
    symbols=["EURUSD", "USDJPY"], source="program/backtests/bt_nf1.py",
    origin="review cycle 2026-10-08 09:2x UTC; news flow: USD at an 18-month high on hawkish-Fed bets, DXY 'towards 102.85', rising yields, oil > $90 on Iran tensions. "
           "A USD-trend tape is where a mechanical, flow-driven USD pattern (fix-related hedging/rebalancing) would matter; it is a family not yet tested here "
           "(NH3 was the Tokyo Gotobi fix on USDJPY only, unconditional on fix-day calendar).",
    rules=dict(
        session="London business days Mon-Thu plus Fri (DST-correct Europe/London); engine flat-by-Friday-20:45 UTC rule is not binding (exit ~17:05 London)",
        signal="unconditional: every weekday, direction = sell USD (EURUSD +1, USDJPY -1)",
        entry="market at the open of the 16:05 London M5 bar (after the 15:59:30-16:00:30 fix window), buy at ask / sell at bid",
        stop="fixed 10 pips EURUSD, 15 pips USDJPY, set at entry, never moved",
        target="none",
        exit="open of the 17:05 London M5 bar (60 min), or the stop first",
        expected_hold="<= 60 min",
        data_primary="M5 bid bars 2023-08..2026-10-06 (EURUSD from M1 resampled, USDJPY M5)",
        data_secondary="H1 bid bars 2014..2026-10-06 coarse proxy: entry at the 16:00 London H1 open, exit at the 17:00 London H1 open, same stops",
        diagnostic="descriptive only, not a rule: mean USD-direction return 15:00->16:00 London (the paper's pre-fix USD appreciation leg) in the same data, to check the documented pattern exists here"),
    costs="engine2 costs: 1.5x live median spread with floors, 0.2 pip entry / 0.3 pip stop-or-time slippage, $0.03/side commission at 0.01 lot, no swap (flat intraday)",
    invalidation="screen v1: full PF < 1.05 or OOS (2024-10-06..) PF < 1.0, < 2 calendar years positive, < 30 trades, or not beating the random-direction p95 "
                 "on the same entries/stops; H1 12y secondary PF < 1.0 counts against it (single-regime); forward kill per RISK_LIMITS s6",
    why_survives_costs="round trip ~0.7-1.0 pip incl. commission at a liquid hour; the paper reports post-fix USD depreciation of a few basis points on average "
                       "(1 bp EURUSD ~ 1.1 pip). Caveat registered up front: the effect may be smaller than costs at retail size; a cost-kill is a likely outcome",
    risk="EURUSD 10 pip x 1000 = $1.00 + 0.3 pip slip $0.03 + $0.06 comm = $1.09 <= $1.10; USDJPY 15 pip at ~158 ~ $0.95 + slip + comm ~ $1.03 <= $1.10",
    rationale="dealers pre-hedge / benchmark-tracking demand for USD concentrates into the fixing and reverts after it (Krohn, Mueller & Whelan 2024; Evans 2018 JBF on the WMR fix); "
              "the pattern is mechanical flow, not information, so it could recur daily",
    would_change_mind="random-direction control matching it; OOS block worse than in-sample; edge only on one pair; H1 12y proxy losing; the pre-fix diagnostic showing no USD appreciation leg",
    forward_kill=">=15 forward trades with PF<0.8, or 8 consecutive losses (RISK_LIMITS s6)"))
print("NF1 registered")
