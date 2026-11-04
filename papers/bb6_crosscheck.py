"""Cross-checks of the best depth-7 schedule found by papers/design_bb6_depth7.py for a code:
(a) papers/run_parallel.py with 12 cycles, both bases; (b) the original pipeline scripts/run_bb.py on the
six-cycle circuits without symmetry; also the standard schedule through the same two paths.

Usage: python papers/bb6_crosscheck.py key [family] [seconds per threshold]
"""
import contextlib
import io
import json
import os
import subprocess
import sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import bb6_depth7 as B
import design_bb6_depth7 as D
import run_parallel

key = sys.argv[1]
family = sys.argv[2] if len(sys.argv) > 2 else "ibm"
tl = float(sys.argv[3]) if len(sys.argv) > 3 else 7200
d = B.CODES[key][2][2]
res_all = json.load(open(os.path.join(ROOT, "results", "papers3", "bb6", f"{key}_{family}.json")))
rows = [r for r in res_all["rows"] if "error" not in r and r["Z"][0] == r["Z"][1] and r["X"][0] == r["X"][1]]
top = max(min(r["Z"][0], r["X"][0]) for r in rows)
best = next(r for r in rows if min(r["Z"][0], r["X"][0]) == top)
std = next(s for s in B.all_valid() if B.to_dicts(*s) == (B.STANDARD["X"], B.STANDARD["Z"]))
out_path = os.path.join(ROOT, "results", "papers3", "bb6", f"{key}_{family}_crosscheck.json")
res = {"code": list(B.CODES[key][2]), "family_value": top}
for label, sched in (("best", (tuple(best["px"]), tuple(best["pz"]))), ("standard", std)):
    rec = res.setdefault(label, {"schedule": D.name_of(sched)})
    sys.modules["bb6cc"] = SimpleNamespace(
        CODES=B.CODES, translations=B.translations, tag=lambda k, label=label: f"{k}_{label}",
        build=lambda k, basis, rounds, p=0.001, sched=sched: B.build(k, basis, rounds, p, schedule=B.to_dicts(*sched)))
    for rounds in (6, 12):
        for basis in "ZX":
            path = os.path.join(ROOT, "results", "papers3", "bb6", f"cc_{key}_{label}_r{rounds}_{basis}.json")
            with contextlib.redirect_stdout(io.StringIO()):
                run_parallel.main("bb6cc", key, basis, path, rounds, 3, d, tl, 1)
            r = json.load(open(path))
            rec[f"run_parallel_r{rounds}_{basis}"] = [r.get("certified_lower_bound"), r.get("certified_upper_bound"),
                                                      (r.get("witness") or {}).get("verified")]
            json.dump(res, open(out_path, "w"), indent=1)
            print(key, label, rounds, basis, rec[f"run_parallel_r{rounds}_{basis}"], flush=True)
    for basis in "ZX":
        circ = os.path.join(ROOT, "circuits", "papers", f"bb6cc{key}_{label}_r6_{basis}.stim")
        out = os.path.join(ROOT, "results", "papers3", "bb6", f"cc_{key}_{label}_run_bb_{basis}.json")
        p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "run_bb.py"), circ, out, "--no-sym", "--kmax", str(d),
                            "--time-limit", str(tl)], capture_output=True, text=True)
        if os.path.exists(out):
            r = json.load(open(out))
            rec[f"run_bb_r6_{basis}"] = [r.get("certified_lower_bound"), r.get("certified_upper_bound")]
        else:
            rec[f"run_bb_r6_{basis}"] = ["failed", p.stderr[-300:]]
        json.dump(res, open(out_path, "w"), indent=1)
        print(key, label, "run_bb", basis, rec[f"run_bb_r6_{basis}"], flush=True)
