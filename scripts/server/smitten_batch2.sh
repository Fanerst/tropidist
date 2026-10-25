#!/bin/bash
# Structured-mitten audit, second batch on 5090: exact searches for the three larger hook-free circuits, both
# bases (6 x 32 = 192 threads). Each search stops at the first weight with a solution; its witness is replayed
# on the circuit with as many rounds as the named distance.
# usage, from the repo root on the server: bash scripts/server/smitten_batch2.sh
cd "$(dirname "$0")/../.." || exit 1
P=${PYTHON:-$HOME/miniconda3/envs/planarnet/bin/python}
mkdir -p logs/smitten results/papers
export MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

for code in "600,120,14" "600,120,16" "840,168,18"; do
    IFS=, read -r n k d <<< "$code"
    for b in Z X; do
        (OMP_NUM_THREADS=32 setsid nohup "$P" papers/run_mitten.py "structured_mitten/[[$code]]" $b \
            "results/papers/smitten${n}d${d}_${b}.json" 14 2 0 0 \
            > "logs/smitten/exact_${n}d${d}_$b.log" 2>&1 < /dev/null &)
    done
done
