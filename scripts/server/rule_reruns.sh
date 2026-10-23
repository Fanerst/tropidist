#!/bin/bash
# Reruns under the lookup-table depth rule (commit c030477), 23 October 2026, approved by Feng:
# - dp=2, first tier, the 21 records that ran with deeper tables than the rule builds up front (dp=1's record of
#   them notes a table cut to 1 GiB, dp=2's none): the 19 of results/bench_recheck and the bb288 and bb360 circuits
#   of arXiv:2603.22532.  1 thread / 600 s / 16 GB, cores 96-116 (socket 1, as dp=2's first pass); records replaced
#   in results/bench and results/bench_wjh;
# - the default configuration's second tier on mitten_200, sector: 32 threads / 3600 s / 90 GB, cores 0-31
#   (socket 0, as the default's second tier); record replaced in results/bench_tierB.
# Under the project's memory guard.
# usage: (setsid nohup bash scripts/server/rule_reruns.sh > /dev/null 2>&1 < /dev/null &)
cd "$(dirname "$0")/../.." || exit 1
PY=${PY:-$HOME/miniconda3/envs/planarnet/bin/python}
mkdir -p logs/bench results/lists
nohup bash scripts/server/mem_guard.sh 400 > /dev/null 2>&1 &
GUARD=$!
REDO="--redo status=exact --redo status=timeout --redo status=bounds --redo status=error --redo status=skipped"
T1="--threads 1 --time-limit 600 --mem-gb 16 $REDO"
printf "%s\n" bb288_r18 color_d11 cornucopia_252 mitten_200 mitten_300 routing_200_24 surface_d21 surface_d23 \
    surface_d25 w8bb_144_16 > results/lists/rule_dp2_main.txt
printf "%s\n" wjh_bb288_circuit wjh_bb360_circuit > results/lists/rule_dp2_wjh.txt
printf "%s\n" mitten_200 > results/lists/rule_default_t2.txt
$PY bench/run_matrix.py --methods ours_pipeline:dp=2 --instances @results/lists/rule_dp2_main.txt --variants sector,full \
    $T1 --total-mem-gb 304 --jobs 19 --cpus 96-114 --out results/bench > logs/bench/rule_dp2_main.log 2>&1 &
P1=$!
$PY bench/run_matrix.py --methods ours_pipeline:dp=2 --instances @results/lists/rule_dp2_wjh.txt --variants sector \
    --instance-dir bench/instances_wjh $T1 --total-mem-gb 32 --jobs 2 --cpus 115-116 --out results/bench_wjh \
    > logs/bench/rule_dp2_wjh.log 2>&1 &
P2=$!
$PY bench/run_matrix.py --methods ours_pipeline --instances @results/lists/rule_default_t2.txt --variants sector \
    --threads 32 --time-limit 3600 --mem-gb 90 --total-mem-gb 90 --jobs 1 --cpus 0-31 $REDO --out results/bench_tierB \
    > logs/bench/rule_default_t2.log 2>&1 &
P3=$!
wait $P1 $P2 $P3
touch logs/bench/rule_reruns.done
kill $GUARD
