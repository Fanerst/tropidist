#!/bin/bash
# Covering bound vs baseline on BB288 collapsed (server).
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
export OMP_NUM_THREADS=128
$PY phase4/bench_kernel.py bb288_r18_Z:collapsed 3 12,13,14 0,c:0 0 0.5 k3 > phase4/logs/bench_bb288_k3.log 2>&1
$PY phase4/bench_kernel.py bb288_r18_Z:collapsed 4 14,15 0,c:0 0 0.8 k4 > phase4/logs/bench_bb288_k4.log 2>&1
touch phase4/logs/bench1.done
