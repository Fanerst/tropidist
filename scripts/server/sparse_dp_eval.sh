#!/bin/bash
# The evaluation of the sparse Rank DP (results/sparse_dp) on the benchmark server.
#   1. scripts/sparse_dp_eval.py in five streams of instances, in parallel, with every configuration;
#   2. the superdense d11 circuit: two sweeps at K = 10 and two witness runs at K = 11 (scripts/sparse_dp_query.py);
#   3. surface d11 with the numpy tables (its trellis needs 62 row slots, the C tables hold 56).
# Every job runs on one thread, on the cores of NUMA node 0 (other users' jobs float over all cores, so no single
# core is free to pin to), under the project's memory guard.  The d11 runs with the uniform split need up to
# 100 GB.  Logs go to logs/sparse_dp_*.log.
# usage: (setsid nohup bash scripts/server/sparse_dp_eval.sh > /dev/null 2>&1 < /dev/null &)
cd "$(dirname "$0")/../.." || exit 1
PY=${PY:-$HOME/claude_runs/circuit_distance/bench/external/venv/bin/python}
export WJH_CIRCUITS=${WJH_CIRCUITS:-$HOME/claude_runs/circuit_distance/papers/downloads/codedistance/examples/stim_circuits}
export OMP_NUM_THREADS=1
OUT=results/sparse_dp
mkdir -p $OUT logs
nohup bash scripts/server/mem_guard.sh 300 > /dev/null 2>&1 &
GUARD=$!
COMMON="--dense-bits 33 --search-seconds 600 --max-states 100000000 --max-seconds 3600"
eval_stream() {   # stream name, instance tokens, [configs]
  taskset -c 0-95,192-287 "$PY" scripts/sparse_dp_eval.py "$OUT/$1.json" "$2" $COMMON ${3:+--configs $3} \
    > "logs/sparse_dp_$1.log" 2>&1
}
query() {         # record name, K, split, [--stop-at-K]
  taskset -c 0-95,192-287 "$PY" scripts/sparse_dp_query.py "$OUT/$1.json" wjh:superdense:11 "$2" "$3" $4 \
    > "logs/sparse_dp_$1.log" 2>&1
}
JOBS=""
eval_stream d11 wjh:superdense:11 & JOBS="$JOBS $!"
eval_stream narrow color:7,color:9,color:11,color:13,color:15,color:17,color:19,color:21,color:23,color:25,color:27 & JOBS="$JOBS $!"
eval_stream lowwidth lowwidth:concat_steane_L2,lowwidth:concat_steane_L3,lowwidth:concat_steane_L4,lowwidth:hypercube_L2,lowwidth:hypercube_L3 & JOBS="$JOBS $!"
eval_stream bb bb:bb72,bb:bb90,bb:bb108,bb:gross & JOBS="$JOBS $!"
eval_stream circuits wjh:surface:3,wjh:superdense:3,wjh:surface:5,wjh:superdense:5,wjh:surface:7,wjh:superdense:7,wjh:surface:9,wjh:superdense:9,wjh:surface:11 & JOBS="$JOBS $!"
eval_stream surface11 wjh:surface:11 sparse:mitm:numpy:0:schedule,sparse:mitm:numpy:0:auto & JOBS="$JOBS $!"
query d11_K10_a5 10 5 & JOBS="$JOBS $!"
query d11_K10_schedule 10 schedule & JOBS="$JOBS $!"
query d11_K11_a6 11 6 --stop-at-K & JOBS="$JOBS $!"
query d11_K11_schedule 11 schedule+1 --stop-at-K & JOBS="$JOBS $!"
wait $JOBS                        # not a bare wait: that would also wait for the guard
kill $GUARD
