"""The two graph bounds of arXiv:2610.03682 (section S10) for a semi-hyperbolic color code:

  d_string  twice the shortest homologically non-trivial cycle of one edge colour (upper bound)
  d_res     median over the three colours of the systole of the restricted lattice (lower bound)

They are recomputed here only to identify a rebuilt tiling with a row of the paper: a row that the
paper lists with the range a..b must have (d_res, d_string) = (a, b).  The exact distance comes from
papers/hyperbolic_run.py, not from this file.

Complex used: the fine triangulation (vertices = checks, triangles = qubits).  Homology labels come
from a tree-cotree decomposition: a spanning tree T of the triangulation graph, a spanning tree T* of
the dual graph on the edges outside T; every remaining edge x gives one basis cycle (its fundamental
cycle in T) and one basis cocycle (the edges crossed by its fundamental cycle in T*).

Usage: python papers/hyperbolic_bounds.py name [name ...]        (names of papers/hyperbolic.CODES)
"""
import sys
from collections import deque

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import hyperbolic as H


def bits(x):
    while x:
        low = x & -x
        yield low.bit_length() - 1
        x ^= low


class _UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, i):
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def join(self, i, j):
        i, j = self.find(i), self.find(j)
        if i != j:
            self.p[max(i, j)] = min(i, j)


def triangulation(name):
    """The fine triangulation with explicit edges (small tilings have parallel edges, so an edge is
    not its pair of end points).  Same geometry and qubit numbering as hyperbolic._fine.
    Returns nv, ne, triangles as (vertex triple, edge triple), by_edge = [two triangles per edge],
    edge end points, vertex permutations and qubit permutations of the symmetry generators."""
    code = next(c for c in H.CODES if c["name"] == name)
    triple, L = H.tiling(code["tiling"]), code["L"]
    N, gens = triple.N, triple.generators
    coords = [(i, j, L - i - j) for i in range(L + 1) for j in range(L - i + 1)]
    pos = {v: i for i, v in enumerate(coords)}
    m = len(coords)
    small = []
    for i in range(L):
        for j in range(L - i):
            small.append((pos[i, j, L - i - j], pos[i + 1, j, L - i - j - 1], pos[i, j + 1, L - i - j - 1]))
            if i + j <= L - 2:
                small.append((pos[i + 1, j, L - i - j - 1], pos[i, j + 1, L - i - j - 1], pos[i + 1, j + 1, L - i - j - 2]))
    ledges = sorted({tuple(sorted((t[x], t[(x + 1) % 3]))) for t in small for x in range(3)})
    lindex = {e: i for i, e in enumerate(ledges)}
    me = len(ledges)
    vuf, euf = _UF(N * m), _UF(N * me)
    for g in range(N):
        for side, perm in enumerate(gens):
            h = perm[g]
            if g < h:
                for i, v in enumerate(coords):
                    if v[side] == 0:
                        vuf.join(g * m + i, h * m + i)
                for i, (u, w) in enumerate(ledges):
                    if coords[u][side] == 0 and coords[w][side] == 0:
                        euf.join(g * me + i, h * me + i)
    vroot = sorted({vuf.find(i) for i in range(N * m)})
    vid = {r: i for i, r in enumerate(vroot)}
    vertex = [vid[vuf.find(i)] for i in range(N * m)]
    eroot = sorted({euf.find(i) for i in range(N * me)})
    eid = {r: i for i, r in enumerate(eroot)}
    edge = [eid[euf.find(i)] for i in range(N * me)]
    tri, by_edge, ends = [], [[] for _ in eroot], [None] * len(eroot)
    for g in range(N):
        for t in small:
            vs = tuple(vertex[g * m + x] for x in t)
            es = []
            for x in range(3):
                le = lindex[tuple(sorted((t[x], t[(x + 1) % 3])))]
                e = edge[g * me + le]
                es.append(e)
                by_edge[e].append(len(tri))
                ends[e] = (vertex[g * m + t[x]], vertex[g * m + t[(x + 1) % 3]])
            tri.append((vs, tuple(es)))
    assert all(len(x) == 2 for x in by_edge), "not a closed surface"
    vperms, qperms = [], []
    for left in triple.left_generators():
        vp = [-1] * len(vroot)
        for g in range(N):
            for i in range(m):
                vp[vertex[g * m + i]] = vertex[left[g] * m + i]
        vperms.append(vp)
        qperms.append([left[q // (L * L)] * L * L + q % (L * L) for q in range(N * L * L)])
    return len(vroot), len(eroot), tri, by_edge, ends, vperms, qperms


def three_colouring(nv, tri, by_edge):
    colour = [-1] * nv
    for i, v in enumerate(tri[0][0]):
        colour[v] = i
    todo = deque([0])
    seen = {0}
    while todo:
        q = todo.popleft()
        vs, es = tri[q]
        for x in range(3):
            z = vs[(x + 2) % 3]                    # vertex opposite the edge between vs[x], vs[x+1]
            for q2 in by_edge[es[x]]:
                if q2 == q:
                    continue
                vs2, es2 = tri[q2]
                y = es2.index(es[x])
                z2 = vs2[(y + 2) % 3]
                if colour[z2] == -1:
                    colour[z2] = colour[z]
                elif colour[z2] != colour[z]:
                    raise ValueError("triangulation is not three-colourable")
                for v_, c_ in ((vs2[y], None), (vs2[(y + 1) % 3], None)):
                    pass
                if q2 not in seen:
                    seen.add(q2)
                    todo.append(q2)
    assert -1 not in colour
    assert all(len({colour[v] for v in vs}) == 3 for vs, _ in tri)
    return colour


def tree_cotree(nv, ne, tri, by_edge, ends):
    """For every edge the label of basis cocycles through it (psi) and of basis cycles containing it
    (phi), as int bitmasks over the remaining edges (one per generator of H1)."""
    adj = [[] for _ in range(nv)]
    for i, (u, w) in enumerate(ends):
        adj[u].append((w, i))
        adj[w].append((u, i))
    parent, pedge, depth = [-1] * nv, [-1] * nv, [0] * nv
    in_tree = [False] * ne
    seen = [False] * nv
    seen[0] = True
    todo = deque([0])
    while todo:
        u = todo.popleft()
        for w, i in adj[u]:
            if not seen[w]:
                seen[w] = True
                parent[w], pedge[w], depth[w] = u, i, depth[u] + 1
                in_tree[i] = True
                todo.append(w)
    assert all(seen)
    nq = len(tri)
    dadj = [[] for _ in range(nq)]
    for i in range(ne):
        if not in_tree[i]:
            a, b = by_edge[i]
            dadj[a].append((b, i))
            dadj[b].append((a, i))
    dparent, dpedge, ddepth = [-1] * nq, [-1] * nq, [0] * nq
    in_cotree = [False] * ne
    dseen = [False] * nq
    dseen[0] = True
    todo = deque([0])
    while todo:
        a = todo.popleft()
        for b, i in dadj[a]:
            if not dseen[b]:
                dseen[b] = True
                dparent[b], dpedge[b], ddepth[b] = a, i, ddepth[a] + 1
                in_cotree[i] = True
                todo.append(b)
    assert all(dseen)
    rest = [i for i in range(ne) if not in_tree[i] and not in_cotree[i]]
    psi, phi = [0] * ne, [0] * ne
    for j, x in enumerate(rest):
        bit = 1 << j
        u, w = ends[x]                             # basis cycle: x plus the tree path between its ends
        phi[x] |= bit
        while u != w:
            if depth[u] < depth[w]:
                u, w = w, u
            phi[pedge[u]] ^= bit
            u = parent[u]
        a, b = by_edge[x]                          # basis cocycle: edges crossed by the dual cycle of x
        psi[x] |= bit
        while a != b:
            if ddepth[a] < ddepth[b]:
                a, b = b, a
            psi[dpedge[a]] ^= bit
            a = dparent[a]
    return psi, phi, len(rest)


def systole(n, arcs, roots, cap=10 ** 9):
    """Shortest closed walk with non-zero total label through one of the roots.  arcs[u] = list of
    (v, weight, label) with weights 0 or 2 or 1; shortest-path tree by 0-1 breadth-first search, then
    every edge closes a candidate cycle with the two tree paths (the non-trivial ones are kept)."""
    best = cap
    for r in roots:
        dist, lab = {r: 0}, {r: 0}
        done = set()
        todo = deque([r])
        while todo:
            u = todo.popleft()
            if u in done:
                continue
            done.add(u)
            du = dist[u]
            if 2 * du >= best:
                break
            for v, w, l in arcs[u]:
                if v not in dist or du + w < dist[v]:
                    dist[v], lab[v] = du + w, lab[u] ^ l
                    (todo.append if w else todo.appendleft)(v)
        for u in done:
            du, lu = dist[u], lab[u]
            for v, w, l in arcs[u]:
                if v in dist and (lab[v] ^ lu ^ l) and du + dist[v] + w < best:
                    best = du + dist[v] + w
    return best


def orbit_representatives(n, perms):
    seen, reps = [False] * n, []
    for s in range(n):
        if seen[s]:
            continue
        reps.append(s)
        seen[s] = True
        todo = [s]
        while todo:
            u = todo.pop()
            for p in perms:
                v = p[u]
                if not seen[v]:
                    seen[v] = True
                    todo.append(v)
    return reps


def bounds(name):
    nv, ne, tri, by_edge, ends, vperms, qperms = triangulation(name)
    colour = three_colouring(nv, tri, by_edge)
    psi, phi, b = tree_cotree(nv, ne, tri, by_edge, ends)
    nq = len(tri)
    res, string = [], []
    for c in range(3):
        # restricted lattice: vertices of the other two colours, edges between them
        arcs = [[] for _ in range(nv)]
        for i, (u, w) in enumerate(ends):
            if colour[u] != c and colour[w] != c:
                arcs[u].append((w, 1, psi[i]))
                arcs[w].append((u, 1, psi[i]))
        roots = [v for v in orbit_representatives(nv, vperms) if colour[v] != c]
        res.append(systole(nv, arcs, roots))
        # coloured cycles of the colour-code tiling: dual graph, weight 2 on edges of colour c
        darcs = [[] for _ in range(nq)]
        for i, (u, w) in enumerate(ends):
            a, d = by_edge[i]
            wt = 2 if (colour[u] != c and colour[w] != c) else 0
            darcs[a].append((d, wt, phi[i]))
            darcs[d].append((a, wt, phi[i]))
        string.append(systole(nq, darcs, orbit_representatives(nq, qperms)))
    return dict(name=name, n=nq, homology_rank=b, restricted_systoles=res, d_res=sorted(res)[1],
                string_by_colour=string, d_string=min(string))


if __name__ == "__main__":
    for name in sys.argv[1:]:
        r = bounds(name)
        print("%s: n=%d rank H1=%d  restricted systoles %s  d_res=%d  d_string=%d (by colour %s)" % (
            r["name"], r["n"], r["homology_rank"], r["restricted_systoles"], r["d_res"], r["d_string"],
            r["string_by_colour"]), flush=True)
