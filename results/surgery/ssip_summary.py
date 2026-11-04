"""Summary of the exact reruns of SSIP's gross-code benchmarks (papers/ssip_exact.py) against SSIP's recorded results.

For each script and basis: the measurements SSIP lists, the depth r it found with QDistRnd, the bare and dressed
distances of the merged code at that depth (the last call of each measurement in the run steered by the bare
distance), and the depth found when the run is steered by the dressed distance.  A script's calls are matched to its
result lines in order: a measurement found at depth r used the calls for depths 1..r.  Also, per measurement, the
distance with the gauge logicals of the other basis fixed (bare distance in the measured basis, dressed in the other)
and, where <script>_gauge/gauge.jsonl exists (papers/ssip_gauge_fix.py), whether preparing the new qubits fixes them.

Usage: python ssip_summary.py PATH/TO/SSIP/benchmarking/results [OUT.json] [RUNS]
    reads <script>_bare/ and <script>_dressed/ in RUNS (default ssip/, next to this file).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = {   # script: (result files in execution order, field index of r, field index of the size figure, size label)
    "ext_merges": (["gross_ext_X_merges", "gross_ext_Z_merges"], 2, 3, "new qubits / 288"),
    "int_merges": (["gross_int_X_merges", "gross_int_Z_merges"], 2, 3, "new qubits / 144"),
    "singleqs": (["gross_X_singleqs", "gross_Z_singleqs"], 1, 3, "new qubits / 144"),
    "par_ext_merges": (["gross_par_ext_X_merges", "gross_par_ext_Z_merges"], 0, 1, "new qubits / 288"),
    "par_singleqs": (["gross_par_X_singleqs", "gross_par_Z_singleqs"], 0, 2, "new qubits / 144"),
}


def lines(path):
    if not os.path.exists(path):
        return None
    return [l.strip().split(",") for l in open(path) if l.strip() and l[0].isdigit()]


def value(x):
    return x["value"] if x["value"] is not None else x["lower_bound"]


def summarize(ssip_results, runs="ssip"):
    out = {}
    for script, (files, ri, si, label) in SCRIPTS.items():
        bare_dir, dressed_dir = os.path.join(HERE, runs, script + "_bare"), os.path.join(HERE, runs, script + "_dressed")
        calls_path = os.path.join(bare_dir, "calls.jsonl")
        if not os.path.exists(calls_path):
            continue
        calls = [json.loads(l) for l in open(calls_path)]
        gauge_path = os.path.join(HERE, runs, script + "_gauge", "gauge.jsonl")       # papers/ssip_gauge_fix.py
        gauge = [json.loads(l) for l in open(gauge_path)] if os.path.exists(gauge_path) else None
        assert gauge is None or len(gauge) == len(calls)
        pos = 0
        rec = {"size_figure": label, "files": {}}
        for name in files:
            ssip = lines(os.path.join(ssip_results, name + ".txt"))
            ours_bare = lines(os.path.join(bare_dir, "results", name + ".txt"))
            ours_dressed = lines(os.path.join(dressed_dir, "results", name + ".txt"))
            if ssip is None or ours_bare is None:
                continue
            b = 0 if "_X_" in name else 1                  # the measured basis, as an index into [X, Z]
            rows = []
            for k, l in enumerate(ssip):
                r = int(l[ri])
                c = calls[pos + r - 1]
                row = {"line": ",".join(l), "r_ssip": r, "size_ssip": float(l[si]), "n": c["n"], "k": c["k"], "gauge": c["gauge"],
                       "bare": [value(x) for x in c["bare"]], "dressed": [value(x) for x in c["dressed"]]}
                # with the gauge logicals of the other basis fixed: bare distance in the measured basis, dressed in the other
                row["gauge_fixed"] = min(row["bare"][b], row["dressed"][1 - b])
                if gauge is not None:
                    g = gauge[pos + r - 1]
                    assert (g["n"], g["gauge"]) == (c["n"], c["gauge"])
                    row["fixed_by_preparation"] = (g["Z_checks_definite_with_0"] and g["gauge_Z_definite_with_0"] == g["gauge"]) if b == 0 \
                        else (g["X_checks_definite_with_plus"] and g["gauge_X_definite_with_plus"] == g["gauge"])
                pos += r
                if ours_dressed is not None and k < len(ours_dressed):
                    row["r_dressed"] = int(ours_dressed[k][ri])
                    row["size_dressed"] = float(ours_dressed[k][si])
                rows.append(row)
            f = {"measurements": len(rows), "bare_rerun_identical": ours_bare == ssip,
                 "dressed_below_12_at_ssip_depth": sum(min(x["dressed"]) < 12 for x in rows),
                 "least_dressed_at_ssip_depth": min(min(x["dressed"]) for x in rows),
                 "bare_at_least_12": all(min(x["bare"]) >= 12 for x in rows),
                 "least_gauge_fixed_at_ssip_depth": min(x["gauge_fixed"] for x in rows)}
            if gauge is not None:
                f["fixed_by_preparation"] = sum(x["fixed_by_preparation"] for x in rows)
            if all("r_dressed" in x for x in rows) and ours_dressed is not None and len(ours_dressed) == len(rows):
                f["deeper_with_dressed"] = sum(x["r_dressed"] > x["r_ssip"] for x in rows)
                f["size_sum_ssip"] = round(sum(x["size_ssip"] for x in rows), 4)
                f["size_sum_dressed"] = round(sum(x["size_dressed"] for x in rows), 4)
            f["rows"] = rows
            rec["files"][name] = f
        rec["calls"], rec["calls_matched"] = len(calls), pos
        out[script] = rec
    return out


if __name__ == "__main__":
    res = summarize(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else "ssip")
    for script, rec in res.items():
        print(script, "calls", rec["calls"], "matched", rec["calls_matched"])
        for name, f in rec["files"].items():
            print("  ", name, {k: v for k, v in f.items() if k != "rows"})
    if len(sys.argv) > 2:
        json.dump(res, open(sys.argv[2], "w"), indent=1)
