#!/bin/bash
# The smaller closing runs, moved from the queue of close_open.sh to 5090c (Feng, 29 October 2026): our final
# configuration, 32 threads, 7-day limit, records in results/bench_extended.  5090c has no Stim, which code
# instances do not need; Python is the uv interpreter of ~/envs/torch with that environment's packages.
# Physical cores 0-31 (socket 0) and 32-63 (socket 1); the hyperthreads 64-127 stay free for other users.
#   0-31   BB [[648,4]]
#   32-63  in turn: Tanner [[360,4]], Tanner [[324,4]], many-hypercube L4
# usage: (setsid nohup bash scripts/server/close_open_5090c.sh > logs/close/launcher_5090c.log 2>&1 < /dev/null &)
cd ~/claude_runs/circuit_distance
PY=~/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/bin/python3.12
export PYTHONPATH=$(ls -d ~/envs/torch/lib/python3.12/site-packages)
OUT=results/bench_extended
LOG=logs/close
T=604800
mkdir -p $LOG

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

(setsid nohup bash scripts/server/mem_guard.sh 200 > /dev/null 2>&1 < /dev/null &)
run 0-31 bench/instances_wjh full wjh_bb_n648 &
(
  run 32-63 bench/instances_wjh full wjh_qt_360_4_24 wjh_qt_324_4_25
  run 32-63 bench/instances full hypercube_L4
) &
wait
echo "$(date '+%F %T') all done"
pkill -u "$USER" -f "[m]em_guard.sh 200"
touch $LOG/all.done
