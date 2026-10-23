#!/bin/bash
# The pipeline with config dp=2 (the sparse Rank DP), 23 October 2026: its first tier on the main suite and on the
# instances of arXiv:2603.22532 (bench/tier_b.py dp2: 1 thread / 600 s / 16 GB, 18 jobs on the physical cores of
# socket 1), then its second tier on what that left (dp2b: 32 threads / 90 GB / 3600 s, the main suite on cores
# 0-95 with 3 jobs and the paper's instances on 96-191 with 2), under the project's memory guard.
# The instance directories need their exported matrices (bench/export_all.py, bench/export_wjh.py).
# usage: (setsid nohup bash scripts/server/dp2_pass.sh > /dev/null 2>&1 < /dev/null &)
cd "$(dirname "$0")/../.." || exit 1
PY=${PY:-$HOME/miniconda3/envs/planarnet/bin/python}
mkdir -p logs/bench
nohup bash scripts/server/mem_guard.sh 600 > /dev/null 2>&1 &
GUARD=$!
"$PY" bench/tier_b.py dp2 dp2b > logs/bench/dp2_pass.log 2>&1
touch logs/bench/dp2_pass.done
kill $GUARD
