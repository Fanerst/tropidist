#!/bin/bash
# Closing runs (Feng, 29 October 2026): the open instances that a few server-days should settle, with our final
# configuration (ours_pipeline:dp=2) and 32 threads, but a 7-day limit per run instead of the benchmark's hour
# (records in results/bench_extended), and the Cornucopia [[2304,1156,16]] circuit (8 cycles, Z basis, the
# paper's fault model; papers/run_parallel.py as in results/cornucopia) with the time-collapsed search taken
# to weight 13: no solution there gives the lower bound 14, which the weight-14 fault set of
# results/cornucopia/win_q64_r8_Z_t1.json matches.
# Physical cores 0-159 of 5090; cores 160-191 and every hyperthread stay free for other users.
#   0-63     Cornucopia [[2304,1156,16]]                     (about 5 days if the relaxation stays tight)
#   64-95    Tanner [[396,4]]                                 (about 3 days)
#   96-127   BB [[756,16]]                                    (about 5 days)
#   128-159  in turn: Tanner [[288,2]], [[360,4]], [[324,4]], BB [[648,4]], many-hypercube L4, mitten 300
#            (about 4 h, 4 h, 12 h, 37 h, 10 h, 3 h)
# usage: (setsid nohup bash scripts/server/close_open.sh > logs/close/launcher.log 2>&1 < /dev/null &)
cd ~/claude_runs/circuit_distance
PY=~/miniconda3/envs/planarnet/bin/python
OUT=results/bench_extended
LOG=logs/close
T=604800
mkdir -p $LOG results/cornucopia

run() {            # cpus, instance directory, variant, instance names (run one after another)
  local cpus=$1 dir=$2 variant=$3
  shift 3
  for name in "$@"; do
    echo "$(date '+%F %T') start $name ($variant) on $cpus"
    $PY bench/run_matrix.py --methods ours_pipeline:dp=2 --instances "$name" --variants "$variant" \
        --instance-dir "$dir" --threads 32 --time-limit $T --mem-gb 90 --total-mem-gb 90 --jobs 1 --cpus "$cpus" \
        --out $OUT >> $LOG/$name.log 2>&1
    echo "$(date '+%F %T') end $name"
  done
}

(setsid nohup bash scripts/server/mem_guard.sh 600 > /dev/null 2>&1 < /dev/null &)
echo "$(date '+%F %T') start cornucopia 2304 on 0-63"
OMP_NUM_THREADS=64 taskset -c 0-63 $PY papers/run_parallel.py cornucopia 64 Z \
    results/cornucopia/circ_q64_r8_Z_k13.json 8 2 13 $T 1 full 1 > $LOG/cornucopia2304.log 2>&1 &
run 64-95 bench/instances_wjh full wjh_qt_396_4_26 &
run 96-127 bench/instances_wjh full wjh_bb_n756 &
(
  run 128-159 bench/instances_wjh full wjh_qt_288_2_24 wjh_qt_360_4_24 wjh_qt_324_4_25 wjh_bb_n648
  run 128-159 bench/instances full hypercube_L4
  run 128-159 bench/instances sector mitten_300
) &
wait
echo "$(date '+%F %T') all done"
pkill -u "$USER" -f "[m]em_guard.sh 600"
touch $LOG/all.done
