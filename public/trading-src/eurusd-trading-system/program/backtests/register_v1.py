"""One-time pre-registration (2026-10-07). Appends to journal/hypotheses.jsonl BEFORE the new backtests are run."""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal as J

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if any(r.get("type") == "RISK_LIMITS_REGISTERED" for r in J.read(J.HYP)):
    sys.exit("already registered")
h = hashlib.sha256(open(os.path.join(P, "RISK_LIMITS.md"), "rb").read()).hexdigest()
J.append(J.HYP, dict(type="RISK_LIMITS_REGISTERED", sha256=h, file="program/RISK_LIMITS.md"))

FWD_KILL = ">=15 forward trades with PF<0.8, or 8 consecutive losses (RISK_LIMITS s6)"
SCREEN = dict(
    type="SCREEN", name="pre-forward screen v1",
    pass_tier=("PASS: fixed pre-declared rules (no parameter search); after-cost PF >= 1.05 over the full backtest AND "
               ">= 1.0 in the 2024-10-06..2026-10-06 OOS block; net positive in >= 2 calendar years (regimes); "
               ">= 30 backtest trades; stop risk at min volume <= $1.10 incl. costs (RISK_LIMITS s2)."),
    marginal_tier=("MARGINAL (forward allowed, max 2 slots): PF >= 1.0 in the OOS block and >= 0.95 full; a documented "
                   "economic rationale; >= 1.5 trades/week, so the 21-day forward test can resolve it; risk-cap compatible. "
                   "Disclosure: this tier was written after the prior-round candidates' numbers were known."),
    reject="anything else, including any candidate whose historical stops do not fit the $1.10 risk cap",
    note="the forward test is the real test; the screen only filters out ideas that are clearly dead or untradeable")
J.append(J.HYP, SCREEN)

H = []
def hyp(**k):
    k.setdefault("version", 1); k.setdefault("status", "proposed"); k.setdefault("forward_kill", FWD_KILL)
    H.append(dict(type="hypothesis", **k))

# ---- seeded from earlier rounds (evidence attached at registration; screen applied in screen_v1.py) ----
hyp(id="N4B", title="News analog kNN, vol-scaled bracket (Round 5/6)", symbols=["EURUSD"], source="research/news_strategies.py",
    rules=dict(entry="T+2 min after a high-impact USD/EUR release when >=AGREE of the K nearest past same-type releases "
               "(features z, pre60_atr, prevol_atr) agree on the direction", stop="0.25 x ATR20(D1)", target="2 x stop",
               exit="T+240 min", expected_hold="~1-4 h"),
    invalidation="an OOS PF below 1 or the random-direction control matching it",
    why_survives_costs="the vol-scaled 2:1 bracket is large relative to the measured news spread",
    prior_evidence=dict(trades=192, pf_measured_p75=1.17, t_all=0.95, oos_trades=25, oos_pf=1.72, oos_t=1.16, years_pos="7/12",
                        avg_risk_usd=2.08, file="data/reference/news_measured_backtest.csv"))
hyp(id="E1", title="EU flash-PMI continuation (Round 5/6)", symbols=["EURUSD"], source="research/news_cost_report.py",
    rules=dict(entry="T+2 min after EU flash PMI with |z|>=1, in the surprise direction", stop="0.25 x ATR20(D1)", target="none",
               exit="T+60 min", expected_hold="1 h"),
    invalidation="OOS losses", why_survives_costs="large post-PMI continuation relative to cost",
    prior_evidence=dict(trades=47, pf_measured_p75=2.30, t_all=1.74, oos_trades=2, years_pos="9/12", avg_risk_usd=2.19))
hyp(id="H24", title="Monday gap fill (Round 4)", symbols=["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"], source="research/new_families.py",
    rules=dict(entry="Sunday 18:00 NY first bar, fade the weekend gap if |gap|>=0.15 ATR20(D1)", stop="|gap|", target="gap fill (|gap|)",
               exit="Monday 08:00 NY", expected_hold="minutes to 14 h"),
    invalidation="gap fills no more often than the stop is hit", why_survives_costs="the gap is large relative to the spread (x3 Sunday spread assumed)",
    prior_evidence=dict(trades=1197, pf=1.00, oos_trades=309, oos_pf=1.18, oos_t=1.19, years_pos="5/13", avg_risk_usd=3.01))
hyp(id="LBO", title="GBPUSD London opening-range breakout, $1/$2 bracket (Round 3, H1-A)", symbols=["GBPUSD"],
    source="research/multi_research.py",
    rules=dict(entry="OCO stop entries 1 spread outside the 08:00-08:30 London range, live 3 h", stop="$1.00 at 0.01 lot (10 pips)",
               target="$2.00 (20 pips)", exit="08:00 London + 8 h (max 20:00 UTC)", expected_hold="1-6 h"),
    invalidation="forward PF < 1 after 30 trades", why_survives_costs="a 20-pip target vs a ~1.2-pip round trip; break-even win rate 36.6%",
    prior_evidence=dict(trades=798, pf=0.99, oos_trades=513, oos_pf=1.04, oos_t=0.44, years_pos="1/4", avg_risk_usd=1.09,
                        trades_per_week=4.93, file="data/reference/multi_ranked.csv"))
hyp(id="H19", title="ML LightGBM 6h direction (Round 4)", symbols=["FX7"], source="research/new_families_ml.py",
    rules=dict(entry="walk-forward LGBM probability threshold, H1", stop="ATR-based", target="ATR-based", exit="6 h"),
    invalidation="OOS PF < 1", why_survives_costs="(claimed) filtered high-confidence predictions",
    prior_evidence=dict(oos_trades=4077, oos_pf=0.92, oos_t=-1.95, years_pos="1/10", avg_risk_usd=3.36))

# ---- new pre-registered variants and hypotheses (rules fixed now; backtests not yet run) ----
hyp(id="N4C", title="N4B signal with a risk-cap-compatible bracket", symbols=["EURUSD"], parent="N4B",
    rules=dict(entry="same as N4B (T+2 min, kNN agreement)", stop="min(0.25 x ATR20(D1), 9.0 pips)", target="2 x stop",
               exit="T+240 min", expected_hold="1-4 h"),
    invalidation="backtest PF < 1.05 with measured costs, or forward kill",
    why_survives_costs="keeps N4B's direction model; the stop is capped so risk <= $1.10; costs from the measured news curve")
hyp(id="E1C", title="E1 with a risk-cap-compatible stop", symbols=["EURUSD"], parent="E1",
    rules=dict(entry="same as E1", stop="min(0.25 x ATR20(D1), 9.0 pips)", target="none", exit="T+60 min", expected_hold="1 h"),
    invalidation="backtest PF < 1.05, or forward kill",
    why_survives_costs="the PMI continuation move (median tens of pips) is much larger than the ~1-2 pip measured cost",
    note="~1 event per month (next: 2026-10-23 07:15-08:00 UTC), so it cannot reach 30 forward trades inside the 21-day window")
hyp(id="NH1", title="US500 intraday momentum: first half-hour predicts last half-hour (Gao, Han, Li & Zhou 2018, JFE)",
    symbols=["US500"],
    rules=dict(signal="r1 = US500 price at 10:00 ET / price at prior 16:00 ET - 1", entry="15:30 ET, in the direction of sign(r1)",
               stop="8.0 index points ($0.80 at 0.1 units)", target="none", exit="15:59 ET (before the cash close)",
               expected_hold="29 min", filters="US cash-session days only; skip if |r1| < 0.0005"),
    invalidation="backtest PF < 1.05 or OOS < 1.0; forward kill",
    why_survives_costs="spread ~0.4-0.5 pt vs a typical last-half-hour range of ~10-15 pts; one round trip per day",
    falsification="the published effect is said to be strongest on high-volatility days and to have weakened after publication; "
                  "if PF <= 1 in 2024-26, the effect is arbitraged away")
hyp(id="NH2", title="Local-trading-hours depreciation (Breedon & Ranaldo 2013, JMCB)",
    symbols=["EURUSD", "GBPUSD", "AUDUSD", "USDJPY"],
    rules=dict(legs=["EURUSD short 07:00->11:59 UTC", "GBPUSD short 07:00->11:59 UTC", "EURUSD long 13:00->16:59 UTC",
                     "GBPUSD long 13:00->16:59 UTC", "AUDUSD short 23:00->04:59 UTC", "USDJPY long 00:00->05:59 UTC"],
               stop="10 pips (USD-quoted) / 14 pips USDJPY", target="none", exit="end of the leg window", expected_hold="5-6 h",
               filters="Mon-Fri; no entry on bank-holiday thin days is NOT applied (fixed rules)"),
    invalidation="backtest PF < 1.05 or OOS < 1.0; forward kill",
    why_survives_costs="the documented drift is a few pips per session; only ~0.7-0.9 pip round-trip cost at 0.01 lot (likely marginal)")
hyp(id="NH3", title="Gotobi Tokyo-fix USDJPY drift", symbols=["USDJPY"],
    rules=dict(entry="00:00 UTC (09:00 JST) long USDJPY on gotobi days (5,10,15,20,25, month-end; weekend -> previous Friday)",
               stop="12 pips", target="none", exit="00:55 UTC (09:55 JST fix)", expected_hold="55 min"),
    invalidation="backtest PF < 1.05 or OOS < 1.0; forward kill",
    why_survives_costs="the documented pre-fix USD demand from Japanese importers; ~0.9 pip cost vs a few-pip drift",
    note="~6 trades per month, so it cannot reach 30 forward trades inside the 21-day window")
for h_ in H:
    J.append(J.HYP, h_)
print(f"registered {len(H)} hypotheses; RISK_LIMITS sha256 {h[:12]}...")
