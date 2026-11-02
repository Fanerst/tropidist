#!/bin/bash
# Pilot of the two-gross schedule scan: one thread per schedule and basis, 32 at a time, 12 minutes each.
# usage: (setsid nohup bash run_pilot.sh > logs/pilot.log 2>&1 < /dev/null &)
set -e
cd ~/claude_runs/bb288_scan
PY=~/miniconda3/envs/planarnet/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p logs instances results/pilot
echo "$(date '+%F %T') build the kernel"
$PY -c "import sys; sys.path.insert(0, '.'); from cdist import search; print(search.lib())"
echo "$(date '+%F %T') export"
EXPORT_PROCS=16 $PY pilot_export.py instances instances/names.txt
echo "$(date '+%F %T') run"
$PY bench/run_matrix.py --methods ours_pipeline:dp=2 --instances "$(cat instances/names.txt)" --variants sector \
    --instance-dir instances --threads 1 --time-limit 720 --mem-gb 6 --total-mem-gb 190 --jobs 32 --cpus 128-159 \
    --out results/pilot
echo "$(date '+%F %T') end"
touch logs/pilot.done
