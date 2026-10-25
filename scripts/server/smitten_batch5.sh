#!/bin/bash
# Structured-mitten audit, fifth batch on 5090: the exact searches continued from a certified lower bound with
# a depth-3 lookup table (k_table=3: about 24 times faster per thread at weight 8 on [[600,120,16]], but 143 GB and a
# 7-minute build per [[600]] search). Results go to results/papers/smitten<n>d<d>_<basis>_k3.json; the records of
# the k_table=2 runs below the start weight stay in results/papers/smitten<n>d<d>_<basis>.json.
# usage, from the repo root on the server: bash scripts/server/smitten_batch5.sh "600,120,14 Z 10" ...
cd "$(dirname "$0")/../.." || exit 1
P=${PYTHON:-$HOME/miniconda3/envs/planarnet/bin/python}
THREADS=${THREADS:-32}
mkdir -p logs/smitten results/papers
export MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

for job in "$@"; do
    read -r code b start <<< "$job"
    IFS=, read -r n k d <<< "$code"
    (OMP_NUM_THREADS=$THREADS setsid nohup "$P" papers/run_mitten.py "structured_mitten/[[$code]]" $b \
        "results/papers/smitten${n}d${d}_${b}_k3.json" 14 3 0 0 "$start" \
        > "logs/smitten/exact_k3_${n}d${d}_$b.log" 2>&1 < /dev/null &)
done
