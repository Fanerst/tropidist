#!/bin/bash
# LINS enumerations for the other triangle groups of arXiv:2610.03682 whose codes have open distance ranges.
cd ~/claude_runs/circuit_distance/results/papers4/hyperbolic || exit 1
G=~/claude_runs/circuit_distance/bench/external/gapenv/bin/gap
for job in "6 6 6 432" "7 7 7 686" "4 4 6 1320" "5 6 6 1440" "7 8 8 2688" "4 4 4 4096" "6 6 6 2184"; do
  set -- $job
  out=lins_$1$2$3_$4.jsonl
  echo "== $(date '+%m-%d %H:%M:%S') ($1,$2,$3) up to $4"
  taskset -c 70 $G -q -o 200g -c "r:=$1;; s:=$2;; t:=$3;; bound:=$4;; out:=\"$out.part\";;" ../../../papers/hyperbolic_lins.g 2>&1 | grep -v "\^\|img :=\|Syntax\|^8$\|^$" | tail -3
  [ -s $out.part ] && mv $out.part $out
done
echo "== $(date '+%m-%d %H:%M:%S') lins queue done"
