#!/usr/bin/env bash
PROJECT=/workspace/projects/ai-trading; D=$PROJECT/data
if flock -n "$PROJECT/ops/.news_supervisor.lock" true 2>/dev/null; then echo "news supervisor: NOT running"
else echo "news supervisor: running (pid $(cat $D/news_recorder_supervisor.pid 2>/dev/null))"; fi
if [ -f $D/news_recorder.pid ] && kill -0 "$(cat $D/news_recorder.pid)" 2>/dev/null; then
  ps -o pid,etime,args -p "$(cat $D/news_recorder.pid)" | cat; else echo "recorder: NOT running"; fi
[ -f "$PROJECT/ops/NEWS_DISABLED" ] && echo "NOTE: ops/NEWS_DISABLED present (auto-start disabled)"
[ -f $D/news_recorder.heartbeat ] && echo "heartbeat age: $(( $(date +%s) - $(stat -c %Y $D/news_recorder.heartbeat) ))s"
echo "tick files: $(ls $D/news_ticks/20*.csv 2>/dev/null | wc -l), rows: $(cat $D/news_ticks/20*.csv 2>/dev/null | grep -vc recv_ts)"
python3 - <<'PY'
import json, time
from datetime import datetime, timezone, timedelta
try:
    d = json.load(open("/workspace/projects/ai-trading/data/news_schedule.json"))
except Exception:
    print("no schedule yet"); raise SystemExit
now = time.time()
print(f"schedule updated {datetime.fromtimestamp(d.get('updated', 0), timezone.utc):%Y-%m-%d %H:%M} UTC; upcoming releases (next 14 days):")
for e in d["events"]:
    if now - 1800 < e["t"] < now + 14 * 86400:
        t = datetime.fromtimestamp(e["t"], timezone.utc)
        print(f"  {(t + timedelta(hours=8)):%a %m-%d %H:%M} UB (UTC+8) | {t:%a %m-%d %H:%M} UTC | {e['cur']} {e['title']}")
PY
echo "--- last log lines"; tail -n 6 $D/news_recorder.log 2>/dev/null
