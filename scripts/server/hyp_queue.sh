#!/bin/bash
# Exact distances of rebuilt codes of arXiv:2610.03682; one code after another on 32 cores of socket 0.
# Usage: nohup bash scripts/server/hyp_queue.sh <tag> <seconds per threshold> name1 name2 ... &
cd ~/claude_runs/circuit_distance || exit 1
P=~/miniconda3/envs/planarnet/bin/python
tag=$1; tl=$2; shift 2
export OMP_NUM_THREADS=${THREADS:-32} HYPERBOLIC_TOTAL_SECONDS=0 HYPERBOLIC_MEMORY_GIB=120 HYPERBOLIC_TABLE_GIB=48
for name in "$@"; do
  echo "== $(date '+%m-%d %H:%M:%S') $name"
  taskset -c ${CPUS:-64-95} $P papers/hyperbolic_run.py results/papers4/hyperbolic/server_$tag.json $name 40 $tl 2>&1 | grep -v "^ *K=\|^$" | tail -4
done
echo "== $(date '+%m-%d %H:%M:%S') queue $tag done"
