#!/bin/bash
# Second tier of the low-width trial for our two configurations: each runs on the instances it did not solve in the
# first tier, with the second-tier limits of the main benchmark (32 threads, 3600 s, 90 GB, give-up 1, as
# bench/tier_b.py frontier()).  The two run side by side once the first tier has finished: the search pipeline on the
# physical cores of socket 1, the DP front end on those of socket 0.
cd ~/claude_runs/circuit_distance
PY=bench/external/venv/bin/python
A=results/bench_lowwidth
B=results/bench_lowwidth_tierB
mkdir -p $B/lists logs/bench
run() {
  local spec=$1 cpus=$2
  local folder=$(echo $spec | sed 's/:dp=1/__dp-1/')
  local list=$B/lists/$folder.txt
  $PY - "$A/$folder" "$list" <<'EOF'
import json, sys
from pathlib import Path
folder, out = Path(sys.argv[1]), Path(sys.argv[2])
names = []
for meta in sorted(Path("bench/instances_lowwidth").glob("*/meta.json")):
    m = json.loads(meta.read_text())
    rec = folder / ("%s__full__t1.json" % m["name"])
    status = json.loads(rec.read_text()).get("status") if rec.exists() else "missing"
    if status != "exact":
        names.append(m["name"])
out.write_text("\n".join(names) + "\n")
print(folder.name, len(names), "unsolved:", " ".join(names))
EOF
  $PY bench/run_matrix.py --methods "$spec" --instances @$list --variants full --instance-dir bench/instances_lowwidth \
      --threads 32 --time-limit 3600 --mem-gb 90 --total-mem-gb 270 --jobs 3 --cpus $cpus --out $B --give-up 1 \
      >> logs/bench/lowwidth_tier2_$folder.log 2>&1
}
run ours_pipeline 96-191 &
sleep 30                                   # the two invocations append to the same manifest
run ours_pipeline:dp=1 0-95 &
wait
touch $B/tier2.done
