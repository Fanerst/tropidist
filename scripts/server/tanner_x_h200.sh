#!/bin/bash
# X distance of the four quantum Tanner codes of the benchmark of arXiv:2603.22532 on the H200 server (Feng, 1 November 2026: if h200 has idle
# cores, run them there, so that the Fig. 3 rows can say code distance; the Z distances are in results/bench_extended).  These codes have no
# qubit permutation that exchanges X and Z (results/bench_extended/xz_symmetry_check.py).  First information-set decoding for a codeword of low
# weight, then the search below that weight: a finished search gives the lower bound, and the codeword closes it.
# Threads by the work the Z distances took; one physical thread per core, on cores idle at the start, leaving the rest to BB [[756,16]] and others.
# usage: (setsid nohup bash scripts/server/tanner_x_h200.sh > logs/launcher.log 2>&1 < /dev/null &)
cd ~/claude_runs/tanner_x
PY=~/anaconda3/bin/python
mkdir -p logs results
(setsid nohup bash scripts/server/mem_guard.sh 400 > /dev/null 2>&1 < /dev/null &)
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
CORES=$($PY - <<'PY'
import time
def snap():
    out = {}
    for l in open("/proc/stat"):
        if l.startswith("cpu") and l[3].isdigit():
            a = l.split()
            v = list(map(int, a[1:]))
            out[int(a[0][3:])] = (v[3] + v[4], sum(v))
    return out
a = snap(); time.sleep(5); b = snap()
idle = {c for c in a if (b[c][0] - a[c][0]) > 0.85 * max(1, b[c][1] - a[c][1])}
print(" ".join(str(c) for c in range(96) if c in idle and c + 96 in idle))
PY
)
set -- $CORES
echo "$(date '+%F %T') idle physical cores: $#"
[ "$#" -ge 80 ] || { echo "fewer than 80 idle physical cores, stopping"; pkill -u "$USER" -f "[m]em_guard.sh 400"; exit 1; }
CORE=("$@"); NEXT=0
NAMES=(wjh_qt_288_2_24_Xdist wjh_qt_324_4_25_Xdist wjh_qt_360_4_24_Xdist wjh_qt_396_4_26_Xdist)
THREADS=(12 12 6 50)
LISTS=()
for t in "${THREADS[@]}"; do L=""; for ((i = 0; i < t; i++)); do L="$L,${CORE[$NEXT]}"; NEXT=$((NEXT + 1)); done; LISTS+=("${L:1}"); done
$PY -c "import sys; sys.path[:0]=['.','bench']; from cdist import search, isd; print('kernel threads', search.lib().gm_num_threads())" || exit 1
for k in 0 1 2 3; do
  n=${NAMES[$k]}
  ISDCPUS=$(echo "${LISTS[$k]}" | cut -d, -f1-${THREADS[$k]})
  $PY bench/run_matrix.py --methods isd --instances $n --variants full --instance-dir instances --threads ${THREADS[$k]} --time-limit 600 --mem-gb 8 \
      --total-mem-gb 8 --jobs 1 --cpus "$ISDCPUS" --out results/$n > logs/$n.isd.log 2>&1 &
done
wait
echo "$(date '+%F %T') ISD done"
for k in 0 1 2 3; do
  n=${NAMES[$k]}
  U=$($PY -c "import json,glob; print(min(json.load(open(f))['upper_bound'] for f in glob.glob('results/$n/isd/*.json')))")
  echo "$(date '+%F %T') $n: codeword of weight $U; search up to $((U - 1)) on ${THREADS[$k]} threads"
  (PIPELINE_PROGRESS=logs/$n.progress.json $PY bench/run_matrix.py --methods "ours_pipeline:dp=2,kmax=$((U - 1))" --instances $n --variants full \
      --instance-dir instances --threads ${THREADS[$k]} --time-limit 604800 --mem-gb 90 --total-mem-gb 90 --jobs 1 --cpus "${LISTS[$k]}" \
      --out results/$n > logs/$n.log 2>&1; echo "$(date '+%F %T') $n ended") &
done
wait
echo "$(date '+%F %T') all ended"
pkill -u "$USER" -f "[m]em_guard.sh 400"
touch logs/all.done
