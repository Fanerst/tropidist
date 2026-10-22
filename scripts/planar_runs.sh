#!/bin/bash
# Runs of the planar study: the pipeline adapter with the DP front end (dp=1) and without it (dp=0) on exported
# instances.  usage: scripts/planar_runs.sh <variant> <out tag> <threads> <time limit> <table GiB> <instance dir>...
# Records go to results/planar_dp/<out tag>_dp{1,0}/<instance>__t<threads>.json; DPS="1 0" by default.
variant=$1; tag=$2; threads=$3; tl=$4; gb=$5; shift 5
PY=${PY:-.venv/bin/python}
for inst in "$@"; do
  name=$(basename "$inst")
  for dp in ${DPS:-1 0}; do
    mkdir -p results/planar_dp/${tag}_dp$dp
    out=results/planar_dp/${tag}_dp$dp/${name}__t$threads.json
    [ -f "$out" ] && continue
    echo "$(date +%T) $name dp=$dp"
    OMP_NUM_THREADS=$threads $PY bench/adapters/ours_pipeline.py --instance "$inst" --variant "$variant" \
      --time-limit "$tl" --threads "$threads" --out "$out" --config dp=$dp,table_gb=$gb
  done
done
