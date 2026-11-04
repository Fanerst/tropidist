"""Cross-validation of the two exact routes on every small circuit:

  direct   : exhaustive search of the real (sector) problem   [scripts/run_bb.py]
  top-down : enumerate collapsed solutions, lift with slack   [scripts/enum_collapsed.py + scripts/run_topdown.py]

For each circuit with direct distance d, the top-down route must report
"no solution of weight <= d-1" and must find a solution at W = d.
"""
import json
import os
import subprocess
import sys

PY = sys.executable
codes = ["bb72_r6", "bb90_r10", "bb108_r10", "bb144_r12"]
rows = []
for c in codes:
    for b in "ZX":
        name = f"{c}_{b}"
        d = json.load(open(f"results/{name}.json"))["stages"]["full"]["distance"]
        out = {"circuit": name, "direct_distance": d}
        for W in (d - 1, d):
            e = f"results/validate/enum_{name}_K{W}.json"
            t = f"results/validate/topdown_{name}_W{W}.json"
            os.makedirs("results/validate", exist_ok=True)
            subprocess.run([PY, "scripts/enum_collapsed.py", f"circuits/{name}.stim", e, str(W), "3"], check=True,
                           stdout=subprocess.DEVNULL)
            subprocess.run([PY, "scripts/run_topdown.py", f"circuits/{name}.stim", e, str(W), t], check=True,
                           stdout=subprocess.DEVNULL)
            r = json.load(open(t))
            en = json.load(open(e))
            out[f"W={W}"] = {"collapsed_orbits": {w: v["orbits"] for w, v in en["weights"].items()},
                             "found": None if r["found"] is None else r["found"]["weight"],
                             "verified": None if r["found"] is None else r["found"]["verified"],
                             "certified_lower_bound": r.get("certified_lower_bound")}
        ok = (out[f"W={d-1}"]["found"] is None and out[f"W={d-1}"]["certified_lower_bound"] == d
              and out[f"W={d}"]["found"] == d and out[f"W={d}"]["verified"])
        out["agree"] = bool(ok)
        rows.append(out)
        print(name, "direct d =", d, "| top-down W=d-1:", out[f"W={d-1}"]["found"], "LB", out[f"W={d-1}"]["certified_lower_bound"],
              "| top-down W=d:", out[f"W={d}"]["found"], "| agree:", ok, flush=True)
json.dump(rows, open("results/validate_topdown_small.json", "w"), indent=1)
print("all agree:", all(r["agree"] for r in rows))
