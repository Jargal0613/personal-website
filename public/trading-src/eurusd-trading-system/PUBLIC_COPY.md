# About this public copy

This is a sanitized copy of a personal research project, published as an educational demo.
It is NOT financial advice. It was only ever paper-traded (simulated) against a cTrader DEMO data feed.
The strategies tested here lost money in backtests and in forward paper trading.

Changes from the original:
- `.env` (real cTrader credentials) removed; see `.env.example`.
- Real cTrader account ids replaced with placeholders; `program/risk.py` reads them from the environment.
- `program/RISK_LIMITS.sha256` regenerated because the account ids in `RISK_LIMITS.md` were redacted.
- Not included: logs, engine state, recorded tick data, the news journal, large trade-level CSVs, raw history
  data, the research/ data folders, and the retired demo-order scripts in ops/.
- Paths such as /workspace/... refer to the original machine and will need adjusting.
