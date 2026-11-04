#!/bin/bash
# Structured-mitten audit (docs/AUDIT.md, docs/notes/PAPERS.md), first batch on 5090: information-set witness
# searches for all five hook-free circuits in both bases, and exact searches for the two smallest codes.
# 10 x 8 + 4 x 32 = 208 threads. Every job is detached; logs go to logs/smitten/.
# usage, from the repo root on the server: bash scripts/server/smitten_batch1.sh
cd "$(dirname "$0")/../.." || exit 1
P=${PYTHON:-$HOME/miniconda3/envs/planarnet/bin/python}
mkdir -p logs/smitten results/papers
export MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

run() {   # threads log-name args...
    local t=$1 log=$2
    shift 2
    (OMP_NUM_THREADS=$t setsid nohup "$P" "$@" > "logs/smitten/$log.log" 2>&1 < /dev/null &)
}

for code in "300,60,9" "330,66,12" "600,120,14" "600,120,16" "840,168,18"; do
    IFS=, read -r n k d <<< "$code"
    for b in Z X; do
        run 8 "isd_${n}d${d}_$b" papers/run_mitten_isd.py "structured_mitten/[[$code]]" $b \
            "results/papers/smitten${n}d${d}_${b}_isd.json" 900 3
    done
done
for code in "300,60,9" "330,66,12"; do
    IFS=, read -r n k d <<< "$code"
    for b in Z X; do
        run 32 "exact_${n}d${d}_$b" papers/run_mitten.py "structured_mitten/[[$code]]" $b \
            "results/papers/smitten${n}d${d}_${b}.json" 12 2 0 0
    done
done
