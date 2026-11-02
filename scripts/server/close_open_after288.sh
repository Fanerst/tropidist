#!/bin/bash
# Follow-up on 5090 once the smaller closing runs moved to 5090c (close_open_5090c.sh): when Tanner [[288,2]],
# already running on cores 128-159 from close_open.sh, has written its record, mitten 300 runs on the same cores.
# usage: (setsid nohup bash scripts/server/close_open_after288.sh > logs/close/after288.log 2>&1 < /dev/null &)
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
REC=results/bench_extended/ours_pipeline__dp-2/wjh_qt_288_2_24__full__t32.json
until [ -f $REC ]; do sleep 60; done
echo "$(date '+%F %T') start mitten_300 (sector) on 128-159"
$PY bench/run_matrix.py --methods ours_pipeline:dp=2 --instances mitten_300 --variants sector --threads 32 \
    --time-limit 604800 --mem-gb 90 --total-mem-gb 90 --jobs 1 --cpus 128-159 --out results/bench_extended \
    >> logs/close/mitten_300.log 2>&1
echo "$(date '+%F %T') end mitten_300"
