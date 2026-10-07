"""Distance problems extracted from Stim circuits.

A problem is a list of distinct columns.  Column j has a detector part
``h[j]`` (Python int bitmask over rows) and a logical part ``l[j]`` (bitmask
over observables).  Every column costs one fault.  The distance is

    d = min { |e| : XOR_j e_j h[j] = 0,  XOR_j e_j l[j] != 0 }.

For circuits whose noise channels have full Pauli support at each location
(depolarizing channels, X/Z flips, measurement flips), this DEM-mechanism
distance equals the number of faulty physical locations: a location's
outcomes are closed under multiplication, so two mechanisms taken from one
location can always be replaced by one, and conversely every single-location
outcome is a mechanism.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import stim


@dataclass
class Problem:
    name: str
    nrows: int
    nobs: int
    h: list            # detector bitmask per column
    l: list            # observable bitmask per column
    row_meta: list     # per-row metadata (coords or check id)
    col_meta: list = field(default_factory=list)   # per-column provenance
    notes: dict = field(default_factory=dict)
    image: list = None  # for relaxations: image of each parent column

    @property
    def ncols(self):
        return len(self.h)

    def check(self, support, obs_bit=None):
        """Return (syndrome, logical) of a set of columns."""
        s = 0
        lg = 0
        for j in support:
            s ^= self.h[j]
            lg ^= self.l[j]
        return s, lg


def dedupe(h, l, meta=None):
    """Drop all-zero columns and merge identical (h, l) columns."""
    seen = {}
    oh, ol, om = [], [], []
    for j, (a, b) in enumerate(zip(h, l)):
        if a == 0 and b == 0:
            continue
        key = (a, b)
        if key in seen:
            if meta is not None:
                om[seen[key]].append(meta[j])
            continue
        seen[key] = len(oh)
        oh.append(a)
        ol.append(b)
        if meta is not None:
            om.append([meta[j]])
    return oh, ol, om


def load_dem_problem(path, name=None):
    """Full undecomposed DEM of a Stim circuit as a Problem."""
    circuit = stim.Circuit.from_file(path)
    dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=True)
    coords = circuit.get_detector_coordinates()
    h, l = [], []
    for inst in dem:
        if inst.type != "error":
            continue
        a = b = 0
        for t in inst.targets_copy():
            if t.is_relative_detector_id():
                a ^= 1 << t.val
            elif t.is_logical_observable_id():
                b ^= 1 << t.val
        h.append(a)
        l.append(b)
    n_raw = len(h)
    meta = list(range(n_raw))
    h, l, cm = dedupe(h, l, meta)
    row_meta = [tuple(coords.get(i, ())) for i in range(circuit.num_detectors)]
    return Problem(name or path, circuit.num_detectors, circuit.num_observables,
                   h, l, row_meta, cm, {"raw_mechanisms": n_raw})


def _project(mask, rowmap):
    out = 0
    while mask:
        low = mask & -mask
        r = rowmap.get(low.bit_length() - 1)
        if r is not None:
            out ^= 1 << r
        mask ^= low
    return out


def project_rows(p: Problem, groups, name, row_meta, note=None):
    """Relaxation: new row g is the XOR of the old rows listed in groups[g].

    Rows not listed are dropped.  Each old row may belong to at most one group.
    Any solution of ``p`` is a solution of the result, so the result's distance
    is a lower bound on that of ``p``.
    """
    rowmap = {}
    for g, rows in enumerate(groups):
        for r in rows:
            assert r not in rowmap
            rowmap[r] = g
    cache = {}
    h = []
    for a in p.h:
        v = cache.get(a)
        if v is None:
            v = cache[a] = _project(a, rowmap)
        h.append(v)
    hh, ll, cm = dedupe(h, p.l, list(range(p.ncols)))
    notes = dict(p.notes)
    if note:
        notes.update(note)
    out = Problem(name, len(groups), p.nobs, hh, ll, row_meta, cm, notes)
    out.image = h          # relaxed syndrome of every column of p (before dedupe)
    return out


def sector_rows(p: Problem, high=None):
    """Split detectors into the two CSS types using the 4th detector coordinate
    (>= 3 for one type, < 3 for the other).

    Returns the rows of the memory-basis type.  By default that is the type
    present at t=0; circuits that also have detectors of the other type in the
    first round (e.g. flag measurements) pass `high` explicitly.
    """
    if high is None:
        t0_types = {m[3] >= 3 for m in p.row_meta if m[2] == 0}
        assert len(t0_types) == 1, "expected one detector type at t=0"
        high = t0_types.pop()
    return [i for i, m in enumerate(p.row_meta) if (m[3] >= 3) == high]


def sector_problem(p: Problem, high=None):
    """Keep only detectors of the memory-basis type.

    This is a relaxation in general (lower bound).  ``sector_is_exact`` checks
    the condition under which it preserves the distance exactly.
    """
    rows = sector_rows(p, high)
    groups = [[r] for r in rows]
    q = project_rows(p, groups, p.name + ":sector", [p.row_meta[r] for r in rows],
                     {"relaxation": "sector"})
    q.notes["sector_rows"] = rows
    return q


def sector_is_exact(p: Problem, q: Problem):
    """True if every sector column is itself a full-DEM column with no
    detectors outside the sector, i.e. sector solutions lift at equal weight."""
    rows = q.notes["sector_rows"]
    full = {(a, b) for a, b in zip(p.h, p.l)}
    for a, b in zip(q.h, q.l):
        lifted = 0
        m = a
        while m:
            low = m & -m
            lifted ^= 1 << rows[low.bit_length() - 1]
            m ^= low
        if (lifted, b) not in full:
            return False
    return True


def collapse_time(q: Problem):
    """Relaxation: XOR all detectors of the same check over time.

    The resulting rows say that the accumulated data error seen by the final
    readout commutes with every check; all information about *when* a fault
    happened is discarded.  Its distance lower-bounds the circuit distance for
    any number of rounds.
    """
    by_check = {}
    for i, m in enumerate(q.row_meta):
        by_check.setdefault((m[0], m[1]), []).append(i)
    keys = sorted(by_check)
    groups = [by_check[k] for k in keys]
    return project_rows(q, groups, q.name + ":collapsed", keys, {"relaxation": "sector+time-collapse"})


def window_problem(q: Problem, t_lo, t_hi, name=None):
    """Restriction: keep only columns whose detectors all lie in rounds
    [t_lo, t_hi] (a sub-experiment).  Solutions are solutions of ``q``, so the
    result's distance is an upper bound."""
    ok_rows = 0
    for i, m in enumerate(q.row_meta):
        if t_lo <= m[2] <= t_hi:
            ok_rows |= 1 << i
    h, l, cm = [], [], []
    for j, (a, b) in enumerate(zip(q.h, q.l)):
        if a & ~ok_rows == 0:
            h.append(a)
            l.append(b)
            cm.append(j)
    # renumber the rows so that only detectors of the window remain
    rows = [i for i, m in enumerate(q.row_meta) if t_lo <= m[2] <= t_hi]
    rowmap = {r: i for i, r in enumerate(rows)}
    cache = {}
    hh = []
    for a in h:
        v = cache.get(a)
        if v is None:
            v = cache[a] = _project(a, rowmap)
        hh.append(v)
    return Problem(name or f"{q.name}:t{t_lo}-{t_hi}", len(rows), q.nobs, hh, l, [q.row_meta[r] for r in rows], cm,
                   dict(q.notes, restriction=f"rounds {t_lo}..{t_hi}"))


def fold_time(q: Problem, period):
    """Relaxation between the full problem and ``collapse_time``: XOR the
    detectors of each check over all rounds with the same  t mod period.

    period = 1 is the full collapse.  A larger period keeps more of the
    timing consistency (which round a check saw a fault in) while staying
    independent of the number of rounds.
    """
    by_key = {}
    for i, m in enumerate(q.row_meta):
        by_key.setdefault((m[0], m[1], int(m[2]) % period), []).append(i)
    keys = sorted(by_key)
    groups = [by_key[k] for k in keys]
    return project_rows(q, groups, f"{q.name}:fold{period}", keys,
                        {"relaxation": f"sector+time-fold-{period}"})


def observable_groups(p: Problem, size=64):
    """Split the observables into groups of at most `size`.  A fault set flips
    some observable iff it flips one in some group, so the distance of p is
    the minimum over the returned problems.  Columns that become identical
    within a group are merged (col_meta keeps all parents)."""
    out = []
    for lo in range(0, p.nobs, size):
        mask = ((1 << size) - 1) << lo
        l = [(b & mask) >> lo for b in p.l]
        hh, ll, cm = dedupe(p.h, l, list(range(p.ncols)))
        q = Problem(f"{p.name}:obs{lo}-{min(lo + size, p.nobs) - 1}", p.nrows, min(size, p.nobs - lo), hh, ll,
                    p.row_meta, cm, dict(p.notes, observable_offset=lo))
        out.append(q)
    return out
