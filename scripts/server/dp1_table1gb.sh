#!/bin/bash
# dp=1 with the table budget that the pipeline's worker had until the fix of 7ef27aa (table_gb=1: 1 GiB) on the
# solved records whose lookup tables got deeper with that fix, beside the runs of dp2_recheck.sh and
# dp2_recheck_pairs.sh: is the slowdown of these records against the first dp=1 pass the depth of the tables or
# the load of the machine?  1 thread / 600 s / 16 GB, 11 jobs on cores 160-170, to results/bench_recheck.
# usage: (setsid nohup bash scripts/server/dp1_table1gb.sh > /dev/null 2>&1 < /dev/null &)
cd "$(dirname "$0")/../.." || exit 1
PY=${PY:-$HOME/miniconda3/envs/planarnet/bin/python}
nohup bash scripts/server/mem_guard.sh 300 > /dev/null 2>&1 &     # also guards the end of dp2_recheck_pairs.sh
GUARD=$!
until [ -f logs/bench/recheck.done ]; do sleep 10; done
printf "%s\n" color_d11 cornucopia_252 surface_d21 surface_d23 surface_d25 w8bb_144_16 > results/lists/recheck_table1gb.txt
"$PY" bench/run_matrix.py --methods ours_pipeline:dp=1,table_gb=1 --instances @results/lists/recheck_table1gb.txt \
    --variants sector,full --threads 1 --time-limit 600 --mem-gb 16 --total-mem-gb 176 --jobs 11 --cpus 160-170 \
    --out results/bench_recheck > logs/bench/recheck_table1gb.log 2>&1
touch logs/bench/recheck_table1gb.done
until [ -f logs/bench/recheck_pairs.done ]; do sleep 10; done
kill $GUARD
