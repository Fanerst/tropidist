#!/bin/bash
# Memory guard for this project's jobs on a shared server.  The machine has a root watchdog that, when
# system memory reaches 92 %, kills EVERY process of the heaviest user's heaviest program name (so all
# of the account's python processes, including other projects').  This guard stops only the jobs that
# run from this directory, long before that: when their total resident memory exceeds LIMIT_GB.
# usage: nohup bash scripts/server/mem_guard.sh [LIMIT_GB] &
LIMIT_GB=${1:-300}
ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
while true; do
  total=0; pids=""
  for p in $(pgrep -u "$USER" ""); do            # every process of the user whose working directory is under ROOT
    cwd=$(readlink /proc/$p/cwd 2>/dev/null)
    case "$cwd" in "$ROOT"*) rss=$(awk '/VmRSS/ {print $2}' /proc/$p/status 2>/dev/null); total=$((total + ${rss:-0})); pids="$pids $p";; esac
  done
  if [ $((total / 1048576)) -ge "$LIMIT_GB" ]; then
    echo "$(date): jobs of $ROOT use $((total / 1048576)) GB >= $LIMIT_GB GB: stopping them" >> "$ROOT/logs/mem_guard.log"
    pkill -u "$USER" -f "scripts/server/server_batch3.sh" 2>/dev/null
    kill $pids 2>/dev/null; sleep 5; kill -9 $pids 2>/dev/null
  fi
  echo "$(date +%H:%M:%S) $((total / 1048576)) GB" > "$ROOT/logs/mem_guard.last"
  sleep 20
done
