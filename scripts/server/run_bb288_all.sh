#!/bin/bash
# Full BB288 pipeline (both bases).  Run on a large-memory machine.
set -e
PY=${PY:-python}
mkdir -p results logs
for b in Z X; do
  OMP_NUM_THREADS=${T1:-128} $PY scripts/run_deep.py circuits/bb288_r18_${b}.stim results/bb288_r18_${b}.json --kmax 17 --k-table 4 > logs/bb288_r18_${b}.log 2>&1 &
done
wait
for b in Z X; do
  OMP_NUM_THREADS=${T1:-128} $PY scripts/enum_collapsed.py circuits/bb288_r18_${b}.stim results/enum_bb288_r18_${b}.json 15 4 > logs/enum_bb288_r18_${b}.log 2>&1 &
done
wait
for b in Z X; do
  OMP_NUM_THREADS=${T2:-192} $PY scripts/run_topdown.py circuits/bb288_r18_${b}.stim results/enum_bb288_r18_${b}.json 15 results/topdown_bb288_r18_${b}_W15.json > logs/topdown_bb288_r18_${b}_W15.log 2>&1
done
echo ALL_DONE > logs/bb288_all.done
