"""Pre-registration of NL1 (2026-10-08 01:3x UTC review cycle). Appended BEFORE its backtest is run."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal as J
if any(r.get("id") == "NL1" and r.get("type") == "hypothesis" for r in J.read(J.HYP)):
    sys.exit("NL1 already registered")
J.append(J.HYP, dict(
    type="hypothesis", id="NL1", version=1, status="proposed",
    title="Equity-to-FX lead-lag: after a sharp 15-min US500 move that AUDUSD/USDJPY have not followed, trade the FX pair in the risk direction for 60 min",
    symbols=["AUDUSD", "USDJPY"], source="program/backtests/bt_nl1.py",
    origin="review cycle 2026-10-08 01:3x UTC; news flow: 'higher yields taking their toll on stocks', Dollar at ~18-month high on hawkish FOMC minutes, "
           "AUD slipping on Fed-hike bets plus Middle East oil risk, Pentagon/Iran headlines: risk sentiment is driving FX through equities. "
           "Cross-asset lead-lag is a family not yet tested in this program (not H16-H18 pairs, which are FX-FX mean reversion). "
           "Frequency matters: only a near-daily process can reach 30 forward trades in 21 days.",
    rules=dict(
        session="signal bars whose CLOSE is between 09:45 and 15:30 New York time, Mon-Fri (US cash session; DST-correct via America/New_York)",
        signal="rU = log(US500 close_t / US500 close_{t-3 bars}) (15 min, M5 bid bars); zU = rU / sdU where sdU = std of all such 15-min US500 returns "
               "in the same 09:45-15:30 NY window over the PRIOR 20 trading days (strictly causal). zX likewise for the FX pair (AUDUSD, USDJPY).",
        entry="|zU| >= 2.0 AND zX * sign(zU) <= 0.5 (the FX pair has not followed the equity move), fresh only (the previous bar did not qualify): "
              "enter at the next M5 bar open in the risk direction: AUDUSD BUY if zU > 0 / SELL if zU < 0; USDJPY BUY if zU > 0 / SELL if zU < 0",
        stop="10 pips AUDUSD ($1.00 at 0.01 lot), 15 pips USDJPY (~$0.95)",
        target="none",
        exit="open of the bar 60 min after entry, or the 15:55 NY bar open, or the stop first",
        expected_hold="<= 60 min",
        limits="one position per symbol at a time (re-entry only after exit and a new fresh signal); engine2 entry_ok blocks Friday after 14:00 NY",
        data_primary="M5 bid bars 2023-08..2026-10-06 (US500, AUDUSD, USDJPY), timestamps joined exactly",
        data_secondary="H1 bid bars 2014..2026-10-06 coarse proxy: 1-bar (60-min) returns on H1 closes 11:00-15:00 NY, same z rules with sd from the prior 20 days, "
                       "entry next H1 open, exit 1 H1 bar later or 16:00 NY"),
    costs="engine2 costs: 1.5x live median spread with a floor, 0.2 pip entry / 0.3 pip stop-or-time slippage, $0.06 round-trip commission at 0.01 lot, "
          "no swap (always flat before 17:00 NY). US cash hours, so no extra session multiplier.",
    invalidation="screen v1: full PF < 1.05 or OOS (2024-10-06..) PF < 1.0, < 2 calendar years positive, < 30 trades, or not beating the random-direction p95 "
                 "on the same entries/brackets; H1 12y secondary PF < 1.0 counts against it (single-regime); forward kill per RISK_LIMITS s6",
    why_survives_costs="round trip ~1.2-1.6 pips; a 2-sigma 15-min equity shock is a large, public risk signal, and if FX catches up by even ~3 pips on average "
                       "over the next hour it clears costs; the 10/15-pip stop is ~1.5x the typical 1-h range, so few stop-outs",
    rationale="information diffusion across asset classes: index futures are the main venue for macro risk news in US hours and are often found to lead "
              "risk-sensitive currencies (AUD, JPY crosses) at intraday horizons; also slow-moving cross-asset hedging/rebalancing flows",
    would_change_mind="random-direction control matching it; edge only in one symbol or one year; the lag being gone in the 2024-26 OOS block (arbitraged away)",
    forward_kill=">=15 forward trades with PF<0.8, or 8 consecutive losses (RISK_LIMITS s6)"))
print("NL1 registered")
