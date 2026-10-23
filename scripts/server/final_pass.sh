#!/bin/bash
# Final pass (23 October 2026; Feng: dp=2 is the final configuration of our pipeline): bench/tier_b.py final1 (first
# tier on both sockets), final8h beside it (the 8-hour protocol of arXiv:2603.22532 on cores 96-141), then final2
# (second tier on socket 0).  The memory guard stops this project's jobs above 1000 GB, far below the machine's
# watchdog (see scripts/server/mem_guard.sh).  Gurobi renews its licence through the local proxy.
cd ~/claude_runs/circuit_distance
PY=bench/external/venv/bin/python
. ~/opt/gurobi-env.sh
export https_proxy=http://127.0.0.1:7890 HTTPS_PROXY=http://127.0.0.1:7890
mkdir -p logs/bench
bash scripts/server/mem_guard.sh 1000 &
guard=$!
$PY bench/tier_b.py final8h > logs/bench/final8h_driver.log 2>&1 &
p8=$!
$PY bench/tier_b.py final1 > logs/bench/final1_driver.log 2>&1
touch logs/bench/final1.done
$PY bench/tier_b.py final2 > logs/bench/final2_driver.log 2>&1
touch logs/bench/final2.done
wait $p8
touch logs/bench/final8h.done
kill $guard
