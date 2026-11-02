#!/bin/bash
# BB [[648,4]] on 5090c, continued (29 October 2026, about 23:50): the first run (close_open_5090c.sh, stopped) excluded
# the thresholds below KMIN; this one searches KMIN..31 and stops there, and the codeword of weight 32 found by the
# randomised search (results/bench_extended/isd__stop%5Fat-32) closes the distance at 32 if nothing lighter turns up.
# 57 threads: physical cores 0-31 and their hyperthreads 64-88 (the 89-thread share less the hypercube's 32 on 32-63).
# usage: (setsid nohup bash scripts/server/close_open_5090c_bb648.sh KMIN > logs/close/launcher_5090c_bb648.log 2>&1 < /dev/null &)
cd ~/claude_runs/circuit_distance
PY=~/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/bin/python3.12
export PYTHONPATH=$(ls -d ~/envs/torch/lib/python3.12/site-packages)
KMIN=$1
echo "$(date '+%F %T') start wjh_bb_n648 (kmin $KMIN, kmax 31) on 0-31,64-88"
PIPELINE_PROGRESS=logs/close/wjh_bb_n648_k31.progress.json \
  $PY bench/run_matrix.py --methods ours_pipeline:dp=2,kmin=$KMIN,kmax=31 --instances wjh_bb_n648 --variants full \
      --instance-dir bench/instances_wjh --threads 57 --time-limit 604800 --mem-gb 90 --total-mem-gb 90 --jobs 1 \
      --cpus 0-31,64-88 --out results/bench_extended >> logs/close/wjh_bb_n648.log 2>&1
echo "$(date '+%F %T') end wjh_bb_n648"
