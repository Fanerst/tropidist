#!/bin/bash
# Mitten 300 (6 rounds, sector) moved from 5090 to qiji2 (30 October 2026, at Feng's request), so that its 32 cores on
# 5090 go to the Cornucopia [[2304]] weight-13 search.  qiji2 is the feng2 container (32-CPU quota, 64 GB): Feng's own
# jobs there run with 8 + 4 threads, so this run takes 20 threads on idle physical cores of NUMA node 1, and 28 GB.
# The container has no compiler: cdist/*.so were built on h200 (Ubuntu 22.04, gcc 11.4, -march=sapphirerapids; qiji2
# is a Xeon 8468V), and libgomp comes from the shared torch environment.  The bounds go to
# logs/close/mitten_300.progress.json while it runs.
# usage: (setsid nohup bash scripts/server/close_open_qiji2_mitten.sh > logs/close/launcher_qiji2.log 2>&1 < /dev/null &)
cd /feng2/claude_runs/circuit_distance
export TZ=CST-8
PY=/feng2/envs/torch/bin/python
mkdir -p lib logs/close
ln -sf /feng2/envs/torch/lib/python3.10/site-packages/torch/lib/libgomp.so.1 lib/libgomp.so.1
export LD_LIBRARY_PATH=$PWD/lib
CPUS=53-58,60-69,71-73,75
echo "$(date '+%F %T') start mitten_300 (sector) on $CPUS"
PIPELINE_PROGRESS=logs/close/mitten_300.progress.json \
  $PY bench/run_matrix.py --methods ours_pipeline:dp=2 --instances mitten_300 --variants sector --threads 20 \
      --time-limit 604800 --mem-gb 28 --total-mem-gb 28 --jobs 1 --cpus $CPUS --out results/bench_extended \
      >> logs/close/mitten_300.log 2>&1
echo "$(date '+%F %T') end mitten_300"
