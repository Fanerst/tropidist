#!/bin/bash
# Second tier of dp=2 on mitten_200, sector problem, outside the give-up chain of bench/tier_b.py dp2b (32 threads,
# 90 GB, 3600 s, cores 160-191, under the project's memory guard), 23 October 2026.  In that chain mitten_300 runs
# first, and after its timeout give-up 1 skips the larger mitten_200.  The default configuration's second-tier
# record of mitten_200 comes from a separate run as well (5 October), so this one is its counterpart.
# usage: (setsid nohup bash scripts/server/dp2_tier2_mitten200.sh > /dev/null 2>&1 < /dev/null &)
cd "$(dirname "$0")/../.." || exit 1
PY=${PY:-$HOME/miniconda3/envs/planarnet/bin/python}
mkdir -p logs/bench results/lists
nohup bash scripts/server/mem_guard.sh 120 > /dev/null 2>&1 &
GUARD=$!
printf "%s\n" mitten_200 > results/lists/tier2_mitten200.txt
"$PY" bench/run_matrix.py --methods ours_pipeline:dp=2 --instances @results/lists/tier2_mitten200.txt \
    --variants sector --threads 32 --time-limit 3600 --mem-gb 90 --total-mem-gb 90 --jobs 1 --cpus 160-191 \
    --out results/bench_tierB > logs/bench/tier2_mitten200.log 2>&1
touch logs/bench/tier2_mitten200.done
kill $GUARD
