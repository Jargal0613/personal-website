#!/usr/bin/env bash
# Stops the paper engine + supervisor and disables auto-start until program_start.sh is run. State is preserved.
PROJECT=/workspace/projects/ai-trading; PS=$PROJECT/program/state
touch "$PROJECT/ops/PROGRAM_DISABLED"
[ -f $PS/engine_supervisor.pid ] && kill -TERM "$(cat $PS/engine_supervisor.pid)" 2>/dev/null
for i in $(seq 1 20); do flock -n "$PROJECT/ops/.program_supervisor.lock" true 2>/dev/null && break; sleep 0.5; done
pkill -TERM -f "program/engine.py" 2>/dev/null
echo "paper engine stopped (auto-start disabled; run ops/program_start.sh to re-enable)"
