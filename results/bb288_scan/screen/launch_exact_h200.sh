#!/bin/bash
# launch_exact_h200.sh CPUS THREADS JOBS KMAX SECONDS ONLY.json TAG: deep_queue.py on the listed classes, detached, on the H200 server (launch_exact.sh elsewhere)
cd ~/claude_runs/bb288_k17
mkdir -p logs tmp
CPUS=$1; T=$2; J=$3; K=$4; SEC=$5; ONLY=$6; TAG=$7
export CHIP_TMP=$PWD/tmp OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 DEEP_ONLY=$PWD/$ONLY
PY=~/anaconda3/bin/python
export CD_ROOT=$PWD
export PYTHONPATH=$PWD:$PWD/bench:$PWD/papers
PIN=""
[ "$CPUS" != "-" ] && PIN="taskset -c $CPUS"
(setsid nohup $PIN $PY deep_queue.py exact_$TAG.jsonl classes.json $T $J $K $SEC 0 1 > logs/exact_$TAG.log 2>&1 < /dev/null &)
