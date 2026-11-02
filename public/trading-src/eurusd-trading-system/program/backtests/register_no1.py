"""Pre-registration of NO1 (2026-10-07 17:3x UTC review cycle). Appended BEFORE its backtest is run."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal as J
if any(r.get("id") == "NO1" and r.get("type") == "hypothesis" for r in J.read(J.HYP)):
    sys.exit("NO1 already registered")
J.append(J.HYP, dict(
    type="hypothesis", id="NO1", version=1, status="proposed",
    title="US500 overnight drift: long into the cash close, out after the next cash open",
    symbols=["US500"], source="program/backtests/bt_no1.py",
    origin="review cycle 2026-10-07 17:3x UTC; news flow: 'Stocks made a record high' while US yields hit 24-year highs; "
           "a non-news, non-FX family not yet tested in this program",
    rules=dict(
        entry="BUY US500 at market at the open of the 15:55 New York M5 bar, Monday-Thursday cash-session days only "
              "(skip if that bar or the next weekday's 09:35 NY bar is missing, e.g. holidays/half days)",
        stop="10.0 index points from the fill ($1.00 at 0.1 units; + 0.5 pt stop slippage = $1.05 risk, under the $1.10 cap)",
        target="none",
        exit="open of the 09:35 New York bar on the next weekday (just after the cash open), or the stop first",
        expected_hold="~17.7 h (one rollover; Thursday entries exit Friday 09:35 NY, well before the Friday 20:45 UTC flat rule)",
        filters="none beyond the calendar; one position at a time",
        data_primary="US500 M5 bid bars 2023-08..2026-10-06 (/workspace/scratch/history/us500_m5.csv)",
        data_secondary="US500 H1 bid bars 2014..2026-10-06, coarse proxy: entry at the 15:00 NY H1 open, exit at the 10:00 NY H1 open "
                       "(adds ~1.5 h of cash-session exposure; stop-first ambiguity)"),
    costs="spread 1.5x the live median (0.6 pt) at both ends (both in the cash session), 0.25 pt entry / 0.5 pt stop-or-time slippage, "
          "no commission, broker swap long -6.26%/yr (~$0.11-0.12 per night at 0.1 units, triple on the reported day)",
    invalidation="screen v1: full-sample after-cost PF < 1.05 or OOS (2024-10-06..2026-10-06) PF < 1.0, or net positive in < 2 calendar years, "
                 "or < 30 trades, or the random-direction control on the same entries does as well; H1 12y PF < 1.0 counts against it; forward kill per RISK_LIMITS s6",
    why_survives_costs="the documented overnight equity premium is a few index points per night at current levels; round-trip cost is ~1.4 pt "
                       "(0.6 spread + 0.75 slippage) plus ~1.2 pt swap, so this is likely MARGINAL; the 10-pt stop truncates gap risk but may cut winners",
    rationale="Cliff, Cooper & Gulen (2008) 'Return differences between trading and non-trading hours'; Kelly & Clark (2011); "
              "Lou, Polk & Skouras (2019, JFE) 'A tug of war: overnight versus intraday expected returns': US equity index returns accrue mostly overnight",
    would_change_mind="random-direction control matching it (it is long-only, so the control mainly tests drift vs. zero); "
                      "profit only in the 2023-24 bull market and not 2025-26; swap eating the whole drift",
    forward_kill=">=15 forward trades with PF<0.8, or 8 consecutive losses (RISK_LIMITS s6)"))
print("registered NO1")
