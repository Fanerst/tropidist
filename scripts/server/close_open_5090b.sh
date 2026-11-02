#!/bin/bash
# The two longest closing runs again on 5090b (Feng, 29 October 2026), whose cores are about 1.7 times faster per
# 32-thread run than 5090's: our final configuration with kmax one below the weight of a codeword found by the
# randomised search (records in results/bench_extended/isd on 5090), so that each run ends as soon as its lower
# bound reaches that weight, and the codeword completes the certificate.  The copies on 5090 keep running until
# these finish.  5090b has no Python environment: pyenv/ holds a copy of 5090c's uv interpreter (3.12.15) and numpy.
# Physical cores 0-31 (socket 0) and 32-63 (socket 1); the hyperthreads 64-127 stay free for other users.
#   0-31   Tanner [[396,4]], kmax 26 (codeword of weight 27)
#   32-63  BB [[756,16]], kmax 33 (codeword of weight 34)
# usage: (setsid nohup bash scripts/server/close_open_5090b.sh > logs/close/launcher_5090b.log 2>&1 < /dev/null &)
cd ~/claude_runs/circuit_distance
PY=pyenv/cpython-3.12.15-linux-x86_64-gnu/bin/python3.12
export PYTHONPATH=$PWD/pyenv/site-packages
OUT=results/bench_extended
LOG=logs/close
T=604800
mkdir -p $LOG

run() {            # cpus, kmax, instance name
  echo "$(date '+%F %T') start $3 (kmax $2) on $1"
  $PY bench/run_matrix.py --methods ours_pipeline:dp=2,kmax=$2 --instances "$3" --variants full \
      --instance-dir bench/instances_wjh --threads 32 --time-limit $T --mem-gb 90 --total-mem-gb 90 --jobs 1 \
      --cpus "$1" --out $OUT >> $LOG/$3.log 2>&1
  echo "$(date '+%F %T') end $3"
}

(setsid nohup bash scripts/server/mem_guard.sh 200 > /dev/null 2>&1 < /dev/null &)
run 0-31 26 wjh_qt_396_4_26 &
run 32-63 33 wjh_bb_n756 &
wait
echo "$(date '+%F %T') all done"
pkill -u "$USER" -f "[m]em_guard.sh 200"
touch $LOG/all.done
