"""Rates of a minimum-weight decoder to order p^5 at C = 10 on chips with one dead check, both schedules (rate_chip.py), from the lists
of fault sets in spec/, against the perfect chips through order p^6 (results/ibm_matched/mwd_gross_c10.json).  Writes rates_chip.json.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rate_chip as RC

CHIPS = {"standard": {"perfect": "perfect", "dead_z": "z0", "dead_x": "x0"}, "distance11": {"dead_z": "d11_z0", "dead_x": "d11_x0"}}


def at_ten(name, basis, p):
    c3 = RC.rate(os.path.join(HERE, "spec", f"{name}_{basis}_c3.npz"), p)[4]
    c4 = RC.rate(os.path.join(HERE, "spec", f"{name}_{basis}_c4.npz"), p)[4]
    return c4 + (c4 - c3) * (10 - 4)


def main():
    out = {}
    for p in (1e-4, 1e-5):
        res = out.setdefault(str(p), {})
        for sched, chips in CHIPS.items():
            for lab, name in chips.items():
                z, x = at_ten(name, "Z", p), at_ten(name, "X", p)
                res.setdefault(sched, {})[lab] = {"Z": z, "X": x, "sum": z + x}
        ref = res["standard"]["perfect"]["sum"]
        for sched in res:
            for lab in res[sched]:
                res[sched][lab]["over_perfect_standard"] = res[sched][lab]["sum"] / ref
    json.dump(out, open(os.path.join(HERE, "rates_chip.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
