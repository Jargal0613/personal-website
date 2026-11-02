#!/usr/bin/env bash
# Idempotent: start the paper-program supervisor unless it is running or ops/PROGRAM_DISABLED exists.
# Called from ~/.bashrc and ~/.profile (no systemd/cron on this box).
PROJECT=/workspace/projects/ai-trading
[ -f "$PROJECT/ops/PROGRAM_DISABLED" ] && exit 0
if flock -n "$PROJECT/ops/.program_supervisor.lock" true 2>/dev/null; then
  setsid nohup "$PROJECT/ops/run_program.sh" >/dev/null 2>&1 < /dev/null &
  echo "program supervisor started"
fi
