#!/bin/bash
# Trial benchmark (22 October 2026) on the low-width instances of bench/export_lowwidth.py (color codes, concatenated
# Steane and many-hypercube codes, code capacity), before deciding whether to add them to the standard benchmark.
# Every method of the code track, first-tier limits of the main benchmark (1 thread, 600 s, 16 GB, give-up 2), in
# the venv the main pass used; Gurobi through gurobi_cl with its licence renewal over the local proxy.
cd ~/claude_runs/circuit_distance
PY=bench/external/venv/bin/python
. ~/opt/gurobi-env.sh
export https_proxy=http://127.0.0.1:7890 HTTPS_PROXY=http://127.0.0.1:7890
EXT=$PWD/bench/external
DM=distm4ri:build=0.14.7
METHODS="ours_pipeline,ours_pipeline:dp=1,ours,$DM,mode=cc,$DM,mode=bracket,$DM,mode=rw"
METHODS="$METHODS,milp:backend=scipy,milp:backend=cpsat,milp:backend=gurobi"
METHODS="$METHODS,sat:mode=incremental,sat:mode=maxsat"
METHODS="$METHODS,sat:mode=maxsat,binary=$EXT/CASHWMaxSAT-CorePlus/bin/cashwmaxsatcoreplus,sat:mode=maxsat,binary=$EXT/enMaxCDCL"
METHODS="$METHODS,qserf:method=cc,qserf:method=bz,qserf:method=mitm,bposd,isd"
mkdir -p logs/bench results/bench_lowwidth
$PY bench/run_matrix.py --methods "$METHODS" --instances all --variants full --instance-dir bench/instances_lowwidth \
    --threads 1 --time-limit 600 --mem-gb 16 --total-mem-gb 288 --jobs 18 --cpus 0-95 --out results/bench_lowwidth \
    --give-up 2 --heuristic-methods "bposd,isd,$DM,mode=rw" ${DRY:+--dry-run} >> logs/bench/lowwidth_trial.log 2>&1
touch results/bench_lowwidth/tier1.done
