#!/bin/bash
# Per-table and per-level costs of the pipeline (scripts/table_depth_probe.py, config dp=1) on the instances whose
# lookup tables got deeper with the table budget fix of 7ef27aa: budget 1 GiB (the depth before that fix) against
# 8 GiB (since then, in the first tier), 23 October 2026.
# - one thread, 600 s, 16 GB: the 11 solved affected records and the sector problems of bb288_r18, mitten_300 and
#   routing_200_24, 18 at a time on cores 0-17;
# - mitten_200 sector with 16 threads, 1800 s and 64 GB, cores 20-35 (1 GiB) and 36-51 (8 GiB), where the deeper
#   table made the second tier 7x faster.
# Under the project's memory guard; results in results/table_depth.
# usage: (setsid nohup bash scripts/server/table_depth_runs.sh > /dev/null 2>&1 < /dev/null &)
cd "$(dirname "$0")/../.." || exit 1
PY=${PY:-$HOME/miniconda3/envs/planarnet/bin/python}
OUT=results/table_depth
mkdir -p $OUT logs
nohup bash scripts/server/mem_guard.sh 450 > /dev/null 2>&1 &
GUARD=$!
jobs1() {                                  # instance variant budget
  for b in 1 8; do
    echo "color_d11 full $b"
    for n in cornucopia_252 surface_d21 surface_d23 surface_d25 w8bb_144_16; do
      for v in sector full; do echo "$n $v $b"; done
    done
    for n in bb288_r18 mitten_300 routing_200_24; do echo "$n sector $b"; done
  done
}
jobs1 | OMP_NUM_THREADS=1 taskset -c 0-17 xargs -P 18 -L 1 sh -c '"$0" scripts/table_depth_probe.py \
    bench/instances/$1 $2 --budget-gb $3 --seconds 600 --mem-gb 16 --out '"$OUT"'/$1__$2__b$3__t1.json \
    > '"$OUT"'/$1__$2__b$3__t1.log 2>&1' "$PY" &
PIDS=$!
for b in 1 8; do
  cpus=$([ $b = 1 ] && echo 20-35 || echo 36-51)
  OMP_NUM_THREADS=16 taskset -c $cpus "$PY" scripts/table_depth_probe.py bench/instances/mitten_200 sector \
      --budget-gb $b --seconds 1800 --mem-gb 64 --out $OUT/mitten_200__sector__b${b}__t16.json \
      > $OUT/mitten_200__sector__b${b}__t16.log 2>&1 &
  PIDS="$PIDS $!"
done
wait $PIDS
touch logs/table_depth.done
kill $GUARD
