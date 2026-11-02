"""Pre-registration of NT1 (2026-10-07 13:3x UTC review cycle). Appended BEFORE its backtest is run."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal as J
if any(r.get("id") == "NT1" and r.get("type") == "hypothesis" for r in J.read(J.HYP)):
    sys.exit("NT1 already registered")
J.append(J.HYP, dict(
    type="hypothesis", id="NT1", version=1, status="proposed",
    title="Post-Treasury-auction USD softening: short USDJPY 5 min after US nominal coupon auctions close",
    symbols=["USDJPY"], source="program/backtests/bt_nt1.py",
    origin="review cycle 2026-10-07 13:3x UTC; news flow: 10y yield at the highest since 2002 'as traders brace for the key 10-year auction', "
           "US 30y at 24-year highs, USD bid into FOMC minutes; USDJPY near 158 tracks US yields",
    rules=dict(
        events="US Treasury nominal fixed-coupon Note/Bond auctions (fiscaldata.treasury.gov auctions_query: security_type Note|Bond, "
               "floating_rate=No, inflation_index_security=No), 2014-01..2026-10-06, original issues and reopenings; several auctions on one day = one event at the latest close",
        signal="unconditional: every auction event",
        entry="SELL USDJPY at market at the open of the first bar >= competitive close time (ET) + 5 min (results are public by then)",
        stop="14 pips from fill (about $0.89 at 158, $1.00 at 140, at 0.01 lot)", target="28 pips from fill",
        exit="16:45 New York the same day (before the 17:00 rollover, so no swap), or stop/target first",
        expected_hold="5 min - 3.5 h",
        filters="engine2.entry_ok (no entries 16:00-18:59 NY, Friday after 14:00 NY, weekends)",
        data_primary="USDJPY M5 bid bars 2023-08..2026-10-06 (/workspace/scratch/history/usdjpy_m5.csv)",
        data_secondary="USDJPY H1 bid bars 2014-04..2026-10-06, entry at the first H1 open >= close+5 min (coarser; bracket ambiguity resolved stop-first)"),
    invalidation="screen v1: full-sample after-cost PF < 1.05 or OOS (2024-10-06..2026-10-06) PF < 1.0, or net positive in < 2 calendar years, "
                 "or < 30 trades, or the random-direction control on the same entries does as well; secondary H1 12y PF < 1.0 also counts against it; forward kill per RISK_LIMITS s6",
    why_survives_costs="normal-hours USDJPY cost ~0.45 pip spread + 0.6 pip commission equivalent + 0.2/0.3 pip slippage (~1.5 pips round trip) vs a 28-pip target; break-even win rate ~36%",
    rationale="Lou, Yan & Zhang (2013, RFS, 'Anticipated and Repeated Shocks in Liquid Markets'): Treasury prices fall (yields rise) into scheduled auctions as dealers absorb supply, "
              "then recover after the auction. USDJPY co-moves strongly with US yields, so the post-auction yield relief should show up as USD softening vs JPY",
    would_change_mind="random-direction control matching it; profit in only one regime (2023-24 hiking/hold) ; < 1.5 trades/week (then not forward-testable as marginal)",
    forward_kill=">=15 forward trades with PF<0.8, or 8 consecutive losses (RISK_LIMITS s6)"))
print("registered NT1")
