"""Write a standard-form logical basis next to the logical matrix of every code instance: <dir>/full.L.std.mtx.

The code-distance problem of an instance is  min |e|  with  H e = 0  and  L e != 0,  where H holds the checks of
one type and L a basis of the logical operators of the other type.  Any basis of the same logical space gives
the same problem, but integer programs and SAT encodings turn every row of L into a parity constraint, and dense
rows weaken them.  The basis written here is the standard form of a CSS code (Gottesman's construction, as in
CSSLXLZ of the codeDistance package of arXiv:2603.22532): row-reduce the problem's checks A, then the other
checks B on the remaining columns; the logical operator for the i-th free column is that column plus the
transposed reduced B on B's pivot columns, so it is supported on B's pivot columns and one free column.
The standard form is much sparser than a generic basis for codes with many logical qubits but can be denser
for a few logical qubits, so the sparser of the two is taken and then reduced greedily: a check row of A or
another logical row is added to a logical row whenever that lowers its weight.

Every basis is checked before it is written: each row commutes with B (lies in ker B), the rows are
independent modulo the row space of A, and together with A they span the same space as the instance's own L
(so the set of solutions, and the distance, are unchanged).  The check matrices come from the instance
registry's builders, and the problem's H must equal A column for column.

The file name keeps 'std' for this sparse basis.

usage: python bench/standard_logicals.py [--only a,b] [--registry main|wjh|both]
"""
import argparse
import json
import os
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "papers")]
import common
import instances


def popcount(x):
    return x.bit_count() if hasattr(x, "bit_count") else bin(x).count("1")


def greedy(l_rows, a_rows):
    """Lower the weight of each logical row by adding check rows of A or other logical rows while that helps
    (neither changes the problem: A's rows lie in ker B, and adding logical rows is a change of basis)."""
    l = list(l_rows)
    pool_a = [r for r in a_rows if r]
    improved = True
    while improved:
        improved = False
        for i in range(len(l)):
            best, bw = l[i], popcount(l[i])
            for v in pool_a + l[:i] + l[i + 1:]:
                w = popcount(best ^ v)
                if w < bw:
                    best, bw, improved = best ^ v, w, True
            l[i] = best
    return l


def rref(rows, columns):
    """Fully reduced row echelon form over GF(2), pivots taken from `columns` in that order.
    Returns (reduced rows of rank r, pivot columns), the reduced rows in pivot order."""
    rows = [r for r in rows if r]
    pivots, done = [], 0
    for c in columns:
        bit = 1 << c
        pick = next((i for i in range(done, len(rows)) if rows[i] & bit), None)
        if pick is None:
            continue
        rows[done], rows[pick] = rows[pick], rows[done]
        for i in range(len(rows)):
            if i != done and rows[i] & bit:
                rows[i] ^= rows[done]
        pivots.append(c)
        done += 1
        if done == len(rows):
            break
    return rows[:done], pivots


def rank(rows, n):
    return len(rref(list(rows), range(n))[0])


def standard_form(a_rows, b_rows, n):
    """Logical operators in ker(B) that are nontrivial modulo rowspace(A), in standard form."""
    a_red, r_cols = rref(list(a_rows), range(n))
    r_set = set(r_cols)
    free_a = [c for c in range(n) if c not in r_set]
    b_red, s_cols = rref(list(b_rows), free_a)
    s_set = set(s_cols)
    k_cols = [c for c in range(n) if c not in r_set and c not in s_set]
    out = []
    for c in k_cols:
        v = 1 << c
        for row, p in zip(b_red, s_cols):
            if (row >> c) & 1:
                v |= 1 << p
        out.append(v)
    return out


def to_rows(cols, nrows):
    """Column bitmasks (over rows) -> row bitmasks (over columns)."""
    rows = [0] * nrows
    for j, c in enumerate(cols):
        m = c
        while m:
            low = m & -m
            rows[low.bit_length() - 1] |= 1 << j
            m ^= low
    return rows


def to_cols(rows, ncols):
    cols = [0] * ncols
    for i, r in enumerate(rows):
        m = r
        while m:
            low = m & -m
            cols[low.bit_length() - 1] |= 1 << i
            m ^= low
    return cols


def process(name, spec, directory):
    path = directory / name
    if not (path / "full.H.mtx").is_file():
        return name, "not exported here", None
    hx, hz, n, _ = instances._code(spec)
    basis = spec["basis"]
    a_rows, b_rows = (hx, hz) if basis == "X" else (hz, hx)       # stabcode.css_distance_problem's convention
    nrows, ncols, hcols = common.read_mtx(str(path / "full.H.mtx"))
    nobs, ncols2, lcols = common.read_mtx(str(path / "full.L.mtx"))
    if ncols != n or ncols2 != n:
        return name, "skipped: the problem merged columns (%d of %d qubits)" % (ncols, n), None
    h_rows = to_rows(hcols, nrows)
    if h_rows != list(a_rows) and not (rank(h_rows, n) == rank(a_rows, n) == rank(h_rows + list(a_rows), n)):
        return name, "skipped: the problem's H does not span the builder's check matrix", None
    l_old = to_rows(lcols, nobs)
    l_std = standard_form(a_rows, b_rows, n)
    start = l_std if sum(map(popcount, l_std)) <= sum(map(popcount, l_old)) else l_old
    l_new = greedy(start, a_rows)
    k = len(l_old)
    # checks: commute with B, independent modulo A, same span with A as the instance's L
    assert all(popcount(v & b) % 2 == 0 for v in l_new for b in b_rows if b), name + ": a row does not commute with B"
    ra = rank(h_rows, n)
    assert len(l_new) == k, "%s: %d standard-form logicals, instance has %d" % (name, len(l_new), k)
    assert rank(h_rows + l_new, n) == ra + k, name + ": rows not independent modulo the checks"
    assert rank(h_rows + l_old + l_new, n) == ra + k, name + ": a different logical space"
    common.write_mtx(str(path / "full.L.std.mtx"), to_cols(l_new, n), k)
    w_old = [popcount(v) for v in l_old]
    w_new = [popcount(v) for v in l_new]
    return name, "written", (k, statistics.median(w_old), statistics.median(w_new), sum(w_old),
                             sum(map(popcount, l_std)), sum(w_new))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only")
    ap.add_argument("--registry", default="both", choices=["main", "wjh", "both"])
    a = ap.parse_args()
    todo = []
    if a.registry in ("main", "both"):
        todo += [(n, s, HERE / "instances") for n, s in instances.INSTANCES.items() if s["track"] == "code"]
    if a.registry in ("wjh", "both"):
        todo += [(n, s, HERE / "instances_wjh") for n, s in instances.WJH.items() if s["track"] == "code"]
    if a.only:
        keep = set(a.only.split(","))
        todo = [t for t in todo if t[0] in keep]
    print("%-24s %-8s %5s %11s %11s %9s %9s %9s" % ("instance", "status", "k", "median old", "median new",
                                                       "nnz old", "nnz std", "nnz new"))
    for name, spec, directory in todo:
        if spec.get("status") != "ready":
            print("%-24s not ready" % name)
            continue
        name, status, stats = process(name, spec, directory)
        if stats:
            print("%-24s %-8s %5d %11.0f %11.0f %9d %9d %9d" % ((name, status) + stats), flush=True)
        else:
            print("%-24s %s" % (name, status), flush=True)


if __name__ == "__main__":
    main()
