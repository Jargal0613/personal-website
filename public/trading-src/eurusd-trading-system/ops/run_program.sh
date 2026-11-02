#!/usr/bin/env bash
# Supervisor loop for program/engine.py (PAPER-ONLY research engine; read-only DEMO API; no orders).
# - single instance via flock on ops/.program_supervisor.lock
# - restarts the engine if it exits/crashes (backoff 5s..300s, reset after a 10-min healthy run)
# - watchdog: restarts if program/state/engine.heartbeat is older than 10 min
# - credentials: inherited env vars; missing CTRADER_* are filled from the chmod-600 .env (never printed).
#   X_BEARER_TOKEN is only inherited from the environment (optional; X sentiment is skipped without it).
set -u
PROJECT=/workspace/projects/ai-trading
PS="$PROJECT/program/state"
LOG="$PS/engine.log"
PIDFILE="$PS/engine.pid"
SUP_PIDFILE="$PS/engine_supervisor.pid"
HEART="$PS/engine.heartbeat"
LOCK="$PROJECT/ops/.program_supervisor.lock"
MAX_LOG_BYTES=$((20*1024*1024))
mkdir -p "$PS"; cd "$PROJECT" || exit 1
exec 9>"$LOCK"
if ! flock -n 9; then echo "program supervisor already running"; exit 0; fi
echo $$ > "$SUP_PIDFILE"
slog() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [supervisor] $*" >> "$LOG"; }
if [ -f "$PROJECT/.env" ]; then
  while IFS='=' read -r k v; do
    case "$k" in CTRADER_CLIENT_ID|CTRADER_CLIENT_SECRET|CTRADER_ACCESS_TOKEN)
      if [ -z "${!k:-}" ]; then export "$k=$v"; fi ;;
    esac
  done < <(grep -E '^CTRADER_[A-Z_]+=' "$PROJECT/.env")
fi
child=0; stopping=0
on_term() { stopping=1; slog "stop signal; terminating engine pid $child"; [ "$child" -gt 0 ] && kill -TERM "$child" 2>/dev/null; }
trap on_term TERM INT HUP
backoff=5
while [ "$stopping" -eq 0 ]; do
  if [ -f "$LOG" ] && [ "$(stat -c %s "$LOG")" -gt "$MAX_LOG_BYTES" ]; then mv "$LOG" "$LOG.1"; fi
  slog "starting program/engine.py"
  start=$(date +%s); date +%s > "$HEART"
  PYTHONUNBUFFERED=1 "$PROJECT/.venv/bin/python" -u -W ignore program/engine.py >> "$LOG" 2>&1 &
  child=$!; echo "$child" > "$PIDFILE"; slog "engine pid $child"
  while kill -0 "$child" 2>/dev/null; do
    sleep 15 & wait $! 2>/dev/null
    [ "$stopping" -eq 1 ] && break
    hb=$(stat -c %Y "$HEART" 2>/dev/null || echo 0)
    if [ $(( $(date +%s) - hb )) -gt 600 ]; then
      slog "STALL: heartbeat older than 10 min; restarting engine"; kill -TERM "$child" 2>/dev/null; break
    fi
  done
  wait "$child" 2>/dev/null; rc=$?
  rm -f "$PIDFILE"
  [ "$stopping" -eq 1 ] && break
  if [ "$rc" -eq 20 ] || [ "$rc" -eq 21 ]; then slog "engine refused to start (rc=$rc: RISK_LIMITS hash / paper-only guard). NOT restarting."; break; fi
  ran=$(( $(date +%s) - start )); [ "$ran" -gt 600 ] && backoff=5
  slog "engine exited rc=$rc after ${ran}s; restarting in ${backoff}s"
  sleep "$backoff" & wait $!
  backoff=$(( backoff * 2 )); [ "$backoff" -gt 300 ] && backoff=300
done
slog "program supervisor exiting"; rm -f "$SUP_PIDFILE"
