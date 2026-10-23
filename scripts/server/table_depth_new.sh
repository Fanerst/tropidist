#!/bin/bash
# The table depth rule of the pipeline (tables up front within EAGER_TABLE_BYTES, deepened after a paired trial;
# bench/adapters/ours_pipeline.py) on the instances of table_depth_runs.sh, first-tier budget 8 GiB, config dp=1,
# 23 October 2026: one thread, 600 s, 16 GB on cores $CPUS1 (default 0-17) for the 14 records, and mitten_200
# with 16 threads, 1800 s, 64 GB on cores $CPUS16 (default 36-51).  Under the project's memory guard; results in
# results/table_depth/*__$TAG__* (default TAG=new).
# usage: (TAG=rule CPUS1=54-71 CPUS16=72-87 setsid nohup bash scripts/server/table_depth_new.sh > /dev/null 2>&1 \
#         < /dev/null &)
cd "$(dirname "$0")/../.." || exit 1
PY=${PY:-$HOME/miniconda3/envs/planarnet/bin/python}
OUT=results/table_depth
TAG=${TAG:-new}
CPUS1=${CPUS1:-0-17}
CPUS16=${CPUS16:-36-51}
mkdir -p $OUT logs
nohup bash scripts/server/mem_guard.sh 400 > /dev/null 2>&1 &
GUARD=$!
jobs1() {
  echo "color_d11 full"
  for n in cornucopia_252 surface_d21 surface_d23 surface_d25 w8bb_144_16; do
    for v in sector full; do echo "$n $v"; done
  done
  for n in bb288_r18 mitten_300 routing_200_24; do echo "$n sector"; done
}
jobs1 | OMP_NUM_THREADS=1 taskset -c $CPUS1 xargs -P 18 -L 1 sh -c '"$0" scripts/table_depth_probe.py \
    bench/instances/$1 $2 --budget-gb 8 --seconds 600 --mem-gb 16 --out '"$OUT"'/$1__$2__'"$TAG"'__t1.json \
    > '"$OUT"'/$1__$2__'"$TAG"'__t1.log 2>&1' "$PY" &
PIDS=$!
OMP_NUM_THREADS=16 taskset -c $CPUS16 "$PY" scripts/table_depth_probe.py bench/instances/mitten_200 sector \
    --budget-gb 8 --seconds 1800 --mem-gb 64 --out $OUT/mitten_200__sector__${TAG}__t16.json \
    > $OUT/mitten_200__sector__${TAG}__t16.log 2>&1 &
PIDS="$PIDS $!"
wait $PIDS
touch logs/table_depth_$TAG.done
kill $GUARD
