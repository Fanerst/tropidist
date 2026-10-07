"""Design of syndrome-extraction gate orders for CSS codes whose checks are
translates of a few base checks, and exact circuit distance of the result.

Circuit family ("sequential"): one cycle is an X-check round followed by a
Z-check round.  In each round every check meets its data qubits in the same
order of *labels* (a label names one term of the base check), so the gates of
a layer are disjoint and the circuit is valid for every order.  Because the
two rounds do not interleave, a fault's effect on the data is seen by one
round of opposite-type checks, and the circuit distance in the Z basis is the
distance of the "effective" problem

    columns: single data errors, and for every X check the suffixes of its gate order
    rows:    Z checks          observables: Z logicals

(X basis: the same with the roles exchanged).  The same statement was verified
on Stim circuits for the mitten codes, and is re-verified here for every
reported design (the effective columns equal the columns of a one-round
window of the Stim circuit, and the witness is replayed).

Screening of orders: for a list of low-weight logical operators e, replacing
the part of e inside a suffix T of some check by one hook fault gives an
explicit undetected logical fault set of weight |e xor T| + 1 (several hooks
on different checks may be combined).  The minimum over the list is a
constructive upper bound on the circuit distance of that order.
"""
from __future__ import annotations

import itertools
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import stabcode
from cdist import search, symmetry
from cdist.problem import Problem, dedupe


class Code:
    """checks_x[c] / checks_z[c]: dict label -> data qubit.  All X checks share
    one label set, all Z checks another.  perms: check permutations (the same
    for X and Z checks) that are symmetries of the code and of any label order."""

    def __init__(self, name, n, checks_x, checks_z, perms, claimed=None):
        self.name, self.n, self.checks_x, self.checks_z, self.perms, self.claimed = name, n, checks_x, checks_z, perms, claimed
        self.hx = [sum(1 << q for q in c.values()) for c in checks_x]
        self.hz = [sum(1 << q for q in c.values()) for c in checks_z]
        self.labels_x = sorted(checks_x[0], key=str)
        self.labels_z = sorted(checks_z[0], key=str)
        self.lx, self.lz = stabcode.css_logicals(self.hx, self.hz, n)
        self.k = len(self.lx)


def effective_problem(code: Code, basis, order):
    """basis 'Z': X faults; hooks are suffixes of the X-check order `order`."""
    hooks, det, log = (code.checks_x, code.hz, code.lz) if basis == "Z" else (code.checks_z, code.hx, code.lx)
    n = code.n
    colh = [sum(1 << i for i, r in enumerate(det) if (r >> j) & 1) for j in range(n)]
    coll = [sum(1 << i for i, r in enumerate(log) if (r >> j) & 1) for j in range(n)]
    h, l, meta = list(colh), list(coll), [("data", j) for j in range(n)]
    for ci, c in enumerate(hooks):
        qs = [c[lab] for lab in (order(ci) if callable(order) else order)]     # per-check orders are allowed
        for m in range(1, len(qs)):
            a = b = 0
            for q in qs[m:]:
                a ^= colh[q]
                b ^= coll[q]
            h.append(a)
            l.append(b)
            meta.append(("hook", ci, m))
    hh, ll, cm = dedupe(h, l, meta)
    return Problem(f"{code.name}:effective:{basis}", len(det), len(log), hh, ll, [(i, 0) for i in range(len(det))], cm)


def problem_symmetry(p, code):
    sym = symmetry.from_row_perms(p, code.perms) if code.perms else {"ok": False}
    return sym, ({"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {})


def low_weight_logicals(code: Code, basis, extra=1, cap=200000, time_limit=120):
    """Logical operators of weight d .. d+extra of the code (one error type),
    one representative per symmetry orbit as far as the search returns them.
    Returns (d, list of qubit tuples)."""
    p = stabcode.css_distance_problem(code.hx, code.hz, code.n, basis, name=code.name)
    sym, kw = problem_symmetry(p, code)
    r = search.distance(p, k_table=2, kmax=code.n, cover=True, **kw)
    d = r["distance"]
    S = search.Searcher(p, labelfree=None, **kw)
    tab = search.Table(p, 2, labelfree=S.labelfree)
    S.add_table(tab, exact=True)
    out = set()
    for K in range(d, d + extra + 1):
        rr = S.search(K, enum_all=True, exclusions=False, cover=True, sol_cap=cap, time_limit=time_limit)
        for s in rr["solutions"]:
            out.add(tuple(sorted(p.col_meta[j][0][1] for j in s)))
        if rr["status"] != "exhausted" or rr["nsol_recorded"] >= cap:
            break
    tab.free()
    return d, sorted(out, key=lambda s: (len(s), s))


class Screen:
    """Constructive upper bound on the circuit distance of an order (one basis)."""

    def __init__(self, code: Code, basis, logicals):
        checks = code.checks_x if basis == "Z" else code.checks_z
        self.labels = code.labels_x if basis == "Z" else code.labels_z
        lab_index = {lab: i for i, lab in enumerate(self.labels)}
        self.w = len(self.labels)
        qcheck = {}
        for ci, c in enumerate(checks):
            for lab, q in c.items():
                qcheck.setdefault(q, []).append((ci, lab_index[lab]))
        # per logical: its weight and, per touched check, the mask of labels inside it
        self.items = []
        for e in logicals:
            per = {}
            for q in e:
                for ci, li in qcheck.get(q, []):
                    per[ci] = per.get(ci, 0) | (1 << li)
            self.items.append((len(e), sorted(per.values())))
        self.lab_index = lab_index
        self.pop = [bin(x).count("1") for x in range(1 << self.w)]

    def bound(self, order):
        """min over logicals of  weight - (best hook saving)  using one hook per
        check; savings on different checks are added only if positive.  The
        result is an upper bound when at most one hook is used; with several
        hooks it is an estimate (supports may overlap) and is returned separately."""
        idx = [self.lab_index[lab] for lab in order]
        suffix = []
        m = 0
        for li in reversed(idx[1:]):
            m |= 1 << li
            suffix.append(m)           # suffixes of size 1 .. w-1
        pop = self.pop
        best1 = best_multi = 10 ** 9
        for wt, masks in self.items:
            s1 = stot = 0
            for q in masks:
                s = 0
                for t in suffix:
                    g = 2 * pop[q & t] - pop[t] - 1
                    if g > s:
                        s = g
                if s > s1:
                    s1 = s
                stot += s
            if wt - s1 < best1:
                best1 = wt - s1
            if wt - stot < best_multi:
                best_multi = wt - stot
        return best1, best_multi


def canonical_orders(labels):
    """One order per class under: swapping the first two, swapping the last
    two, and reversal (these do not change the set of hook faults)."""
    seen = set()
    for perm in itertools.permutations(labels):
        if str(perm[0]) > str(perm[1]) or str(perm[-2]) > str(perm[-1]):
            continue
        rev = perm[::-1]
        rev = tuple(sorted(rev[:2], key=str)) + rev[2:-2] + tuple(sorted(rev[-2:], key=str))
        key = min(perm, rev, key=lambda x: tuple(map(str, x)))
        if key in seen:
            continue
        seen.add(key)
        yield perm


def exact_distance(code: Code, basis, order, kmax, k_table=2, time_limit=0.0, cover=False, log=None, start=1):
    p = effective_problem(code, basis, order)
    sym, kw = problem_symmetry(p, code)
    r = search.distance(p, k_table=k_table, kmax=kmax, time_limit=time_limit, cover=cover, log=log, start=start, **kw)
    return p, r


def local_search(screen: Screen, labels, iters=20000, seed=0, restarts=20):
    """Maximise the screening bound over orders by random restarts and swaps."""
    rng = random.Random(seed)
    best = None
    for _ in range(restarts):
        order = list(labels)
        rng.shuffle(order)
        cur = screen.bound(order)
        for _ in range(iters // restarts):
            i, j = rng.sample(range(len(order)), 2)
            order[i], order[j] = order[j], order[i]
            new = screen.bound(order)
            if new >= cur:
                cur = new
            else:
                order[i], order[j] = order[j], order[i]
        if best is None or cur > best[0]:
            best = (cur, list(order))
    return best
