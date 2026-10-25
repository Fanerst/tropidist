#!/bin/bash
# Structured-mitten audit, fourth batch on 5090: restricted witness searches (data errors plus hook faults at one or
# two schedule positions, papers/mitten_restricted_isd.py) for the circuits whose exact search is still open.
# usage, from the repo root on the server: bash scripts/server/smitten_batch4.sh "600,120,14 X" "840,168,18 Z" ...
cd "$(dirname "$0")/../.." || exit 1
P=${PYTHON:-$HOME/miniconda3/envs/planarnet/bin/python}
THREADS=${THREADS:-8}
SECONDS_PER_SUBSET=${SECONDS_PER_SUBSET:-60}
mkdir -p logs/smitten results/papers
export MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

for job in "$@"; do
    read -r code b <<< "$job"
    IFS=, read -r n k d <<< "$code"
    (OMP_NUM_THREADS=$THREADS setsid nohup "$P" papers/mitten_restricted_isd.py "structured_mitten/[[$code]]" $b \
        "results/papers/smitten${n}d${d}_${b}_risd.json" "$SECONDS_PER_SUBSET" 3 \
        > "logs/smitten/risd_${n}d${d}_$b.log" 2>&1 < /dev/null &)
done
