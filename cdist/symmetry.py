"""Lattice translation symmetry of a distance problem.

If a translation g permutes the rows such that the column set is mapped to
itself, and the logical labels transform as  l(g c) = M l(c) + B h(c)  for
fixed matrices M, B, then g maps undetected logical fault sets to undetected
logical fault sets of the same weight.  A search may then assume that the
solution contains one fixed representative ("anchor") of the lowest-ranked
column orbit it touches.
"""
from __future__ import annotations


def _axis(vals):
    vals = sorted(set(vals))
    if len(vals) == 1:
        return vals[0], 1.0, 1
    step = min(b - a for a, b in zip(vals, vals[1:]))
    period = vals[-1] - vals[0] + step
    return vals[0], step, int(round(period / step))


def _apply(mask, perm, cache):
    v = cache.get(mask)
    if v is None:
        v = 0
        m = mask
        while m:
            low = m & -m
            v |= 1 << perm[low.bit_length() - 1]
            m ^= low
        cache[mask] = v
    return v


def _labels_consistent(p, colmap):
    """Check l(g c) = M l(c) + B h(c) for some M, B (GF(2) elimination)."""
    nb = p.nobs
    basis = {}
    for c in range(p.ncols):
        v = (p.h[c] << nb) | p.l[c]
        rhs = p.l[colmap[c]]
        while v:
            b = v.bit_length() - 1
            w = basis.get(b)
            if w is None:
                basis[b] = (v, rhs)
                break
            v ^= w[0]
            rhs ^= w[1]
        else:
            if rhs:
                return False
    return True


def translations(p):
    """Find the smallest row translation along each lattice axis (x, y detector
    coordinates) that is a symmetry of the problem.  Returns the generators,
    their column maps, and the column orbits (rank = orbit index, anchors =
    one representative per orbit)."""
    xs = [m[0] for m in p.row_meta]
    ys = [m[1] for m in p.row_meta]
    x0, sx, nx = _axis(xs)
    y0, sy, ny = _axis(ys)
    # rows are identified by (x, y, time/phase); further coordinates (e.g. a
    # colour annotation) carry no meaning for the fault model
    index = {tuple(m[:3]): i for i, m in enumerate(p.row_meta)}
    assert len(index) == p.nrows
    colindex = {}
    for j, a in enumerate(p.h):
        if a in colindex:
            return {"ok": False, "reason": "two columns share a syndrome"}
        colindex[a] = j

    def try_shift(dx, dy):
        perm = []
        for m in p.row_meta:
            x = x0 + ((m[0] - x0) / sx + dx) % nx * sx
            y = y0 + ((m[1] - y0) / sy + dy) % ny * sy
            t = index.get((x, y) + tuple(m[2:3]))
            if t is None:
                return None
            perm.append(t)
        cache = {}
        colmap = []
        for a in p.h:
            j = colindex.get(_apply(a, perm, cache))
            if j is None:
                return None
            colmap.append(j)
        if not _labels_consistent(p, colmap):
            return None
        return colmap

    # smallest shifts along each axis that are symmetries, plus mixed shifts
    gens = []
    for dx in range(1, nx + 1):
        cm = try_shift(dx, 0)
        if cm is not None:
            if dx < nx:
                gens.append(((dx, 0), cm))
            break
    for dy in range(1, ny + 1):
        cm = try_shift(0, dy)
        if cm is not None:
            if dy < ny:
                gens.append(((0, dy), cm))
            break
    # orbits by union-find over the generators
    parent = list(range(p.ncols))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for _, cm in gens:
        for c, d in enumerate(cm):
            ra, rb = find(c), find(d)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    roots = sorted({find(c) for c in range(p.ncols)})
    rank_of_root = {r: i for i, r in enumerate(roots)}
    rank = [rank_of_root[find(c)] for c in range(p.ncols)]
    sizes = {}
    for c in range(p.ncols):
        sizes[rank[c]] = sizes.get(rank[c], 0) + 1
    return {"ok": True, "generators": [g for g, _ in gens], "grid": (nx, ny),
            "rank": rank, "anchors": roots, "orbit_sizes": [sizes[i] for i in range(len(roots))],
            "colmaps": [cm for _, cm in gens]}


def from_row_perms(p, perms):
    """Symmetry from explicit candidate row permutations (perm[r] = image of
    row r).  Each candidate is kept only if it maps the column set to itself
    with consistent logical labels; the kept ones generate the orbits.
    Returns the same dictionary layout as `translations`."""
    colindex = {}
    for j, a in enumerate(p.h):
        if a in colindex:
            return {"ok": False, "reason": "two columns share a syndrome"}
        colindex[a] = j
    kept = []
    seen = set()
    for perm in perms:
        key = tuple(perm)
        if key in seen or all(i == x for i, x in enumerate(perm)):
            continue
        seen.add(key)
        cache = {}
        colmap = []
        ok = True
        for a in p.h:
            j = colindex.get(_apply(a, perm, cache))
            if j is None:
                ok = False
                break
            colmap.append(j)
        if ok and _labels_consistent(p, colmap):
            kept.append((key, colmap))
    parent = list(range(p.ncols))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for _, cm in kept:
        for c, d in enumerate(cm):
            ra, rb = find(c), find(d)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    roots = sorted({find(c) for c in range(p.ncols)})
    rank_of_root = {r: i for i, r in enumerate(roots)}
    rank = [rank_of_root[find(c)] for c in range(p.ncols)]
    sizes = {}
    for c in range(p.ncols):
        sizes[rank[c]] = sizes.get(rank[c], 0) + 1
    return {"ok": True, "generators": [f"perm{i}" for i in range(len(kept))] , "n_symmetries_kept": len(kept),
            "rank": rank, "anchors": roots, "orbit_sizes": [sizes[i] for i in range(len(roots))],
            "colmaps": [cm for _, cm in kept]}
