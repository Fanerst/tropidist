"""Second, independent replay of every stored witness, using Stim's detector
sampler instead of the tableau simulator: all noise is removed from the
circuit and the witness faults are inserted as error channels with
probability 1.  A witness passes if no detector fires and at least one
observable flips.  Reads only the JSON records (instruction position and
Pauli), not the DEM.
"""
import glob
import json
import os
import sys

import numpy as np
import stim

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cdist import replay


def check(circuit_path, faults):
    circ = stim.Circuit.from_file(circuit_path)
    flat = replay._expand(circ)
    ins = {}
    for f in faults:
        if not f["paulis"]:
            return None          # pure record flip: not handled by this checker
        idx = replay._flat_index(circ, [tuple(x) for x in f["stack"]])
        assert flat[idx].name == f["instruction"]
        ins.setdefault(idx, []).extend((p, q) for p, q in f["paulis"])
    out = stim.Circuit()
    for k, inst in enumerate(flat):
        for p, q in ins.get(k, ()):
            out.append(f"{p}_ERROR", [q], 1.0)
        if inst.name in replay.NOISE:
            continue
        if inst.name in replay.MEASURE and inst.gate_args_copy():
            out.append(inst.name, inst.targets_copy())
        else:
            out.append(inst)
    dets, obs = out.compile_detector_sampler(seed=1).sample(4, separate_observables=True)
    assert (dets == dets[0]).all() and (obs == obs[0]).all()
    return int(dets[0].sum()), [int(i) for i in np.flatnonzero(obs[0])]


def main():
    n = 0
    files = (sorted(glob.glob("results/bb*.json")) + sorted(glob.glob("results/deep_bb*.json"))
             + sorted(glob.glob("results/papers/*.json")))
    for f in files:
        r = json.load(open(f))
        if not isinstance(r, dict):
            continue
        wits = []
        if isinstance(r.get("witness"), dict) and "physical_faults" in r["witness"]:
            wits.append(("witness", r["witness"]))
        for key in ("window_t0", "window_t1"):
            if key in r and "witness" in r[key]:
                wits.append((key, r[key]["witness"]))
        if "collapsed" in r and "lift_witness" in r["collapsed"]:
            wits.append(("lift", r["collapsed"]["lift_witness"]))
        for label, w in wits:
            path = w.get("circuit") or r.get("circuit")
            if not path or not os.path.exists(path):
                print(f"{os.path.basename(f)} {label}: circuit file not found, skipped")
                continue
            res = check(path, w["physical_faults"])
            if res is None:
                print(f"{os.path.basename(f)} {label}: weight {w['weight']} contains a record flip, skipped")
                continue
            ndet, obs = res
            ok = ndet == 0 and len(obs) > 0 and obs == w["replay"]["flipped_observables"]
            print(f"{os.path.basename(f)} {label}: weight {w['weight']}: detectors fired {ndet}, observables flipped {obs} -> {'OK' if ok else 'FAIL'}")
            assert ok
            n += 1
    print(f"ok: {n} witnesses re-verified with the detector sampler")


if __name__ == "__main__":
    main()
