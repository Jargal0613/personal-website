#!/usr/bin/env bash
PROJECT=/workspace/projects/ai-trading
rm -f "$PROJECT/ops/NEWS_DISABLED"
"$PROJECT/ops/news_ensure_running.sh" || true
sleep 3; "$PROJECT/ops/news_status.sh"
