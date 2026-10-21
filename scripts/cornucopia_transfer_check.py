"""Replay the fault sets found in windows of the N_c-cycle Cornucopia circuits in the one-cycle circuit of the same
code (the setting of the authors' circuit-distance search).  The first cycle of both circuits is the same list of
instructions, so a fault set that lies in the first cycle has the same locations in both; Stim decides whether it
is still undetected and logical there.  Writes results/cornucopia/transfer.json.

usage: python scripts/cornucopia_transfer_check.py
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "papers")]
import cornucopia
from cdist import replay


def main():
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "results/cornucopia/win_q*_r*_Z_t1.json"))):
        d = json.load(open(path))
        w = d.get("witness")
        if not w or not w.get("verified") or d["rounds"] == 1:
            continue
        q = [k for k, v in cornucopia.CODES.items() if list(v[2]) == d["code"]][0]
        faults = w["physical_faults"]
        rec = {"source": os.path.relpath(path, ROOT), "weight": len(faults), "rounds": d["rounds"],
               "ticks": sorted({f["tick"] for f in faults})}
        try:
            dets, obs = replay.replay(cornucopia.build(q, d["basis"], 1), faults)
            rec.update({"one_cycle_fired_detectors": len(dets), "one_cycle_flipped_observables": len(obs),
                        "undetected_logical_in_one_cycle": not dets and bool(obs)})
        except AssertionError:          # a fault lies beyond the first cycle: no such location in one cycle
            rec.update({"undetected_logical_in_one_cycle": None, "note": "fault set extends beyond cycle 1"})
        out[f"[[{','.join(map(str, d['code']))}]]"] = rec
        print(rec["source"], {k: v for k, v in rec.items() if k != "source"})
    json.dump(out, open(os.path.join(ROOT, "results/cornucopia/transfer.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
