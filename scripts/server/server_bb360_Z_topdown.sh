#!/bin/bash
# After the BB360 Z collapsed run ends: enumerate every collapsed solution up to weight W
# (with the covering bound) and lift each one, for W = 17 and 18.
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
export OMP_NUM_THREADS=96
while pgrep -f "scripts/run_deep.py circuits/bb360_r24_[Z]" > /dev/null; do sleep 20; done
for W in 17 18; do
  $PY scripts/enum_collapsed.py circuits/bb360_r24_Z.stim results/phase4/enum_cover_bb360_r24_Z_K$W.json $W 3 1 \
      > logs/phase4/enum_cover_bb360_r24_Z_K$W.log 2>&1 || break
  $PY scripts/run_topdown.py circuits/bb360_r24_Z.stim results/phase4/enum_cover_bb360_r24_Z_K$W.json $W \
      results/phase4/topdown_bb360_r24_Z_W$W.json > logs/phase4/topdown_bb360_r24_Z_W$W.log 2>&1 || break
  grep -q "certified lower bound" logs/phase4/topdown_bb360_r24_Z_W$W.log || break
done
touch logs/phase4/bb360_Z_topdown.done
