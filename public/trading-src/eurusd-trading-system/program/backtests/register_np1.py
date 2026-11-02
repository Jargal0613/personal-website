"""Pre-registration of NP1 (2026-10-07 review cycle). Appended BEFORE its backtest is run."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal as J
if any(r.get("id") == "NP1" and r.get("type") == "hypothesis" for r in J.read(J.HYP)):
    sys.exit("NP1 already registered")
J.append(J.HYP, dict(
    type="hypothesis", id="NP1", version=1, status="proposed",
    title="Post-release drift: continue the first-15-minute move after high-impact USD/EUR releases, entered outside the news-cost window",
    symbols=["EURUSD"], source="program/backtests/bt_np1.py",
    origin="review cycle 2026-10-07 09:2x UTC; news flow dominated by scheduled USD data/FOMC minutes and rate repricing; "
           "N1A/N2/N4C/E1C entered at T+2 and were killed by measured news costs, so this tests the same information later, at normal cost",
    rules=dict(
        events="ForexFactory high-impact USD or EUR releases with an exact time (time_masked=False); rows sharing a timestamp = one event",
        signal="m = EURUSD bid open of the T+16 M1 bar minus bid open of the T-1 M1 bar; trade only if |m| >= 10 pips",
        entry="market at the open of the T+16 M1 bar (outside the -2..+15 min news-cost window), direction sign(m)",
        stop="10 pips from fill ($1.00 at 0.01 lot)", target="20 pips from fill ($2.00)",
        exit="T+240 min, or Friday 20:00 UTC, whichever first", expected_hold="15 min - 4 h",
        filters="engine2.entry_ok (no entries 16:00-18:59 New York, none Friday after 14:00 NY or weekends)"),
    invalidation="full-sample after-cost PF < 1.05 or OOS (2024-10-06..2026-10-06) PF < 1.0; or the random-direction control on the same entries does as well; forward kill per RISK_LIMITS s6",
    why_survives_costs="entry after the spike at normal spread (~0.2 pip + 0.6 pip commission + slippage, ~1.2 pip round trip) vs a 20-pip target; break-even win rate ~36%",
    rationale="post-announcement drift: order flow keeps absorbing macro news for hours after the first repricing (Evans & Lyons 2005, 'Do currency markets absorb news quickly?', JIMF; Love & Payne 2008)",
    would_change_mind="random-direction control matching it, a single-regime (one or two years) profit, or < 1.5 trades/week",
    data="EURUSD M1 bid bars 2014-04..2026-10-06 (/workspace/scratch/history/eurusd_m1_12y.csv); econ_calendar.csv 2014-01..2026-10-02",
    forward_kill=">=15 forward trades with PF<0.8, or 8 consecutive losses (RISK_LIMITS s6)"))
print("registered NP1")
