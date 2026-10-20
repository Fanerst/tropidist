#!/bin/bash
# Gurobi, first logical basis, 32 threads: code_mm_324 and the larger codes of its family had been skipped by the
# give-up rule after the licence failure of the code_w8bb_144_6 run, which has since been repeated and solved.
cd ~/claude_runs/circuit_distance
. ~/opt/gurobi-env.sh
export https_proxy=http://127.0.0.1:7890 HTTPS_PROXY=http://127.0.0.1:7890
bench/external/venv/bin/python bench/run_matrix.py --methods milp:backend=gurobi --instances @results/bench_tierB/lists/redo_gurobi_mm324.txt --variants full --threads 32 --time-limit 3600 --mem-gb 90 --total-mem-gb 270 --jobs 1 --out results/bench_tierB --give-up 1 --redo status=skipped --cpus 0-31 > logs/bench/redo_gurobi_mm324.log 2>&1
echo "redo done $(date)" >> logs/bench/redo_gurobi_mm324.log
