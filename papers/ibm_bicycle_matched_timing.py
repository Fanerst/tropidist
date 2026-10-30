"""Cycle times of the gross code's distance-11 schedules when initialisation and measurement each take one timestep
(Tour de gross, arXiv:2506.03094, Sec. 2.2), and whether their instructions keep the mechanisms of
papers/ibm_bicycle.py.

A check qubit is busy from its preparation to its measurement: one timestep each, and the CNOT slots from its first to
its last.  The X and Z check qubits of the standard schedule act in slots 1-6 and 0-5, so each is busy for eight
timesteps and the cycles interleave (8C + 1 timesteps for C cycles).  A check qubit acting in both slot 0 and slot 6 is
busy for nine, so with one check qubit per check its schedule needs nine timesteps per cycle.

For each schedule of results/ibm/scan_gross_d11_c1.jsonl certified at distance 11 in both bases: the period of
papers/ibm_bicycle_matched.py, and whether its C = 1 instruction there has the same mechanisms (detectors and
observables) as papers/ibm_bicycle.py's in both bases, so that the certified distance carries over.

Usage: python papers/ibm_bicycle_matched_timing.py OUT.json
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import bb6_depth7 as B
import ibm_bicycle as IB
import ibm_bicycle_matched as M
import ibm_bicycle_matched_bound as MB

BEST = ((1, 0, 6, 4, 3, 2), (3, 4, 2, 5, 6, 0))      # results/ibm/curves.json, best_gross_schedule


def main(out):
    t0 = time.time()
    rows = [json.loads(line) for line in open(os.path.join(ROOT, "results", "ibm", "scan_gross_d11_c1.jsonl"))]
    d11 = [r for r in rows if all(r[b][0] == r[b][1] == 11 for b in "ZX")]
    res = {"best": {"px": list(BEST[0]), "pz": list(BEST[1])}, "n_d11": len(d11), "schedules": []}
    for r in d11:
        s = B.to_dicts(tuple(r["px"]), tuple(r["pz"]))
        pm, period = M.timing(s)
        same = all(set(MB.mechanisms(IB.build_instruction("gross", b, 1, 1e-4, s))[0])
                   == set(MB.mechanisms(M.build_matched("gross", b, 1, 1e-4, s))[0]) for b in "ZX")
        res["schedules"].append({"px": r["px"], "pz": r["pz"], "period": period,
                                 "preparation_measurement": {t: list(v) for t, v in pm.items()},
                                 "same_mechanisms_c1": same})
        if (tuple(r["px"]), tuple(r["pz"])) == BEST:
            res["best"].update(period=period, same_mechanisms_c1=same)
    by = {}
    for x in res["schedules"]:
        k = str(x["period"])
        by.setdefault(k, {"schedules": 0, "same_mechanisms_c1": 0})
        by[k]["schedules"] += 1
        by[k]["same_mechanisms_c1"] += x["same_mechanisms_c1"]
    res["by_period"] = by
    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(out, "w"), indent=0)
    print(f"{len(d11)} schedules of distance 11: {by}; best schedule: {res['best']}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
