#!/bin/bash
# after the main Gurobi chain: repeat its one interrupted run (status 11) with the same limits

. ~/opt/gurobi-env.sh
echo surface_d11 > results/bench_tierB/lists/redo_gurobi_d11.txt
bench/external/venv/bin/python bench/run_matrix.py --methods milp:backend=gurobi --instances @results/bench_tierB/lists/redo_gurobi_d11.txt --variants sector --threads 32 --time-limit 3600 --mem-gb 90 --total-mem-gb 270 --jobs 1 --out results/bench_tierB --give-up 1 --redo status=error --cpus 0-31
echo "redo done"
