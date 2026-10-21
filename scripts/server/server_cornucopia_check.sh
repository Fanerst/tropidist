#!/bin/bash
# Check of the distances of arXiv:2608.02773 (Cornucopia codes), October 2026.
#   queue A: code distances of [[2844,1426]] without the parity shortcut, then the circuit distance in the
#            setting of the authors' repository (one syndrome cycle, CNOT faults only) for all seven codes;
#   queue B: the circuit distance of the memory experiments the paper simulates (N_c = 7, 8, 8 cycles, the
#            paper's full fault model) for the three largest codes, with the covering bound.
# usage: [QS="7 16 ..."] [K_COLL=k] scripts/server/server_cornucopia_check.sh A|B [threads] [seconds per threshold]
# A finished record (key "seconds") is not recomputed.
Q=$1
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
export OMP_NUM_THREADS=${2:-64}
T=${3:-3600}
# completion table of the collapsed problem: all column sets of size <= k, 9 bytes per slot at load 0.5, so k = 3
# needs 77 GB for q = 25 and 155 GB for q = 29 but 620 GB from q = 49 on; k = 2 there
kc() { if [ -n "$K_COLL" ]; then echo $K_COLL; elif [ "$1" -le 29 ]; then echo 3; else echo 2; fi; }
done_rec() { [ -f "$1" ] && grep -q '^ "seconds": ' "$1"; }
mkdir -p results/cornucopia logs/cornucopia
if [ "$Q" = A ]; then
  done_rec results/cornucopia/code_distance_noparity.json ||
    $PY scripts/cornucopia_code_distance.py results/cornucopia/code_distance_noparity.json 79 XZ 0 --no-parity \
        > logs/cornucopia/code_distance_noparity.log 2>&1
  for q in ${QS:-7 16 25 29 49 64 79}; do
    for b in Z X; do
      [ "$q" -ge 49 ] && [ "$b" = X ] && continue
      done_rec results/cornucopia/circ_q${q}_r1_${b}_cx.json && continue
      $PY papers/run_parallel.py cornucopia $q $b results/cornucopia/circ_q${q}_r1_${b}_cx.json 1 $(kc $q) 20 $T 1 cx \
          > logs/cornucopia/circ_q${q}_r1_${b}_cx.log 2>&1
    done
  done
else
  # the last step (exact search of the sector problem) builds an all-pairs table of its columns: 77 GB for q = 49,
  # 7 cycles, about 310 GB for q = 79, 8 cycles; it is run for q = 49 only
  for qr in "49 7 1" "64 8 0" "79 8 0"; do
    set -- $qr
    done_rec results/cornucopia/circ_q$1_r$2_Z.json && continue
    $PY papers/run_parallel.py cornucopia $1 Z results/cornucopia/circ_q$1_r$2_Z.json $2 $(kc $1) 18 $T $3 full 1 \
        > logs/cornucopia/circ_q$1_r$2_Z.log 2>&1
  done
fi
touch logs/cornucopia/queue_$Q.done
