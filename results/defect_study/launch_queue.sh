#!/bin/bash
# launch_queue.sh CPUS THREADS JOBS KMAX SECONDS R M [TAG]: exact two-gross scan, detached, on this server; TAG names the log of a further instance
cd ~/claude_runs/defect_study
mkdir -p logs tmp
CPUS=$1
export CD_ROOT=$PWD CHIP_TMP=$PWD/tmp OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
if [ -d ~/envs/torch/lib/python3.12/site-packages ]; then
    PY=~/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/bin/python
    export PYTHONPATH=$HOME/claude_runs/pylib:$HOME/envs/torch/lib/python3.12/site-packages:$PWD:$PWD/bench:$PWD/papers
else
    PY=~/claude_runs/circuit_distance/pyenv/cpython-3.12.15-linux-x86_64-gnu/bin/python3.12
    export PYTHONPATH=$HOME/claude_runs/pylib:$HOME/claude_runs/circuit_distance/pyenv/site-packages:$PWD:$PWD/bench:$PWD/papers
fi
(setsid nohup taskset -c $CPUS $PY deep_queue.py exact_scan$8.jsonl classes.json $2 $3 $4 $5 $6 $7 > logs/exact_scan$8.log 2>&1 < /dev/null &)
