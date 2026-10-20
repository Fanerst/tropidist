#!/bin/bash
# dist-m4ri 0.14.7 random window (a heuristic) had been put under the give-up rule in the first tier: the harness
# split the --heuristic-methods value at every comma, so "distm4ri:build=0.14.7,mode=rw" never matched.  Run the
# skipped instances with the fixed harness, same limits (1 thread, 600 s, 16 GB).
cd ~/claude_runs/circuit_distance
for v in sector full; do
  bench/external/venv/bin/python bench/run_matrix.py --methods distm4ri:build=0.14.7,mode=rw \
    --heuristic-methods distm4ri:build=0.14.7,mode=rw --instances @results/bench/lists/redo_dm4ri_rw__$v.txt \
    --variants $v --threads 1 --time-limit 600 --mem-gb 16 --total-mem-gb 400 --jobs 25 --give-up 2 \
    --redo status=skipped --out results/bench --cpus 96-127
done > logs/bench/redo_dm4ri_rw.log 2>&1
echo "redo done $(date)" >> logs/bench/redo_dm4ri_rw.log
