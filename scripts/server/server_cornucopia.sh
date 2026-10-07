#!/bin/bash
# Cornucopia codes (arXiv:2608.02773): circuit distance of the published 12-layer schedule.
# usage: scripts/server/server_cornucopia.sh "<q list>" <threads> [k_coll] [kmax] [seconds per threshold]
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
export OMP_NUM_THREADS=${2:-64}
mkdir -p results/papers2 logs/papers2
for q in $1; do
  for b in Z X; do
    $PY papers/run_parallel.py cornucopia $q $b results/papers2/cornucopia_q${q}_r6_$b.json 6 ${3:-2} ${4:-12} ${5:-0} \
        > logs/papers2/cornucopia_q${q}_r6_$b.log 2>&1
  done
done
touch logs/papers2/cornucopia_"${1// /_}".done
