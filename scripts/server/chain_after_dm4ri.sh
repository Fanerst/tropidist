#!/bin/bash
# After the dist-m4ri pass: (1) repeat in pure CC mode its second-tier runs that the bracketing mode stopped
# early (predicted CC round not started), 32 threads / 1 h on cores 32-95, alongside (2) the first tier of the
# sparse-logical-basis rerun (cores 0-23); then (3) the second tier of that rerun.
# Step (3) did not run from here: the waiting parent was stopped on 19 October while the reruns of step (1) went
# on, and sparseL2_split.sh ran that tier on idle cores instead.
cd ~/claude_runs/circuit_distance
while pgrep -u panfeng -f "tier_b.py dm4r[i]" > /dev/null; do sleep 60; done
. ~/opt/gurobi-env.sh
# Gurobi's licence service (token.gurobi.com) is intercepted on direct HTTPS from this machine: renew through
# the local proxy, as git does here
export https_proxy=http://127.0.0.1:7890 HTTPS_PROXY=http://127.0.0.1:7890
bench/external/venv/bin/python - <<'EOF'
import json, glob
for out in ("results/bench_tierB", "results/bench_wjh_tierB"):
    names = {"sector": [], "full": []}
    for p in glob.glob(out + "/distm4ri__build-0.14.7__mode-bracket/*__t32.json"):
        r = json.load(open(p))
        if r.get("status") == "timeout" and r["seconds"] < 0.9 * r["time_limit"] and "predictive" in str(r.get("notes")):
            names[r["variant"]].append(r["instance"].rstrip("/").split("/")[-1])
    for v, ns in names.items():
        open("%s/lists/dm4ri_cc_rerun__%s.txt" % (out, v), "w").write("".join(n + "\n" for n in ns))
        print(out, v, ns, flush=True)
EOF
( for out in results/bench_tierB results/bench_wjh_tierB; do
    idir=bench/instances; [ "$out" = results/bench_wjh_tierB ] && idir=bench/instances_wjh
    for v in sector full; do
      f=$out/lists/dm4ri_cc_rerun__$v.txt
      [ -s $f ] || continue
      bench/external/venv/bin/python bench/run_matrix.py --methods "distm4ri:build=0.14.7,mode=cc" --instances @$f \
        --variants $v --instance-dir $idir --threads 32 --time-limit 3600 --mem-gb 90 --total-mem-gb 180 --jobs 2 \
        --out $out --cpus 32-95
    done
  done > logs/bench/dm4ri_cc_rerun.log 2>&1 ) &
RERUN=$!
bench/external/venv/bin/python bench/tier_b.py sparseL1 > logs/bench/chain_sparseL1.log 2>&1
wait $RERUN
bench/external/venv/bin/python bench/tier_b.py sparseL2 > logs/bench/chain_sparseL2.log 2>&1
echo "chain done $(date)" >> logs/bench/chain_after_dm4ri.log
