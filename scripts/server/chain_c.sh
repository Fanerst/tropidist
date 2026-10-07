#!/bin/bash
# Passes added after scripts/server/chain_b.sh started; waits for its tier_b.py process to exit.
# Usage: nohup bash scripts/server/chain_c.sh <pid of the running tier_b.py> > logs/bench/chain_c.log 2>&1 &
cd ~/claude_runs/circuit_distance || exit 1
taskset -cp 0-95,192-287 $$ > /dev/null
V=$PWD/bench/external/venv/bin/python
while kill -0 "$1" 2> /dev/null; do sleep 60; done
date
$V bench/tier_b.py stimsat b1s
date
