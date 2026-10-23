#!/bin/bash
# The records of table_depth_suite.sh whose run under the depth rule held a deepening trial (notes: stages.*.deepen),
# rerun after the trial's last change (task depth 1 for its two sample runs), again side by side with table_gb=1 so
# that each pair keeps its common time: the flags and cores of table_depth_suite.sh without give-up (these records
# ran there), records replaced in results/bench_tables, 23 October 2026.  Under the project's memory guard.
# usage: (setsid nohup bash scripts/server/table_depth_trials.sh > /dev/null 2>&1 < /dev/null &)
cd "$(dirname "$0")/../.." || exit 1
PY=${PY:-$HOME/miniconda3/envs/planarnet/bin/python}
mkdir -p logs/bench results/lists
nohup bash scripts/server/mem_guard.sh 500 > /dev/null 2>&1 &
GUARD=$!
"$PY" - <<'EOF'
import json, glob, os
out = {"sector": set(), "full": set()}
for f in glob.glob("results/bench_tables/ours_pipeline__dp-1/*__t1.json"):
    r = json.load(open(f))
    n = r.get("notes")
    n = json.loads(n) if isinstance(n, str) and n.startswith("{") else (n if isinstance(n, dict) else {})
    if any(st.get("deepen") for st in n.get("stages", {}).values()):
        out[r["variant"]].add(r["instance"])
for v, names in out.items():
    open("results/lists/table_trials_%s.txt" % v, "w").write("".join(x + "\n" for x in sorted(names)))
    print(v, sorted(names))
EOF
REDO="--redo status=exact --redo status=timeout --redo status=bounds --redo status=error"
RUN="$PY bench/run_matrix.py --threads 1 --time-limit 600 --mem-gb 16 --total-mem-gb 288 --jobs 18
     --out results/bench_tables $REDO"
PIDS=""
for v in sector full; do
  [ -s results/lists/table_trials_$v.txt ] || continue
  $RUN --methods ours_pipeline:dp=1 --instances @results/lists/table_trials_$v.txt --variants $v --cpus 0-17 \
      >> logs/bench/tables_trials_rule.log 2>&1 &
  PIDS="$PIDS $!"
  $RUN --methods ours_pipeline:dp=1,table_gb=1 --instances @results/lists/table_trials_$v.txt --variants $v \
      --cpus 18-35 >> logs/bench/tables_trials_1gib.log 2>&1 &
  PIDS="$PIDS $!"
  wait $PIDS
  PIDS=""
done
touch logs/bench/tables_trials.done
kill $GUARD
