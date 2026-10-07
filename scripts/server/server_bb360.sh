#!/bin/bash
# Phase 4: covering-bound search.  Regression on BB288 (known answer), then BB360 lower bounds.
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
mkdir -p results/phase4 logs/phase4
OMP_NUM_THREADS=128 $PY scripts/run_deep.py circuits/bb288_r18_Z.stim results/phase4/deep_cover_bb288_r18_Z.json \
    --cover --skip-ub --k-table 3 --kmax 16 > logs/phase4/deep_cover_bb288_r18_Z.log 2>&1
for b in Z X; do
  OMP_NUM_THREADS=96 nohup $PY scripts/run_deep.py circuits/bb360_r24_$b.stim results/phase4/deep_cover_bb360_r24_$b.json \
    --cover --skip-ub --k-table 3 --kmax 20 --start 14 --time-limit 43200 > logs/phase4/deep_cover_bb360_r24_$b.log 2>&1 &
done
wait
touch logs/phase4/bb360.done
