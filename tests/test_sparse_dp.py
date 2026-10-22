"""cdist.sparse_dp: the weight-truncated sparse Rank DP agrees with brute force, with the dense DP and with known
distances, in both modes (forward, meet in the middle), with and without the lookahead bound, with both table
formats and with the dense fallback; every witness is checked."""
import itertools
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "papers"), os.path.join(ROOT, "scripts"), os.path.join(ROOT, "bench")]

import stabcode
import dp_vs_search_local as dvs
from cdist import auto, search, sparse_dp
from cdist.problem import Problem

BACKENDS = ("numpy", "c")


def brute(p, obs):
    for w in range(1, p.ncols + 1):
        for cols in itertools.combinations(range(p.ncols), w):
            s = lg = 0
            for j in cols:
                s ^= p.h[j]
                lg ^= p.l[j]
            if s == 0 and (lg >> obs) & 1:
                return w
    return None


def check_witness(p, cols, value, obs=None):
    s = lg = 0
    for j in cols:
        s ^= p.h[j]
        lg ^= p.l[j]
    assert s == 0 and len(cols) == value == len(set(cols))
    assert ((lg >> obs) & 1) if obs is not None else lg != 0


def random_problem(rng):
    n, m, k = rng.randint(2, 12), rng.randint(1, 7), rng.randint(1, 2)
    dens = rng.choice([0.2, 0.35, 0.5])
    h = [sum(1 << r for r in range(m) if rng.random() < dens) for _ in range(n)]
    l = [sum(1 << r for r in range(k) if rng.random() < 0.4) for _ in range(n)]
    return Problem("rand", m, k, h, l, [(i, 0) for i in range(m)])


def test_random_queries_all_thresholds_and_splits():
    rng = random.Random(3)
    checked = 0
    for _ in range(60):
        p = random_problem(rng)
        order = list(range(p.ncols))
        rng.shuffle(order)
        for obs in range(p.nobs):
            tr = sparse_dp.Trellis.for_query(p, obs, order)
            truth = brute(p, obs)
            assert tr.feasible == (truth is not None)
            if not tr.feasible:
                continue
            for K in range(1, p.ncols + 2):
                want = truth if truth <= K else None
                configs = [("forward", None, d) for d in (None, 1e-9)] + [("mitm", a, None) for a in range(1, K + 1)]
                for mode, split, dense in configs:
                    for use_h in (False, True):
                        for backend in BACKENDS:
                            r = sparse_dp.query(tr, K, mode=mode, split=split, use_h=use_h, backend=backend,
                                                dense=dense, every=rng.choice([1, 2, 5]))
                            assert r["value"] == want, (mode, split, use_h, backend, K, r["value"], want)
                            if want is not None:
                                check_witness(p, r["witness"], want, obs)
                            checked += 1
    assert checked > 1000


def test_distance_driver_matches_brute_force():
    rng = random.Random(5)
    for _ in range(80):
        p = random_problem(rng)
        truth = [brute(p, i) for i in range(p.nobs)]
        truth = min((t for t in truth if t is not None), default=None)
        order = list(range(p.ncols))
        rng.shuffle(order)
        for mode in ("forward", "mitm"):
            r = sparse_dp.distance(p, order=order, mode=mode, kmax=p.ncols + 1, backend=rng.choice(BACKENDS))
            assert r["distance"] == truth
            if truth is not None:
                check_witness(p, r["witness"], truth)


def test_codes_match_the_dense_dp():
    # surface and 6.6.6 color codes in both sectors; the dense DP and the search agree
    for build, d in ((dvs.rotated_surface, 7), (dvs.rotated_surface, 9), (dvs.color_code, 7), (dvs.color_code, 9),
                     (dvs.color_code, 11), (dvs.color_code, 13)):
        hx, hz, n = build(d)
        for sector in ("X", "Z"):
            p = stabcode.css_distance_problem(hx, hz, n, sector)
            order = auto.best_order(p)[0]
            dense, _ = auto.dp_distance(p, order)
            assert dense == d
            for mode, backend in (("mitm", "c"), ("mitm", "numpy"), ("forward", "c")):
                r = sparse_dp.distance(p, order=order, mode=mode, backend=backend, start=d - 2)
                assert r["distance"] == d and r["lower_bound"] == d, (build.__name__, d, sector, mode, r)
                check_witness(p, r["witness"], d)


def test_dense_fallback_agrees():
    hx, hz, n = dvs.color_code(11)
    p = stabcode.css_distance_problem(hx, hz, n, "Z")
    order = auto.best_order(p)[0]
    tr = sparse_dp.Trellis.for_query(p, 0, order)
    for backend in BACKENDS:
        for K in (10, 11, 13):
            plain = sparse_dp.query(tr, K, mode="forward", backend=backend)
            dense = sparse_dp.query(tr, K, mode="forward", backend=backend, dense=0.25)
            assert dense["dense_cuts"] > 0 and plain["dense_cuts"] == 0
            assert plain["value"] == dense["value"] == (11 if K >= 11 else None)
            if K >= 11:
                check_witness(p, dense["witness"], 11, 0)
            mitm = sparse_dp.query(tr, K, mode="mitm", backend=backend, dense=0.25)
            assert mitm["value"] == plain["value"]


def test_bb_codes_and_the_search():
    # [[72,12,6]] and [[90,8,10]]: many observables, wide trellises (cut rank 20 and 26)
    import bb6_depth7
    for key, d in (("bb72", 6), ("bb90", 10)):
        hx, hz, n = bb6_depth7.matrices(key)
        p = stabcode.css_distance_problem(hx, hz, n, "Z")
        r = sparse_dp.distance(p, mode="mitm", backend="c", start=d - 1)
        assert r["distance"] == d and r["lower_bound"] == d
        check_witness(p, r["witness"], d)
        assert search.distance(p, k_table=2, kmax=20, labelfree=True, cover=True, start=d - 1)["distance"] == d


def test_lookahead_is_admissible_and_prunes():
    # the bound never exceeds the true remaining cost: compare with the exact backward table (untruncated)
    hx, hz, n = dvs.color_code(9)
    p = stabcode.css_distance_problem(hx, hz, n, "X")
    order = auto.best_order(p)[0]
    tr = sparse_dp.Trellis.for_query(p, 0, order)
    import numpy as np
    for fwd in (True, False):
        exact = sparse_dp.Sweep(tr, -1 if fwd else +1, 99, 99, use_h=False)     # the other direction, no pruning
        exact.every = 1
        exact.run()
        hd = tr.bound_data(fwd)
        for c in range(0, tr.N + 1, 3):
            keys, vals = exact.ckpt[c]
            # forward bound at c for state s compares with the backward value of s ^ t at c, and vice versa
            h = sparse_dp.bound(keys ^ np.uint64(tr.tmask[c]), tr.tmask[c], hd[c])
            assert (h <= vals.astype(np.int64)).all(), (fwd, c)
    f0 = sparse_dp.query(tr, 9, mode="forward", use_h=False)
    f1 = sparse_dp.query(tr, 9, mode="forward", use_h=True)
    assert f0["value"] == f1["value"] == 9 and sum(f1["forward_counts"]) < sum(f0["forward_counts"])


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
