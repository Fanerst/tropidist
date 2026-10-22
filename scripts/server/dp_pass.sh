#!/bin/bash
# 22 October 2026, after the lift fix (commit 6dac207):
#   dp1   first tier of the pipeline with the dense Rank DP front end (config dp=1; cdist/auto.py), every instance,
#         the limits of the first tier: 1 thread / 600 s / 16 GB / 18 jobs, on the physical cores of socket 1
#   wjh   the same for the instances of arXiv:2603.22532 (circuits: sector problem; codes as they are),
#         results/bench_wjh, after the dp1 pass
#   tier2 the five second-tier reruns of the lift fix repeated on the physical cores of socket 0, where the original
#         second-tier pass ran (the reruns on socket 1 were 15-35 % slower in stages the fix does not touch)
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
L=results/lift_fix_rerun
REDO="--redo status=exact --redo status=timeout --redo status=bounds --redo status=skipped --redo status=error"
if [ "$1" = wjh ]; then
  while [ ! -f $L/dp1.done ]; do sleep 60; done
  for tv in "circuit sector" "code full"; do
    set -- $tv
    $PY bench/run_matrix.py --methods "ours_pipeline:dp=1" --instances @results/bench_wjh/instances_$1.txt \
        --variants $2 --instance-dir bench/instances_wjh --threads 1 --time-limit 600 --mem-gb 16 --total-mem-gb 288 \
        --jobs 18 --cpus 96-191 --out results/bench_wjh --give-up 2 $REDO >> logs/bench/dp1_wjh_tier1.log 2>&1
  done
  touch $L/dp1_wjh.done
elif [ "$1" = dp1 ]; then
  $PY bench/run_matrix.py --methods "ours_pipeline:dp=1" --instances all --variants sector,full --threads 1 \
      --time-limit 600 --mem-gb 16 --total-mem-gb 288 --jobs 18 --cpus 96-191 --out results/bench --give-up 2 $REDO \
      >> logs/bench/dp1_tier1_final.log 2>&1
  touch $L/dp1.done
else
  T2="--threads 32 --time-limit 3600 --mem-gb 90 --total-mem-gb 270 --jobs 3 --cpus 0-95 --give-up 1"
  $PY bench/run_matrix.py --methods ours_pipeline --instances @$L/tier2.txt --variants sector \
      --out results/bench_tierB $T2 $REDO >> logs/bench/rerun_lift_fix_t2_socket0.log 2>&1
  $PY bench/run_matrix.py --methods ours_pipeline --instances @$L/wjh_tier2.txt --variants sector \
      --instance-dir bench/instances_wjh --out results/bench_wjh_tierB $T2 $REDO >> logs/bench/rerun_lift_fix_t2_socket0.log 2>&1
  touch $L/tier2_socket0.done
fi
