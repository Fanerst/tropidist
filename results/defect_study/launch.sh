#!/bin/bash
# launch.sh PART PROCESSES SECONDS_PER_RUN: run jobs_PART.jsonl detached on this server (5090b or 5090c), records in rec_PART.jsonl
cd ~/claude_runs/defect_study
mkdir -p tmp logs
export CD_ROOT=$PWD CHIP_TMP=$PWD/tmp OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
if [ -d ~/envs/torch/lib/python3.12/site-packages ]; then
    PY=~/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/bin/python
    export PYTHONPATH=$HOME/claude_runs/pylib:$HOME/envs/torch/lib/python3.12/site-packages:$PWD:$PWD/bench:$PWD/papers
else
    PY=~/claude_runs/circuit_distance/pyenv/cpython-3.12.15-linux-x86_64-gnu/bin/python3.12
    export PYTHONPATH=$HOME/claude_runs/pylib:$HOME/claude_runs/circuit_distance/pyenv/site-packages:$PWD:$PWD/bench:$PWD/papers
fi
$PY -c "from cdist import search; print('threads', search.lib().gm_num_threads())" || exit 1
(setsid nohup $PY run_chips.py jobs_$1.jsonl rec_$1.jsonl $2 $3 > logs/run_$1.log 2>&1 < /dev/null &)
