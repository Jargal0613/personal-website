#!/usr/bin/env bash
# Stops the supervisor + trader and disables auto-start until start.sh is run.
PROJECT=/workspace/projects/ai-trading; D=$PROJECT/data
touch "$PROJECT/ops/DISABLED"
if [ -f $D/live_paper_supervisor.pid ]; then kill -TERM "$(cat $D/live_paper_supervisor.pid)" 2>/dev/null; fi
for i in $(seq 1 20); do flock -n "$PROJECT/ops/.supervisor.lock" true 2>/dev/null && break; sleep 0.5; done
pkill -TERM -f "$PROJECT/.venv/bin/python -u -W ignore::UserWarning trading/live_paper.py" 2>/dev/null
echo "stopped (auto-start disabled; run ops/start.sh to re-enable)"
