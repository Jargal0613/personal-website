"""Final report of the 21-day paper program (also triggered automatically by the kill switch).
Usage: python3 program/final_report.py [--reason TEXT]. Writes program/reports/final_report_<UTCstamp>.md and prints it."""
import io
import json
import os
import sys
import time
from contextlib import redirect_stdout
from datetime import datetime, timezone

P = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, P)
import daily_summary
import journal as J
import risk as R
import stats as ST


def main():
    reason = sys.argv[sys.argv.index("--reason") + 1] if "--reason" in sys.argv else "scheduled end of the 21-day window"
    now = time.time()
    out = io.StringIO()
    with redirect_stdout(out):
        print(f"# FINAL REPORT: 21-day paper trading research program\n\nGenerated {J.now_iso(now)}. Reason: {reason}.")
        print("PAPER ONLY: no live or demo orders were placed by the program. No profit is promised or implied.\n")
        print("## Snapshot\n```"); daily_summary.main(); print("```\n")
        st = J.hyp_status()
        print("## Hypothesis journal (latest status per id)\n")
        print("| id | v | status | reason |\n|---|---|---|---|")
        for k, v in sorted(st.items()):
            print(f"| {k} | {v.get('version', 1)} | {v.get('status')} | {str(v.get('reason', '')).replace('|', '/')[:300]} |")
        print("\n## Forward results per hypothesis (promotion test, RISK_LIMITS s8)\n")
        any_tr = False
        for k, v in sorted(st.items()):
            tr = ST.trades(k, int(v.get("version", 1)))
            if not tr: continue
            any_tr = True
            pr = ST.promotion(k, int(v.get("version", 1)), now)
            print(f"### {k} v{v.get('version', 1)}\n```\n{json.dumps({x: pr[x] for x in pr if x != 'criteria'}, indent=1, default=str)}\n"
                  f"criteria: {json.dumps(pr['criteria'])}\n```")
        if not any_tr: print("No closed forward paper trades.")
        all_tr = ST.trades()
        pn = [t["pnl_usd"] for t in all_tr]
        s = ST.summary(pn)
        print(f"\n## Whole program (all hypotheses together; not a promotion test)\n```\n{json.dumps(s, indent=1, default=str)}\n```")
        promoted = [k for k, v in st.items() if v.get("status") == "promoted"]
        print("\n## Verdict\n")
        if promoted:
            print(f"Validated by the pre-registered rule: {promoted}. Read reports/promotion_*.md. Even so, a 21-day paper "
                  "sample is small. No live trading follows without an explicit human decision.")
        else:
            print("No process met the promotion rule (>=30 trades and >=14 days, net > 0, PF >= 1.3, beats the random-direction "
                  "control, t >= 2, max DD < 35%). So no repeatable net-positive process was validated in this window.")
        print("\n## Assumptions logged\n")
        for a in J.read(J.ASSUME): print(f"- [{a['ts_utc']}] {a.get('key')}: {a.get('value')}")
    txt = out.getvalue()
    path = os.path.join(P, "reports", f"final_report_{datetime.now(timezone.utc):%Y%m%dT%H%MZ}.md")
    open(path, "w").write(txt)
    J.append(J.DEC, dict(kind="final_report", path=path, reason=reason))
    print(txt); print(f"[written to {path}]")


if __name__ == "__main__":
    main()
