#!/bin/bash
# Second tier of the sparse-logical-basis rerun (what `tier_b.py sparseL2` runs), split over idle cores so that it
# need not wait for the dist-m4ri reruns: CP-SAT at 32 threads on cores 96-159 and the five single-thread tools on
# cores 160-189 start at once; Gurobi at 32 threads starts on cores 0-63 when the dist-m4ri reruns have ended.
# Per-run limits as in tier_b.py: 32 threads / 90 GB or 1 thread / 16 GB, 1 h, give-up 1, instances that the same
# configuration did not solve in the first tier (results/bench).
cd ~/claude_runs/circuit_distance
. ~/opt/gurobi-env.sh
export https_proxy=http://127.0.0.1:7890 HTTPS_PROXY=http://127.0.0.1:7890
PY=bench/external/venv/bin/python
LOG=logs/bench/sparseL2_split.log
$PY - <<'PYEOF' >> $LOG 2>&1
import sys
from pathlib import Path
sys.path.insert(0, "bench")
import tier_b
sl = lambda s: s + ",lbasis=std"
specs = {"cpsat": sl("milp:backend=cpsat"), "gurobi": sl(tier_b.GUROBI), "scipy": sl("milp:backend=scipy"),
         "incremental": sl("sat:mode=incremental"), "rc2": sl("sat:mode=maxsat"), "cashw": sl(tier_b.CASHW),
         "enmax": sl(tier_b.ENMAX)}
lists = Path("results/bench_tierB/lists")
for key, spec in specs.items():
    names = tier_b.unsolved(spec, Path("results/bench"), tracks=("code",))["full"]
    tier = "b32" if key in ("cpsat", "gurobi") else "b1"
    (lists / ("sparseL2_%s__%s__full.txt" % (tier, key))).write_text("".join(n + "\n" for n in names))
    (lists / ("sparseL2_%s__%s__spec.txt" % (tier, key))).write_text(spec + "\n")
    print(key, len(names), " ".join(names), flush=True)
PYEOF
run() {   # key tier threads mem jobs cpus
  local L=results/bench_tierB/lists/sparseL2_$2__$1
  echo "$(date +%T) start $1 cpus $6 jobs $5" >> $LOG
  $PY bench/run_matrix.py --methods "$(cat ${L}__spec.txt)" --instances @${L}__full.txt --variants full --threads $3 \
    --time-limit 3600 --mem-gb $4 --total-mem-gb 270 --jobs $5 --out results/bench_tierB --give-up 1 --cpus $6 \
    > logs/bench/sparseL2_$1.log 2>&1
  echo "$(date +%T) done $1 (exit $?)" >> $LOG
}
run cpsat b32 32 90 2 96-159 &
run scipy b1 1 16 6 160-165 &
run incremental b1 1 16 6 166-171 &
run rc2 b1 1 16 6 172-177 &
run cashw b1 1 16 6 178-183 &
run enmax b1 1 16 6 184-189 &
while pgrep -u panfeng -f "chain_after_dm4r[i]" > /dev/null; do sleep 60; done
run gurobi b32 32 90 2 0-63 &
wait
echo "$(date +%T) sparseL2 done $(date)" >> $LOG
