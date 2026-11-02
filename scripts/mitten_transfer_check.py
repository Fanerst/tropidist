"""Replay the weight-12 fault set of the 3-round mitten [[300,60,14]] Z circuit (results/papers/mitten300_Z_isd.json)
in the 6-round circuit of the benchmark instance mitten_300.  All twelve faults lie in one instruction of the first
round, and the two circuits are the same list of instructions up to it, so the fault set has the same locations in
both; Stim decides whether it is still undetected and logical there.  The faults' columns in the exported sector
variant are then checked with bench/common.check_witness.  Together with the lower bound 12 of the extended-budget
pipeline run (results/bench_extended/ours_pipeline__dp-2/mitten_300__sector__t32.json) this settles the instance at
12.  Writes results/bench_extended/transfer/mitten_300__sector.json.

usage: python scripts/mitten_transfer_check.py      (needs Stim and the exported instance files)
"""
import json
import os
import sys

import stim

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "bench")]
import common
from cdist import replay

SOURCE = "results/papers/mitten300_Z_isd.json"
INSTANCE = os.path.join(ROOT, "bench/instances/mitten_300")
OUT = "results/bench_extended/transfer/mitten_300__sector.json"


def main():
    w = json.load(open(os.path.join(ROOT, SOURCE)))["witness"]
    faults = w["physical_faults"]
    assert all(len(f["stack"]) == 1 for f in faults), "a fault lies inside a REPEAT block"
    last = max(f["stack"][0][0] for f in faults)
    c3 = stim.Circuit.from_file(os.path.join(ROOT, w["circuit"]))
    c6 = stim.Circuit.from_file(os.path.join(INSTANCE, "circuit.stim"))
    assert str(c3[:last + 1]) == str(c6[:last + 1]), "the circuits differ before the last faulted instruction"
    dets, obs = replay.replay(c6, faults)
    # each fault's column in the sector variant: its detectors restricted to the sector rows, matched by row metadata
    full_meta = [tuple(m) for m in json.load(open(os.path.join(INSTANCE, "full.rowmeta.json")))]
    sec = common.load(INSTANCE, "sector")
    sec_row = {tuple(m): r for r, m in enumerate(sec.rowmeta)}
    column = {}
    for j in range(sec.ncols):
        column.setdefault((sec.h[j], sec.l[j]), j)
    cols = []
    for f in faults:
        d, o = replay.replay(c6, [f])
        h = sum(1 << sec_row[full_meta[x]] for x in d if full_meta[x] in sec_row)
        cols.append(column[(h, sum(1 << x for x in o))])
    check = common.check_witness(sec, cols)
    rounds = json.load(open(os.path.join(INSTANCE, "meta.json")))["rounds"]
    rec = {"instance": "mitten_300", "variant": "sector", "rounds": rounds, "source": SOURCE,
           "source_rounds": w["rounds"], "weight": len(faults), "instructions_compared": last + 1,
           "fired_detectors": dets, "flipped_observables": obs, "sector_columns": cols, "check_witness": check,
           "undetected_logical": not dets and bool(obs) and check["ok"]}
    os.makedirs(os.path.dirname(os.path.join(ROOT, OUT)), exist_ok=True)
    json.dump(rec, open(os.path.join(ROOT, OUT), "w"), indent=1)
    print({k: v for k, v in rec.items() if k != "flipped_observables"})


if __name__ == "__main__":
    main()
