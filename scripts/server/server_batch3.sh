#!/bin/bash
# Third batch (catalog papers, 2026-10-03): server runs of the instances the builders left open.
# usage: scripts/server/server_batch3.sh tests|routing|routing200|star|walkingcat|family
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
# Stay on socket 0 (NUMA node 0): another session of the same user runs timed benchmarks pinned to socket 1.
taskset -cp 0-95,192-287 $$ > /dev/null 2>&1
mkdir -p results/papers3/{routing,star,walkingcat,shift,lrgross,estdist} logs/papers3/{routing,star,walkingcat,shift,lrgross,estdist}
case "$1" in
  tests)
    export OMP_NUM_THREADS=4
    for t in routing star walkingcat; do
      $PY tests/test_$t.py > logs/papers3/$t/tests_server.log 2>&1; echo "test_$t exit $?" >> logs/papers3/tests_server.summary
    done ;;
  routing)       # [[110,8,11]] and the two [[140,8,.]] codes: exact value wanted
    export OMP_NUM_THREADS=16
    for key in 110 140_12 140_13; do
      ( for b in Z X; do
          $PY papers/run_parallel.py routing $key $b results/papers3/routing/server_${key}_$b.json 6 3 14 7200 \
              > logs/papers3/routing/server_${key}_$b.log 2>&1
        done ) &
    done
    wait; touch logs/papers3/routing/server.done ;;
  routing200)    # weight-11 codes: lower bounds only are expected
    export OMP_NUM_THREADS=16
    for key in 200_24 200_16; do
      ( for b in Z X; do
          $PY papers/run_parallel.py routing $key $b results/papers3/routing/server_${key}_$b.json 6 3 18 3600 0 \
              > logs/papers3/routing/server_${key}_$b.log 2>&1
        done ) &
    done
    wait; touch logs/papers3/routing/server200.done ;;
  star)          # every valid depth-8 schedule of the d = 6 code (paper: 20 at distance 5, 192 at 4), then 78 Z
    export OMP_NUM_THREADS=1
    N=$($PY -c "import sys; sys.path.insert(0,'papers'); import star; print(len(star.valid_schedules(42)))")
    for i in $(seq 0 $((N-1))); do for b in Z X; do echo "$i $b"; done; done | \
      xargs -P 24 -L 1 bash -c '$0 papers/star_run.py $1 42 $2 results/papers3/star/schedule_${1}_$2.json 6 2 10 600 1 full > logs/papers3/star/schedule_${1}_$2.log 2>&1' $PY
    OMP_NUM_THREADS=24 $PY papers/run_parallel.py star 78 Z results/papers3/star/78_Z_extended.json 6 3 12 3600 \
        > logs/papers3/star/78_Z_extended.log 2>&1
    touch logs/papers3/star/server.done ;;
  walkingcat)    # every numbering of the Table 10 terms
    for key in 70 54 102; do
      $PY papers/walkingcat_labelings.py $key 24 Z 6 900 > logs/papers3/walkingcat/labelings_$key.log 2>&1
    done
    touch logs/papers3/walkingcat/labelings.done ;;
  family)        # all 3456 mirror orders for the small self-dual BB codes below full distance
    for n in 16 32 56 64 80 78 84; do
      $PY papers/design_sdbb_parallel_all.py $n ${2:-48} 6 300 > logs/papers2/design/sdbb${n}_parallel_family.log 2>&1
    done
    touch logs/papers2/design/family.done ;;
esac
# ---- added later: shift circuits (arXiv:2601.09911), six cycles, static / dynamic / one dynamic pair
if [ "$1" = shift ]; then
  export OMP_NUM_THREADS=8
  for n in 120 144 170; do
    ( for v in s d m; do for b in Z X; do
        $PY papers/run_parallel.py shift $n$v $b results/papers3/shift/server_${n}${v}_$b.json 6 3 12 3600 \
            > logs/papers3/shift/server_${n}${v}_$b.log 2>&1
      done; done ) &
  done
  wait; touch logs/papers3/shift/server.done
fi
# ---- added later: decide the weight-11 routing codes with the full search; code distances; walking-cat top numberings
if [ "$1" = routing200full ]; then
  export OMP_NUM_THREADS=16
  for b in Z X; do
    $PY papers/run_parallel.py routing 200_24 $b results/papers3/routing/server_full_200_24_$b.json 6 3 12 7200 1 \
        > logs/papers3/routing/server_full_200_24_$b.log 2>&1 &
  done
  wait
  for b in Z X; do
    $PY papers/run_parallel.py routing 200_16 $b results/papers3/routing/server_full_200_16_$b.json 6 3 14 7200 1 \
        > logs/papers3/routing/server_full_200_16_$b.log 2>&1 &
  done
  wait; touch logs/papers3/routing/server200full.done
fi
if [ "$1" = wctop ]; then
  export OMP_NUM_THREADS=8
  for key in 70 54 102; do $PY papers/walkingcat_top.py $key 6 1800 > logs/papers3/walkingcat/top_$key.log 2>&1; done
  touch logs/papers3/walkingcat/top.done
fi
# ---- added later: the lead's own re-runs of everything the builders ran locally (small cases)
if [ "$1" = verify ]; then
  export OMP_NUM_THREADS=8
  run() { $PY papers/run_parallel.py $1 $2 $3 results/papers3/$1/server_$2_$3.json 6 3 ${4:-14} 3600 > logs/papers3/$1/server_$2_$3.log 2>&1; }
  for k in 54 70 80 90 100; do for b in Z X; do run routing $k $b; done; done
  for k in 42 66 78; do for b in Z X; do run star $k $b 12; done; done
  for k in 54 70 102; do run walkingcat $k X 12; done
  for k in 72s 72d 72m; do for b in Z X; do run shift $k $b 12; done; done
  touch logs/papers3/verify.done
fi
# ---- added later: mirror orders of the larger self-dual BB codes that fell short of full distance (window filter first)
if [ "$1" = funnel ]; then
  while [ ! -f logs/papers2/design/family.done ]; do sleep 30; done
  for n in ${3:-104 112 132 160 152}; do
    $PY papers/design_sdbb_parallel_funnel.py $n ${2:-48} 0 300 3600 12 > logs/papers2/design/sdbb${n}_parallel_funnel.log 2>&1
  done
  touch logs/papers2/design/funnel.done
fi
# ---- added later: code distances that papers give as estimates (registry of papers/estimated_codes.py)
if [ "$1" = estdist ]; then
  export ESTDIST_TOTAL_SECONDS=0
  # the whole registry again, as the lead's own run (the builder's local run certified 245 of 250)
  OMP_NUM_THREADS=32 $PY papers/estimated_codes_run.py results/papers3/estdist/server.json 20 1800 > logs/papers3/estdist/server.log 2>&1
  # the open cases with long limits
  for c in "balanced_550_110_18 20 7200" "balanced_525_105_18 20 7200" "balanced_625_125_20 22 7200" "llmbb_360_12_24_V 24 21600"; do
    set -- $c
    OMP_NUM_THREADS=32 $PY papers/estimated_codes_run.py results/papers3/estdist/server_$1.json $2 $3 $1 > logs/papers3/estdist/server_$1.log 2>&1
  done
  touch logs/papers3/estdist/server.done
fi
if [ "$1" = design2 ]; then      # sequential designs, restarted with fewer processes
  export OMP_NUM_THREADS=1
  for n in 144 150 162 174 186 152 160 168 176 184; do
    $PY papers/design_selfdual_bb.py $n results/papers2/design/sdbb$n.json 48 300 1800 > logs/papers2/design/sdbb$n.log 2>&1
  done
  for n in 138 180; do
    $PY papers/design_selfdual_bb.py $n results/papers2/design/sdbb${n}_long.json 48 600 5400 > logs/papers2/design/sdbb${n}_long.log 2>&1
  done
  touch logs/papers2/design/remaining.done
fi
# ---- added later: mirror parallel circuits for the weight-8 BB codes of 2609.06572 (papers/bb8_parallel.py)
if [ "$1" = bb8 ]; then
  P=${2:-40}
  for k in 1 2; do
    $PY papers/design_sdbb_parallel_all.py $k $P 6 600 bb8_parallel > logs/papers2/design/bb8_${k}_parallel_family.log 2>&1
  done
  for k in 3 4 5; do
    $PY papers/design_sdbb_parallel_funnel.py $k $P 0 120 3600 8 bb8_parallel > logs/papers2/design/bb8_${k}_parallel_funnel.log 2>&1
  done
  touch logs/papers2/design/bb8.done
fi
# ---- added later: BB756 code-distance lower bound (window t=0 with the covering bound), continued from weight 28
if [ "$1" = bb756 ]; then
  while [ ! -f logs/papers2/design/funnel.done ] || [ ! -f logs/papers2/design/bb8.done ]; do sleep 60; done
  OMP_NUM_THREADS=64 $PY scripts/run_window.py circuits/bb756_r34_Z.stim results/phase4/window0_cover_bb756_r34_Z_from28.json 0 0 30 3 14400 28 1 \
      > logs/phase4/window0_cover_bb756_r34_Z_from28.log 2>&1
  touch logs/phase4/bb756_from28.done
fi
# ---- added later: cross-checks of the mirror circuits found by the full sweeps
if [ "$1" = famcheck ]; then
  export OMP_NUM_THREADS=12
  for n in 16 32 56 64 78; do $PY papers/family_crosscheck.py $n > logs/papers2/design/sdbb${n}_family_crosscheck.log 2>&1; done
  $PY papers/family_crosscheck.py 1 bb8_parallel > logs/papers2/design/bb8_1_family_crosscheck.log 2>&1
  touch logs/papers2/design/famcheck.done
fi
# ---- added later: every depth-7 schedule of the standard family (936) for the weight-6 BB codes
if [ "$1" = bb6 ]; then
  mkdir -p results/papers3/bb6 logs/papers3/bb6
  while [ ! -f logs/papers3/routing/server200full.done ]; do sleep 30; done
  for key in bb72 bb90 bb108 gross; do
    $PY papers/design_bb6_depth7.py $key ibm ${2:-40} 900 $([ $key = gross ] && echo 11 || echo 99) 14400 > logs/papers3/bb6/${key}_ibm.log 2>&1
  done
  touch logs/papers3/bb6/ibm.done
fi
# ---- added later (after the kill of 01:21:57): re-runs and the complete depth-7 family
if [ "$1" = bb6all ]; then
  for key in bb72 bb90 bb108 gross; do
    $PY papers/design_bb6_depth7.py $key all ${2:-40} 900 $([ $key = gross ] && echo 11 || echo 99) 14400 > logs/papers3/bb6/${key}_all.log 2>&1
  done
  touch logs/papers3/bb6/all.done
fi
if [ "$1" = rerun1 ]; then
  $PY papers/design_sdbb_parallel_all.py 2 ${2:-40} 6 600 bb8_parallel > logs/papers2/design/bb8_2_parallel_family.log 2>&1
  $PY papers/design_sdbb_parallel_funnel.py 104 ${2:-40} 0 120 3600 6 > logs/papers2/design/sdbb104_parallel_funnel.log 2>&1
  touch logs/papers2/design/rerun1.done
fi
if [ "$1" = rerun200 ]; then
  OMP_NUM_THREADS=32 $PY papers/run_parallel.py routing 200_16 X results/papers3/routing/server_full2_200_16_X.json 6 3 10 14400 1 \
      > logs/papers3/routing/server_full2_200_16_X.log 2>&1
  touch logs/papers3/routing/rerun200.done
fi
# ---- added later (after the second kill, 03:06:53): resume what was lost, one chain at a time
if [ "$1" = rerun2 ]; then
  while [ ! -f logs/papers2/design/rerun1.done ]; do sleep 30; done
  $PY papers/design_sdbb_parallel_all.py 2 ${2:-40} 6 600 bb8_parallel >> logs/papers2/design/bb8_2_parallel_family.log 2>&1
  $PY papers/design_bb6_depth7.py bb108 all ${2:-40} 900 99 14400 >> logs/papers3/bb6/bb108_all.log 2>&1
  $PY papers/design_sdbb_parallel_funnel.py 112 ${2:-40} 0 120 3600 6 > logs/papers2/design/sdbb112_parallel_funnel.log 2>&1
  $PY papers/design_sdbb_parallel_funnel.py 3 ${2:-40} 0 120 3600 8 bb8_parallel > logs/papers2/design/bb8_3_parallel_funnel.log 2>&1
  touch logs/papers2/design/rerun2.done
fi
if [ "$1" = rerun3 ]; then
  while [ ! -f logs/papers2/design/remaining.done ]; do sleep 60; done
  export OMP_NUM_THREADS=1
  for n in 168 174; do
    $PY papers/design_selfdual_bb.py $n results/papers2/design/sdbb$n.json 48 300 1800 > logs/papers2/design/sdbb$n.log 2>&1
  done
  OMP_NUM_THREADS=40 $PY papers/run_parallel.py routing 200_16 X results/papers3/routing/server_full2_200_16_X.json 6 3 10 6000 1 \
      > logs/papers3/routing/server_full2_200_16_X.log 2>&1
  touch logs/papers2/design/rerun3.done
fi
# ---- added later: first exact values for the larger weight-8 BB codes (collapsed-bound pick instead of the window filter)
if [ "$1" = pick ]; then
  for k in 3 4 5; do
    $PY papers/design_parallel_pick.py bb8_parallel $k ${2:-40} 6 1500 10 > logs/papers2/design/bb8_${k}_parallel_pick.log 2>&1
  done
  touch logs/papers2/design/pick.done
fi
# ---- added later (06:20, after the memory leak was found and fixed): resume the two all-schedule sweeps and the picks
if [ "$1" = rerun4 ]; then
  $PY papers/design_bb6_depth7.py bb108 all ${2:-40} 900 99 14400 >> logs/papers3/bb6/bb108_all.log 2>&1
  $PY papers/design_bb6_depth7.py gross all ${2:-40} 900 11 14400 >> logs/papers3/bb6/gross_all.log 2>&1
  touch logs/papers3/bb6/all2.done
fi
if [ "$1" = pick3 ]; then
  while [ ! -f logs/papers2/design/pick.done ]; do sleep 60; done
  $PY papers/design_parallel_pick.py bb8_parallel 3 ${2:-40} 6 1500 10 > logs/papers2/design/bb8_3_parallel_pick.log 2>&1
  touch logs/papers2/design/pick3.done
fi
# ---- added later: BB360 Z, lower bound 18 (all collapsed solutions up to weight 17, then lifting); W = 17 only
if [ "$1" = bb360z17 ]; then
  export OMP_NUM_THREADS=${2:-96}
  $PY scripts/enum_collapsed.py circuits/bb360_r24_Z.stim results/phase4/enum_cover_bb360_r24_Z_K17.json 17 3 1 \
      > logs/phase4/enum_cover_bb360_r24_Z_K17.log 2>&1 && \
  $PY scripts/run_topdown.py circuits/bb360_r24_Z.stim results/phase4/enum_cover_bb360_r24_Z_K17.json 17 \
      results/phase4/topdown_bb360_r24_Z_W17.json > logs/phase4/topdown_bb360_r24_Z_W17.log 2>&1
  touch logs/phase4/bb360_Z_W17.done
fi
