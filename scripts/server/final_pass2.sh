#!/bin/bash
# The rest of the final pass's second tier in parallel (bench/tier_b.py final2b), after the sequential final2 was
# stopped on 24 October 2026; its running RC2 sector harness was left to finish.  Memory guard as in final_pass.sh.
cd ~/claude_runs/circuit_distance
PY=bench/external/venv/bin/python
. ~/opt/gurobi-env.sh
export https_proxy=http://127.0.0.1:7890 HTTPS_PROXY=http://127.0.0.1:7890
bash scripts/server/mem_guard.sh 1000 &
guard=$!
$PY bench/tier_b.py final2b > logs/bench/final2b_driver.log 2>&1
touch logs/bench/final2b.done
kill $guard
