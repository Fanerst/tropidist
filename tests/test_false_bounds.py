"""Regression tests for four ways the search and DP kernels reported a false lower bound (external review of
2026-10-30, methods findings 1-4).  Each test is one of that review's reproduction scripts on a small instance.

  1. Truncated enumeration: the kernel stores at most sol_cap solutions and used to drop the rest silently, still
     reporting "exhausted"; a lifting argument over such a list raises a false bound.  Runs now say whether
     their list is complete (solutions_complete).
  2. Completion bookkeeping: complete() restored only the first 4096 columns of a pivot row that it had
     forbidden, so in rows of higher degree later columns stayed forbidden in sibling branches.
  3. Depth limit: branches deeper than the kernel's DMAX levels were cut silently and the threshold reported as
     exhausted.  Larger thresholds are now refused.
  4. 8-bit DP costs: a cost of 255 read as "no logical" (dense DP) or as an absent state (sparse DP), and 256
     wrapped to 0.  The dense DP now raises when a feasible query saturates; the sparse DP refuses tables that
     would hold weights above 254.

Run directly or with pytest.  The degree-4101 problems build lookup tables of about 0.3 GB.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cdist import auto, kernel, multi, search, sparse_dp, trellis
from cdist.lift import TopDown, enumerate_solutions
from cdist.problem import Problem, collapse_time, project_rows
from cdist.tree_dp import tree_min_distance_for_mask


def raises(exc, fn, *args, **kw):
    try:
        fn(*args, **kw)
    except exc:
        return True
    return False


# ---------------------------------------------------------------------- 1. truncated enumeration
def test_dropped_solutions_are_flagged():
    """enum_cap_repro: three equal columns with distinct labels have three minimum pairs."""
    p = Problem("cap", 1, 2, [1, 1, 1], [1, 2, 3], [()])
    S = search.Searcher(p, labelfree=True)
    t = search.Table(p, 1, labelfree=True)
    S.add_table(t, exact=True)
    try:
        r = S.search(2, enum_all=True, sol_cap=1)
        assert r["status"] == "exhausted" and r["best"] == 2
        assert r["nsol_recorded"] == 1 < r["nsol_found"] and not r["solutions_complete"], r
        r = S.search(2, enum_all=True, sol_cap=100)
        assert r["solutions_complete"] and r["nsol_found"] == r["nsol_recorded"], r
        assert set(r["solutions"]) == {(0, 1), (0, 2), (1, 2)}
    finally:
        t.free()
    assert raises(AssertionError, enumerate_solutions, p, 2, k_table=1, sol_cap=1)
    assert enumerate_solutions(p, 2, k_table=1, sol_cap=100)[0] == {(0, 1), (0, 2), (1, 2)}


def test_overflowing_minimum_enumeration_is_not_complete():
    """enum_default_cap_repro and enum_timecollapse_cap_repro: a 19-round sector problem whose time collapse has
    450 equal columns with distinct labels, so 101,025 minimum pairs, of which only the last one lifts to the
    sector.  The default cap keeps 100,000 records (each pair is recorded twice) and loses that pair; a runner
    that took the list as complete would certify 3 although the distance is 2."""
    n = 450

    def paired_bits(x):
        out = 0
        for j in range(9):
            if x >> j & 1:
                out ^= (1 << (2 * j + 1)) | (1 << (2 * j + 2))
        return out

    h = [1 ^ paired_bits(i + 1) for i in range(n - 1)] + [1 ^ paired_bits(n - 1)]
    sector = Problem("time-collapse-cap", 19, 9, h, list(range(n)), [(0, 0, t, 3) for t in range(19)])
    coll = collapse_time(sector)
    assert coll.h == [1] * n and coll.l == list(range(n))
    r = search.distance(coll, k_table=1, kmax=2, enum_all=True, labelfree=True)
    run = r["runs"][-1]
    assert r["distance"] == 2 and run["status"] == "exhausted"
    assert run["nsol_found"] > run["nsol_recorded"] and not run["solutions_complete"] and not r["solutions_complete"]
    assert not multi.distance(coll, k_table=1, kmax=2, enum_all=True)["solutions_complete"]

    def lifts(s):
        return sector.check(tuple(coll.col_meta[j][0] for j in s))[0] == 0
    # with room for every record the list is complete and holds the pair that lifts
    S = search.Searcher(coll, labelfree=True)
    S.build_exclusions()
    t = search.Table(coll, 1, labelfree=True)
    S.add_table(t, exact=True)
    try:
        r = S.search(2, enum_all=True, sol_cap=4 * n * n)
    finally:
        t.free()
    sols = set(r["solutions"])
    assert r["solutions_complete"] and len(sols) == n * (n - 1) // 2
    assert [s for s in sols if lifts(s)] == [(n - 2, n - 1)]


# ---------------------------------------------------------------------- 2. completion bookkeeping
def degree_problem():
    """Row 1 holds 4100 columns; every solution contains column 0, and (0, 2, 4100) has the least weight, 3."""
    h = [1, 7, 11] + [2 | ((i + 1) << 4) for i in range(4097)] + [10]
    return Problem("degree", 17, 1, h, [1] + [0] * (len(h) - 1), [()] * 17)


def test_completion_restores_every_forbidden_column():
    """completion_degree_repro: from the anchor alone, a table of depth 2 completes through two levels of
    complete(); its first branch forbids all 4100 columns of row 1, of which only 4096 used to be restored, so
    the second branch could not reach column 4100."""
    p = degree_problem()
    for k in (1, 2):
        S = search.Searcher(p, anchors=[0], labelfree=True)
        t = search.Table(p, k, labelfree=True)
        S.add_table(t, exact=True)
        try:
            r = S.search(3, exclusions=False)
        finally:
            t.free()
        assert r["status"] == "found" and r["best"] == 3 and r["solutions"] == [(0, 2, 4100)], (k, r["status"])


def test_topdown_lift_above_row_degree_4096():
    """topdown_degree_repro: TopDown's restricted-anchor lifting on the same problem, relaxed by dropping every
    row; with k_main = 2 the valid lift came back exhausted."""
    p = degree_problem()
    q = project_rows(p, [], "drop-all-rows", [])
    for k in (1, 2):
        td = TopDown(p, q, k_main=k)
        try:
            r = td.lift([0], slack=2)
        finally:
            td.table.free()
        assert r["status"] == "found" and r["best"] == 3 and r["solutions"] == [(0, 2, 4100)], (k, r["status"])


def test_unrestricted_search_above_row_degree_4096():
    """unrestricted_degree_repro: the full search reached the solution through another anchor even before the fix,
    while the completion from anchor 0 came back empty (a false hit).  Now every hit at threshold 3 completes."""
    p = degree_problem()
    for labelfree in (False, True):
        r = search.distance(p, k_table=2, kmax=3, labelfree=labelfree, exclusions=False)
        assert r["distance"] == r["lower_bound"] == 3 and r["solutions"] == [(0, 2, 4100)]
        assert r["runs"][-1]["false_hits"] == 0, (labelfree, r["runs"])


# ---------------------------------------------------------------------- 3. depth limit
def cycle(n):
    """Incidence matrix of an n-cycle with a logical on one edge: the only nonzero kernel vector takes every edge."""
    return Problem("%d-cycle" % n, n, 1, [(1 << i) ^ (1 << ((i + 1) % n)) for i in range(n)], [1] + [0] * (n - 1),
                   [()] * n)


def test_thresholds_beyond_the_depth_limit_are_refused():
    """depth_limit_repro: the 42-cycle has distance 42, and thresholds 41 and 42 came back exhausted (lower bound
    43).  The deepest threshold the kernel holds still works."""
    r = search.distance(cycle(search.DMAX), k_table=1, kmax=search.DMAX, labelfree=True)
    assert r["distance"] == search.DMAX and r["solutions"] == [tuple(range(search.DMAX))]
    p = cycle(42)
    assert raises(ValueError, search.distance, p, k_table=1, kmax=42, labelfree=True)
    # past the wrapper's check the kernel refuses by itself (status 4), and the wrapper raises on that status
    S = search.Searcher(p, labelfree=True)
    t = search.Table(p, 1, labelfree=True)
    S.add_table(t, exact=True)
    check = search.check_threshold
    search.check_threshold = lambda K: None
    try:
        assert raises(RuntimeError, S.search, 41)
    finally:
        search.check_threshold = check
        t.free()


# ---------------------------------------------------------------------- 4. 8-bit DP costs
def chain(n):
    """dp_boundary_check: checks e_0 = e_1 = ... = e_{n-1} and the logical e_0; the distance is n."""
    h = [1] + [(1 << (j - 1)) | (1 << j) for j in range(1, n - 1)] + [1 << (n - 2)]
    return Problem("chain", n - 1, 1, h, [1] + [0] * (n - 1), [(j, 0) for j in range(n - 1)])


def balanced(x):
    if len(x) == 1:
        return x[0]
    m = len(x) // 2
    return balanced(x[:m]), balanced(x[m:])


def test_dense_dp_at_the_8bit_boundary():
    """Distance 254 is exact in both executors; 255 and 256 used to read as "no logical" (None) and now raise.  A
    query without a logical still gives None; the tree DP (wider costs) gives all three distances."""
    for n in (254, 255, 256):
        p, order = chain(n), list(range(n))
        plan = trellis.build_plan(p.h, p.l, 1, order, p.nrows)
        assert plan.feasible
        assert tree_min_distance_for_mask(p.h, p.l, 1, balanced(order))[0] == n
        if n < 255:
            assert kernel.run_plan_numpy(plan) == n and kernel.run_plan(plan)[0] == n
            assert auto.dp_distance(p, order)[0] == n and auto.dp_witness(p, order, 0) == order
        else:
            assert raises(OverflowError, kernel.run_plan_numpy, plan)
            assert raises(OverflowError, kernel.run_plan, plan)
            assert raises(OverflowError, auto.dp_distance, p, order)
            assert raises(OverflowError, auto.dp_witness, p, order, 0)
    p = Problem("no logical", 1, 1, [1, 1], [1, 1], [(0, 0)])
    plan = trellis.build_plan(p.h, p.l, 1, [0, 1], p.nrows)
    assert not plan.feasible and kernel.run_plan_numpy(plan) is None and kernel.run_plan(plan)[0] is None


def test_sparse_dp_at_the_8bit_boundary():
    """dp_boundary_check and dp_overflow_check.  A forward sweep keeps weights up to K: K = 254 is exact, also
    with the dense fallback, and 255 and 256 (no value, or a wrap to 0) are refused.  A meet in the middle keeps
    about K/2 per direction: 255 and 256 are exact, 510 (forward cap 256, which gave 254) is refused.  distance()
    with start = kmax = 255 returned the false lower bound 256 in forward mode."""
    for backend in ("numpy", "c"):
        for n in (254, 255, 256):
            p = chain(n)
            tr = sparse_dp.Trellis.for_query(p, 0, list(range(n)))
            if n == 254:
                for dense in (None, 0.25):
                    r = sparse_dp.query(tr, n, mode="forward", backend=backend, use_h=False, dense=dense)
                    assert r["value"] == n and r["witness"] == list(range(n)), (backend, dense, r["value"])
                    assert (r["dense_cuts"] > 0) == (dense is not None)
            else:
                assert raises(ValueError, sparse_dp.query, tr, n, mode="forward", backend=backend, use_h=False)
            for dense in (None, 0.25):
                r = sparse_dp.query(tr, n, mode="mitm", backend=backend, use_h=False, dense=dense)
                assert r["value"] == n and r["witness"] == list(range(n)), (backend, n, dense, r["value"])
        tr = sparse_dp.Trellis.for_query(chain(510), 0, list(range(510)))
        assert raises(ValueError, sparse_dp.query, tr, 510, mode="mitm", backend=backend, use_h=False, witness=False)
        p = chain(255)
        kw = dict(order=list(range(255)), start=255, kmax=255, backend=backend, use_h=False)
        assert raises(ValueError, sparse_dp.distance, p, mode="forward", **kw)
        r = sparse_dp.distance(p, mode="mitm", **kw)
        assert r["distance"] == r["lower_bound"] == 255 and r["witness"] == list(range(255))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name, flush=True)
