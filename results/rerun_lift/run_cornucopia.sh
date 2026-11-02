#!/bin/bash
# Waits for the pool of the small rerun jobs (PID given) to end, then reruns the seven Cornucopia enumerations
# with 4 workers of 6 threads (24 threads: within the 268-thread share next to the Cornucopia weight-13 search).
cd ~/claude_runs/rerun_enum
while kill -0 $1 2>/dev/null; do sleep 60; done
echo "$(date '+%F %T') start cornucopia reruns"
~/miniconda3/envs/planarnet/bin/python scripts/rerun_lift_enumerations.py run jobs.json out 4 6 1 2 3 5 6 82 83
echo "$(date '+%F %T') end cornucopia reruns"
