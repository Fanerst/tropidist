#!/bin/bash
# launch_exact.sh CPUS THREADS JOBS KMAX SECONDS ONLY.json TAG: deep_queue.py on the listed classes, detached, on this server; CPUS "-" leaves the placement to the system
if [ -d ~/claude_runs/defect_study ]; then cd ~/claude_runs/defect_study; else cd ~/claude_runs/bb288_scan/screen; fi
mkdir -p logs tmp
CPUS=$1; T=$2; J=$3; K=$4; SEC=$5; ONLY=$6; TAG=$7
export CHIP_TMP=$PWD/tmp OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 DEEP_ONLY=$PWD/$ONLY
if [ -d ~/miniconda3/envs/planarnet ]; then
    PY=~/miniconda3/envs/planarnet/bin/python
    export CD_ROOT=$HOME/claude_runs/bb288_scan
    export PYTHONPATH=$CD_ROOT:$CD_ROOT/bench:$CD_ROOT/papers:$PWD
elif [ -d ~/envs/torch/lib/python3.12/site-packages ]; then
    PY=~/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/bin/python
    export CD_ROOT=$PWD
    export PYTHONPATH=$HOME/claude_runs/pylib:$HOME/envs/torch/lib/python3.12/site-packages:$PWD:$PWD/bench:$PWD/papers
else
    PY=~/claude_runs/circuit_distance/pyenv/cpython-3.12.15-linux-x86_64-gnu/bin/python3.12
    export CD_ROOT=$PWD
    export PYTHONPATH=$HOME/claude_runs/pylib:$HOME/claude_runs/circuit_distance/pyenv/site-packages:$PWD:$PWD/bench:$PWD/papers
fi
PIN=""
[ "$CPUS" != "-" ] && PIN="taskset -c $CPUS"
(setsid nohup $PIN $PY deep_queue.py exact_$TAG.jsonl classes.json $T $J $K $SEC 0 1 > logs/exact_$TAG.log 2>&1 < /dev/null &)
