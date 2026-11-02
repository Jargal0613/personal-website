#!/usr/bin/env bash
# Supervisor loop for the EUR/USD live PAPER trader (trading/live_paper.py).
# - singleton via flock on ops/.supervisor.lock
# - restarts the trader if it exits/crashes (exponential backoff, 5s..300s)
# - stall watchdog: restarts if no new signal row for STALL_MIN minutes
#   during FX market hours (skipped Fri 20:00 UTC .. Sun 23:00 UTC)
# - credentials: inherited env vars; any missing ones are filled from the
#   chmod-600 project .env (never printed)
set -u
PROJECT=/workspace/projects/ai-trading
LOG="$PROJECT/data/live_paper.log"
SUP_LOG="$PROJECT/data/live_paper_supervisor.log"
SIGNALS="$PROJECT/data/live_paper_signals.csv"
PIDFILE="$PROJECT/data/live_paper.pid"
SUP_PIDFILE="$PROJECT/data/live_paper_supervisor.pid"
LOCK="$PROJECT/ops/.supervisor.lock"
STALL_MIN=${STALL_MIN:-20}
MAX_LOG_BYTES=$((50*1024*1024))

cd "$PROJECT" || exit 1
exec 9>"$LOCK"
if ! flock -n 9; then echo "supervisor already running"; exit 0; fi
echo $$ > "$SUP_PIDFILE"

slog() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [supervisor] $*" >> "$SUP_LOG"; echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [supervisor] $*" >> "$LOG"; }

# Fill missing credentials from .env without echoing them.
if [ -f "$PROJECT/.env" ]; then
  while IFS='=' read -r k v; do
    case "$k" in CTRADER_CLIENT_ID|CTRADER_CLIENT_SECRET|CTRADER_ACCESS_TOKEN)
      if [ -z "${!k:-}" ]; then export "$k=$v"; fi ;;
    esac
  done < <(grep -E '^CTRADER_[A-Z_]+=' "$PROJECT/.env")
fi

child=0
stopping=0
on_term() { stopping=1; slog "received stop signal; terminating trader pid $child"; [ "$child" -gt 0 ] && kill -TERM "$child" 2>/dev/null; }
trap on_term TERM INT HUP

market_closed() {  # rough FX weekend window in UTC
  local dow hour; dow=$(date -u +%u); hour=$(date -u +%H); hour=$((10#$hour))
  [ "$dow" -eq 6 ] && return 0
  [ "$dow" -eq 5 ] && [ "$hour" -ge 20 ] && return 0
  [ "$dow" -eq 7 ] && [ "$hour" -lt 23 ] && return 0
  return 1
}

backoff=5
while [ "$stopping" -eq 0 ]; do
  if [ -f "$LOG" ] && [ "$(stat -c %s "$LOG")" -gt "$MAX_LOG_BYTES" ]; then mv "$LOG" "$LOG.1"; fi
  slog "starting trading/live_paper.py"
  start=$(date +%s)
  PYTHONPATH="$PROJECT" PYTHONUNBUFFERED=1 "$PROJECT/.venv/bin/python" -u -W ignore::UserWarning trading/live_paper.py >> "$LOG" 2>&1 &
  child=$!
  echo "$child" > "$PIDFILE"
  slog "trader pid $child"
  stalled=0
  while kill -0 "$child" 2>/dev/null; do
    sleep 15 &
    wait $! 2>/dev/null
    [ "$stopping" -eq 1 ] && break
    now=$(date +%s)
    if [ $((now - start)) -gt $((STALL_MIN*60)) ] && ! market_closed; then
      last=$(stat -c %Y "$SIGNALS" 2>/dev/null || echo 0)
      [ "$last" -lt "$start" ] && last=$start
      if [ $((now - last)) -gt $((STALL_MIN*60)) ]; then
        slog "STALL: no new signal row for >${STALL_MIN} min during market hours; restarting trader"
        stalled=1
        kill -TERM "$child" 2>/dev/null
        break
      fi
    fi
  done
  wait "$child" 2>/dev/null; rc=$?
  rm -f "$PIDFILE"
  [ "$stopping" -eq 1 ] && break
  ran=$(( $(date +%s) - start ))
  if [ "$ran" -gt 600 ] || [ "$stalled" -eq 1 ]; then backoff=5; fi
  slog "trader exited rc=$rc after ${ran}s; restarting in ${backoff}s"
  sleep "$backoff" & wait $!
  backoff=$(( backoff * 2 )); [ "$backoff" -gt 300 ] && backoff=300
done
slog "supervisor exiting"
rm -f "$SUP_PIDFILE"
