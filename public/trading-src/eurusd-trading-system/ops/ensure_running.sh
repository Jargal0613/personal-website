#!/usr/bin/env bash
# Idempotent: start the paper-trader supervisor if it is not already running.
PROJECT=/workspace/projects/ai-trading
[ -f "$PROJECT/ops/DISABLED" ] && exit 0
if flock -n "$PROJECT/ops/.supervisor.lock" true 2>/dev/null; then
  setsid nohup "$PROJECT/ops/run_live_paper.sh" >/dev/null 2>&1 < /dev/null &
  echo "live_paper supervisor started"
fi
