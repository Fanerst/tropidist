#!/bin/bash
# The other half of the same-time comparison started by dp2_recheck.sh, so that every record it reruns exists for
# dp=1 and dp=2 under the same code (8ec918b) and the same machine load (1 thread / 600 s / 16 GB, no give-up):
# - dp=2 on the records whose lookup tables got deeper with 7ef27aa, on cores 178-191, beside dp2_recheck.sh's
#   dp=1 runs of them;
# - dp=1 on the records whose sparse stage runs the probe, on cores 174-177 once dp2_recheck.sh's dp=2 runs of
#   them are done (dp2_recheck.sh has finished).
# Both go to results/bench_recheck.
# usage: (setsid nohup bash scripts/server/dp2_recheck_pairs.sh > /dev/null 2>&1 < /dev/null &)
cd "$(dirname "$0")/../.." || exit 1
PY=${PY:-$HOME/miniconda3/envs/planarnet/bin/python}
RUN="$PY bench/run_matrix.py --threads 1 --time-limit 600 --mem-gb 16 --out results/bench_recheck"
$RUN --methods ours_pipeline:dp=2 --instances @results/lists/recheck_dp1.txt --variants sector,full \
    --total-mem-gb 224 --jobs 14 --cpus 178-191 > logs/bench/recheck_pairs_dp2.log 2>&1 &
DP2=$!
until [ -f logs/bench/recheck.done ]; do sleep 10; done
$RUN --methods ours_pipeline:dp=1 --instances @results/lists/recheck_dp2_main.txt --variants sector,full \
    --total-mem-gb 64 --jobs 4 --cpus 174-177 > logs/bench/recheck_pairs_dp1_main.log 2>&1
$RUN --methods ours_pipeline:dp=1 --instances @results/lists/recheck_dp2_wjh.txt --variants sector \
    --instance-dir bench/instances_wjh --total-mem-gb 64 --jobs 4 --cpus 174-177 > logs/bench/recheck_pairs_dp1_wjh.log 2>&1
wait $DP2
touch logs/bench/recheck_pairs.done
