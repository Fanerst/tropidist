#!/bin/bash
# Pilot of the two-gross schedule scan, run stage: one thread per schedule and basis, 32 at a time, 12 minutes each.
set -e
cd ~/claude_runs/bb288_scan
PY=~/miniconda3/envs/planarnet/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
NAMES=$($PY -c "print(','.join(dict.fromkeys(open('instances/names.txt').read().strip().split(','))))")
echo "$(date '+%F %T') run $(echo $NAMES | tr ',' '\n' | wc -l) instances"
$PY bench/run_matrix.py --methods ours_pipeline:dp=2 --instances "$NAMES" --variants sector \
    --instance-dir instances --threads 1 --time-limit 720 --mem-gb 6 --total-mem-gb 190 --jobs 32 --cpus 128-159 \
    --out results/pilot > logs/pilot_matrix.log 2>&1
echo "$(date '+%F %T') end"
touch logs/pilot.done
