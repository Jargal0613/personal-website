#!/usr/bin/env bash
PROJECT=/workspace/projects/ai-trading
rm -f "$PROJECT/ops/PROGRAM_DISABLED"
"$PROJECT/ops/program_ensure_running.sh" || true
sleep 3; "$PROJECT/ops/program_status.sh"
