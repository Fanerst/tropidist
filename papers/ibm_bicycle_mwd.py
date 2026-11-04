"""Low-weight failures of a minimum-weight decoder on a memory instruction of papers/ibm_bicycle.py, from all logical
fault sets of weight at most 12 (papers/ibm_bicycle_spectrum.py).

A decoder that returns a least-weight fault set consistent with the detector outcomes, ties broken towards the more
likely set, fails on a configuration C contained in a logical fault set G when C is heavier than its complement G - C
(the two have the same detector outcomes and logical effects that differ by that of G), and on the less likely of C
and G - C when the two are equally heavy.  A failing configuration of weight w therefore lies in a logical set of
weight at most 2w, and the sets of weight <= 12 give every failing configuration of weight <= 6:

    weight 5 (d = 10):   the less likely half of each split of a weight-10 set into halves;
    weight 6:            the subsets of weight 6 of weight-10 sets (d = 10) and of weight-11 sets, without those that
                         contain a failing configuration of weight 5, and the less likely half of each split of a
                         weight-12 set.

Each configuration contributes P(C) = prod_{j in C} p_j, the probability that its mechanisms occur whatever else
occurs; configurations of weight 6 from weight-10 and weight-11 sets are counted once, the halves of weight-12 sets
(about 10^8) without that check.  Here the weight-5 configurations are counted once per split, so one that is the failing
half of two sets counts twice, and two that share four mechanisms overlap at weight 6; papers/ibm_bicycle_matched_mwd.py,
which gives the paper's rates, counts each once and subtracts that overlap.  A half that contains a
reducible pair (two mechanisms whose joint effect is that of one mechanism of the model) has a lighter explanation in
its own class; the decoder then fails on the other half, which lies in a weight-11 set and is counted there, so such
splits of weight-12 sets are left out.  The remaining exceptions (a configuration of a weight-11 set whose own class
has a lighter explanation) need logical sets of weight 10 and are rare.  The result is the expansion of the logical error rate of such a decoder to
order p^6, which holds where the terms of weight 7 are small (p well below 10^-3 for the gross code).

Usage: python papers/ibm_bicycle_mwd.py OUT.json SPECTRUM.json [SPECTRUM.json ...]
       (each spectrum file: one code, schedule and basis, all sets of weight <= 12; the schedule from its tag)
"""
import itertools
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import bb6_depth7 as B
import ibm_bicycle as IB
import ibm_bicycle_bound as BD
from cdist import problem

PS = (5e-5, 1e-4, 2e-4, 5e-4, 7.322e-4, 1e-3)


def schedule_of(tag):
    if tag == "standard":
        return None
    px, pz = tag[1:].split("_")
    return B.to_dicts(tuple(map(int, px)), tuple(map(int, pz)))


def full_columns(key, basis, cycles, sched):
    """The full detector error model's (detector, observable) masks, and a map from sector columns to the full-model
    mechanism that fires no detector outside the sector (as in papers/ibm_bicycle_bound.py)."""
    circ = IB.build_instruction(key, basis, cycles, 1e-3, sched)
    path = os.path.join(ROOT, "circuits", "papers", f"ibm_mwd_{os.getpid()}.stim")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    circ.to_file(path)
    full = problem.load_dem_problem(path, os.path.basename(path))
    os.remove(path)
    sector = problem.sector_problem(full)
    lookup = {(a, b): j for j, (a, b) in enumerate(zip(full.h, full.l))}
    rows = sector.notes["sector_rows"]
    cmap = []
    for j in range(sector.ncols):
        lifted, m = 0, sector.h[j]
        while m:
            low = m & -m
            lifted ^= 1 << rows[low.bit_length() - 1]
            m ^= low
        cmap.append(lookup.get((lifted, sector.l[j]), -1))
    return full, cmap


def halves_less_likely(sets, logr, reducible=None):
    """Sum over the splits of equal-weight halves of each set of the smaller exp(sum of logr over a half), leaving
    out the splits in which a half contains a reducible pair (reducible: {set index: [(i, j), ...]} positions)."""
    g = len(sets[0])
    h = g // 2
    combos = np.array([c for c in itertools.combinations(range(g), h) if 0 in c])      # each split once
    mask = np.zeros((len(combos), g))
    for i, c in enumerate(combos):
        mask[i, list(c)] = 1.0
    arr = np.array(sets)
    sums, n, dropped = [], 0, 0
    for start in range(0, len(arr), 20000):
        lr = logr[arr[start:start + 20000]]                       # (sets, g)
        part = lr @ mask.T                                        # (sets, splits)
        v = np.minimum(part, lr.sum(axis=1)[:, None] - part)
        for k in range(len(v)):
            pairs = (reducible or {}).get(start + k)
            if pairs:
                bad = np.zeros(len(combos), dtype=bool)
                for i, j in pairs:
                    bad |= mask[:, i] == mask[:, j]
                v[k, bad] = -np.inf
                dropped += int(bad.sum())
        v = v.ravel()
        v = v[np.isfinite(v)]
        sums.append(logsum(v))
        n += len(v)
    return logsum(sums), n, dropped


def reducible_pairs(sets, full):
    """Positions (i, j) of the pairs of mechanisms in each set whose joint effect is that of a single mechanism of the
    model: a half containing such a pair has a lighter explanation in its own logical class."""
    single = set(zip(full.h, full.l))
    out = {}
    for k, G in enumerate(sets):
        pr = [(i, j) for i in range(len(G)) for j in range(i + 1, len(G))
              if (full.h[G[i]] ^ full.h[G[j]], full.l[G[i]] ^ full.l[G[j]]) in single]
        if pr:
            out[k] = pr
    return out


def logsum(v):
    v = np.asarray(v, dtype=float)
    if len(v) == 0:
        return -math.inf
    m = v.max()
    return m + math.log(np.exp(v - m).sum())


def analyse(spec):
    key, basis, cycles, stag = spec["code"], spec["basis"], spec["cycles"], spec["schedule"]
    assert spec["complete"] and spec["kmax"] >= 12
    sched = schedule_of(stag)
    full, cmap = full_columns(key, basis, cycles, sched)
    by = {}
    for s in spec["sets"]:
        cols = [cmap[j] for j in s]
        assert min(cols) >= 0
        by.setdefault(len(cols), []).append(sorted(cols))
    d = min(by)
    res = {"code": key, "schedule": stag, "basis": basis, "cycles": cycles, "distance": d,
           "sets_by_weight": {w: len(v) for w, v in sorted(by.items())}, "rates": {}}
    # failing configurations of weight 5 (even d = 10) and the weight-6 subsets of weight-10 and weight-11 sets
    fail5 = set()
    pairs5 = []
    if d == 10:
        for G in by.get(10, []):
            for E in itertools.combinations(G, 5):
                if E[0] != G[0]:
                    continue
                Ep = tuple(x for x in G if x not in E)
                pairs5.append((E, Ep))
    six = set()
    for g in (10, 11):
        for G in by.get(g, []):
            for C in itertools.combinations(G, 6):
                six.add(C)
    res["n_pairs_weight5"] = len(pairs5)
    red12 = reducible_pairs(by.get(12, []), full)
    res["n_sets12_with_reducible_pairs"] = len(red12)
    for p in PS:
        probs = BD.merged_probabilities(IB.build_instruction(key, basis, cycles, p, sched))
        pj = np.array([probs[(a, b)] for a, b in zip(full.h, full.l)])
        logr = np.log(pj)                                         # marginal probabilities of the mechanisms
        # weight 5: the less likely half of each pair
        t5, fail5 = [], set()
        for E, Ep in pairs5:
            a, b = logr[list(E)].sum(), logr[list(Ep)].sum()
            t5.append(min(a, b))
            fail5.add(E if a <= b else Ep)
        # weight 6 from weight-10 and weight-11 sets, without those containing a failing weight-5 configuration
        t6a = [logr[list(C)].sum() for C in six
               if not fail5 or not any(tuple(x for x in C if x != y) in fail5 for y in C)]
        # weight 6: halves of weight-12 sets
        t6b, n6b, drop = halves_less_likely(by[12], logr, red12) if by.get(12) else (-math.inf, 0, 0)
        r = {"log10_w5": logsum(t5) / math.log(10), "log10_w6_from_10_11": logsum(t6a) / math.log(10),
             "log10_w6_from_12": t6b / math.log(10), "n_w5": len(t5), "n_w6_from_10_11": len(t6a), "n_w6_from_12": n6b,
             "n_w6_from_12_dropped": drop}
        r["log10_total"] = logsum([logsum(t5), logsum(t6a), t6b]) / math.log(10)
        res["rates"][str(p)] = r
        print(key, stag, basis, p, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    return res


def main(out, *specs):
    res = [analyse(json.load(open(f))) for f in specs]
    json.dump({"p": list(PS), "entries": res}, open(out, "w"), indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
