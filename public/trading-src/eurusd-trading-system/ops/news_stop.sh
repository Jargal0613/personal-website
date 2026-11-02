#!/usr/bin/env bash
# Stops the news recorder + supervisor and disables auto-start until news_start.sh is run.
PROJECT=/workspace/projects/ai-trading; D=$PROJECT/data
touch "$PROJECT/ops/NEWS_DISABLED"
[ -f $D/news_recorder_supervisor.pid ] && kill -TERM "$(cat $D/news_recorder_supervisor.pid)" 2>/dev/null
for i in $(seq 1 20); do flock -n "$PROJECT/ops/.news_supervisor.lock" true 2>/dev/null && break; sleep 0.5; done
pkill -TERM -f "trading/news_spread_recorder.py" 2>/dev/null
echo "news recorder stopped (auto-start disabled; run ops/news_start.sh to re-enable)"
