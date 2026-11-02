#!/bin/bash
# launch_deep.sh CPUS THREADS KMAX SECONDS LOG PROBLEM...: two-gross deep runs, one after the other, detached, on this server
cd ~/claude_runs/defect_study
mkdir -p logs
CPUS=$1; T=$2; K=$3; SEC=$4; LOG=$5; shift 5
export CD_ROOT=$PWD OMP_NUM_THREADS=$T OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
if [ -d ~/envs/torch/lib/python3.12/site-packages ]; then
    PY=~/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/bin/python
    export PYTHONPATH=$HOME/claude_runs/pylib:$HOME/envs/torch/lib/python3.12/site-packages:$PWD:$PWD/bench:$PWD/papers
else
    PY=~/claude_runs/circuit_distance/pyenv/cpython-3.12.15-linux-x86_64-gnu/bin/python3.12
    export PYTHONPATH=$HOME/claude_runs/pylib:$HOME/claude_runs/circuit_distance/pyenv/site-packages:$PWD:$PWD/bench:$PWD/papers
fi
(setsid nohup taskset -c $CPUS $PY deep_run.py $T $K $SEC "$@" > logs/$LOG.log 2>&1 < /dev/null &)
