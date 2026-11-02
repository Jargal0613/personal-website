#!/usr/bin/env bash
PROJECT=/workspace/projects/ai-trading
rm -f "$PROJECT/ops/DISABLED"
"$PROJECT/ops/ensure_running.sh" || true
sleep 1; "$PROJECT/ops/status.sh"
