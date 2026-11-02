#!/usr/bin/env bash
# Idempotent: start the news-recorder supervisor unless it is running or ops/NEWS_DISABLED exists.
# Called from ~/.bashrc and ~/.profile (there is no systemd or cron on this box).
PROJECT=/workspace/projects/ai-trading
[ -f "$PROJECT/ops/NEWS_DISABLED" ] && exit 0
if flock -n "$PROJECT/ops/.news_supervisor.lock" true 2>/dev/null; then
  setsid nohup "$PROJECT/ops/run_news_recorder.sh" >/dev/null 2>&1 < /dev/null &
  echo "news recorder supervisor started"
fi
