"""Cross-checks of a mirror circuit found by the full sweep (design_sdbb_parallel_all.py):
the best order is written to the order file, then (a) the pipeline is re-run with 12 cycles in
both bases, (b) the six-cycle Z circuit is given to the original pipeline of this project
(run_bb.py: labelled search, no symmetry).

Usage: python papers/family_crosscheck.py n [module]
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import run_parallel

n = int(sys.argv[1])
module = sys.argv[2] if len(sys.argv) > 2 else "sdbb_parallel"
mod = __import__(module)
prefix = getattr(mod, "PREFIX", "sdbb")
fam = json.load(open(os.path.join(ROOT, "results", "papers2", "design", f"{prefix}{n}_parallel_family.json")))
order = fam["best_orders"][0]
json.dump({"order": order, "source": "best order of the full sweep"}, open(mod.order_file(n), "w"))
d = mod.CODES[n][2][2]
res = {"code": fam["code"], "order": order, "family_value": fam["best_circuit_distance"]}
for b in "ZX":
    out = os.path.join(ROOT, "results", "papers2", "design", f"{prefix}{n}_family_rounds12_{b}.json")
    run_parallel.main(module, n, b, out, 12, 2 if d <= 8 else 3, d, 3600, 1)
    r = json.load(open(out))
    res[f"rounds12_{b}"] = [r.get("certified_lower_bound"), r.get("certified_upper_bound")]
circ = os.path.join(ROOT, "circuits", "papers", f"{prefix}{n}_family_r6_Z.stim")
mod.build(n, "Z", 6).to_file(circ)
out = os.path.join(ROOT, "results", "papers2", "design", f"{prefix}{n}_family_run_bb_Z.json")
p = subprocess.run([sys.executable, os.path.join(ROOT, "run_bb.py"), circ, out, "--no-sym"], capture_output=True, text=True)
res["run_bb_returncode"] = p.returncode
if os.path.exists(out):
    r = json.load(open(out))
    res["run_bb"] = [r.get("certified_lower_bound"), r.get("certified_upper_bound")]
else:
    res["run_bb_stderr"] = p.stderr[-500:]
json.dump(res, open(os.path.join(ROOT, "results", "papers2", "design", f"{prefix}{n}_family_crosscheck.json"), "w"), indent=1)
print(json.dumps(res))
