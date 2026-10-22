#!/bin/bash
# Reruns after the lift fix of 22 October 2026 (lift steps start at the certified lower bound; commit 6dac207).
# Selection: the pipeline records whose stored lift stages spent at least 1 s and 1% of the run below their last
# threshold (finished runs) or 1% of the time limit (unfinished runs), plus the rest of the surface-code series
# d = 17..25 where any member is affected.  Same limits as the original passes (bench/tier_b.py): first tier
# 1 thread / 600 s / 16 GB / 18 jobs on the physical cores of socket 0; second tier 32 threads / 3600 s / 90 GB on
# the physical cores of socket 1.
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
L=results/lift_fix_rerun
mkdir -p $L logs/bench
printf "surface_d17\nsurface_d19\nsurface_d21\nsurface_d23\nsurface_d25\n" > $L/surface.txt
printf "bb108_best_r6\nbb108_r10\nbb144_r12\nbb90_r10\ngross_best_r6\nrouting_90\n" > $L/symmetry_extra.txt
printf "bb288_r18\nrouting_140_13\nsurface_d23\nsurface_d25\n" > $L/tier2.txt
printf "wjh_bb288_circuit\n" > $L/wjh_tier2.txt
REDO="--redo status=exact --redo status=timeout --redo status=bounds --redo status=skipped"
T1="--threads 1 --time-limit 600 --mem-gb 16 --total-mem-gb 288 --jobs 18 --cpus 0-95 --give-up 2"
T2="--threads 32 --time-limit 3600 --mem-gb 90 --total-mem-gb 270 --jobs 3 --cpus 96-191 --give-up 1"
if [ "$1" = tier1 ]; then
  $PY bench/run_matrix.py --methods ours_pipeline --instances @$L/surface.txt --variants sector,full \
      --out results/bench $T1 $REDO >> logs/bench/rerun_lift_fix_t1.log 2>&1
  $PY bench/run_matrix.py --methods "ours_pipeline:cover=0,ours_pipeline:window=0,ours_pipeline:symmetry=0" \
      --instances @$L/surface.txt --variants sector --out results/bench_ablation $T1 $REDO >> logs/bench/rerun_lift_fix_t1.log 2>&1
  $PY bench/run_matrix.py --methods "ours_pipeline:symmetry=0" --instances @$L/symmetry_extra.txt --variants sector \
      --out results/bench_ablation $T1 $REDO >> logs/bench/rerun_lift_fix_t1.log 2>&1
  touch $L/tier1.done
else
  $PY bench/run_matrix.py --methods ours_pipeline --instances @$L/tier2.txt --variants sector \
      --out results/bench_tierB $T2 $REDO >> logs/bench/rerun_lift_fix_t2.log 2>&1
  $PY bench/run_matrix.py --methods ours_pipeline --instances @$L/wjh_tier2.txt --variants sector \
      --instance-dir bench/instances_wjh --out results/bench_wjh_tierB $T2 $REDO >> logs/bench/rerun_lift_fix_t2.log 2>&1
  touch $L/tier2.done
fi
