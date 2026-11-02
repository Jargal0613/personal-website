"""Apply 'pre-forward screen v1' to the registered hypotheses and append status records (append-only)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal as J

if any(r.get("type") == "status" and r.get("screen") == "pre-forward screen v1" for r in J.read(J.HYP)):
    sys.exit("screen v1 already applied")
RES = "program/backtests/results/"
S = []
def s(id_, status, reason, bt=None, tier=None):
    S.append(dict(type="status", id=id_, version=1, status=status, screen="pre-forward screen v1", tier=tier, reason=reason, backtest=bt))

s("N4B", "rejected", "not tradeable under RISK_LIMITS s2: 0 of 192 historical trades had stop risk <= $1.10 (avg $2.08). "
  "The vol-scaled stop is the edge's structure, so capping it is a different hypothesis (N4C).",
  dict(trades=192, pf=1.17, oos_pf=1.72, oos_t=1.16, risk_capped_trades=0))
s("E1", "rejected", "not tradeable under the $1.10 cap: 0 of 47 trades had risk <= $1.10 (avg $2.19)",
  dict(trades=47, pf=2.30, risk_capped_trades=0))
s("H24", "rejected", "the risk-cap-compatible subset (risk <= $1.10, 139 trades) has PF 0.77 / OOS PF 0.96 / t -1.54; the uncapped "
  "version needs ~$3 risk. In the allowed symbols the capped subset loses on EURUSD/GBPUSD/USDJPY.",
  dict(capped_trades=139, capped_pf=0.77, capped_oos_pf=0.96, capped_t=-1.54, uncapped_pf=1.00, uncapped_oos_pf=1.18))
s("H19", "rejected", "not cost-viable: OOS PF 0.92, t -1.95, 1/10 years positive; avg risk $3.36 > cap",
  dict(oos_trades=4077, oos_pf=0.92, oos_t=-1.95))
s("LBO", "backtested", "MARGINAL tier: full PF 0.99 (fails PASS), OOS PF 1.04 (>=1.0), ~4.9 trades/wk, $1.09 risk fits the cap, "
  "documented session-open rationale. Only 1/4 years positive; low prior odds. Forward-tested as a marginal slot.",
  dict(trades=798, pf=0.99, oos_trades=513, oos_pf=1.04, oos_t=0.44, years_pos="1/4", avg_risk_usd=1.09), tier="MARGINAL")
s("LBO", "forward", "admitted to forward paper testing (marginal slot 1/2). Kill: >=15 trades with PF<0.8 or 8 consecutive losses.",
  tier="MARGINAL")
s("N4C", "rejected", "measured-cost backtest PF 0.75 (t -1.94) over 198 trades, 5/12 years; OOS PF 1.03 on 25 trades. "
  "Capping the stop destroys N4B's (already insignificant) edge. Also max risk $1.28 > $1.10 in news windows.",
  dict(trades=198, pf=0.75, t=-1.94, oos_trades=25, oos_pf=1.03, years_pos="5/12", max_risk_usd=1.28, file=RES + "news_capped_v1.csv"))
s("E1C", "rejected", "backtest PF 1.42 (t 0.94, 50 trades, 6/12 years, only 2 OOS trades), but the measured news costs push "
  "risk at a 9-pip stop to $1.28 > $1.10 cap, so every signal would be skipped. Not re-tuned under this id (no post-hoc stop change).",
  dict(trades=50, pf=1.42, t=0.94, oos_trades=2, years_pos="6/12", max_risk_usd=1.28, file=RES + "news_capped_v1.csv"))
s("NH1", "rejected", "US500 intraday momentum: PF 0.68 (3y M5, 684 trades, OOS t -3.19, 0/4 years) and PF 0.55 (12y H1, 0/13 years). "
  "Clearly negative after costs; the opposite sign is NOT adopted (that would be post-hoc).",
  dict(m5_trades=684, m5_pf=0.68, m5_oos_pf=0.67, m5_oos_t=-3.19, h1_trades=2697, h1_pf=0.55, file=RES + "new_v1_summary.csv"))
s("NH2", "rejected", "local-hours depreciation, pooled: PF 0.88 (12y H1, 17,966 trades, 1/13 years), PF 0.84 (3y M5). No leg reaches PF 1.",
  dict(h1_trades=17966, h1_pf=0.88, h1_oos_pf=0.87, h1_oos_t=-2.95, m5_pf=0.84, file=RES + "new_v1_summary.csv"))
s("NH3", "rejected", "Gotobi USDJPY: PF 0.77 (12y H1, 901 trades, 2/13 years), OOS PF 0.57 (t -3.02); 3y M5 PF 0.74.",
  dict(h1_trades=901, h1_pf=0.77, h1_oos_pf=0.57, m5_pf=0.74, file=RES + "new_v1_summary.csv"))
for r in S: J.append(J.HYP, r)
for k, v in sorted(J.hyp_status().items()): print(f"{k:5s} {v['status']:10s} {v.get('tier') or ''}")
