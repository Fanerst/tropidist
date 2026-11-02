#!/bin/bash
# BB [[756,16]] on the H200 server (Feng, 29 October 2026: use every thread we have; the paper goes out next week):
# threshold 33 alone (kmin=kmax=33), which on 32 threads would take about three times the 32 thresholds before it.
# The run on 5090b (close_open_5090b.sh, kmax=32) excludes the weights up to 32; together with this record that
# gives the lower bound 34, and the codeword of weight 34 (results/bench_extended/isd on 5090) closes it.  If 5090b
# finds a lighter codeword instead, that settles the distance and this record is not needed.
# 134 threads (70% of the 192), on the 96 physical cores 0-95 and the hyperthreads 96-133.
# usage: (setsid nohup bash scripts/server/close_open_h200.sh > logs/close/launcher_h200.log 2>&1 < /dev/null &)
cd ~/claude_runs/circuit_distance
PY=~/anaconda3/bin/python
mkdir -p logs/close
(setsid nohup bash scripts/server/mem_guard.sh 400 > /dev/null 2>&1 < /dev/null &)
echo "$(date '+%F %T') start wjh_bb_n756 threshold 33 on 0-133"
PIPELINE_PROGRESS=logs/close/wjh_bb_n756_k33.progress.json \
  $PY bench/run_matrix.py --methods ours_pipeline:dp=2,kmin=33,kmax=33 --instances wjh_bb_n756 --variants full \
      --instance-dir bench/instances_wjh --threads 134 --time-limit 604800 --mem-gb 200 --total-mem-gb 200 --jobs 1 \
      --cpus 0-133 --out results/bench_extended >> logs/close/wjh_bb_n756.log 2>&1
echo "$(date '+%F %T') end wjh_bb_n756 threshold 33"
pkill -u "$USER" -f "[m]em_guard.sh 400"
touch logs/close/all.done
