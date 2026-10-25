#!/bin/bash
# Structured-mitten audit, third batch on 5090: code distances (data errors only) of the six structured-mitten codes
# and the abelian lifted-product code [[560,112,14]], both CSS types (2 x 2 x 2 + 5 x 2 x 5 = 58 threads):
# information-set witness, then exhaustive search below it, at most 6 h per threshold.
# usage, from the repo root on the server: bash scripts/server/smitten_batch3.sh
cd "$(dirname "$0")/../.." || exit 1
P=${PYTHON:-$HOME/miniconda3/envs/planarnet/bin/python}
mkdir -p logs/smitten results/papers
export MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

run() {   # threads label code isd-seconds k-table
    local t=$1 label=$2 code=$3 isd=$4 kt=$5
    for b in Z X; do
        (OMP_NUM_THREADS=$t setsid nohup "$P" papers/smitten_code_distance.py "$code" $b \
            "results/papers/smitten_code_${label}_${b}.json" 30 21600 "$isd" "$kt" \
            > "logs/smitten/code_${label}_$b.log" 2>&1 < /dev/null &)
    done
}

run 2 300d9 "structured_mitten/[[300,60,9]]" 120 2
run 2 330d12 "structured_mitten/[[330,66,12]]" 300 2
run 5 alp560d14 "abelian_poly_LP/[[560,112,14]]" 900 3
run 5 600d14 "structured_mitten/[[600,120,14]]" 900 3
run 5 600d16 "structured_mitten/[[600,120,16]]" 900 3
run 5 840d18 "structured_mitten/[[840,168,18]]" 900 3
run 5 1200d20 "structured_mitten/[[1200,240,20]]" 1200 3
