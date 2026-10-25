#!/bin/bash
# Structured-mitten audit, sixth batch on 5090: witness searches for [[840,168,18]] by exhaustive search restricted to
# data errors and hooks after a check's second or third gate (papers/mitten_restricted_exact.py), first with the
# depth-2 table (weights up to 10; 2 x 16 threads), then with the depth-3 table from weight 11 (about 107 GB each;
# 2 x 100 threads, run alone with the code-distance search of batch 3).
# usage, from the repo root on the server: bash scripts/server/smitten_batch6.sh k2 | k3
cd "$(dirname "$0")/../.." || exit 1
P=${PYTHON:-$HOME/miniconda3/envs/planarnet/bin/python}
mkdir -p logs/smitten results/papers
export MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

for b in Z X; do
    if [ "$1" = k2 ]; then
        (OMP_NUM_THREADS=16 setsid nohup "$P" papers/mitten_restricted_exact.py "structured_mitten/[[840,168,18]]" $b \
            "results/papers/smitten840d18_${b}_rex23.json" 2,3 16 2 0 3 > "logs/smitten/rex23_840d18_$b.log" 2>&1 < /dev/null &)
    else
        (OMP_NUM_THREADS=100 setsid nohup "$P" papers/mitten_restricted_exact.py "structured_mitten/[[840,168,18]]" $b \
            "results/papers/smitten840d18_${b}_rex23k3.json" 2,3 12 3 0 3 11 > "logs/smitten/rex23k3_840d18_$b.log" 2>&1 < /dev/null &)
    fi
done
