#!/bin/bash
# Cornucopia [[2304,1156,16]] (close_open.sh): weight 12 of the time-collapsed search took about 20 h on 64 threads, and
# each weight costs 8-9 times the one before, so weight 13 would take about a week there, past the 7-day limit per
# weight.  Once the 64-thread run has excluded weight 12, this stops it and searches weight 13 alone with 236 threads
# (the 268-thread share of 5090 less mitten 300's 32), on every logical CPU but mitten's (128-159 and siblings
# 320-351).  The 5090 copies of Tanner [[396,4]] and BB [[756,16]] (both now run faster on 5090b, close_open_5090b.sh)
# are stopped too, if still running.  The lower bound 14 then rests on two records of the same problem: weights up to 12 in
# results/cornucopia/circ_q64_r8_Z_k13.json and weight 13 in results/cornucopia/circ_q64_r8_Z_w13.json.
# usage: (setsid nohup bash scripts/server/cornucopia_w13.sh LAUNCHER_PID RUN_PID WORKER_PID... \
#             > logs/close/cornucopia_w13.log 2>&1 < /dev/null &)
#   LAUNCHER_PID  close_open.sh, stopped first so that it does not stop the memory guard when its jobs end;
#   RUN_PID       its papers/run_parallel.py;
#   WORKER_PID    the search workers of the two copies, stopped as at a time limit (their harness still writes a record)
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
LAUNCHER=$1
RUN=$2
shift 2
LOG=logs/close/cornucopia2304.log
until grep -q "K=12: " $LOG; do sleep 60; done
if ! grep -q "K=12: exhausted best=None" $LOG; then
  echo "$(date '+%F %T') weight 12 did not end exhausted without a solution; the run continues as it is"
  exit 0
fi
echo "$(date '+%F %T') weight 12 excluded: stopping the 64-thread run and the 5090 copies of Tanner [[396,4]] and BB [[756,16]]"
kill $LAUNCHER
kill $RUN
for w in "$@"; do kill -TERM $w; done
sleep 60
for w in "$@"; do kill -0 $w 2>/dev/null && kill -KILL $w; done
sleep 5
echo "$(date '+%F %T') start weight 13 with 236 threads"
OMP_NUM_THREADS=236 taskset -c 0-127,160-319,352-383 $PY papers/run_parallel.py cornucopia 64 Z results/cornucopia/circ_q64_r8_Z_w13.json \
    8 2 13 604800 1 full 1 13 > logs/close/cornucopia2304_w13.log 2>&1
echo "$(date '+%F %T') weight-13 run ended"
