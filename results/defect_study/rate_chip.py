"""Low-noise logical rate of a chip against the perfect chip, for a minimum-weight decoder, from the complete lists of logical fault
sets of weight <= 10 (chip_spectrum.py).  The leading term is of order p^5 for circuit distances 9 and 10:

    a set of weight 9 fails on each of its C(9,5) subsets of five faults (the other four are the lighter explanation);
    a set of weight 10 fails on the less likely half of each of its 126 splits into five and five.

Failing configurations are counted once.  Each contributes the product of its mechanisms' probabilities (as in
papers/ibm_bicycle_matched_mwd.py: a sector column stands for the full-model mechanism with exactly its detectors).  The rate of C
cycles is linear in C, since the sets are local in time, so two enumerations give the rate per cycle in the bulk and at C = 10.

Usage: python rate_chip.py P SPEC_C1.npz SPEC_C2.npz ...      (the meta of each file gives basis, cycles, dead checks, schedule)
Prints one line per file, and for each pair with equal chip the extrapolation to C = 10.
"""
import itertools
import json
import math
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chip
from cdist import problem

R5 = np.array(list(itertools.combinations(range(9), 5)))
C5 = np.array([c for c in itertools.combinations(range(10), 5) if 0 in c])
N5 = np.array([[x for x in range(10) if x not in c] for c in C5])


def merged(circ):
    dem = circ.detector_error_model(decompose_errors=False, flatten_loops=True)
    out = {}
    for inst in dem:
        if inst.type != "error":
            continue
        a = b = 0
        for t in inst.targets_copy():
            if t.is_relative_detector_id():
                a ^= 1 << t.val
            elif t.is_logical_observable_id():
                b ^= 1 << t.val
        q = inst.args_copy()[0]
        r = out.get((a, b), 0.0)
        out[(a, b)] = r + q - 2 * r * q
    return out


def priors(meta, p):
    s = None if meta["schedule"] == "standard" else chip.B.to_dicts(*(tuple(map(int, x)) for x in meta["schedule"].split("_")))
    c = chip.build_chip("gross", meta["basis"], meta["cycles"], p, s, tuple(meta["dead_x"]), tuple(meta["dead_z"]))
    with tempfile.TemporaryDirectory() as tmp:
        c.to_file(tmp + "/c.stim")
        full = problem.load_dem_problem(tmp + "/c.stim", "c")
    sector = problem.sector_problem(full)
    probs = merged(c)
    rows = sector.notes["sector_rows"]
    out = []
    for j in range(sector.ncols):
        lifted, m = 0, sector.h[j]
        while m:
            low = m & -m
            lifted ^= 1 << rows[low.bit_length() - 1]
            m ^= low
        out.append(probs[(lifted, sector.l[j])])
    return np.log(np.array(out))


def rate(path, p):
    z = np.load(path)
    meta = json.loads(str(z["meta"]))
    assert all(r["complete"] for r in meta["runs"]) and meta["runs"][-1]["K"] >= 10
    logr = priors(meta, p)
    fail = {}
    n9 = n10 = 0
    if "sets_9" in z:
        for G in z["sets_9"].astype(np.int64):
            n9 += 1
            for c in G[R5]:
                fail[tuple(sorted(c.tolist()))] = logr[c].sum()
    if "sets_10" in z:
        G = z["sets_10"].astype(np.int64)
        n10 = len(G)
        a, b = logr[G[:, C5]].sum(axis=2), logr[G[:, N5]].sum(axis=2)
        worse = np.where((a <= b)[:, :, None], G[:, C5], G[:, N5]).reshape(-1, 5)
        val = np.minimum(a, b).ravel()
        for c, v in zip(worse.tolist(), val.tolist()):
            fail[tuple(sorted(c))] = v
    total = sum(math.exp(v) for v in fail.values())
    return meta, n9, n10, len(fail), total, set(meta["runs"][-1]["sets"].keys())


def main():
    p = float(sys.argv[1])
    res = {}
    for f in sys.argv[2:]:
        meta, n9, n10, nf, total, _ = rate(f, p)
        lower = {k: v for k, v in meta["runs"][-1]["sets"].items() if int(k) < 9}
        key = (meta["basis"], tuple(meta["dead_x"]), tuple(meta["dead_z"]), meta["schedule"])
        res.setdefault(key, {})[meta["cycles"]] = total
        print(os.path.basename(f), "basis", key[0], "dead x", key[1], "dead z", key[2], "C", meta["cycles"], "lighter sets", lower, "w9", n9, "w10", n10,
              "failing configurations", nf, "rate %.3e" % total, "log10 %.3f" % math.log10(total), flush=True)
    for key, v in res.items():
        if len(v) >= 2:
            c = sorted(v)
            slope = (v[c[-1]] - v[c[-2]]) / (c[-1] - c[-2])
            r10 = v[c[-1]] + slope * (10 - c[-1])
            print("chip", key, "bulk per cycle %.3e  C = 10: %.3e, log10 %.3f, per cycle log10 %.3f" % (slope, r10, math.log10(r10), math.log10(r10 / 10)), flush=True)


if __name__ == "__main__":
    main()
