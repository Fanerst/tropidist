"""Weight-truncated sparse Rank DP: the linear min-plus sweep of trellis.py / kernel.py, built weight by weight.

The dense DP keeps, at every cut of the column order, a table over all 2^(cut rank) states (the partial parities
of the rows active at the cut) holding the least weight of a fault set on the processed columns with that state.
Here the table is a sparse map, and states are dropped:

  truncation   a state of weight > K.  Exact for the question "is there a solution of weight <= K, and if so the
               least": the value of a state only grows along the sweep, so a dropped state never leads to one.
  lookahead    a state with weight + h > K, where h is an admissible lower bound on the faults still needed among
               the remaining columns (Trellis._bound_data).  Exact for the same reason.

By induction over the cuts, every state through which a solution of weight <= K passes keeps its exact value, so
the sweep returns the exact minimum whenever it is <= K and "nothing <= K" otherwise; distance() deepens K from a
lower bound.  K = infinity is the dense DP (breadth first, untruncated); the search of search.py is the truncated
depth-first evaluation of the same min-plus sum.

mode="forward" is one such sweep.  mode="mitm" splits the weight between the two directions, like the search's
meet-in-the-middle table: a backward sweep (the same trellis read from the right) keeps weights <= K - a; a
forward sweep keeps weights <= a - 1, and its new or improved states of weight <= a are joined with the backward
table at every cut (query() has the argument why every solution is seen).  The tables then only hold states of
weight about K/2, which is what makes the sweep cheaper than the dense DP on wide problems of moderate distance.

Witnesses come from a traceback through the tables; tables are kept at checkpoints only and recomputed segment by
segment (about 2 sqrt(N) tables in memory).  Where a sparse table would hold more than a fraction of all 2^w
states, a sweep without a frontier (forward mode, the backward half of mitm) switches to a dense array and runs
kernel.c's update, and switches back when the table thins out.

Two interchangeable table formats: NumpyTables (reference: sorted keys and values in numpy arrays, up to 64 row
slots) and CTables (sparse_dp.c: one packed uint64 per state, up to 56 slots).
"""
from __future__ import annotations

import ctypes
import glob
import heapq
import math
import os
import subprocess
import sys
import time

import numpy as np

from . import trellis

INF = 255
Q = 720720                      # lcm(1..16); the lookahead weights are multiples of 1/Q (rounded down: admissible)
U64 = np.uint64
KEYMASK = (1 << 56) - 1
_HERE = os.path.dirname(os.path.abspath(__file__))


def _bits(x):
    out = []
    while x:
        low = x & -x
        out.append(low.bit_length() - 1)
        x ^= low
    return out


class Trellis:
    """Minimal-span trellis of one query  min{|e| : H e = 0, (L e)_obs = 1}  in a column order.

    Rows (the constraint rows in minimal span form and the reduced target row) are given fixed bit positions
    ("slots"), by an interval colouring of their spans, so that a state means the same in the forward and the
    backward sweep: bit slot[r] is the partial parity of row r.  Cut c separates positions [0, c) from [c, N)."""

    def __init__(self, h, lrow, order, nrows, name=""):
        self.name = name
        self.order = list(order)
        self.N = N = len(self.order)
        hrows = trellis.minimal_span_form(trellis.rows_from_columns(h, self.order, nrows))
        lr = trellis.reduce_target_row(lrow, hrows)
        self.feasible = lr != 0
        if not self.feasible:
            return
        rows = list(hrows) + [lr]
        self.rows = rows
        self.target = [0] * len(hrows) + [1]
        self.L = len(rows) - 1
        self.start = [trellis.lowbit(r) for r in rows]
        self.end = [r.bit_length() - 1 for r in rows]
        # slots: rows whose closed spans [start, end] overlap get distinct slots
        slot = [0] * len(rows)
        free, busy, nslots = [], [], 0
        for r in sorted(range(len(rows)), key=lambda r: self.start[r]):
            while busy and busy[0][0] < self.start[r]:
                heapq.heappush(free, heapq.heappop(busy)[1])
            if free:
                s = heapq.heappop(free)
            else:
                s, nslots = nslots, nslots + 1
            slot[r] = s
            heapq.heappush(busy, (self.end[r], s))
        if nslots > 64:
            raise ValueError("trellis needs %d bits per state (at most 64 supported)" % nslots)
        self.slot, self.nslots = slot, nslots
        col = [0] * N
        for r, row in enumerate(rows):
            b = 1 << slot[r]
            for p in _bits(row):
                col[p] |= b
        self.col = col                                       # slot mask of the rows containing position p
        fsm, fsb, bsm, bsb = [0] * N, [0] * N, [0] * N, [0] * N
        starts_at, ends_at = [[] for _ in range(N)], [[] for _ in range(N)]
        for r in range(len(rows)):
            b = 1 << slot[r]
            fsm[self.end[r]] |= b                            # forward: a row is checked where it ends
            bsm[self.start[r]] |= b                          # backward: where it starts
            if self.target[r]:
                fsb[self.end[r]] |= b
                bsb[self.start[r]] |= b
            starts_at[self.start[r]].append((slot[r], self.target[r]))
            ends_at[self.end[r]].append((slot[r], self.target[r]))
        self.fsel_mask, self.fsel_bits, self.bsel_mask, self.bsel_bits = fsm, fsb, bsm, bsb
        self.starts_at, self.ends_at = starts_at, ends_at    # (slot, target) of the rows starting / ending at p
        # rows active at cut c: start < c <= end
        delta = [[] for _ in range(N + 1)]
        for r in range(len(rows)):
            delta[self.start[r] + 1].append(r)
            delta[self.end[r] + 1].append(~r)
        act, cur = [], set()
        for c in range(N + 1):
            for x in delta[c]:
                if x >= 0:
                    cur.add(x)
                else:
                    cur.discard(~x)
            act.append(sorted(cur))
        self.active_rows = act
        self.active = [sum(1 << slot[r] for r in a) for a in act]
        self.width = [len(a) for a in act]
        Ls = 1 << slot[self.L]
        self.tmask = [Ls if self.L in set(a) else 0 for a in act]
        self._bd = {}

    @classmethod
    def for_query(cls, p, obs, order):
        lrow = 0
        for pos, j in enumerate(order):
            if (p.l[j] >> obs) & 1:
                lrow |= 1 << pos
        return cls(p.h, lrow, order, p.nrows, name="%s obs %d" % (getattr(p, "name", ""), obs))

    # ------------------------------------------------------------------ lookahead bound
    def _bound_data(self, forward):
        """Per cut: (masks, weights, extra) of the bound h(s) = ceil((extra + sum_k w_k |U(s) & mask_k|) / Q),
        where U(s) = s ^ tmask are the active rows whose remaining parity is odd.

        A remaining column j (position >= c going forward, < c going backward) flips the relevant rows
        supp(j) ∩ R_c, where R_c = the active rows, plus the target row while it lies wholly on the remaining
        side (its parity there is still 0, its target 1).  Give row r the weight y_r = 1 / max_{j ∋ r} |supp(j) ∩ R_c|.
        Every remaining column then carries total weight <= 1, and the remaining faults must flip every row of U,
        so they number at least sum_{r in U} y_r (a dual solution of the covering LP).  y is rounded down to a
        multiple of 1/Q."""
        N, rows = self.N, self.rows
        S = np.zeros((len(rows), N), dtype=np.int32)
        for r, row in enumerate(rows):
            S[r, _bits(row)] = 1
        out = []
        for c in range(N + 1):
            rel = list(self.active_rows[c])
            lone = False                                      # target row wholly on the remaining side
            if forward and self.start[self.L] >= c:
                rel.append(self.L)
                lone = True
            if not forward and self.end[self.L] < c:
                rel.append(self.L)
                lone = True
            if not rel:
                out.append(((), (), 0))
                continue
            if forward:
                lo, hi = c, max(self.end[r] for r in rel) + 1
            else:
                lo, hi = min(self.start[r] for r in rel), c
            sub = S[rel, lo:hi]
            cnt = sub.sum(axis=0)
            cmax = (sub * cnt).max(axis=1)
            assert (cmax >= 1).all()
            w = Q // cmax
            masks, extra = {}, 0
            for r, wr in zip(rel, w.tolist()):
                if lone and r == self.L:
                    extra = wr
                    continue
                masks[wr] = masks.get(wr, 0) | (1 << self.slot[r])
            ks = sorted(masks)
            out.append((tuple(U64(masks[k]) for k in ks), tuple(np.int64(k) for k in ks), extra))
        return out

    def bound_data(self, forward):
        if forward not in self._bd:
            self._bd[forward] = self._bound_data(forward)
        return self._bd[forward]

    def bound_arrays(self, forward):
        """bound_data as contiguous arrays for the C kernel: per cut (masks uint64, weights int64, extra)."""
        key = ("arrays", forward)
        if key not in self._bd:
            self._bd[key] = [(np.array(m, dtype=U64), np.array(w, dtype=np.int64), int(e))
                             for m, w, e in self.bound_data(forward)]
        return self._bd[key]


def bound(keys, tmask, hd):
    """The lookahead lower bound for an array of states (see Trellis._bound_data)."""
    masks, weights, extra = hd
    if not len(masks):
        return np.full(keys.shape, (extra + Q - 1) // Q, dtype=np.int64)
    u = keys ^ U64(tmask)
    tot = np.full(keys.shape, extra, dtype=np.int64)
    for m, w in zip(masks, weights):
        tot += w * np.bitwise_count(u & m).astype(np.int64)
    return (tot + (Q - 1)) // Q


# ---------------------------------------------------------------------- dense tables (fallback)
class Dense:
    """A table over all states of the active rows: T[i] for the compact index i of a state (bit k of i = the bit of
    slots[k], slots ascending); INF = absent."""
    __slots__ = ("slots", "T")

    def __init__(self, slots, T):
        self.slots, self.T = list(slots), T

    def compact(self, keys):
        out = np.zeros(keys.shape, dtype=np.int64)
        for k, s in enumerate(self.slots):
            out |= ((keys >> U64(s)) & U64(1)).astype(np.int64) << k
        return out

    def expand(self, idx):
        out = np.zeros(idx.shape, dtype=U64)
        for k, s in enumerate(self.slots):
            out |= ((idx >> k) & 1).astype(U64) << U64(s)
        return out

    def cmask(self, mask):
        return sum(1 << k for k, s in enumerate(self.slots) if (mask >> s) & 1)

    def count(self):
        return int(np.count_nonzero(self.T != INF))

    def lookup(self, s):
        if s & ~sum(1 << x for x in self.slots):
            return INF
        return int(self.T[int(self.compact(np.array([s], dtype=U64))[0])])

    def lookup_many(self, keys):
        """Values of the given states (INF where absent or outside the active rows)."""
        act = U64(sum(1 << x for x in self.slots))
        ok = (keys & ~act) == 0
        out = np.full(keys.shape, INF, dtype=np.uint8)
        out[ok] = self.T[self.compact(keys[ok])]
        return out

    def insert_slot(self, slot):
        pos = sum(1 for x in self.slots if x < slot)
        w = len(self.slots)
        A = self.T.reshape(1 << (w - pos), 1 << pos)
        self.T = np.stack([A, np.full_like(A, INF)], axis=1).reshape(-1)
        self.slots.insert(pos, slot)

    def select_slot(self, slot, target):
        pos = self.slots.index(slot)
        w = len(self.slots)
        self.T = np.ascontiguousarray(self.T.reshape(1 << (w - pos - 1), 2, 1 << pos)[:, target, :]).reshape(-1)
        self.slots.pop(pos)

    def prune(self, cap, K, tmask, hd, chunk=1 << 22):
        T = self.T
        T[(T > cap) & (T != INF)] = INF
        if hd is None:
            return
        masks, weights, extra = hd
        cms = [U64(self.cmask(int(m))) for m in masks]
        ct = U64(self.cmask(tmask))
        for lo in range(0, T.size, chunk):
            idx = np.arange(lo, min(T.size, lo + chunk), dtype=U64)
            u = idx ^ ct
            tot = np.full(idx.shape, extra, dtype=np.int64)
            for m, w in zip(cms, weights):
                tot += np.int64(w) * np.bitwise_count(u & m).astype(np.int64)
            h = (tot + (Q - 1)) // Q
            seg = T[lo:lo + idx.size]
            seg[(seg.astype(np.int64) + h > K) & (seg != INF)] = INF


def _dense_update(T, cm):
    if not cm:
        return
    from . import kernel
    kernel.lib().dp_update(T.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), T.size, cm)


# ---------------------------------------------------------------------- numpy tables
class NumpyTables:
    """Sparse tables as (keys, vals): keys sorted and unique (uint64), vals uint8."""
    name = "numpy"

    def __init__(self, tr):
        self.tr = tr

    @staticmethod
    def start():
        return np.zeros(1, dtype=U64), np.zeros(1, dtype=np.uint8)

    @staticmethod
    def size(tab):
        return tab.count() if isinstance(tab, Dense) else tab[0].size

    @staticmethod
    def nbytes(tab):
        return tab.T.nbytes if isinstance(tab, Dense) else tab[0].nbytes + tab[1].nbytes

    @staticmethod
    def arrays(tab):
        """(keys, vals) of a sparse table."""
        return tab

    @staticmethod
    def from_arrays(keys, vals):
        return keys, vals

    @staticmethod
    def lookup(tab, s):
        if isinstance(tab, Dense):
            return tab.lookup(s)
        keys, vals = tab
        i = int(np.searchsorted(keys, U64(s)))
        if i < keys.size and int(keys[i]) == s:
            return int(vals[i])
        return INF

    def step(self, tab, upd, sel_mask, sel_bits, cap, K, tmask, hd, keep_below=None, want_changed=False):
        """One column on a sparse table:  T'[s] = min(T[s], T[s ^ upd] + 1),  then keep the states whose bits
        sel_mask equal sel_bits and clear those bits (the rows that close here), and drop values > cap and states
        with value + h > K (hd: the lookahead data of the new cut, or None).

        Returns (table, changed).  changed = (keys, vals) of the states that are new or got a smaller value (when
        want_changed).  States with value >= keep_below are returned in changed only, not in the table: in the
        meet-in-the-middle sweep a forward state at the cap weight cannot grow further and only needs to be joined
        at the cut where it appears."""
        keys, vals = tab
        n = keys.size
        improved = None
        if upd and n:
            src = vals < cap                                   # the only states with a successor within the cap
            if not src.all():
                tk, tv = keys[src] ^ U64(upd), vals[src] + np.uint8(1)
            else:
                tk, tv = keys ^ U64(upd), vals + np.uint8(1)
            idx = np.searchsorted(keys, tk)
            idx[idx == n] = n - 1
            hit = keys[idx] == tk
            imp = hit & (tv < vals[idx])
            if imp.any():
                ii = idx[imp]
                vals = vals.copy()
                vals[ii] = tv[imp]
                if want_changed:
                    improved = np.zeros(n, dtype=bool)
                    improved[ii] = True
            miss = ~hit
            nk, nv = tk[miss], tv[miss]                        # distinct, and not in keys
        else:
            nk = np.empty(0, dtype=U64)
            nv = np.empty(0, dtype=np.uint8)
        if sel_mask:
            sm, sb = U64(sel_mask), U64(sel_bits)
            ok = (keys & sm) == sb
            keys, vals = keys[ok], vals[ok]
            if improved is not None:
                improved = improved[ok]
            ok = (nk & sm) == sb
            nk, nv = nk[ok], nv[ok]
            if sel_bits:                                       # target-0 bits are already clear
                clr = ~sm
                keys = keys & clr
                nk = nk & clr
        keys, vals, ok = _prune(keys, vals, cap, K, tmask, hd)
        if ok is not None and improved is not None:
            improved = improved[ok]
        nk, nv, _ = _prune(nk, nv, cap, K, tmask, hd)
        changed = None
        if want_changed:
            if improved is not None and improved.any():
                changed = (np.concatenate([keys[improved], nk]), np.concatenate([vals[improved], nv]))
            else:
                changed = (nk, nv)
        if keep_below is not None and nk.size:
            ok = nv < keep_below                               # (improved and kept states are already below it)
            nk, nv = nk[ok], nv[ok]
        if nk.size:
            o = np.argsort(nk)
            nk, nv = nk[o], nv[o]
            pos = np.searchsorted(keys, nk)
            keys = np.insert(keys, pos, nk)
            vals = np.insert(vals, pos, nv)
        return (keys, vals), changed

    @staticmethod
    def changed_size(ch):
        return ch[0].size

    @staticmethod
    def persistent(tab):
        return tab

    @staticmethod
    def truncate(tab, below):
        keys, vals = tab
        ok = vals < below
        return keys[ok], vals[ok]

    @staticmethod
    def join(ch, btab, tmask):
        """Least value(f) + value(b) over changed forward states f and backward states b with b = f ^ tmask:
        (total, forward key, forward value, backward key), or None."""
        ck, cv = ch
        if not ck.size:
            return None
        q = ck ^ U64(tmask)
        if isinstance(btab, Dense):
            bv = btab.lookup_many(q)
            hit = bv != INF
            if not hit.any():
                return None
            tot = cv[hit].astype(np.int64) + bv[hit].astype(np.int64)
        else:
            bkeys, bvals = btab
            if not bkeys.size:
                return None
            idx = np.searchsorted(bkeys, q)
            idx[idx == bkeys.size] = bkeys.size - 1
            hit = bkeys[idx] == q
            if not hit.any():
                return None
            tot = cv[hit].astype(np.int64) + bvals[idx[hit]].astype(np.int64)
        i = int(np.argmin(tot))
        fi = int(np.flatnonzero(hit)[i])
        return int(tot[i]), int(ck[fi]), int(cv[fi]), int(q[fi])


def _prune(keys, vals, cap, K, tmask, hd):
    ok = vals <= cap
    if hd is not None and keys.size:
        ok &= vals.astype(np.int64) + bound(keys, tmask, hd) <= K
    if ok.all():
        return keys, vals, None
    return keys[ok], vals[ok], ok


# ---------------------------------------------------------------------- C tables
_CLIB = None


def build_lib(force=False):
    """Compile sparse_dp.c next to this file and return the library path."""
    src = os.path.join(_HERE, "sparse_dp.c")
    out = os.path.join(_HERE, "libsparse_dp.so")
    if not force and os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
        return out
    base = ["cc", "-O3", "-shared", "-fPIC", src, "-o", out]
    attempts = []
    if sys.platform == "darwin":
        for sdk in sorted(glob.glob("/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk")):
            attempts.append(base + ["-isysroot", sdk])
        attempts.append(base)
    else:
        attempts += [base + ["-march=native", "-fopenmp"], base + ["-fopenmp"], base]
    err = None
    for cmd in attempts:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return out
        err = r.stderr
    raise RuntimeError("could not build the sparse DP kernel: %s" % err)


def clib():
    global _CLIB
    if _CLIB is None:
        L = ctypes.CDLL(build_lib())
        vp, i64, u64, ci = ctypes.c_void_p, ctypes.c_int64, ctypes.c_uint64, ctypes.c_int
        L.sp_candidates.argtypes = [vp, i64, u64, u64, u64, ci, ci, vp, vp, i64, u64, ci, ci, ci, vp, vp, ci]
        L.sp_candidates.restype = i64
        L.sp_merge.argtypes = [vp, i64, vp, i64, u64, u64, ci, ci, ci, vp, vp, i64, u64, ci, ci, vp, vp,
                               ctypes.POINTER(i64)]
        L.sp_merge.restype = i64
        L.sp_join.argtypes = [vp, i64, vp, i64, u64, ctypes.POINTER(u64), ctypes.POINTER(u64)]
        L.sp_join.restype = ci
        L.sp_hist.argtypes = [vp, i64, vp]
        L.sp_num_threads.restype = ci
        _CLIB = L
    return _CLIB


def _p(a):
    return a.ctypes.data_as(ctypes.c_void_p) if a is not None else None


class CTables:
    """Sparse tables as one sorted array of packed states  key | value << 56  (sparse_dp.c).

    step() writes into two alternating buffers of this object: the table it returns stays valid only until the
    step after next, so a sweep copies the tables it keeps (persistent()).  Use one object per sweep."""
    name = "c"
    SORT = 1                    # 0: radix sort of the candidates, 1: reorder by the XOR (one pass per bit)

    def __init__(self, tr):
        if tr.nslots > 56:
            raise ValueError("the C tables hold at most 56 row slots (this trellis needs %d)" % tr.nslots)
        self.tr = tr
        self.nbits = max(1, tr.nslots)
        self.lib = clib()
        self.bufs = {}
        self.flip = 0

    def _buf(self, name, n):
        b = self.bufs.get(name)
        if b is None or b.size < n:
            b = self.bufs[name] = np.empty(max(n, int(1.25 * (b.size if b is not None else 0)), 1024), dtype=U64)
        return b

    @staticmethod
    def persistent(tab):
        return tab if isinstance(tab, Dense) else tab.copy()

    @staticmethod
    def truncate(tab, below):
        return tab[(tab >> U64(56)) < U64(below)]

    @staticmethod
    def start():
        return np.zeros(1, dtype=U64)

    @staticmethod
    def size(tab):
        return tab.count() if isinstance(tab, Dense) else tab.size

    @staticmethod
    def nbytes(tab):
        return tab.T.nbytes if isinstance(tab, Dense) else tab.nbytes

    @staticmethod
    def arrays(tab):
        return tab & U64(KEYMASK), (tab >> U64(56)).astype(np.uint8)

    @staticmethod
    def from_arrays(keys, vals):
        return keys | (vals.astype(U64) << U64(56))

    @staticmethod
    def lookup(tab, s):
        if isinstance(tab, Dense):
            return tab.lookup(s)
        keys = tab & U64(KEYMASK)
        i = int(np.searchsorted(keys, U64(s)))
        if i < keys.size and int(keys[i]) == s:
            return int(tab[i] >> U64(56))
        return INF

    def step(self, tab, upd, sel_mask, sel_bits, cap, K, tmask, hd, keep_below=None, want_changed=False):
        """As NumpyTables.step; changed is a sorted packed array."""
        L = self.lib
        n = tab.size
        if hd is None:
            ncls, mp, wp, extra, use_h = 0, None, None, 0, 0
        else:
            m_arr, w_arr, extra = hd
            ncls, mp, wp, use_h = m_arr.size, _p(m_arr), _p(w_arr), 1
        cand = self._buf("cand", n)
        tmp = self._buf("tmp", n)
        m = L.sp_candidates(_p(tab), n, upd, sel_mask, sel_bits, cap, ncls, mp, wp, extra, tmask, K, use_h,
                            self.nbits, _p(cand), _p(tmp), self.SORT)
        self.flip ^= 1
        out = self._buf("out%d" % self.flip, n + m)
        ch = self._buf("changed", m) if want_changed else None
        nch = ctypes.c_int64(0)
        no = L.sp_merge(_p(tab), n, _p(cand), m, sel_mask, sel_bits, cap, keep_below or 0, ncls, mp, wp, extra,
                        tmask, K, use_h, _p(out), _p(ch), ctypes.byref(nch))
        out = out[:no]
        if want_changed:
            ch = ch[:nch.value]
        return out, ch

    @staticmethod
    def changed_size(ch):
        return ch.size

    def join(self, ch, btab, tmask):
        if not ch.size:
            return None
        if isinstance(btab, Dense):
            ck, cv = self.arrays(ch)
            return NumpyTables.join((ck, cv), btab, tmask)
        fb, bb = ctypes.c_uint64(0), ctypes.c_uint64(0)
        tot = self.lib.sp_join(_p(ch), ch.size, _p(btab), btab.size, tmask, ctypes.byref(fb), ctypes.byref(bb))
        if tot < 0:
            return None
        return int(tot), fb.value & KEYMASK, fb.value >> 56, bb.value & KEYMASK


BACKENDS = {"numpy": NumpyTables, "c": CTables}


class BudgetExceeded(RuntimeError):
    """A table outgrew max_states or a sweep ran past its deadline (time.monotonic())."""


# ---------------------------------------------------------------------- sweeps
class Sweep:
    """One direction of the truncated sweep of a trellis, with tables kept at checkpoints for recomputation.

    direction +1: cuts 0 -> N, starting from {0: 0} at cut 0; -1: cuts N -> 0 from {0: 0} at cut N.  cap: largest
    weight kept, or caps: one per cut, non-increasing in the sweep direction (the table at cut c keeps weights
    <= caps[c], which keeps the stored values exact).  K: the total threshold that the lookahead compares with
    (use_h).  frontier (forward sweeps of the meet in the middle): the step out of cut p keeps weights <= caps[p] - 1
    and returns the new or improved states of weight <= caps[p] as `changed` (NumpyTables.step, keep_below); where
    caps drops, the table before the cut to the new cap is also returned (`extra`), to be joined in full.  dense:
    switch to a dense table where the sparse one holds more than this fraction of the 2^w states (and back below a
    quarter of it), if 2^w <= dense_max bytes; not with frontier."""

    def __init__(self, tr, direction, K, cap=None, use_h=True, every=None, frontier=False, backend="numpy",
                 dense=None, dense_max=1 << 30, max_states=None, deadline=None, caps=None):
        self.tr, self.direction, self.K = tr, direction, K
        self.caps = [min(int(x), K) for x in caps] if caps is not None else [min(cap, K)] * (tr.N + 1)
        if direction > 0:
            assert all(x >= y for x, y in zip(self.caps, self.caps[1:])), "forward caps must not increase"
        else:
            assert all(x <= y for x, y in zip(self.caps, self.caps[1:])), "backward caps must not decrease"
        self.use_h = use_h
        self.frontier = frontier
        self.be = BACKENDS[backend](tr) if isinstance(backend, str) else backend
        if use_h:
            self.hd = tr.bound_arrays(direction > 0) if self.be.name == "c" else tr.bound_data(direction > 0)
            self.hd_np = tr.bound_data(direction > 0)
        else:
            self.hd = self.hd_np = None
        self.every = every or max(1, int(math.isqrt(tr.N)))
        self.dense = None if frontier else dense
        self.dense_max = dense_max
        self.max_states, self.deadline = max_states, deadline
        self.ckpt = {}
        self.counts = [0] * (tr.N + 1)
        self.changed_counts = [0] * (tr.N + 1)
        self.dense_cuts = 0
        self.peak = 0
        self.peak_bytes = 0
        self.steps_done = 0

    def first(self):
        return (0 if self.direction > 0 else self.tr.N), self.be.start()

    def _step(self, tab, p, want_changed):
        """The step at position p: (new cut, table, changed, extra); see the class docstring."""
        tr, fwd = self.tr, self.direction > 0
        cut = p + 1 if fwd else p
        if fwd:
            upd, sm, sb = tr.col[p], tr.fsel_mask[p], tr.fsel_bits[p]
        else:
            upd, sm, sb = tr.col[p], tr.bsel_mask[p], tr.bsel_bits[p]
        self.steps_done += 1
        cap, kb = self.caps[cut], None
        if self.frontier:
            cap = kb = self.caps[p]
        if isinstance(tab, Dense):
            tab = Dense(tab.slots, tab.T.copy())             # the old table may be a checkpoint
            for s, _ in sorted(tr.starts_at[p] if fwd else tr.ends_at[p]):
                tab.insert_slot(s)
            _dense_update(tab.T, tab.cmask(upd))
            for s, t in (tr.ends_at[p] if fwd else tr.starts_at[p]):
                tab.select_slot(s, t)
            tab.prune(cap, self.K, tr.tmask[cut], self.hd_np[cut] if self.hd_np else None)
            if tab.count() < self.dense / 4 * tab.T.size:
                keys = tab.expand(np.flatnonzero(tab.T != INF))
                vals = tab.T[tab.T != INF]
                tab = self.be.from_arrays(keys, vals)
            return cut, tab, None, None
        tab, ch = self.be.step(tab, upd, sm, sb, cap, self.K, tr.tmask[cut], self.hd[cut] if self.hd else None,
                               kb, want_changed)
        if self.frontier and self.caps[cut] < cap:
            # the cap drops here: the states of weight in [caps[cut], cap) leave the table; join them all first
            return cut, self.be.truncate(tab, self.caps[cut]), ch, tab
        if self.dense and tr.width[cut] <= 62:
            n = self.be.size(tab)
            full = 1 << tr.width[cut]
            if n > self.dense * full and full <= self.dense_max:
                slots = sorted(tr.slot[r] for r in tr.active_rows[cut])
                D = Dense(slots, np.full(full, INF, dtype=np.uint8))
                keys, vals = self.be.arrays(tab)
                D.T[D.compact(keys)] = vals
                tab = D
        return cut, tab, ch, None

    def _iter(self, cut, tab, stop, want_changed=False):
        """Yield (cut, table, changed, extra) for the cuts after `cut` up to `stop` (inclusive)."""
        if self.direction > 0:
            rng = range(cut, stop)
        else:
            rng = range(cut - 1, stop - 1, -1)
        for p in rng:
            c, tab, ch, extra = self._step(tab, p, want_changed)
            yield c, tab, ch, extra

    def is_ckpt(self, c):
        return c % self.every == 0 or c == 0 or c == self.tr.N

    def run(self, on_cut=None):
        """Full sweep from the start, keeping checkpoints and per-cut counts.  on_cut(cut, table, changed, extra)
        (changed: the new or improved states; extra: see the class docstring) may return True to stop; returns
        the last cut reached."""
        c0, tab = self.first()
        self.ckpt[c0] = tab
        self.counts[c0] = self.changed_counts[c0] = 1
        self.peak = 1
        if on_cut and on_cut(c0, tab, tab, None):
            return c0
        stop = self.tr.N if self.direction > 0 else 0
        ck_bytes = self.be.nbytes(tab)
        for c, tab, ch, extra in self._iter(c0, tab, stop, want_changed=on_cut is not None):
            n = self.be.size(tab)
            self.counts[c] = n
            nc = self.be.changed_size(ch) if ch is not None else 0
            self.changed_counts[c] = nc
            self.peak = max(self.peak, n, nc)
            if isinstance(tab, Dense):
                self.dense_cuts += 1
            if self.is_ckpt(c):
                self.ckpt[c] = self.be.persistent(tab)
                ck_bytes += self.be.nbytes(tab)
            self.peak_bytes = max(self.peak_bytes, ck_bytes + self.be.nbytes(tab))
            if self.max_states is not None and max(n, nc) > self.max_states:
                raise BudgetExceeded("%d states at cut %d" % (max(n, nc), c))
            if self.deadline is not None and time.monotonic() > self.deadline:
                raise BudgetExceeded("deadline at cut %d" % c)
            if on_cut and on_cut(c, tab, ch, extra):
                return c
        return stop

    def segment(self, lo, hi):
        """Tables at the cuts lo..hi (lo <= hi), recomputed from a checkpoint: dict cut -> table."""
        out = {}
        if self.direction > 0:
            c0 = max(c for c in self.ckpt if c <= lo)
            tab = self.ckpt[c0]
            if c0 >= lo:
                out[c0] = tab
            for c, tab, _, _ in self._iter(c0, tab, hi):
                if c >= lo:
                    out[c] = self.be.persistent(tab)
        else:
            c0 = min(c for c in self.ckpt if c >= hi)
            tab = self.ckpt[c0]
            if c0 <= hi:
                out[c0] = tab
            for c, tab, _, _ in self._iter(c0, tab, lo):
                if c <= hi:
                    out[c] = self.be.persistent(tab)
        return out

    def table(self, c, cache):
        """Table at cut c, for cuts requested in the opposite order of the sweep (cache: a dict reused between
        calls): a backward sweep's tables in increasing c, a forward sweep's in decreasing c."""
        if c not in cache:
            cache.clear()
            if self.direction < 0:
                hi = min(x for x in self.ckpt if x >= c)
                cache.update(self.segment(c, hi))
            else:
                lo = max(x for x in self.ckpt if x <= c)
                cache.update(self.segment(lo, c))
        return cache[c]

    def traceback(self, cut, state, value):
        """Columns (problem indices) of a partial solution reaching `state` with weight `value` at `cut`."""
        tr = self.tr
        used = []
        s, v = int(state), int(value)
        if self.direction > 0:
            c = cut
            while c > 0:
                lo = max(0, (c - 1) // self.every * self.every)
                tabs = self.segment(lo, c - 1)
                for p in range(c - 1, lo - 1, -1):          # step p: cut p -> p + 1
                    s, v = self._undo(tabs[p], s, v, s | tr.fsel_bits[p], tr.col[p], tr.order[p], used)
                c = lo
        else:
            c = cut
            while c < tr.N:
                hi = min(tr.N, (c // self.every + 1) * self.every)
                tabs = self.segment(c + 1, hi)
                for p in range(c, hi):                       # backward step p: cut p + 1 -> p
                    s, v = self._undo(tabs[p + 1], s, v, s | tr.bsel_bits[p], tr.col[p], tr.order[p], used)
                c = hi
        assert s == 0 and v == 0, (s, v)
        return used

    def _undo(self, tab, s, v, s_mid, upd, column, used):
        """One traceback step: state s with value v after the step; tab the table before it."""
        if self.be.lookup(tab, s_mid) == v:
            return s_mid, v
        prev = s_mid ^ upd
        assert upd and self.be.lookup(tab, prev) == v - 1, "traceback lost the path"
        used.append(column)
        return prev, v - 1


# ---------------------------------------------------------------------- choice of the split
def weight_profile(tr, direction, cap, backend="c"):
    """Number of states of each weight <= cap summed over all cuts, for a sweep keeping weights <= cap (no
    lookahead): the work of that direction at that cap."""
    sw = Sweep(tr, direction, cap, cap, use_h=False, backend=backend)
    c0, tab = sw.first()
    tot = np.zeros(cap + 1)
    tot[0] = 1
    for c, tab, _, _ in sw._iter(c0, tab, tr.N if direction > 0 else 0):
        if isinstance(tab, Dense):
            vals = tab.T[tab.T != INF]
        else:
            vals = sw.be.arrays(tab)[1]
        tot += np.bincount(vals, minlength=cap + 1)[:cap + 1]
    return tot


def choose_split(tr, K, backend="c", probe=3, budget=2e9):
    """Split a of the meet-in-the-middle sweep at threshold K that minimises the predicted work

        sum_{w <= a-1} F(w) + F(a-1) + 2 sum_{w <= K-a} B(w),

    F, B: states per weight summed over all cuts going forward and backward (the forward bulk, its frontier, the
    backward sweep and its recomputation).  F and B are measured up to weight `probe` (fewer if that would cost
    more than `budget` states) and extrapolated with the growth factor of their last two weights, which falls
    with the weight on these problems, so the prediction is pessimistic.  Returns (a, info)."""
    t0 = time.time()
    prof = {}
    for direction in (+1, -1):
        p = weight_profile(tr, direction, min(2, probe), backend)
        if probe > 2 and len(p) > 2 and p[1] > 0 and p[2] * p[2] / p[1] < budget:
            p = weight_profile(tr, direction, probe, backend)
        prof[direction] = p

    def extend(p, upto):
        p = list(p)
        r = p[-1] / p[-2] if len(p) > 1 and p[-2] > 0 else 1.0
        while len(p) <= upto:
            p.append(p[-1] * max(r, 1.0))
        return p

    F, B = extend(prof[+1], K), extend(prof[-1], K)
    costs = {a: sum(F[:a]) + F[a - 1] + 2 * sum(B[:K - a + 1]) for a in range(1, K + 1)}
    a = min(costs, key=costs.get)
    return a, {"forward_profile": [float(x) for x in prof[+1]], "backward_profile": [float(x) for x in prof[-1]],
               "predicted_work": {int(k): float(v) for k, v in costs.items()}, "probe_seconds": time.time() - t0}


def cut_profiles(tr, direction, cap, backend="c"):
    """States of each weight <= cap at every cut (array (N + 1, cap + 1)) of a sweep keeping weights <= cap."""
    sw = Sweep(tr, direction, cap, cap, use_h=False, backend=backend)
    c0, tab = sw.first()
    out = np.zeros((tr.N + 1, cap + 1))
    out[c0, 0] = 1
    for c, tab, _, _ in sw._iter(c0, tab, tr.N if direction > 0 else 0):
        vals = tab.T[tab.T != INF] if isinstance(tab, Dense) else sw.be.arrays(tab)[1]
        out[c] = np.bincount(vals, minlength=cap + 1)[:cap + 1]
    return out


def choose_schedule(tr, K, backend="c", probe=3, budget=2e9, window=100):
    """A split a(c) per cut, non-increasing, minimising the predicted work

        sum_c  F_c(<= a(c) - 1) + F_c(a(c) - 1) + 2 B_c(<= K - a(c)),

    with F_c(w), B_c(w) the forward and backward states of weight w at cut c: measured up to weight `probe` and
    extrapolated with the growth factor of the last two weights over a window of cuts (a dynamic programme over
    the cuts and the values of a).  Returns (schedule, info)."""
    t0 = time.time()
    prof = {}
    for direction in (+1, -1):
        p = cut_profiles(tr, direction, min(2, probe), backend)
        tot = p.sum(axis=0)
        if probe > 2 and tot[1] > 0 and tot[2] * tot[2] / tot[1] < budget:
            p = cut_profiles(tr, direction, probe, backend)
        prof[direction] = p

    def wsum(x):                                       # sums over the window of cuts around each cut
        cs = np.concatenate([[0.0], np.cumsum(x)])
        idx = np.arange(x.size)
        return cs[np.minimum(x.size, idx + window + 1)] - cs[np.maximum(0, idx - window)]

    def extend(p):
        top = p.shape[1] - 1
        if top >= K:
            return p[:, :K + 1]
        hi = wsum(p[:, top])
        lo = wsum(p[:, top - 1]) if top >= 1 else hi
        r = np.where(lo > 0, hi / np.maximum(lo, 1e-300), 1.0)
        r = np.maximum(r, 1.0)
        cols = [p[:, w] for w in range(top + 1)]
        while len(cols) <= K:
            cols.append(cols[-1] * r)
        return np.stack(cols, axis=1)

    F, B = extend(prof[+1]), extend(prof[-1])
    cF, cB = np.cumsum(F, axis=1), np.cumsum(B, axis=1)
    n = tr.N + 1
    cost = np.zeros((n, K + 1))
    for a in range(1, K + 1):
        cost[:, a] = cF[:, a - 1] + F[:, a - 1] + 2 * cB[:, K - a]
    cost[:, 0] = np.inf
    # best[c, a] = least cost of cuts 0..c with a(c) = a; a(c) <= a(c - 1)
    best = np.empty((n, K + 1))
    arg = np.zeros((n, K + 1), dtype=np.int64)
    best[0] = cost[0]
    for c in range(1, n):
        # suffix minimum over a' >= a of best[c - 1, a']
        prev = best[c - 1]
        suf = np.minimum.accumulate(prev[::-1])[::-1]
        sarg = np.empty(K + 1, dtype=np.int64)
        m, ai = np.inf, K
        for a in range(K, -1, -1):
            if prev[a] < m:
                m, ai = prev[a], a
            sarg[a] = ai
        best[c] = cost[c] + suf
        arg[c] = sarg
    a = int(np.argmin(best[n - 1]))
    sched = [0] * n
    for c in range(n - 1, -1, -1):
        sched[c] = a
        if c:
            a = int(arg[c, a])
    uniform = {a: float(cost[:, a].sum()) for a in range(1, K + 1)}
    return sched, {"predicted_work": float(best[n - 1].min()), "uniform_predicted_work": uniform,
                   "schedule": _runs(sched), "forward_profile": prof[+1].sum(axis=0).tolist(),
                   "backward_profile": prof[-1].sum(axis=0).tolist(), "probe_seconds": time.time() - t0}


# ---------------------------------------------------------------------- one query at one threshold
def query(tr, K, mode="mitm", split=None, use_h=True, witness=True, lower=0, every=None, backend="numpy",
          dense=None, dense_max=1 << 30, log=None, max_states=None, deadline=None):
    """Least weight of a solution of the trellis' query if it is <= K (else None), with per-cut statistics and a
    witness (columns of the problem).  lower: a known lower bound; reaching it stops the sweep.  max_states,
    deadline (time.monotonic()): raise BudgetExceeded beyond them.

    mode "forward": one truncated sweep (weights <= K).

    mode "mitm", with a split a(c) per cut, non-increasing in c: a backward sweep keeping weights <= K - a(c) at
    cut c, then a forward sweep keeping weights <= a(c) - 1, whose new or improved states (weights <= a(c)) are
    joined with the backward table at every cut; where a drops, the whole forward table is joined once more
    before it is cut down.  split: an int (the same a at every cut; default K // 2 + 1), "auto" (choose_split),
    "schedule" (choose_schedule) or a list of N + 1 values.

    Why every solution e of weight w <= K is seen.  Let f(c) = |e ∩ [0, c)|, lo(c) = w - (K - a(c)), hi(c) = a(c).
    A join at c of all forward states of weight <= hi(c) with all backward states of weight <= K - a(c) would see
    e iff lo(c) <= f(c) <= hi(c).  Both bounds fall with c while f rises by steps of one, from f(0) = 0 to
    f(N) = w, and lo(c) <= hi(c).  If f(0) >= lo(0) the cut 0 sees e.  Otherwise take the last cut c with
    f(c) < lo(c): then f(c + 1) <= f(c) + 1 <= lo(c) <= a(c) and f(c + 1) >= lo(c + 1).  If a(c + 1) = a(c), e's
    left part at c + 1 is within the cap; if a dropped, its weight is <= a(c), the old cap, and the join of the
    changed states and of the whole old table covers it.  The joins at a cut of only the new or improved forward
    states lose nothing: a state carried unchanged from cut c' was joined there with a backward table that holds,
    for the same right part, a value no larger (when the backward cap is the same, i.e. a did not drop in
    between; where it dropped, the whole table was joined).  The stored values are exact for the states on
    solutions of weight <= K because the caps never grow in a sweep's own direction (module docstring)."""
    t0 = time.time()
    rec = {"K": K, "mode": mode, "use_h": bool(use_h), "value": None, "witness": None, "width": max(tr.width),
           "backend": backend if isinstance(backend, str) else backend.name}
    bname = backend if isinstance(backend, str) else backend.name

    def new_be():
        return BACKENDS[backend](tr) if isinstance(backend, str) else backend.__class__(tr)

    be = new_be()
    if mode == "forward":
        fw = Sweep(tr, +1, K, K, use_h, every, backend=be, dense=dense, dense_max=dense_max, max_states=max_states,
                   deadline=deadline)
        fw.run()
        tab = fw.ckpt[tr.N]
        rec.update(forward_counts=fw.counts, peak_states=fw.peak, peak_table_bytes=fw.peak_bytes,
                   sweep_seconds=time.time() - t0, steps=fw.steps_done, dense_cuts=fw.dense_cuts)
        v = be.lookup(tab, 0)
        if v != INF:
            rec["value"] = v
            if witness:
                t1 = time.time()
                rec["witness"] = sorted(fw.traceback(tr.N, 0, v))
                rec["traceback_seconds"] = time.time() - t1
        rec["seconds"] = time.time() - t0
        return rec
    predicted = None
    if split == "auto":
        split, rec["split_choice"] = choose_split(tr, K, bname)
        predicted = rec["split_choice"]["predicted_work"][split]
    elif split == "schedule":
        split, rec["split_choice"] = choose_schedule(tr, K, bname)
        predicted = rec["split_choice"]["predicted_work"]
    if split is None:
        split = K // 2 + 1
    sched = [max(1, min(int(x), K)) for x in split] if isinstance(split, (list, tuple)) else \
        [max(1, min(int(split), K))] * (tr.N + 1)
    assert len(sched) == tr.N + 1 and all(x >= y for x, y in zip(sched, sched[1:])), "split must not increase"
    bw = Sweep(tr, -1, K, use_h=use_h, every=every, backend=be, dense=dense, dense_max=dense_max,
               max_states=max_states, deadline=deadline, caps=[K - x for x in sched])
    if log:
        log("K=%d split a=%s: backward sweep (weights <= %s)%s" % (
            K, _runs(sched), _runs([K - x for x in sched]), "" if predicted is None else
            ", predicted work %.3g" % predicted))
    bw.run()
    t1 = time.time()
    if log:
        log("backward sweep done: %.1f s, peak %d states, %.3g states in all" % (t1 - t0, bw.peak, sum(bw.counts)))
    fw = Sweep(tr, +1, K, use_h=use_h, every=bw.every, frontier=True, backend=new_be(), max_states=max_states,
               deadline=deadline, caps=sched)
    best = [None]
    cache = {}
    joins = [0]
    last = [time.time()]

    def join(c, tab, ch, extra):
        if log and time.time() - last[0] > 60:
            last[0] = time.time()
            log("forward cut %d/%d, %d states, %.0f s" % (c, tr.N, fw.be.size(tab), last[0] - t1))
        for part in (ch, extra):
            if part is None or not be.changed_size(part):
                continue
            joins[0] += be.changed_size(part)
            r = be.join(part, bw.table(c, cache), tr.tmask[c])
            if r is not None and (best[0] is None or r[0] < best[0][0]):
                best[0] = (r[0], c) + tuple(r[1:])
        return best[0] is not None and best[0][0] <= max(lower, 0)

    fw.run(on_cut=join)
    cache.clear()
    rec.update(forward_counts=fw.counts, backward_counts=bw.counts, changed_counts=fw.changed_counts,
               peak_states=max(fw.peak, bw.peak), peak_table_bytes=fw.peak_bytes + bw.peak_bytes,
               backward_seconds=t1 - t0, forward_seconds=time.time() - t1,
               split=sched[0] if len(set(sched)) == 1 else _runs(sched), split_values=sched, joined=joins[0],
               steps=fw.steps_done + bw.steps_done, dense_cuts=bw.dense_cuts)
    if best[0] is not None and best[0][0] <= K:
        value, c, sl, fl, sr = best[0]
        rec["value"], rec["join_cut"] = value, c
        if witness:
            t2 = time.time()
            cols = fw.traceback(c, sl, fl) + bw.traceback(c, sr, value - fl)
            rec["witness"] = sorted(cols)
            rec["traceback_seconds"] = time.time() - t2
    rec["seconds"] = time.time() - t0
    return rec


def _runs(x):
    """A per-cut list as 'value' or 'value@cut,value@cut,...' at the cuts where it changes."""
    out = [(v, c) for c, v in enumerate(x) if c == 0 or v != x[c - 1]]
    return str(out[0][0]) if len(out) == 1 else ",".join("%d@%d" % vc for vc in out)


# ---------------------------------------------------------------------- distance
def default_order(p, seeds=2):
    from . import auto
    return auto.best_order(p, seeds=seeds)[0]


def distance(p, order=None, start=1, kmax=64, mode="mitm", use_h=True, witness=True, log=None, every=None,
             backend="numpy", dense=None, split=None):
    """Exact distance by iterative deepening of the threshold K from `start`, which must be a lower bound (each
    threshold that fails for every observable proves the next one).  Returns a dict with the distance (None if
    none <= kmax), a verified witness and one record per (threshold, observable)."""
    t0 = time.time()
    order = default_order(p) if order is None else order
    trs = [Trellis.for_query(p, i, order) for i in range(p.nobs)]
    out = {"distance": None, "witness": None, "runs": [], "lower_bound": start,
           "order_cut_rank": max((max(t.width) for t in trs if t.feasible), default=0)}
    for K in range(start, kmax + 1):
        best = None
        for i, tr in enumerate(trs):
            if not tr.feasible:
                continue
            # every threshold below K failed for all observables, so d >= K: a value K is optimal
            r = query(tr, K, mode=mode, use_h=use_h, witness=witness, lower=K, every=every, backend=backend,
                      dense=dense, split=split(K) if callable(split) else split)
            r["obs"] = i
            out["runs"].append(summary(r))
            if log:
                log("  K=%d obs %d: value %s peak %d states %.2fs" % (K, i, r["value"], r["peak_states"],
                                                                       r["seconds"]))
            if r["value"] is not None and (best is None or r["value"] < best["value"]):
                best = r
                if r["value"] <= K:
                    break
        if best is not None:
            out["distance"] = best["value"]
            if witness:
                cols = best["witness"]
                s = lg = 0
                for j in cols:
                    s ^= p.h[j]
                    lg ^= p.l[j]
                assert s == 0 and lg != 0 and len(cols) == best["value"] == len(set(cols)), "witness check failed"
                out["witness"] = cols
            break
        out["lower_bound"] = K + 1
    out["seconds"] = time.time() - t0
    return out


def summary(r):
    """A query record without the per-cut arrays (their totals instead)."""
    out = {k: v for k, v in r.items() if not k.endswith("_counts") and k not in ("witness", "split_values")}
    for k in ("forward_counts", "backward_counts", "changed_counts"):
        if k in r:
            out[k.replace("_counts", "_states_total")] = int(sum(r[k]))
    return out
