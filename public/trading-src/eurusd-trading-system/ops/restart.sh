#!/usr/bin/env bash
PROJECT=/workspace/projects/ai-trading
"$PROJECT/ops/stop.sh"; sleep 1; "$PROJECT/ops/start.sh"
