#!/bin/bash
# Remaining self-dual BB design searches, quick codes first; waits for a running search to finish.
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
export OMP_NUM_THREADS=1
while pgrep -f "design_selfdual_bb.py 138" > /dev/null; do sleep 15; done
for n in 140 154 156 170 182 190 196 180 192 198 200 152 160 136 144 150 162 168 174 176 184 186; do
  $PY papers/design_selfdual_bb.py $n results/papers2/design/sdbb$n.json 128 300 1800 > logs/papers2/design/sdbb$n.log 2>&1
done
touch logs/papers2/design/queue.done
