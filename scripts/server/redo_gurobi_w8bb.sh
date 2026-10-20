#!/bin/bash
# The 32-thread Gurobi run on code_w8bb_144_6 (15 October) failed at start-up on the licence service; repeat it
# through the proxy.  It was written to wait for chain_after_dm4ri.sh, but was run directly on 19 October
# (06:22) as soon as cores 0-31 were free, so the wait is left out here.
cd ~/claude_runs/circuit_distance
. ~/opt/gurobi-env.sh
export https_proxy=http://127.0.0.1:7890 HTTPS_PROXY=http://127.0.0.1:7890
echo code_w8bb_144_6 > results/bench_tierB/lists/redo_gurobi_w8bb.txt
bench/external/venv/bin/python bench/run_matrix.py --methods milp:backend=gurobi --instances @results/bench_tierB/lists/redo_gurobi_w8bb.txt --variants full --threads 32 --time-limit 3600 --mem-gb 90 --total-mem-gb 90 --jobs 1 --out results/bench_tierB --redo status=error --cpus 0-31
echo "redo done $(date)"
