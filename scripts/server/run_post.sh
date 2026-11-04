#!/bin/bash
# Everything except the BB288 pipeline: tests, small codes (two routes), consistency checks, dense run.
PY=${PY:-python}
T=${T:-128}
mkdir -p results logs
export OMP_NUM_THREADS=$T
{
  for t in test_dp test_search test_topdown test_enum test_tn test_replay independent_bb72; do
    $PY tests/$t.py || echo "FAILED $t"
  done
} > logs/tests.log 2>&1
for c in bb72_r6 bb90_r10 bb108_r10 bb144_r12; do
  for b in Z X; do
    $PY scripts/run_bb.py circuits/${c}_${b}.stim results/${c}_${b}.json --enum-collapsed > logs/${c}_${b}.log 2>&1
    $PY scripts/run_deep.py circuits/${c}_${b}.stim results/deep_${c}_${b}.json --kmax 14 --k-table 3 > logs/deep_${c}_${b}.log 2>&1
  done
done
$PY scripts/validate_topdown_small.py > logs/validate_topdown_small.log 2>&1
for b in X Z; do
  $PY scripts/crosscheck_plain.py circuits/bb288_r18_${b}.stim results/crosscheck_bb288_r18_${b}.json 12 > logs/crosscheck_bb288_r18_${b}.log 2>&1
done
for c in bb72_r6 bb144_r12; do
  for b in Z X; do
    $PY scripts/crosscheck_plain.py circuits/${c}_${b}.stim results/crosscheck_${c}_${b}.json 9 > logs/crosscheck_${c}_${b}.log 2>&1
  done
done
# dense Rank DP near the memory limit: BB144 code capacity, one process per observable
export OMP_NUM_THREADS=16
for i in 0 1 2 3 4 5 6 7 8 9 10 11; do
  $PY scripts/run_dense_big.py circuits/bb144_r12_Z.stim capacity results/dense_big_bb144_r12_Z_obs${i}.json 38 $i > logs/dense_big_bb144_obs${i}.log 2>&1 &
done
wait
# ... and the collapsed BB90 circuit problem (64 GB per observable)
export OMP_NUM_THREADS=24
for i in 0 1 2 3 4 5 6 7; do
  $PY scripts/run_dense_big.py circuits/bb90_r10_Z.stim collapsed results/dense_big_bb90_r10_Z_collapsed_obs${i}.json 38 $i > logs/dense_big_bb90c_obs${i}.log 2>&1 &
done
wait
echo POST_DONE > logs/post.done
