"""Linear rank decomposition (syndrome trellis) of a distance problem.

For a column order, the interface at cut i is  span(past) ∩ span(future),
of dimension  λ_i = rank(past) + rank(future) - rank(all)  (the cut rank /
connectivity function of the column matroid).  Bringing the row space into
*minimal span form* gives a row basis in which exactly λ_i rows are "active"
(started, not yet ended) at cut i, so the DP state is simply the vector of
their partial parities.  A min-plus sweep over this trellis is the Viterbi
algorithm; it is the linear-tree special case of min-plus Rank DP.
"""
from __future__ import annotations

from dataclasses import dataclass


def lowbit(x):
    return (x & -x).bit_length() - 1


def rank_profile(cols, order):
    """Prefix ranks r[i] = rank(cols[order[:i]]) for i = 0..N."""
    basis = {}
    out = [0]
    r = 0
    for j in order:
        v = cols[j]
        while v:
            b = v.bit_length() - 1
            w = basis.get(b)
            if w is None:
                basis[b] = v
                r += 1
                break
            v ^= w
        out.append(r)
    return out


def cut_profile(cols, order):
    """λ_i for cuts i = 0..N (cut i separates order[:i] from order[i:])."""
    pre = rank_profile(cols, order)
    suf = rank_profile(cols, order[::-1])[::-1]
    total = pre[-1]
    return [a + b - total for a, b in zip(pre, suf)]


def rows_from_columns(cols, order, nrows):
    """Row r as an int bitmask over column *positions* in the given order."""
    rows = [0] * nrows
    for pos, j in enumerate(order):
        v = cols[j]
        bit = 1 << pos
        while v:
            low = v & -v
            rows[low.bit_length() - 1] |= bit
            v ^= low
    return rows


def minimal_span_form(rows):
    """Row-reduce to distinct starts (lowest set bit) and distinct ends
    (highest set bit).  Dependent rows vanish.  Returns the new rows."""
    by_start = {}
    for r in rows:
        while r:
            s = lowbit(r)
            q = by_start.get(s)
            if q is None:
                by_start[s] = r
                break
            # keep the row that ends earlier, continue with the sum
            if r.bit_length() < q.bit_length():
                by_start[s] = r
                r, q = q, r
            r ^= q
    rows = list(by_start.values())
    # distinct ends: when two rows share an end, the one starting earlier
    # absorbs the other (its start is unchanged, its end moves left)
    by_end = {}
    stack = sorted(rows, key=lowbit, reverse=True)  # latest start first
    for r in stack:
        while True:
            e = r.bit_length()
            q = by_end.get(e)
            if q is None:
                by_end[e] = r
                break
            if lowbit(q) > lowbit(r):
                r ^= q
            else:
                by_end[e] = r
                r = q ^ r
    out = list(by_end.values())
    starts = [lowbit(r) for r in out]
    ends = [r.bit_length() for r in out]
    assert len(set(starts)) == len(out) and len(set(ends)) == len(out)
    return out


def reduce_target_row(lrow, hrows):
    """Shorten the span of the target-1 row using the constraint rows (the
    reverse operation is not allowed).  Returns 0 if it is a combination of
    constraint rows, i.e. the query is infeasible."""
    by_start = {lowbit(r): r for r in hrows}
    by_end = {r.bit_length(): r for r in hrows}
    while lrow:
        q = by_start.get(lowbit(lrow))
        if q is None:
            break
        lrow ^= q
    while lrow:
        q = by_end.get(lrow.bit_length())
        if q is None or lowbit(q) < lowbit(lrow):
            break
        lrow ^= q
        # the start may now coincide with a constraint row start again
        while lrow:
            q2 = by_start.get(lowbit(lrow))
            if q2 is None:
                break
            lrow ^= q2
    return lrow


@dataclass
class Plan:
    ops: list          # ("expand",) | ("update", mask) | ("select", pos, target)
    peak_bits: int     # log2 of the largest table
    widths: list       # active rows after each column
    ncols: int
    feasible: bool = True

    def work(self):
        """Total number of table entries touched by updates (in units of states)."""
        tot = 0
        bits = 0
        for op in self.ops:
            if op[0] == "expand":
                bits += 1
            elif op[0] == "select":
                bits -= 1
            else:
                tot += 1 << bits
        return tot


def make_plan(hrows, lrow, ncols):
    """DP schedule for constraint rows (target 0) and one target-1 row."""
    if lrow == 0:
        return Plan([], 0, [], ncols, feasible=False)
    rows = [(r, 0) for r in hrows] + [(lrow, 1)]
    start_at = {}
    end_at = {}
    for idx, (r, _) in enumerate(rows):
        start_at.setdefault(lowbit(r), []).append(idx)
        end_at.setdefault(r.bit_length() - 1, []).append(idx)
    active = []          # row indices; list position = table bit
    ops = []
    widths = []
    peak = 0
    for j in range(ncols):
        for idx in start_at.get(j, ()):
            active.append(idx)
            ops.append(("expand",))
        peak = max(peak, len(active))
        mask = 0
        for pos, idx in enumerate(active):
            if (rows[idx][0] >> j) & 1:
                mask |= 1 << pos
        if mask:
            ops.append(("update", mask))
        else:
            # column touches no active row: it is a free zero-syndrome fault,
            # never useful for a minimum
            pass
        ending = sorted((active.index(idx) for idx in end_at.get(j, ())), reverse=True)
        for pos in ending:
            ops.append(("select", pos, rows[active[pos]][1]))
            active.pop(pos)
        widths.append(len(active))
    assert not active
    return Plan(ops, peak, widths, ncols)


def build_plan(h, l, obs_mask, order, nrows):
    """Plan for the query  H e = 0, (obs_mask · L) e = 1  with given column order."""
    hrows = minimal_span_form(rows_from_columns(h, order, nrows))
    lrow = 0
    for pos, j in enumerate(order):
        if bin(l[j] & obs_mask).count("1") & 1:
            lrow |= 1 << pos
    lrow = reduce_target_row(lrow, hrows)
    return make_plan(hrows, lrow, len(order))
