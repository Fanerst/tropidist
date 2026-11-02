#!/bin/bash
# BB [[756,16]] on 5090b, restarted (29 October 2026, 23:45) as the first part of a split run: thresholds up to 32
# (kmax=32) here, threshold 33 alone on the H200 server (close_open_h200.sh).  57 threads: physical cores 32-63 and
# their hyperthreads 96-120 (the 89-thread share of 5090b less Tanner [[396,4]]'s 32 on cores 0-31).  The bounds go to
# logs/close/wjh_bb_n756_k32.progress.json while it runs.
# usage: (setsid nohup bash scripts/server/close_open_5090b_bb756.sh > logs/close/launcher_5090b_bb756.log 2>&1 < /dev/null &)
cd ~/claude_runs/circuit_distance
PY=pyenv/cpython-3.12.15-linux-x86_64-gnu/bin/python3.12
export PYTHONPATH=$PWD/pyenv/site-packages
echo "$(date '+%F %T') start wjh_bb_n756 (kmax 32) on 32-63,96-120"
PIPELINE_PROGRESS=logs/close/wjh_bb_n756_k32.progress.json \
  $PY bench/run_matrix.py --methods ours_pipeline:dp=2,kmax=32 --instances wjh_bb_n756 --variants full \
      --instance-dir bench/instances_wjh --threads 57 --time-limit 604800 --mem-gb 90 --total-mem-gb 90 --jobs 1 \
      --cpus 32-63,96-120 --out results/bench_extended >> logs/close/wjh_bb_n756.log 2>&1
echo "$(date '+%F %T') end wjh_bb_n756"
