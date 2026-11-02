#!/bin/bash
# run_spectra.sh THREADS LIST [SCHEDULE]: fault sets up to weight 10 of chips, one after the other; LIST lines: NAME BASIS CYCLES DEAD_X DEAD_Z
# SCHEDULE: as in chip_spectrum.py, for example 561234_324015; default the standard schedule
cd ~/claude_runs/defect_study
mkdir -p spec logs
export CD_ROOT=$PWD OMP_NUM_THREADS=$1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
if [ -d ~/envs/torch/lib/python3.12/site-packages ]; then
    PY=~/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/bin/python
    export PYTHONPATH=$HOME/claude_runs/pylib:$HOME/envs/torch/lib/python3.12/site-packages:$PWD:$PWD/bench:$PWD/papers
else
    PY=~/claude_runs/circuit_distance/pyenv/cpython-3.12.15-linux-x86_64-gnu/bin/python3.12
    export PYTHONPATH=$HOME/claude_runs/pylib:$HOME/claude_runs/circuit_distance/pyenv/site-packages:$PWD:$PWD/bench:$PWD/papers
fi
while read -r NAME BASIS C DX DZ; do
    [ -f spec/$NAME.npz ] && continue
    $PY chip_spectrum.py spec/$NAME.tmp.npz $BASIS $C $DX $DZ 1 10 43200 2 ${3:-standard} > logs/spec_$NAME.log 2>&1 && mv spec/$NAME.tmp.npz spec/$NAME.npz
done < "$2"
