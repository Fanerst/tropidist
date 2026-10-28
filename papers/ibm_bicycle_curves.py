"""Logical error rates of IBM's memory instruction (papers/ibm_bicycle.py) over a grid of physical error rates, for
figure 5 of the NCS manuscript: decoder-independent lower bounds and leading-order terms (papers/ibm_bicycle_bound.py)
of the gross code with the standard schedule and with the best depth-seven schedule (the smallest leading-order term
at p = 1e-3 in results/ibm/bound_gross_d11_c1.jsonl), and of the two-gross code with the standard schedule (from the
witnesses of the certified pipeline runs, the fault sets of papers/ibm_bicycle_enum.py where present, and their
symmetry orbits).

Usage: python papers/ibm_bicycle_curves.py OUT.json
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT]

import bb6_depth7 as B
import ibm_bicycle_bound as BD

PS = (5e-5, 1e-4, 2e-4, 5e-4, 7.322e-4, 1e-3, 2e-3)    # 7.322e-4: the two-gross TFIM estimate of ref.
RES = os.path.join(ROOT, "results", "ibm")


def best_gross():
    """The depth-seven schedule with the smallest leading-order term at p = 1e-3 (sum over the two bases)."""
    best = None
    for line in open(os.path.join(RES, "bound_gross_d11_c1.jsonl")):
        r = json.loads(line)
        if any("error" in r[b] for b in "ZX"):
            continue
        lead = sum(10 ** r[b]["rates"]["0.001"]["log10_leading_order"] for b in "ZX")
        if best is None or lead < best[0]:
            best = (lead, (tuple(r["px"]), tuple(r["pz"])))
    return best[1]


def entry(key, sched, stag, d, given=None, bases="ZX"):
    """d: the certified distance, or {basis: distance}; given: None or {basis: fault sets}."""
    dist = d if isinstance(d, dict) else {b: d for b in bases}
    out = {"code": key, "schedule": stag, "distance": min(dist.values()), "bases": {}}
    for b in bases:
        g = None if given is None else given[b]
        r = BD.compute(key, b, 1, dist[b], None if sched is None else B.to_dicts(*sched), stag, 3, PS, quiet=True, given=g)
        out["bases"][b] = {k: r[k] for k in ("source", "n_orbit_representatives", "n_minimum_fault_sets", "n_family",
                                             "n_family_mechanisms", "rates") if k in r}
        out["bases"][b]["distance"] = dist[b]
        out["bases"][b]["n_failing_configurations"] = r.get("n_failing_configurations")
        print(key, stag, b, r["n_minimum_fault_sets"], {p: round(v["log10_lower_bound"], 2) for p, v in r["rates"].items()},
              flush=True)
    return out


def main(out):
    std = (tuple(B.STANDARD["X"][l] for l in [(s, a) for s in "LR" for a in range(3)]),
           tuple(B.STANDARD["Z"][l] for l in [(s, a) for s in "LR" for a in range(3)]))
    best = best_gross()
    tag = "s" + "".join(map(str, best[0])) + "_" + "".join(map(str, best[1]))
    res = {"p": list(PS), "best_gross_schedule": {"px": list(best[0]), "pz": list(best[1])}, "entries": []}
    res["entries"].append(entry("gross", std, "standard", 10))
    res["entries"].append(entry("gross", best, tag, 11))
    # two-gross: the bases whose distance is certified; the instruction's distance is the smallest of them, and every
    # other basis must have a lower bound at least as large
    two, bounds = {}, {}
    for b in "ZX":
        f = os.path.join(RES, f"pipe_bb288_standard_c1_{b}.json")
        if not os.path.exists(f):                                       # a longer run still under way
            f = f.replace(".json", "_2h.json")
        rec = json.load(open(f))
        bounds[b] = (rec["lower_bound"], rec["upper_bound"])
        if rec["status"] == "exact" and rec["lower_bound"] == rec["upper_bound"]:
            sets = [rec["witness"]]
            more = os.path.join(RES, f"enum_bb288_standard_c1_{b}.json")      # papers/ibm_bicycle_enum.py, if run
            if os.path.exists(more):
                sets += json.load(open(more))["solutions"]
            two[b] = (rec["lower_bound"], sets)
    d2 = min(v[0] for v in two.values())
    assert all(lo >= d2 for lo, _ in bounds.values()), bounds
    bases = "".join(b for b in "ZX" if b in two)
    e = entry("bb288", std, "standard", {b: two[b][0] for b in bases}, {b: two[b][1] for b in bases}, bases)
    e["distance_bounds"] = {b: list(v) for b, v in bounds.items()}
    res["entries"].append(e)
    json.dump(res, open(out, "w"), indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1])
