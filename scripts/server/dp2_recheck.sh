#!/bin/bash
# The first-tier records that the probe change of 8ec918b can alter, and a baseline with the same code, 23 October
# 2026 (1 thread / 600 s / 16 GB, no give-up, under the project's memory guard):
# - dp=2 on every record whose sparse stage ran the probe (main suite: fx_sdbb16_r3, routing_54, sdbb_64, star_42,
#   walkingcat_54; arXiv:2603.22532: superdense d5-d11), on cores 174-177;
# - dp=1 on the records whose lookup tables got deeper with the table budget fix of 7ef27aa, which came after the
#   first dp=1 pass (results/bench/ours_pipeline__dp-1), on cores 160-173.  Written to results/bench_recheck,
#   so that the dp=2 records can be compared with dp=1 under the same code (dp2_recheck_pairs.sh runs the other
#   half).  The run of 23 October wrote it as results/bench_dp1_current, the folder named in its records.
# usage: (setsid nohup bash scripts/server/dp2_recheck.sh > /dev/null 2>&1 < /dev/null &)
cd "$(dirname "$0")/../.." || exit 1
PY=${PY:-$HOME/miniconda3/envs/planarnet/bin/python}
mkdir -p logs/bench results/lists
nohup bash scripts/server/mem_guard.sh 300 > /dev/null 2>&1 &
GUARD=$!
RUN="$PY bench/run_matrix.py --threads 1 --time-limit 600 --mem-gb 16"
printf "%s\n" fx_sdbb16_r3 routing_54 sdbb_64 star_42 walkingcat_54 > results/lists/recheck_dp2_main.txt
printf "%s\n" wjh_superdense_d5 wjh_superdense_d7 wjh_superdense_d9 wjh_superdense_d11 > results/lists/recheck_dp2_wjh.txt
printf "%s\n" bb288_r18 color_d11 cornucopia_252 mitten_200 mitten_300 routing_200_24 surface_d21 surface_d23 \
    surface_d25 w8bb_144_16 > results/lists/recheck_dp1.txt
$RUN --methods ours_pipeline:dp=1 --instances @results/lists/recheck_dp1.txt --variants sector,full \
    --total-mem-gb 224 --jobs 14 --cpus 160-173 --out results/bench_recheck > logs/bench/recheck_dp1.log 2>&1 &
DP1=$!
$RUN --methods ours_pipeline:dp=2 --instances @results/lists/recheck_dp2_main.txt --variants sector,full \
    --total-mem-gb 64 --jobs 4 --cpus 174-177 --out results/bench > logs/bench/recheck_dp2_main.log 2>&1
$RUN --methods ours_pipeline:dp=2 --instances @results/lists/recheck_dp2_wjh.txt --variants sector \
    --instance-dir bench/instances_wjh --total-mem-gb 64 --jobs 4 --cpus 174-177 --out results/bench_wjh \
    > logs/bench/recheck_dp2_wjh.log 2>&1
wait $DP1
touch logs/bench/recheck.done
kill $GUARD
