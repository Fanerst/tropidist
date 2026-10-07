"""Closed triangle-group color codes from arXiv:2610.03682.

No GAP or downloaded data are used. Points are triangles, generator actions
are right multiplication, and the commuting left actions supply symmetries.
Only ordered generators are identified in cover enumeration by default;
``uncolored=True`` also identifies permutations of equal-order side labels.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import combinations, permutations, product
import math

import numpy as np


@dataclass(frozen=True)
class Triple:
    generators: tuple
    orders: tuple = (4, 4, 4)
    name: str = "unnamed"

    @property
    def N(self):
        return len(self.generators[0])

    @property
    def orientable(self):
        parity = [-1] * self.N
        parity[0] = 0
        todo = deque([0])
        while todo:
            g = todo.popleft()
            for perm in self.generators:
                h = perm[g]
                if parity[h] < 0:
                    parity[h] = parity[g] ^ 1
                    todo.append(h)
                elif parity[h] == parity[g]:
                    return False
        return True

    def left_generators(self):
        return regular_left_generators(self)


def canonical_triple(generators, orders=(4, 4, 4), name="unnamed", uncolored=False):
    """Canonical rooted BFS Cayley graph; the root is immaterial for regular actions."""
    def ordered(gs, os):
        n = len(gs[0])
        old = [0]
        index = {0: 0}
        for g in old:
            for perm in gs:
                h = perm[g]
                if h not in index:
                    index[h] = len(old)
                    old.append(h)
        if len(old) != n:
            raise ValueError("generator action is not transitive")
        return tuple(tuple(index[p[g]] for g in old) for p in gs), tuple(os)
    if uncolored:
        candidates = [ordered(tuple(generators[i] for i in p), tuple(orders[i] for i in p))
                      for p in permutations(range(3)) if tuple(orders[i] for i in p) == tuple(orders)]
        gs, os = min(candidates)
    else:
        gs, os = ordered(generators, orders)
    return Triple(gs, os, name)


@lru_cache(maxsize=128)
def regular_left_generators(triple):
    """Direct regularity certificate, without enumerating N large permutations.

    Propagate each left generator from its image of 0 and verify that it
    commutes with all right generators. Their orbit of 0 must be all N points.
    A right stabilizer of 0 then fixes that entire orbit, hence is the identity:
    the generated permutation group has exactly N elements.
    """
    n, gs = triple.N, triple.generators
    if any(sorted(p) != list(range(n)) or any(p[p[i]] != i or p[i] == i for i in range(n))
           for p in gs):
        raise ValueError("generators must be fixed-point-free involutions")
    maps = []
    for generator in gs:
        image = [-1] * n
        image[0] = generator[0]
        todo = deque([0])
        while todo:
            g = todo.popleft()
            for p in gs:
                h, j = p[g], p[image[g]]
                if image[h] < 0:
                    image[h] = j
                    todo.append(h)
                elif image[h] != j:
                    raise ValueError("lift is transitive but not regular")
        if sorted(image) != list(range(n)):
            raise ValueError("left action is not a permutation")
        maps.append(tuple(image))
    orbit = {0}
    todo = deque([0])
    while todo:
        g = todo.popleft()
        for p in maps:
            if p[g] not in orbit:
                orbit.add(p[g])
                todo.append(p[g])
    if len(orbit) != n:
        raise ValueError("left action is not transitive")
    return tuple(maps)


def face_orbits(triple):
    out = []
    for x, y in ((0, 1), (1, 2), (2, 0)):
        unseen = set(range(triple.N))
        faces = []
        while unseen:
            start = min(unseen)
            face, g, side = [], start, x
            while True:
                face.append(g)
                g = triple.generators[side][g]
                side = y if side == x else x
                if g == start and side == x:
                    break
                if len(face) > triple.N * 2:
                    raise ValueError("invalid face walk")
            if len(set(face)) != len(face):
                raise ValueError("face has repeated vertices")
            unseen.difference_update(face)
            faces.append(tuple(face))
        out.append(tuple(faces))
    return tuple(out)


def validate_triple(triple):
    triple.left_generators()
    for faces, order in zip(face_orbits(triple), triple.orders):
        if any(len(face) != 2 * order for face in faces):
            raise ValueError("quotient is not smooth: pair order dropped")
    return True


def bolza():
    """The order-16 Pauli group i^phase X^x Z^z, a=X,b=Z,c=iXZ.

    Its three involutions anticommute pairwise, all pair products have order
    four, and cbabca=e. The even-word subgroup is Q8.
    """
    elements = list(product(range(4), range(2), range(2)))
    index = {g: i for i, g in enumerate(elements)}
    def mul(g, h):
        p, x, z = g
        q, y, w = h
        return ((p + q + 2 * z * y) % 4, x ^ y, z ^ w)
    generators = tuple(tuple(index[mul(g, h)] for g in elements)
                       for h in ((0, 1, 0), (0, 0, 1), (1, 1, 1)))
    triple = canonical_triple(generators, name="bolza")
    validate_triple(triple)
    for g in range(16):
        h = g
        for side in (2, 1, 0, 1, 2, 0):
            h = triple.generators[side][h]
        assert h == g
    return triple


def code_k(triple):
    value = 4 + triple.N * (1 - sum(Fraction(1, r) for r in triple.orders))
    assert value.denominator == 1
    return int(value)


class _UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i
    def join(self, i, j):
        i, j = self.find(i), self.find(j)
        if i != j:
            self.parent[max(i, j)] = min(i, j)


@lru_cache(maxsize=2)
def _fine(triple, L):
    if not isinstance(L, int) or L < 1:
        raise ValueError("side length L must be a positive integer")
    coords = [(i, j, L-i-j) for i in range(L+1) for j in range(L-i+1)]
    pos = {v: i for i, v in enumerate(coords)}
    m = len(coords)
    uf = _UnionFind(triple.N * m)
    for g in range(triple.N):
        for side, perm in enumerate(triple.generators):
            h = perm[g]
            if g < h:
                for i, v in enumerate(coords):
                    if v[side] == 0:
                        uf.join(g*m+i, h*m+i)
    roots = sorted({uf.find(i) for i in range(triple.N*m)})
    root_index = {v: i for i, v in enumerate(roots)}
    vertex = [root_index[uf.find(i)] for i in range(triple.N*m)]
    small = []
    for i in range(L):
        for j in range(L-i):
            small.append((pos[i,j,L-i-j], pos[i+1,j,L-i-j-1], pos[i,j+1,L-i-j-1]))
            if i+j <= L-2:
                small.append((pos[i+1,j,L-i-j-1], pos[i,j+1,L-i-j-1],
                              pos[i+1,j+1,L-i-j-2]))
    assert len(small) == L*L
    rows = [0] * len(roots)
    for g in range(triple.N):
        for j, corners in enumerate(small):
            for i in corners:
                rows[vertex[g*m+i]] |= 1 << (g*L*L+j)
    row_perms = []
    for left in triple.left_generators():
        perm = [-1] * len(roots)
        for g in range(triple.N):
            for i in range(m):
                src, dst = vertex[g*m+i], vertex[left[g]*m+i]
                assert perm[src] in (-1, dst)
                perm[src] = dst
        row_perms.append(tuple(perm))
    return tuple(rows), triple.N * L*L, tuple(row_perms)


def color_code(triple, L=1):
    rows, n, _ = _fine(triple, L)
    return list(rows), n


def _rref(matrix, p, ncols=None):
    """Small dense finite-field elimination, numpy is only integer arithmetic."""
    a = np.asarray(matrix, dtype=np.int64)
    if a.size == 0:
        a = np.zeros((0, ncols or 0), dtype=np.int64)
    a = a.reshape((-1, a.shape[-1])).copy() % p
    pivots, row = [], 0
    for col in range(a.shape[1]):
        candidates = np.flatnonzero(a[row:, col])
        if not len(candidates):
            continue
        j = row + int(candidates[0])
        a[[row, j]] = a[[j, row]]
        a[row] = a[row] * pow(int(a[row, col]), -1, p) % p
        factors = a[:, col].copy()
        factors[row] = 0
        a = (a - factors[:, None] * a[row]) % p
        pivots.append(col)
        row += 1
        if row == len(a):
            break
    return a[:row], pivots


def _kernel(matrix, p, ncols):
    a, pivots = _rref(matrix, p, ncols)
    free = [i for i in range(ncols) if i not in pivots]
    result = np.zeros((len(free), ncols), dtype=np.int64)
    for i, f in enumerate(free):
        result[i, f] = 1
        for j, pivot in enumerate(pivots):
            result[i, pivot] = -a[j, f] % p
    return result, free


@lru_cache(maxsize=48)
def cohomology(triple, p=2):
    """Gauge-fixed face-closed edge voltages and the three left actions on H^1."""
    validate_triple(triple)
    if p < 2 or any(p % d == 0 for d in range(2, int(p**0.5)+1)):
        raise ValueError("p must be prime")
    edges, edge_index = [], {}
    for g in range(triple.N):
        for side, perm in enumerate(triple.generators):
            h = perm[g]
            if g < h:
                key = (g, h, side)
                edge_index[key] = len(edges)
                edges.append(key)
    def edge(g, side):
        h = triple.generators[side][g]
        return edge_index[min(g,h), max(g,h), side], 1 if g < h else -1
    tree, order, parent = set(), [0], {0: None}
    for g in order:
        for side, perm in enumerate(triple.generators):
            h = perm[g]
            if h not in parent:
                e, sign = edge(g, side)
                tree.add(e)
                parent[h] = (g, e, sign)
                order.append(h)
    cotree = [e for e in range(len(edges)) if e not in tree]
    cindex = {e: i for i,e in enumerate(cotree)}
    relations = []
    for (x,y), faces in zip(((0,1),(1,2),(2,0)), face_orbits(triple)):
        for face in faces:
            row = [0] * len(cotree)
            for j,g in enumerate(face):
                e, sign = edge(g, x if j%2 == 0 else y)
                if e in cindex:
                    row[cindex[e]] += sign
            relations.append(row)
    basis, free = _kernel(relations, p, len(cotree))
    full = np.zeros((len(basis),len(edges)), dtype=np.int64)
    full[:,cotree] = basis
    actions = []
    for left in triple.left_generators():
        transformed = np.zeros_like(full)
        for e,(g,h,side) in enumerate(edges):
            j, sign = edge(left[g], side)
            transformed[:,e] = full[:,j] * sign % p
        potentials = np.zeros((len(basis),triple.N), dtype=np.int64)
        for h in order[1:]:
            g,e,sign = parent[h]
            potentials[:,h] = (potentials[:,g] + sign*transformed[:,e]) % p
        for e,(g,h,_) in enumerate(edges):
            transformed[:,e] = (transformed[:,e] - potentials[:,h] + potentials[:,g]) % p
        action = transformed[:, [cotree[f] for f in free]]
        assert np.array_equal(action @ basis % p, transformed[:,cotree])
        actions.append(action)
    return dict(p=p, edges=tuple(edges), basis=full, actions=tuple(actions),
                dimension=len(basis), free=tuple(cotree[f] for f in free))


def invariant_subspaces(triple, p=2, c=1, max_subspaces=1000000):
    """All invariant subspaces via fixed vectors (F2 lines) or RREF enumeration."""
    data = cohomology(triple,p)
    d, actions = data["dimension"], data["actions"]
    if c == 1 and p == 2:
        constraints = np.concatenate([(a-np.eye(d,dtype=np.int64)).T for a in actions])
        fixed,_ = _kernel(constraints,p,d)
        if 2**len(fixed)-1 > max_subspaces:
            raise ValueError("too many invariant lines for configured enumeration budget")
        for coeffs in product(range(p),repeat=len(fixed)):
            if any(coeffs):
                yield np.asarray(coeffs,dtype=np.int64).reshape(1,-1) @ fixed % p
        return
    count = 0
    for pivots in combinations(range(d),c):
        slots = [(i,j) for i,pivot in enumerate(pivots) for j in range(pivot+1,d) if j not in pivots]
        count += p**len(slots)
        if count > max_subspaces:
            raise ValueError("too many subspaces for configured enumeration budget")
        for values in product(range(p),repeat=len(slots)):
            u = np.zeros((c,d),dtype=np.int64)
            for i,pivot in enumerate(pivots):
                u[i,pivot] = 1
            for (i,j),value in zip(slots,values):
                u[i,j] = value
            invariant = True
            for a in actions:
                v = u @ a % p
                v = (v - v[:,pivots] @ u) % p
                if np.any(v):
                    invariant = False
                    break
            if invariant:
                yield u


def voltage_cover(triple, U, p=2, name="cover"):
    data = cohomology(triple,p)
    U = np.asarray(U,dtype=np.int64) % p
    if U.ndim != 2 or U.shape[1] != data["dimension"] or len(_rref(U,p)[1]) != len(U):
        raise ValueError("U must be an independent cohomology subspace basis")
    voltage = U @ data["basis"] % p
    c, q = len(U), p**len(U)
    vectors = list(product(range(p),repeat=c))
    index = {v:i for i,v in enumerate(vectors)}
    directed = {}
    for e,(g,h,side) in enumerate(data["edges"]):
        directed[g,side] = voltage[:,e]
        directed[h,side] = -voltage[:,e] % p
    gs = []
    for side,perm in enumerate(triple.generators):
        out = []
        for g in range(triple.N):
            for v in vectors:
                w = tuple((v[i]+int(directed[g,side][i])) % p for i in range(c))
                out.append(perm[g]*q+index[w])
        gs.append(tuple(out))
    cover = canonical_triple(gs,triple.orders,name)
    validate_triple(cover)  # Direct regularity and smoothness checks, on every returned cover.
    assert cover.N == triple.N*q
    return cover


def elementary_covers(triple,p=2,c=1,uncolored=True):
    """Connected regular covers, deduplicated as labeled or unlabeled tilings."""
    seen = {}
    for u in invariant_subspaces(triple,p,c):
        cover = voltage_cover(triple,u,p)
        canonical = canonical_triple(cover.generators,cover.orders,uncolored=uncolored)
        if canonical.generators not in seen:
            seen[canonical.generators] = canonical
    return [Triple(t.generators,t.orders,f"{triple.name}_p{p}c{c}_{i+1}")
            for i,t in enumerate(sorted(seen.values(),key=lambda t:t.generators))]


TILINGS = {"bolza": bolza()}
CODES = []


def register(triple, distances=None, paper_label=None):
    """Register all four L values; paper claims are metadata, never search certificates."""
    validate_triple(triple)
    TILINGS[triple.name] = triple
    for L in range(1,5):
        distance = (distances or {}).get(L)
        CODES.append(dict(name=f"{triple.name}_L{L}",tiling=triple.name,L=L,n=triple.N*L*L,
                          k=code_k(triple),N=triple.N,orders=triple.orders,
                          orientable=triple.orientable,paper_label=paper_label,
                          d_claimed=distance,status=("certified" if isinstance(distance,int)
                                                    else "open range" if distance else "unidentified")))


register(TILINGS["bolza"],{1:2,2:6,3:8,4:12},"_32")


def tiling(name):
    return TILINGS[name]


def matrices(name):
    code = next((c for c in CODES if c["name"] == name),None)
    if code is None:
        raise KeyError(f"unknown code {name!r}")
    h,n = color_code(tiling(code["tiling"]),code["L"])
    return h,h.copy(),n


def symmetries(name, L=None):
    """Row permutations for cdist.symmetry.from_row_perms; three left generators."""
    if isinstance(name,Triple):
        triple = name
        L = 1 if L is None else L
    else:
        code = next((c for c in CODES if c["name"] == name),None)
        if code is None:
            raise KeyError(name)
        triple,L = tiling(code["tiling"]),code["L"]
    return [list(p) for p in _fine(triple,L)[2]]


class FiniteField:
    """Prime fields and F25 = F5[u]/(u^2-2), encoded as a+5*b."""

    def __init__(self, q: int):
        self.q = q
        self.p = 5 if q == 25 else q
        self.degree = 2 if q == 25 else 1
        if q != 25 and (q < 3 or any(q % d == 0 for d in range(2, math.isqrt(q) + 1))):
            raise ValueError("Only odd prime fields and F25 are implemented")
        self.add = [[self._add(a, b) for b in range(q)] for a in range(q)]
        self.mul = [[self._mul(a, b) for b in range(q)] for a in range(q)]
        self.neg = [next(b for b in range(q) if self.add[a][b] == 0) for a in range(q)]
        self.inv = [0] + [next(b for b in range(1, q) if self.mul[a][b] == 1) for a in range(1, q)]
        self.squares = {self.mul[a][a] for a in range(1, q)}
        self.frobenius = [self.power(a, self.p) for a in range(q)]

    def _add(self, a, b):
        if self.degree == 1:
            return (a + b) % self.p
        return (a % 5 + b % 5) % 5 + 5 * ((a // 5 + b // 5) % 5)

    def _mul(self, a, b):
        if self.degree == 1:
            return a * b % self.p
        a0, a1, b0, b1 = a % 5, a // 5, b % 5, b // 5
        return (a0 * b0 + 2 * a1 * b1) % 5 + 5 * ((a0 * b1 + a1 * b0) % 5)

    def power(self, a, n):
        v = 1
        while n:
            if n & 1:
                v = self.mul[v][a]
            a = self.mul[a][a]
            n >>= 1
        return v


class ProjectiveGroup:
    """PSL/PGL(2,q) with canonical faithful projective-line permutations."""

    def __init__(self, kind: str, q: int):
        if kind not in ("PSL", "PGL"):
            raise ValueError("kind must be PSL or PGL")
        self.kind, self.q = kind, q
        self.field = f = FiniteField(q)
        matrices = []
        # The first nonzero entry is normalized to 1.  An invertible 2x2
        # matrix always has a nonzero first row, giving these two cases.
        for b in range(q):
            for c in range(q):
                for d in range(q):
                    det = f.add[d][f.neg[f.mul[b][c]]]
                    if det and (kind == "PGL" or det in f.squares):
                        matrices.append((1, b, c, d))
        for c in range(1, q):
            det = f.neg[c]
            if kind == "PGL" or det in f.squares:
                matrices.extend((0, 1, c, d) for d in range(q))
        self.matrices = tuple(sorted(matrices))
        self.index = {m: i for i, m in enumerate(self.matrices)}
        self.identity = self.index[(1, 0, 0, 1)]
        expected = q * (q * q - 1) // (2 if kind == "PSL" else 1)
        assert len(self.matrices) == expected
        self.inverses = tuple(self.index[self.normalize((d, f.neg[b], f.neg[c], a))]
                              for a, b, c, d in self.matrices)
        self.involutions = tuple(i for i, (a, _, _, d) in enumerate(self.matrices)
                                 if f.add[a][d] == 0 and i != self.identity)
        self.frobenius = tuple(self.index[tuple(f.frobenius[x] for x in m)]
                               for m in self.matrices)

    def __len__(self):
        return len(self.matrices)

    def normalize(self, m):
        scale = self.field.inv[next(x for x in m if x)]
        return tuple(self.field.mul[x][scale] for x in m)

    def multiply(self, i, j):
        a, b, c, d = self.matrices[i]
        e, f, g, h = self.matrices[j]
        mul, add = self.field.mul, self.field.add
        m = (add[mul[a][e]][mul[b][g]], add[mul[a][f]][mul[b][h]],
             add[mul[c][e]][mul[d][g]], add[mul[c][f]][mul[d][h]])
        return self.index[self.normalize(m)]

    def conjugate(self, h, g):
        """h*g*h^-1."""
        return self.multiply(self.multiply(h, g), self.inverses[h])

    def order(self, i):
        v = self.identity
        # Every element order divides q-1, q+1, or the characteristic.
        for n in range(1, self.q + 2):
            v = self.multiply(v, i)
            if v == self.identity:
                return n
        raise AssertionError("Unexpected projective element order")

    def projective_permutation(self, i):
        """Finite x is x; the point at infinity is encoded by q."""
        a, b, c, d = self.matrices[i]
        mul, add, inv = self.field.mul, self.field.add, self.field.inv
        image = []
        for x in range(self.q):
            numerator, denominator = add[mul[a][x]][b], add[mul[c][x]][d]
            image.append(mul[numerator][inv[denominator]] if denominator else self.q)
        image.append(mul[a][inv[c]] if c else self.q)
        assert len(set(image)) == self.q + 1
        return tuple(image)

    def generated_order(self, triple):
        """Explicit closure, rather than a group-theoretic generation test."""
        seen = {self.identity}
        queue = deque([self.identity])
        while queue:
            g = queue.popleft()
            for x in triple:
                gx = self.multiply(g, x)
                if gx not in seen:
                    seen.add(gx)
                    queue.append(gx)
        return len(seen)


@lru_cache(maxsize=None)
def projective_group(kind: str, q: int):
    return ProjectiveGroup(kind, q)


@dataclass(frozen=True)
class ProjectiveTriple:
    kind: str
    q: int
    orders: tuple[int, int, int]
    generators: tuple[int, int, int]

    @property
    def group(self):
        return projective_group(self.kind, self.q)

    @property
    def permutations(self):
        return tuple(self.group.projective_permutation(i) for i in self.generators)

    @property
    def matrices(self):
        return tuple(self.group.matrices[i] for i in self.generators)


def _inner_canonicalizer(group):
    """Maps triples to representatives after fixing a and then b."""
    # For each involution choose a conjugator sending it to its class minimum.
    involution_to_a, centralizers = {}, {}
    remaining = set(group.involutions)
    while remaining:
        a = min(remaining)
        orbit = {}
        centralizer = []
        for h in range(len(group)):
            ah = group.conjugate(h, a)
            orbit.setdefault(ah, group.inverses[h])
            if ah == a:
                centralizer.append(h)
        for x, h in orbit.items():
            involution_to_a[x] = (a, h)
        remaining.difference_update(orbit)
        centralizers[a] = tuple(centralizer)

    @lru_cache(maxsize=None)
    def canonical(triple):
        a, b, c = triple
        a0, h = involution_to_a[a]
        b, c = group.conjugate(h, b), group.conjugate(h, c)
        pairs = [(group.conjugate(j, b), group.conjugate(j, c))
                 for j in centralizers[a0]]
        b0, c0 = min(pairs)
        return a0, b0, c0

    return centralizers, canonical


@lru_cache(maxsize=None)
def projective_triples(kind: str, q: int, orders: tuple[int, int, int]):
    """All ordered generating involution triples modulo inner+field actions.

    Fixing one involution and then reducing the second by its centralizer
    avoids enumerating |Inv(G)|^3 triples.  The remaining centralizer reduces
    the third.  Every returned triple is checked to generate the whole target.
    """
    group = projective_group(kind, q)
    r, s, t = orders
    centralizers, canonical = _inner_canonicalizer(group)
    representatives = set()
    for a, ca in sorted(centralizers.items()):
        eligible_b = {b for b in group.involutions if group.order(group.multiply(a, b)) == r}
        while eligible_b:
            b = min(eligible_b)
            orbit_b = {group.conjugate(h, b) for h in ca}
            eligible_b.difference_update(orbit_b)
            cab = tuple(h for h in ca if group.conjugate(h, b) == b)
            eligible_c = {c for c in group.involutions
                          if group.order(group.multiply(c, a)) == t
                          and group.order(group.multiply(b, c)) == s}
            while eligible_c:
                c = min(eligible_c)
                eligible_c.difference_update(group.conjugate(h, c) for h in cab)
                triple = (a, b, c)
                if group.generated_order(triple) != len(group):
                    continue
                candidates = [canonical(triple)]
                image = triple
                for _ in range(1, group.field.degree):
                    image = tuple(group.frobenius[x] for x in image)
                    candidates.append(canonical(image))
                representatives.add(min(candidates))
    result = tuple(ProjectiveTriple(kind, q, orders, x) for x in sorted(representatives))
    return result


@dataclass(frozen=True)
class RegularProjectiveAction:
    """Adjacency and symmetry generators on the same canonical group points."""
    right: tuple[tuple[int, ...], ...]
    left: tuple[tuple[int, ...], ...]
    words: tuple[tuple[int, ...], ...]
    orientable: bool
    orders: tuple[int, int, int]
    projective: ProjectiveTriple

    @property
    def n(self):
        return len(self.right[0])


def regular_representation(triple: ProjectiveTriple):
    """Right adjacency, left symmetries, and words, identity point first.

    The point ordering is breadth-first from the identity with alphabet a,b,c.
    Faithful regularity follows explicitly from enumerating all target group
    elements; no permutation-group package or N by N table is built.
    """
    group = triple.group
    elements = [group.identity]
    position = {group.identity: 0}
    words = [()]
    parity = [0]
    orientable = True
    for i, g in enumerate(elements):
        for letter, x in enumerate(triple.generators):
            gx = group.multiply(g, x)
            if gx not in position:
                position[gx] = len(elements)
                elements.append(gx)
                words.append(words[i] + (letter,))
                parity.append(1 - parity[i])
            elif parity[position[gx]] == parity[i]:
                orientable = False
    assert len(elements) == len(group)
    right = tuple(tuple(position[group.multiply(g, x)] for g in elements)
                  for x in triple.generators)
    left = tuple(tuple(position[group.multiply(x, g)] for g in elements)
                 for x in triple.generators)
    for p in right:
        assert all(p[p[i]] == i and p[i] != i for i in range(len(group)))
    for l in left:
        for rperm in right:
            assert all(l[rperm[i]] == rperm[l[i]] for i in range(len(group)))
    return RegularProjectiveAction(right, left, tuple(words), orientable, triple.orders, triple)


def orientable_double_cover(action: RegularProjectiveAction):
    """Generated subgroup of G x Z2, with a,b,c flipping the Z2 bit.

    An already orientable quotient is returned unchanged, as in S1 F iii.
    Otherwise the point (g,v) is numbered 2*g+v and both regular actions flip v.
    """
    if action.orientable:
        return action
    def lift(p):
        return tuple(2 * p[g] + (1 - v) for g in range(action.n) for v in (0, 1))
    right, left = tuple(map(lift, action.right)), tuple(map(lift, action.left))
    words = [None] * (2 * action.n)
    words[0] = ()
    queue = deque([0])
    while queue:
        g = queue.popleft()
        for letter, p in enumerate(right):
            gx = p[g]
            if words[gx] is None:
                words[gx] = words[g] + (letter,)
                queue.append(gx)
    assert all(w is not None for w in words), "The lift must generate the full product"
    for l in left:
        for rperm in right:
            assert all(l[rperm[i]] == rperm[l[i]] for i in range(len(right[0])))
    return RegularProjectiveAction(right, left, tuple(words), True, action.orders, action.projective)


REQUESTED_PROJECTIVE_TARGETS = (
    ("PGL", 7, (4, 4, 4)),
    ("PSL", 23, (4, 4, 4)),
    ("PSL", 25, (4, 4, 4)),
    ("PGL", 17, (4, 6, 6)),
    ("PSL", 29, (5, 5, 5)),
    ("PGL", 19, (4, 4, 5)),
)




def available_tilings():
    return list(TILINGS.values())


def _register_reconstructions():
    previous = TILINGS['bolza']
    # Built without GAP as covers of Bolza.  They are tilings of the LINS list, but not the rows the
    # paper tabulates: the paper's _40 and _58 are lins444_40 and lins444_58 (see register_lins).
    for N, label, ds in ((32,None,{}), (64,None,{}), (128,None,{})):
        covers = elementary_covers(previous)
        assert len(covers) == 1
        previous = Triple(covers[0].generators,(4,4,4),f'bolza{N}')
        register(previous,ds,label)
    covers = elementary_covers(TILINGS['bolza'],5,2)
    assert len(covers) == 1
    register(Triple(covers[0].generators,(4,4,4),'bolza400'))      # the paper's _109 is lins444_109
    for kind,q,orders in REQUESTED_PROJECTIVE_TARGETS:
        for i,pt in enumerate(projective_triples(kind,q,orders),1):
            action = regular_representation(pt)
            stem = f'{kind.lower()}{q}_'+''.join(map(str,orders))+f'_c{i}'
            triple = Triple(action.right,orders,stem)
            ds,label = {},None
            if (kind,q)==('PGL',7):
                ds,label = {},None                                 # the paper's _96 is lins444_96
            elif (kind,q)==('PSL',23):
                ds,label = {2:22,3:32,4:[42,44]},'PSL(2,23)'
            elif (kind,q)==('PSL',25):
                ds,label = {2:[22,24],3:32,4:[42,46]},'PSL(2,25)'
            register(triple,ds,label)
            if (kind,q) in (('PGL',19),('PSL',25)):
                double = orientable_double_cover(action)
                name = stem+'_x2'
                # The paper's |i enumeration is unknown: retain all candidates.
                claim = {} if q==19 else {1:[10,14]}
                register(Triple(double.right,orders,name),claim,
                         ('PGL(2,19) x Z2 |1 candidate' if q==19 else 'PSL(2,25) x Z2'))
    parent = TILINGS['pgl7_444_c1']
    covers = elementary_covers(parent)
    assert len(covers) == 1
    parent = Triple(covers[0].generators,parent.orders,'pgl7_672')
    register(parent)
    for i,cover in enumerate(elementary_covers(parent),1):
        register(Triple(cover.generators,parent.orders,f'pgl7_1344_c{i}'))


_register_reconstructions()

# A numbered paper label is a candidate until a distance distinguishes it.
# Do not apply the best candidate's bounds to every quotient of the same size.
for code in CODES:
    if code['L'] == 1:
        if code['tiling'].startswith('pgl17_'):
            code['paper_candidates'] = {'|1': [8,10]}
        elif code['tiling'].startswith('psl29_'):
            code['paper_candidates'] = {'|1': [8,10]}
        elif code['tiling'].startswith('pgl19_') and code['tiling'].endswith('_x2'):
            code['paper_candidates'] = {'|1': [8,12]}
        elif code['tiling'].startswith('pgl7_1344_'):
            code['paper_candidates'] = {'_271': [10,12]}
    if code['tiling'].startswith('pgl7_1344_'):
        code['paper_candidates'] = {'_271': {1:[10,12],2:[18,20],3:28,4:[36,38]}[code['L']]}
    code['locator'] = 'Methods A/B/D/E; S1/S2A/S10/S12'
    code['paper_identification'] = ('verified all four distances' if code['tiling'] == 'bolza'
                                   else 'rejected _40 candidate' if code['tiling'] == 'bolza32'
                                   else 'unresolved candidate' if 'candidate' in (code['paper_label'] or '')
                                   else 'target identified; local distance unrun' if code['paper_label']
                                   else 'unidentified')


# ---------------------------------------------------------------------------------------------
# Tilings from GAP's LINS enumeration (papers/hyperbolic_lins.g, run on the server): every smooth
# quotient up to the index bound, named lins<rst>_<p> with p the 0-based position of the normal
# subgroup in the LINS list.  The paper's subscripts appear to be these positions (its _32 is the
# order-16 Bolza quotient, entry 33 of the list), so lins444_40 is the candidate for its _40, etc.
# The match is confirmed only where the certified distances agree.
PAPER_444 = {32: {1: 2, 2: 6, 3: 8, 4: 12}, 40: {1: 4, 2: 8, 3: 12, 4: 16},
             58: {1: 8, 2: 12, 3: 16, 4: [20, 24]}, 96: {2: 14, 3: 20, 4: [26, 28]},
             109: {2: [14, 16], 3: 22, 4: 30}, 120: {2: 16, 3: 24, 4: 32},
             271: {1: [10, 12], 2: [18, 20], 3: 28, 4: [36, 38]}}


def register_lins(path):
    import json
    names = []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            orders = tuple(r["type"])
            name = "lins" + "".join(map(str, orders)) + "_%d" % (r["position"] - 1)
            if name in TILINGS:
                continue
            triple = Triple(tuple(tuple(r[x]) for x in "abc"), orders, name)
            claim = PAPER_444.get(r["position"] - 1, {}) if orders == (4, 4, 4) else {}
            register(triple, claim, ("_%d by LINS position" % (r["position"] - 1)) if claim else None)
            for code in CODES[-4:]:
                code["group_id"] = r.get("id")
                code["paper_identification"] = "LINS position; confirmed only where distances agree"
            names.append(name)
    return names


def _register_lins_files():
    import glob
    import os
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "papers4", "hyperbolic")
    # Smallest index bound first.  LINS orders normal subgroups of equal index differently for
    # different bounds (e.g. the two order-400 quotients of (4,4,4) swap between the runs to 1344 and
    # to 4096), so a name is fixed by the smallest list that contains it; larger lists only add names.
    def bound(path):
        return int(os.path.basename(path)[:-len(".jsonl")].rsplit("_", 1)[1])
    for path in sorted(glob.glob(os.path.join(root, "lins_*.jsonl")), key=bound):
        register_lins(path)


_register_lins_files()
