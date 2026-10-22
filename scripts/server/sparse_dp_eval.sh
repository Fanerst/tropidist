#!/bin/bash
# Evaluation of the sparse Rank DP (scripts/sparse_dp_eval.py) on the benchmark server: five streams of instances
# in parallel, every job on one thread, on the cores of NUMA node 0 (other users' jobs float over all cores, so no
# single core is free to pin to), under the project's memory guard.  Records go to results/sparse_dp/<stream>.json, logs to logs/sparse_dp_<stream>.log.
# usage: (setsid nohup bash scripts/server/sparse_dp_eval.sh > /dev/null 2>&1 < /dev/null &)
cd "$(dirname "$0")/../.." || exit 1
PY=${PY:-$HOME/claude_runs/circuit_distance/bench/external/venv/bin/python}
export WJH_CIRCUITS=${WJH_CIRCUITS:-$HOME/claude_runs/circuit_distance/papers/downloads/codedistance/examples/stim_circuits}
mkdir -p results/sparse_dp logs
nohup bash scripts/server/mem_guard.sh 300 > /dev/null 2>&1 &
GUARD=$!
COMMON="--dense-bits 33 --search-seconds 600 --max-states 100000000 --max-seconds 3600"
run() {   # stream name, instance tokens
  taskset -c 0-95,192-287 "$PY" scripts/sparse_dp_eval.py "results/sparse_dp/$1.json" "$2" $COMMON > "logs/sparse_dp_$1.log" 2>&1
}
run d11 wjh:superdense:11 &
run narrow color:7,color:9,color:11,color:13,color:15,color:17,color:19,color:21,color:23,color:25,color:27 &
run lowwidth lowwidth:concat_steane_L2,lowwidth:concat_steane_L3,lowwidth:concat_steane_L4,lowwidth:hypercube_L2,lowwidth:hypercube_L3 &
run bb bb:bb72,bb:bb90,bb:bb108,bb:gross &
run circuits wjh:surface:3,wjh:superdense:3,wjh:surface:5,wjh:superdense:5,wjh:surface:7,wjh:superdense:7,wjh:surface:9,wjh:superdense:9,wjh:surface:11 &
wait
kill $GUARD
