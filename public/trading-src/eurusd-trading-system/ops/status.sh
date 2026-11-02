#!/usr/bin/env bash
PROJECT=/workspace/projects/ai-trading; D=$PROJECT/data
if flock -n "$PROJECT/ops/.supervisor.lock" true 2>/dev/null; then echo "supervisor: NOT running"; else echo "supervisor: running (pid $(cat $D/live_paper_supervisor.pid 2>/dev/null))"; fi
if [ -f $D/live_paper.pid ] && kill -0 "$(cat $D/live_paper.pid)" 2>/dev/null; then
  ps -o pid,etime,args -p "$(cat $D/live_paper.pid)" | cat
else echo "trader: NOT running"; fi
[ -f "$PROJECT/ops/DISABLED" ] && echo "NOTE: ops/DISABLED present (auto-start on shell login disabled)"
echo "last signal row: $(tail -n1 $D/live_paper_signals.csv)"
echo "signals file mtime: $(date -r $D/live_paper_signals.csv '+%Y-%m-%d %H:%M:%S %Z')"
echo "--- last supervisor events"; tail -n5 $D/live_paper_supervisor.log 2>/dev/null
