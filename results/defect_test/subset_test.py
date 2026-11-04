"""Do real decoders correct every fault configuration that an optimal decoder must correct?  Take the certified
minimum logical fault sets of the gross code's memory instruction (standard schedule, Z basis, 10 cycles) and give a
decoder each subset of w faults.  A set of weight 10 has complement of weight 10 - w, so below w = 5 the subset is the
lighter side and a minimum-weight decoder corrects it; at w = 5 no decoder can correct both sides of a split.
usage: subset_test.py P ITERS OSD_ORDER [max sets per weight]"""
import itertools
import json
import math
import random
import sys
import time

import numpy as np
import scipy.sparse as sp

R = "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance"
sys.path[:0] = [R + "/papers", R]
import ibm_bicycle_matched as M
import ibm_bicycle_matched_mwd as MWD
from ldpc import BpOsdDecoder

p, iters, order = float(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
key, basis, cycles = "gross", "Z", 10
z = np.load(R + "/results/ibm_matched/spectrum_gross_c10_std_Z.npz", allow_pickle=True)
full, sector, cmap, colmaps = MWD.model(key, basis, cycles, None)
rows = list(sector.notes["sector_rows"])
pos = {r: i for i, r in enumerate(rows)}
# priors on the sector columns: the circuit's mechanisms at p, merged by their effect on the memory basis
circ = M.build_matched(key, basis, cycles, p, None)
merged = {}
for inst in circ.detector_error_model(decompose_errors=False).flattened():
    if inst.type != "error":
        continue
    h, l = 0, 0
    for t in inst.targets_copy():
        if t.is_relative_detector_id() and t.val in pos:
            h ^= 1 << pos[t.val]
        elif t.is_logical_observable_id():
            l ^= 1 << t.val
    q = inst.args_copy()[0]
    r = merged.get((h, l), 0.0)
    merged[(h, l)] = r + q - 2 * r * q
missing = [j for j in range(sector.ncols) if (sector.h[j], sector.l[j]) not in merged]
assert not missing, len(missing)
pri = np.array([merged[(sector.h[j], sector.l[j])] for j in range(sector.ncols)])


def matrix(masks, nrows):
    r, c = [], []
    for j, m in enumerate(masks):
        while m:
            low = m & -m
            r.append(low.bit_length() - 1)
            c.append(j)
            m ^= low
    return sp.csc_matrix((np.ones(len(r), dtype=np.uint8), (r, c)), shape=(nrows, len(masks)))


H = matrix(sector.h, sector.nrows)
L = matrix(sector.l, sector.nobs)
dec = BpOsdDecoder(H, error_channel=list(pri), max_iter=iters, bp_method="minimum_sum", ms_scaling_factor=0.625,
                   osd_method="osd_cs", osd_order=order)
print("sector", sector.nrows, sector.ncols, "prior range", pri.min(), pri.max(), "p", p, "iters", iters, "osd", order, flush=True)
sets = z["sets_10"].astype(int)
print("reps", len(sets), "orbit sizes", set(z["orbit_10"].tolist()), flush=True)
# a check of the sets themselves
for F in sets:
    assert not (H[:, F].sum(axis=1).A1 % 2).any() and (L[:, F].sum(axis=1).A1 % 2).any()
res = {}
t0 = time.time()
for w in range(1, 7):
    total = fails = 0
    examples = []
    for F in sets:
        for c in itertools.combinations(F.tolist(), w) if w <= 5 else ():
            e = np.zeros(sector.ncols, dtype=np.uint8)
            e[list(c)] = 1
            s = (H @ e) % 2
            cor = dec.decode(s.astype(np.uint8))
            assert not (((H @ cor) + s) % 2).any()
            bad = ((L @ ((cor + e) % 2)) % 2).any()
            total += 1
            if bad:
                fails += 1
                if len(examples) < 3:
                    examples.append(c)
    if total:
        res[w] = (fails, total)
        print("subsets of %d faults: %d of %d fail (%.2f%%), %.0f s" % (w, fails, total, 100 * fails / total, time.time() - t0), flush=True)
json.dump({"p": p, "iters": iters, "osd_order": order, "fails_by_w": res}, open(sys.argv[4] if len(sys.argv) > 4 else "/dev/null", "w"))
