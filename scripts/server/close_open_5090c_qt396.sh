#!/bin/bash
# Tanner [[396,4]], threshold 26 alone on 5090c, once BB [[648,4]] (close_open_5090c_bb648.sh) has finished (29 October
# 2026).  The run on 5090b (close_open_5090b.sh, kmax=26) excludes the thresholds up to 25 well before then and keeps
# going on 26 as well; whichever finishes threshold 26 first gives the lower bound 27, which the codeword of weight 27
# (results/bench_extended/isd__stop%5Fat-27 on 5090) closes.  89 threads (all of 5090c's share) if the hypercube run
# has ended by then, else 57 on cores 0-31 and hyperthreads 64-88.
# usage: (setsid nohup bash scripts/server/close_open_5090c_qt396.sh > logs/close/launcher_5090c_qt396.log 2>&1 < /dev/null &)
cd ~/claude_runs/circuit_distance
PY=~/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/bin/python3.12
export PYTHONPATH=$(ls -d ~/envs/torch/lib/python3.12/site-packages)
BB648=results/bench_extended/ours_pipeline__dp-2__kmin-31__kmax-31/wjh_bb_n648__full__t57.json
HYPER=results/bench_extended/ours_pipeline__dp-2/hypercube_L4__full__t32.json
until [ -f $BB648 ]; do sleep 60; done
if [ -f $HYPER ]; then CPUS=0-88; THREADS=89; else CPUS=0-31,64-88; THREADS=57; fi
echo "$(date '+%F %T') start wjh_qt_396_4_26 threshold 26 on $CPUS"
PIPELINE_PROGRESS=logs/close/wjh_qt_396_4_26_k26.progress.json \
  $PY bench/run_matrix.py --methods ours_pipeline:dp=2,kmin=26,kmax=26 --instances wjh_qt_396_4_26 --variants full \
      --instance-dir bench/instances_wjh --threads $THREADS --time-limit 604800 --mem-gb 90 --total-mem-gb 90 --jobs 1 \
      --cpus $CPUS --out results/bench_extended >> logs/close/wjh_qt_396_4_26.log 2>&1
echo "$(date '+%F %T') end wjh_qt_396_4_26 threshold 26"
