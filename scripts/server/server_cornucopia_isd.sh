#!/bin/bash
# Witnesses (upper bounds) for the circuit distance of the Cornucopia circuits by randomised information-set
# search on windows of the sector problem (scripts/run_isd.py).  Every witness is checked in the full detector
# error model and replayed in Stim.  First two calibration cases with known exact values ([[900]] one cycle: 9;
# [[1044]] six cycles: 10), then the three largest codes, one cycle (the setting of the authors' search) and
# N_c cycles (the paper's memory experiment, a window of two middle cycles).
# usage: [SPECS="q rounds a b stop_at seconds;..."] scripts/server/server_cornucopia_isd.sh [threads] [seconds per case]
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
export OMP_NUM_THREADS=${1:-32}
S=${2:-1800}
mkdir -p results/cornucopia/isd logs/cornucopia circuits/papers
DEFAULT="25 1 0 1 9 600;29 6 2 3 10 600;49 1 0 1 1 $S;64 1 0 1 1 $S;79 1 0 1 1 $S;49 7 2 3 1 $S;64 8 2 3 1 $S;79 8 2 3 1 $S"
IFS=';' read -ra LIST <<< "${SPECS:-$DEFAULT}"
for spec in "${LIST[@]}"; do
  set -- $spec
  n=$((36 * $1))
  c=circuits/papers/cornucopia${n}_r$2_Z_full.stim
  [ -f $c ] || $PY papers/cornucopia.py $1 Z $2 $c > /dev/null
  out=results/cornucopia/isd/isd_q$1_r$2_Z_w$3-$4.json
  [ -f $out ] && continue
  $PY scripts/run_isd.py $c $out $3 $4 $6 $5 > logs/cornucopia/isd_q$1_r$2_Z_w$3-$4.log 2>&1
done
touch logs/cornucopia/queue_isd.done
