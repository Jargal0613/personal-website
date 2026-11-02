#!/usr/bin/env bash
PROJECT=/workspace/projects/ai-trading; PS=$PROJECT/program/state
if flock -n "$PROJECT/ops/.program_supervisor.lock" true 2>/dev/null; then echo "program supervisor: NOT running"
else echo "program supervisor: running (pid $(cat $PS/engine_supervisor.pid 2>/dev/null))"; fi
if [ -f $PS/engine.pid ] && kill -0 "$(cat $PS/engine.pid)" 2>/dev/null; then
  ps -o pid,etime,args -p "$(cat $PS/engine.pid)" | cat; else echo "engine: NOT running"; fi
[ -f "$PROJECT/ops/PROGRAM_DISABLED" ] && echo "NOTE: ops/PROGRAM_DISABLED present (auto-start disabled)"
[ -f "$PS/HALTED" ] && echo "KILL SWITCH: program HALTED: $(cat $PS/HALTED)"
[ -f $PS/engine.heartbeat ] && echo "heartbeat age: $(( $(date +%s) - $(stat -c %Y $PS/engine.heartbeat) ))s"
echo "--- last log lines"; tail -n 8 $PS/engine.log 2>/dev/null
