"""Python driver for the weight-bounded exact search (gmitm.c)."""
from __future__ import annotations

import ctypes
import math
import os
import random
import subprocess
import sys
import time

import numpy as np

from .problem import Problem

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = None
DMAX = 40


def _build():
    src = os.path.join(_HERE, "gmitm.c")
    out = os.path.join(_HERE, "libgmitm.so")
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
        return out
    base = ["cc", "-O3", "-shared", "-fPIC", src, "-o", out]
    if sys.platform == "darwin":
        attempts = [base + ["-isysroot", "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk"], base]
    else:
        attempts = [base + ["-march=native", "-fopenmp"], base + ["-fopenmp"]]
    err = None
    for cmd in attempts:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return out
        err = r.stderr
    raise RuntimeError(f"could not build gmitm: {err}")


def lib():
    global _LIB
    if _LIB is None:
        L = ctypes.CDLL(_build())
        L.tab_create.restype = ctypes.c_void_p
        L.tab_create.argtypes = [ctypes.c_int, ctypes.c_int]
        L.tab_free.argtypes = [ctypes.c_void_p]
        L.tab_count.restype = ctypes.c_int64
        L.tab_count.argtypes = [ctypes.c_void_p]
        L.tab_build.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                                ctypes.c_void_p, ctypes.c_int]
        L.gm_search.restype = ctypes.c_int
        L.gm_num_threads.restype = ctypes.c_int
        _LIB = L
    return _LIB


def _ptr(a):
    return a.ctypes.data_as(ctypes.c_void_p)


def row_hashes(nrows, seed):
    rng = random.Random(seed)
    return ([rng.getrandbits(64) for _ in range(nrows)], [rng.getrandbits(64) for _ in range(nrows)])


def column_hashes(h, rh):
    zh = np.zeros(len(h), dtype=np.uint64)
    zl = np.zeros(len(h), dtype=np.uint64)
    cache = {}
    for j, a in enumerate(h):
        v = cache.get(a)
        if v is None:
            x = y = 0
            m = a
            while m:
                low = m & -m
                r = low.bit_length() - 1
                x ^= rh[0][r]
                y ^= rh[1][r]
                m ^= low
            v = cache[a] = (x, y)
        zh[j], zl[j] = v
    return zh, zl


class Table:
    """All column subsets of size <= k of a problem, keyed by syndrome hash."""

    def __init__(self, p: Problem, k, seed=12345, load=0.5, labelfree=False):
        """labelfree: store no logical labels (9 bytes per slot, any number of
        observables); to be used with a label-free Searcher."""
        assert labelfree or p.nobs <= 64, "more than 64 observables need a label-free table"
        self.problem = p
        self.k = k
        self.labelfree = labelfree
        self.wide = p.nobs > 16 and not labelfree    # 17 instead of 9 bytes per slot
        self.rh = row_hashes(p.nrows, seed)
        self.zh, self.zl = column_hashes(p.h, self.rh)
        self.lg = np.zeros(p.ncols, dtype=np.uint64) if labelfree else np.array(p.l, dtype=np.uint64)
        n = p.ncols
        total = sum(math.comb(n, i) for i in range(k + 1))
        log2 = max(10, math.ceil(math.log2(total / load + 1)))
        self.log2slots = log2
        L = lib()
        self.handle = L.tab_create(log2, 1 if self.wide else 0)
        if not self.handle:
            raise MemoryError(f"table with 2^{log2} slots")
        t = time.time()
        L.tab_build(self.handle, n, _ptr(self.zh), _ptr(self.zl), _ptr(self.lg), k)
        self.build_seconds = time.time() - t
        self.entries = L.tab_count(self.handle)

    def hashes_for(self, h):
        """Hashes of arbitrary syndromes of this table's problem."""
        return column_hashes(h, self.rh)

    def free(self):
        if self.handle:
            lib().tab_free(self.handle)
            self.handle = None


class Searcher:
    def __init__(self, p: Problem, rank=None, anchors=None, labelfree=None):
        """labelfree (default: when there are more than 64 observables): the
        search carries no logical label; every syndrome match in a table counts
        as a hit and the logical value is computed for complete zero-syndrome
        sets only.  Exact for any number of observables; costs extra hits on
        zero-logical sets."""
        self.p = p
        self.labelfree = (p.nobs > 64) if labelfree is None else bool(labelfree)
        n, m = p.ncols, p.nrows
        self.W = max(1, (m + 63) // 64)
        assert self.W < 256     # the covering bound reads one zero word past the syndrome
        col = np.zeros((n, self.W), dtype=np.uint64)
        col_rows, col_start = [], [0]
        row_lists = [[] for _ in range(m)]
        wmax = 0
        for j, a in enumerate(p.h):
            x = a
            for w in range(self.W):
                col[j, w] = x & 0xFFFFFFFFFFFFFFFF
                x >>= 64
            rows = []
            x = a
            while x:
                low = x & -x
                rows.append(low.bit_length() - 1)
                x ^= low
            wmax = max(wmax, len(rows))
            col_rows.extend(rows)
            col_start.append(len(col_rows))
            for r in rows:
                row_lists[r].append(j)
        self.col = col
        if self.labelfree:
            self.lw = max(1, (p.nobs + 63) // 64)
            full = np.zeros((n, self.lw), dtype=np.uint64)
            for j, b in enumerate(p.l):
                for q in range(self.lw):
                    full[j, q] = (b >> (64 * q)) & 0xFFFFFFFFFFFFFFFF
            self.full_lg = full
            self.lg = np.zeros(n, dtype=np.uint64)
        else:
            self.full_lg = None
            self.lg = np.array(p.l, dtype=np.uint64)
        self.col_rows = np.array(col_rows, dtype=np.int32)
        self.col_start = np.array(col_start, dtype=np.int32)
        rc, rs = [], [0]
        for r in range(m):
            rc.extend(row_lists[r])
            rs.append(len(rc))
        self.row_cols = np.array(rc, dtype=np.int32)
        self.row_start = np.array(rs, dtype=np.int32)
        self.wmax = wmax
        self.rank = np.array(rank if rank is not None else list(range(n)), dtype=np.int32)
        self.anchors = np.array(anchors if anchors is not None else list(range(n)), dtype=np.int32)
        self.tables = []     # (Table, zh, zl) for this problem's columns
        self.main = -1
        self.ex_start = None
        self.ex_cols = None
        self.kernel = None
        self._row_lists = row_lists

    def build_exclusions(self):
        """Pairs of columns whose sum is again a column (with matching logical
        label).  No minimum solution contains such a pair."""
        p = self.p
        index = {(a, b): j for j, (a, b) in enumerate(zip(p.h, p.l))}
        partners = [set() for _ in range(p.ncols)]
        seen = set()
        for cols in self._row_lists:
            for i, x in enumerate(cols):
                for y in cols[i + 1:]:
                    if (x, y) in seen:
                        continue
                    seen.add((x, y))
                    z = index.get((p.h[x] ^ p.h[y], p.l[x] ^ p.l[y]))
                    if z is not None:
                        partners[x].update((y, z))
                        partners[y].update((x, z))
                        partners[z].update((x, y))
        start, cols = [0], []
        for j in range(p.ncols):
            cols.extend(sorted(partners[j]))
            start.append(len(cols))
        self.ex_start = np.array(start, dtype=np.int32)
        self.ex_cols = np.array(cols if cols else [0], dtype=np.int32)
        return len(cols) // 2

    def set_kernel(self, sets):
        """Kernel dominance: zero-syndrome, zero-logical column sets.  A
        minimum solution contains at most half of each, so the search forbids
        the rest of a set once a prefix holds floor(|s|/2) of its columns."""
        sets = [tuple(s) for s in sets if len(s) >= 3]
        for s in sets:
            sy, lg = self.p.check(s)
            assert sy == 0 and lg == 0 and len(set(s)) == len(s), "not a zero-logical kernel element"
        if not sets:
            self.kernel = None
            return 0
        ks_start = np.cumsum([0] + [len(s) for s in sets]).astype(np.int32)
        ks_cols = np.array([j for s in sets for j in s], dtype=np.int32)
        by_col = [[] for _ in range(self.p.ncols)]
        for i, s in enumerate(sets):
            for j in s:
                by_col[j].append(i)
        kc_start = np.cumsum([0] + [len(x) for x in by_col]).astype(np.int32)
        kc_ids = np.array([i for x in by_col for i in x], dtype=np.int32)
        self.kernel = (len(sets), ks_start, ks_cols, kc_start, kc_ids)
        return len(sets)

    def add_table(self, table: Table, zh=None, zl=None, exact=False):
        """Attach a lookup table.  exact=True: the table is built from this
        very problem (a hit is a solution).  Otherwise zh/zl give, per column
        of this problem, the hash of its image in the relaxed problem."""
        # a labelled table queried without a label would skip some entries
        assert table.labelfree == self.labelfree, "label-free searches need label-free tables (and vice versa)"
        assert self.labelfree or table.wide or self.p.nobs <= 16, "a compact table compares only 16 observable bits"
        if exact:
            zh, zl = table.zh, table.zl
            self.main = len(self.tables)
        self.tables.append((table, np.ascontiguousarray(zh), np.ascontiguousarray(zl)))

    def _call(self, K, nt, tabs, tzh, tzl, main, rank_arr, anchors_arr, use_ex, enum_all, task_depth, time_limit,
              sol_cap, kernel_mode=False, use_kernel=True, cover=False):
        L = lib()
        # cover: False, True / "ascent" (covering bound with the greedy dual
        # ascent), "simple" (first dual solution only), or a number g: ascent
        # variant evaluated only at nodes with |residual| >= g * R
        gate = 0 if not cover else (4 if isinstance(cover, (bool, str)) else max(1, int(round(4 * cover))))
        L.gm_set_cover(ctypes.c_int(gate), ctypes.c_int(0 if cover == "simple" else 1))
        if self.kernel is not None and use_kernel:
            n, a, b, c, d = self.kernel
            L.gm_set_kernel(ctypes.c_int(n), _ptr(a), _ptr(b), _ptr(c), _ptr(d))
        else:
            L.gm_set_kernel(ctypes.c_int(0), None, None, None, None)
        L.gm_set_kernel_mode(ctypes.c_int(1 if kernel_mode else 0))
        if self.full_lg is not None:
            L.gm_set_full_labels(_ptr(self.full_lg), ctypes.c_int(self.lw))
        else:
            L.gm_set_full_labels(None, ctypes.c_int(0))
        nodes = np.zeros(DMAX + 2, dtype=np.int64)
        stats = np.zeros(8, dtype=np.int64)
        best = ctypes.c_int(-1)
        nsol = ctypes.c_int(0)
        stride = K + 2
        sol = np.zeros((sol_cap, stride), dtype=np.int32)
        t0 = time.time()
        rc = L.gm_search(
            ctypes.c_int(self.W), ctypes.c_int(self.p.ncols), ctypes.c_int(self.p.nrows), ctypes.c_int(self.wmax),
            _ptr(self.col), _ptr(self.lg), _ptr(self.row_start), _ptr(self.row_cols),
            _ptr(self.col_start), _ptr(self.col_rows),
            ctypes.c_int(nt), tabs, tzh, tzl, ctypes.c_int(main),
            _ptr(rank_arr), ctypes.c_int(len(anchors_arr)), _ptr(anchors_arr),
            _ptr(self.ex_start) if use_ex else None, _ptr(self.ex_cols) if use_ex else None,
            ctypes.c_int(K), ctypes.c_int(1 if enum_all else 0), ctypes.c_int(task_depth),
            ctypes.c_double(time_limit), _ptr(nodes), _ptr(stats),
            ctypes.byref(best), ctypes.c_int(sol_cap), ctypes.c_int(stride), _ptr(sol), ctypes.byref(nsol))
        L.gm_set_kernel_mode(ctypes.c_int(0))
        L.gm_set_kernel(ctypes.c_int(0), None, None, None, None)
        L.gm_set_cover(ctypes.c_int(0), ctypes.c_int(0))
        L.gm_set_full_labels(None, ctypes.c_int(0))
        dt = time.time() - t0
        status = {0: "exhausted", 1: "found", 2: "timeout", 3: "too_many_tasks"}[rc]
        sols = []
        for i in range(min(nsol.value, sol_cap)):
            w = int(sol[i, 0])
            sols.append(tuple(sorted(int(x) for x in sol[i, 1:1 + w])))
        return {
            "K": K, "status": status, "best": None if best.value < 0 else best.value,
            "solutions": sols, "nsol_recorded": nsol.value,
            "nodes": [int(x) for x in nodes[:K + 2]], "lookups": int(stats[0]),
            "hits": int(stats[1]), "false_hits": int(stats[2]), "tasks": int(stats[3]),
            "cover_pruned": int(stats[4]), "ascent_pruned": int(stats[5]), "cover_calls": int(stats[6]),
            "seconds": dt, "threads": L.gm_num_threads(),
        }

    def kernel_sets(self, wmax_s, colmaps=(), task_depth=2, sol_cap=2000000):
        """All zero-syndrome, zero-logical column sets of size <= wmax_s that
        contain no smaller such set as a canonical prefix (with this
        searcher's anchors and ranks, closed under the column maps)."""
        L = lib()
        L.gm_set_pattern(None, None, ctypes.c_int(0), ctypes.c_int(0))
        tabs = (ctypes.c_void_p * 1)()
        r = self._call(wmax_s, 0, tabs, tabs, tabs, -1, self.rank, self.anchors, False, True,
                       max(1, min(task_depth, wmax_s - 1)), 0.0, sol_cap, kernel_mode=True, use_kernel=False)
        assert r["status"] == "exhausted" and r["nsol_recorded"] <= sol_cap, r["status"]
        out = set(s for s in r["solutions"] if len(s) >= 3)
        if colmaps:
            from .lift import expand_orbits
            out = expand_orbits(out, colmaps)
        return sorted(out, key=lambda s: (len(s), s)), r

    def search(self, K, enum_all=False, task_depth=None, time_limit=0.0, sol_cap=100000, exclusions=True,
               pattern=None, anchors=None, rank=None, use_kernel=True, cover=False):
        """pattern = (cls, onpat, slack): class id per column (-1 for none),
        0/1 flag per class, and the number of off-pattern columns allowed."""
        L = lib()
        if pattern is not None:
            cls = np.ascontiguousarray(pattern[0], dtype=np.int32)
            onpat = np.ascontiguousarray(pattern[1], dtype=np.uint8)
            L.gm_set_pattern(_ptr(cls), _ptr(onpat), ctypes.c_int(len(onpat)), ctypes.c_int(int(pattern[2])))
        else:
            L.gm_set_pattern(None, None, ctypes.c_int(0), ctypes.c_int(0))
        anchors_arr = self.anchors if anchors is None else np.ascontiguousarray(anchors, dtype=np.int32)
        rank_arr = self.rank if rank is None else np.ascontiguousarray(rank, dtype=np.int32)
        nt = len(self.tables)
        assert self.main >= 0, "an exact table is required"
        kmain = self.tables[self.main][0].k
        auto_depth = task_depth is None
        if auto_depth:
            # with the covering bound the subtrees are very uneven: split finer
            task_depth = max(1, min(4 if cover else 3, K - kmain - 1))
        tabs = (ctypes.c_void_p * nt)(*[t[0].handle for t in self.tables])
        tzh = (ctypes.c_void_p * nt)(*[_ptr(t[1]) for t in self.tables])
        tzl = (ctypes.c_void_p * nt)(*[_ptr(t[2]) for t in self.tables])
        use_ex = exclusions and self.ex_start is not None
        while True:
            r = self._call(K, nt, tabs, tzh, tzl, self.main, rank_arr, anchors_arr, use_ex, enum_all, task_depth,
                           time_limit, sol_cap, use_kernel=use_kernel, cover=cover)
            if r["status"] != "too_many_tasks" or not auto_depth or task_depth <= 1:
                return r
            task_depth -= 1


def verify(p: Problem, cols):
    """Independent check that a column set is an undetected logical fault set."""
    s, lg = p.check(cols)
    return s == 0 and lg != 0 and len(set(cols)) == len(cols)


def distance(p: Problem, k_table=2, kmax=20, relaxed=None, rank=None, anchors=None,
             enum_all=False, time_limit=0.0, log=None, start=1, exclusions=True, on_run=None,
             table_load=0.5, kernel=None, cover=False, labelfree=None):
    """Exact distance by iterative deepening.

    relaxed: optional list of (Table of a relaxed problem, per-column relaxed
    syndromes of p).  Returns a dict with the certified lower bound, the
    distance if found, and per-threshold records.
    """
    S = Searcher(p, rank=rank, anchors=anchors, labelfree=labelfree)
    # Valid because thresholds are tried in increasing order: when K is
    # searched, no solution lighter than K exists (requires start <= true
    # distance, e.g. a certified lower bound).
    n_excl = S.build_exclusions() if exclusions else 0
    if kernel:
        S.set_kernel(kernel)
    for tab, img in (relaxed or []):
        zh, zl = tab.hashes_for(img)
        S.add_table(tab, zh, zl)
    main = Table(p, k_table, load=table_load, labelfree=S.labelfree)
    if log:
        log(f"  table k={k_table}: {main.entries} entries in 2^{main.log2slots} slots ({main.build_seconds:.1f}s)")
    S.add_table(main, exact=True)
    out = {"k_table": k_table, "table_entries": main.entries, "table_seconds": main.build_seconds,
           "exclusion_pairs": n_excl,
           "runs": [], "lower_bound": start, "distance": None, "solutions": []}
    for K in range(start, kmax + 1):
        r = S.search(K, enum_all=enum_all, time_limit=time_limit, exclusions=exclusions, cover=cover)
        for s in r["solutions"]:
            assert verify(p, s), "reported solution failed verification"
        rec = {x: r[x] for x in ("K", "status", "best", "nodes", "lookups", "hits", "false_hits", "seconds", "tasks",
                                 "cover_pruned")}
        out["runs"].append(rec)
        if log:
            log(f"  K={K}: {r['status']} best={r['best']} nodes={sum(r['nodes'])} lookups={r['lookups']} "
                f"false_hits={r['false_hits']} {r['seconds']:.2f}s")
        if on_run:
            on_run(rec)
        if r["status"] in ("timeout", "too_many_tasks"):
            break
        if r["best"] is not None:
            out["distance"] = r["best"]
            out["solutions"] = sorted({s for s in r["solutions"] if len(s) == r["best"]})
            out["lower_bound"] = r["best"]
            break
        out["lower_bound"] = K + 1
    main.free()
    return out
