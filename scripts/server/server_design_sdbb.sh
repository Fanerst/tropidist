#!/bin/bash
# Exhaustive gate-order search (sequential schedules) for the self-dual BB codes of arXiv:2510.05211.
# usage: scripts/server/server_design_sdbb.sh "<n list>" <processes> <seconds per threshold> <budget seconds per code>
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
export OMP_NUM_THREADS=1
mkdir -p results/papers2/design logs/papers2/design
for n in $1; do
  $PY papers/design_selfdual_bb.py $n results/papers2/design/sdbb$n.json ${2:-64} ${3:-300} ${4:-0} \
      > logs/papers2/design/sdbb$n.log 2>&1
done
touch logs/papers2/design/sdbb.done
