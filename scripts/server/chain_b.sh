#!/bin/bash
# Passes that follow the first benchmark tier; waits for the harness of the first tier to exit.
# Usage: nohup bash scripts/server/chain_b.sh <pid of the first-tier harness> > logs/bench/chain_b.log 2>&1 &
cd ~/claude_runs/circuit_distance || exit 1
taskset -cp 0-95,192-287 $$ > /dev/null
V=$PWD/bench/external/venv/bin/python
while kill -0 "$1" 2> /dev/null; do sleep 60; done
date
$V bench/tier_b.py fix collapsed ablation b32 b1
date
