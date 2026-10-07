#!/bin/bash
# Remaining runs of the second batch (2026-10-03 evening): sequential designs for the last
# self-dual BB codes, the [[492,170,20]] pair-partition instance, BB360 Z top-down.
# usage: scripts/server/server_remaining.sh design|kasai|bb360z
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
mkdir -p results/papers2/design logs/papers2/design results/phase4 logs/phase4
case "$1" in
  design)
    export OMP_NUM_THREADS=1
    for n in 192 198 200 136 144 150 162 174 186 152 160 168 176 184; do
      $PY papers/design_selfdual_bb.py $n results/papers2/design/sdbb$n.json 96 300 1800 > logs/papers2/design/sdbb$n.log 2>&1
    done
    for n in 138 180; do
      $PY papers/design_selfdual_bb.py $n results/papers2/design/sdbb${n}_long.json 96 600 5400 > logs/papers2/design/sdbb${n}_long.log 2>&1
    done
    touch logs/papers2/design/remaining.done ;;
  kasai)
    export OMP_NUM_THREADS=48
    $PY papers/kasai_codes.py results/papers2/kasai_492.json 20 28800 qc_492 > logs/papers2/kasai_492.log 2>&1
    touch logs/papers2/kasai_492.done ;;
  bb360z)
    bash scripts/server/server_bb360_Z_topdown.sh > logs/phase4/bb360_Z_topdown.out 2>&1 ;;
esac
