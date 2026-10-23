#!/bin/bash
# The main suite's first tier with config dp=1 under the pipeline's table depth rule (default: tables up front within
# EAGER_TABLE_BYTES, deepened within the 8 GiB budget after a paired trial) and as before 7ef27aa (table_gb=1: 1 GiB
# for the lookup tables and for the DP front end, which the rule reproduces exactly), side by side: cores 0-17 and
# 18-35 of 5090 (socket 0), 1 thread / 600 s / 16 GB / 18 jobs / give-up 2 each, the flags of the dp=1 pass
# (scripts/server/dp_pass.sh), 23 October 2026.  Under the project's memory guard; results in results/bench_tables.
# usage: (setsid nohup bash scripts/server/table_depth_suite.sh > /dev/null 2>&1 < /dev/null &)
cd "$(dirname "$0")/../.." || exit 1
PY=${PY:-$HOME/miniconda3/envs/planarnet/bin/python}
mkdir -p logs/bench
nohup bash scripts/server/mem_guard.sh 500 > /dev/null 2>&1 &
GUARD=$!
RUN="$PY bench/run_matrix.py --instances all --variants sector,full --threads 1 --time-limit 600 --mem-gb 16
     --total-mem-gb 288 --jobs 18 --give-up 2 --out results/bench_tables"
$RUN --methods ours_pipeline:dp=1 --cpus 0-17 > logs/bench/tables_rule.log 2>&1 &
PIDS=$!
$RUN --methods ours_pipeline:dp=1,table_gb=1 --cpus 18-35 > logs/bench/tables_1gib.log 2>&1 &
PIDS="$PIDS $!"
wait $PIDS
touch logs/bench/tables_suite.done
kill $GUARD
