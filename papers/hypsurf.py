"""Modular hyperbolic surface-code memories from arXiv:2610.03682.

Square modules of the four Table S2 LINS tilings. Corner cats are measured
at one third of the bulk rate; incomplete cats are closed before final data
readout. Published circuit distances are upper bounds, not exact claims.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json


LINS_SOURCES = {6: ("246", 240, 25), 8: ("248", 256, 30),
                10: ("2410", 240, 24), 12: ("2412", 192, 43)}


def _orbits(generators, n):
    seen = set()
    orbit_list = []
    point_orbit = [-1] * n
    for initial in range(n):
        if initial in seen:
            continue
        orbit = {initial}
        todo = [initial]
        while todo:
            point = todo.pop()
            for permutation in generators:
                new = permutation[point]
                if new not in orbit:
                    orbit.add(new)
                    todo.append(new)
        orbit = tuple(sorted(orbit))
        for point in orbit:
            point_orbit[point] = len(orbit_list)
        orbit_list.append(orbit)
        seen.update(orbit)
    return tuple(orbit_list), tuple(point_orbit)


@lru_cache(None)
def tiling(q):
    """Return the specified {4,q} quotient, with explicit face incidences."""
    rst, bound, position = LINS_SOURCES[q]
    # This also works after integration into papers/hypsurf.py.
    root = Path(__file__).resolve()
    while not (root / "results" / "papers4" / "hyperbolic").is_dir():
        if root.parent == root:
            raise FileNotFoundError("cannot locate project root")
        root = root.parent
    path = root / "results" / "papers4" / "hyperbolic" / f"lins_{rst}_{bound}.jsonl"
    entry = next(json.loads(line) for line in path.open()
                 if json.loads(line)["position"] - 1 == position)
    a, b, c = (tuple(entry[name]) for name in "abc")
    ntri = len(a)
    assert ntri == 8 * q
    for permutation in (a, b, c):
        assert sorted(permutation) == list(range(ntri))
        assert all(permutation[permutation[i]] == i != permutation[i]
                   for i in range(ntri))
    faces, point_face = _orbits((b, c), ntri)
    vertices, point_vertex = _orbits((c, a), ntri)
    edges, point_edge = _orbits((a, b), ntri)
    assert all(len(face) == 8 for face in faces)
    assert all(len(vertex) == 2 * q for vertex in vertices)
    assert all(len(edge) == 4 for edge in edges)
    assert len(faces) == q and len(vertices) == 4 and len(edges) == 2 * q

    face_corners = []
    face_sides = []
    flag_corner = {}
    edge_sides = [[] for _ in edges]
    for f, face in enumerate(faces):
        current = min(face)
        corners = []
        for i in range(4):
            corners.append(current)
            flag_corner[current] = flag_corner[c[current]] = (f, i)
            current = b[c[current]]
        assert current == corners[0]
        assert len(set(corners + [c[t] for t in corners])) == 8
        face_corners.append(tuple(corners))
        side_edges = []
        for i, corner in enumerate(corners):
            start_flag = c[corner]
            assert b[start_flag] == corners[(i + 1) % 4]
            edge = point_edge[start_flag]
            side_edges.append(edge)
            edge_sides[edge].append((f, i))
        face_sides.append(tuple(side_edges))

    side_pairs = []
    for incidences in edge_sides:
        assert len(incidences) == 2
        (f, i), (g, j) = incidences
        mapped_start = flag_corner[a[c[face_corners[f][i]]]]
        assert mapped_start in ((g, j), (g, (j + 1) % 4))
        reverse = mapped_start == (g, (j + 1) % 4)
        mapped_end = flag_corner[a[face_corners[f][(i + 1) % 4]]]
        assert mapped_end == (g, j if reverse else (j + 1) % 4)
        side_pairs.append((f, i, g, j, reverse))

    corner_cycles = []
    for vertex in vertices:
        current = min(vertex)
        initial = current
        incidence_list = []
        for _ in range(q):
            incidence_list.append(flag_corner[current])
            current = c[a[current]]
        assert current == initial
        assert len(set(incidence_list)) == q
        corner_cycles.append(tuple(incidence_list))
    return dict(q=q, name=f"lins{rst}_{position}", source=str(path),
                position=position, ntri=ntri, a=a, b=b, c=c,
                orientable=entry["orientable"], faces=faces,
                vertices=vertices, edges=edges, point_face=point_face,
                point_vertex=point_vertex, point_edge=point_edge,
                face_corners=tuple(face_corners), face_sides=tuple(face_sides),
                corner_vertex=tuple(tuple(point_vertex[t] for t in face)
                                    for face in face_corners),
                side_pairs=tuple(side_pairs), corner_cycles=tuple(corner_cycles))


def _side_xy(side, position, L):
    return ((position, 0), (L, position), (L - position, L),
            (0, L - position))[side]


@lru_cache(None)
def geometry(q, L):
    """Fine mesh, CSS checks, and one ancilla at each module-local vertex.

    ``ancillas`` use indices starting at zero; the circuit adds ``n``.
    ``data`` entries (qubit, direction) assign every ancilla's own module's
    data coupling to a direction NW, NE, SE, SW from the ancilla.
    ``check_ancillas`` are in geometric cyclic order at base corners and in
    deterministic face order elsewhere.
    """
    assert isinstance(L, int) and L >= 1
    base = tiling(q)
    F = len(base["faces"])
    local_n = F * (L + 1) ** 2
    parent = list(range(local_n))

    def local(f, x, y):
        return f * (L + 1) ** 2 + y * (L + 1) + x

    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left, right):
        left, right = find(left), find(right)
        if left != right:
            parent[max(left, right)] = min(left, right)

    for f, i, g, j, reverse in base["side_pairs"]:
        for t in range(L + 1):
            x, y = _side_xy(i, t, L)
            xx, yy = _side_xy(j, L - t if reverse else t, L)
            union(local(f, x, y), local(g, xx, yy))
    roots = sorted({find(i) for i in range(local_n)})
    root_check = {root: i for i, root in enumerate(roots)}
    local_check = tuple(root_check[find(i)] for i in range(local_n))
    nchecks = len(roots)
    assert nchecks == F * (L * L - 1) + 4
    adjacency = [set() for _ in roots]
    check_local = [[] for _ in roots]
    for f in range(F):
        for y in range(L + 1):
            for x in range(L + 1):
                check = local_check[local(f, x, y)]
                check_local[check].append((f, x, y))
                for xx, yy in ((x + 1, y), (x, y + 1)):
                    if xx <= L and yy <= L:
                        other = local_check[local(f, xx, yy)]
                        assert other != check, "fine mesh is not bipartite"
                        adjacency[check].add(other)
                        adjacency[other].add(check)
    colors = [None] * nchecks
    colors[0] = "X"
    todo = [0]
    while todo:
        check = todo.pop()
        opposite = "Z" if colors[check] == "X" else "X"
        for other in adjacency[check]:
            if colors[other] is None:
                colors[other] = opposite
                todo.append(other)
            assert colors[other] == opposite, "fine mesh is not bipartite"
    assert all(color is not None for color in colors)
    rows = [0] * nchecks
    data_corners = []
    for f in range(F):
        for y in range(L):
            for x in range(L):
                qubit = f * L * L + y * L + x
                corners = tuple(local_check[local(f, xx, yy)]
                                for xx, yy in ((x, y), (x + 1, y),
                                               (x + 1, y + 1), (x, y + 1)))
                for check in corners:
                    rows[check] ^= 1 << qubit
                data_corners.append(corners)
    ancillas = []
    check_ancillas = [[] for _ in roots]
    for f in range(F):
        for y in range(L + 1):
            for x in range(L + 1):
                index = local(f, x, y)
                check = local_check[index]
                owned = []
                for direction, (xx, yy) in enumerate(((x - 1, y - 1), (x, y - 1),
                                                     (x, y), (x - 1, y))):
                    if 0 <= xx < L and 0 <= yy < L:
                        owned.append((f * L * L + yy * L + xx, direction))
                ancillas.append(dict(index=index, face=f, x=x, y=y,
                                     check=check, color=colors[check], data=tuple(owned)))
                check_ancillas[check].append(index)
    corner_xy = ((0, 0), (L, 0), (L, L), (0, L))
    high_checks = []
    for cycle in base["corner_cycles"]:
        indices = tuple(local(f, *corner_xy[i]) for f, i in cycle)
        check = local_check[indices[0]]
        assert set(indices) == set(check_ancillas[check])
        check_ancillas[check] = list(indices)
        high_checks.append(check)
    assert len(high_checks) == 4
    assert all(len(check_ancillas[check]) == q for check in high_checks)
    hx = tuple(row for row, color in zip(rows, colors) if color == "X")
    hz = tuple(row for row, color in zip(rows, colors) if color == "Z")
    assert all(bin(x & z).count("1") % 2 == 0 for x in hx for z in hz)
    # Each small square has two checks of each Pauli type, and each local
    # ancilla touches only data in its own module.
    assert all([colors[v] for v in corner].count("X") == 2 for corner in data_corners)
    return dict(q=q, L=L, base=base, n=F * L * L, nchecks=nchecks,
                hx=hx, hz=hz, rows=tuple(rows), check_colors=tuple(colors),
                local_check=local_check, check_local=tuple(tuple(v) for v in check_local),
                data_corners=tuple(data_corners), ancillas=tuple(ancillas),
                check_ancillas=tuple(tuple(v) for v in check_ancillas),
                high_checks=tuple(high_checks), nancillas=len(ancillas),
                total_qubits=F * (2 * L * L + 2 * L + 1))


import collections
import random
from functools import lru_cache


def _schedule_popcount(value):
    return bin(value).count("1")


def schedule_options(kind="ZZ"):
    """Eight joint corner schedules, directions NW, NE, SE, SW.

    The same dihedral operation is applied to both bases for NZ, as required
    by S4 B vi.  Times are the direction from an ancilla to its data qubit.
    """
    kind = kind.upper()
    if kind == "ZZ":
        px = pz = (0, 1, 3, 2)
    elif kind == "NZ":
        px, pz = (3, 1, 0, 2), (3, 2, 0, 1)
    else:
        raise ValueError("schedule kind must be ZZ or NZ")
    options = []
    for reflected in (False, True):
        for rotation in range(4):
            indices = tuple((rotation - i if reflected else rotation + i) % 4
                            for i in range(4))
            options.append((tuple(px[i] for i in indices),
                            tuple(pz[i] for i in indices)))
    assert len(set(options)) == 8
    return tuple(options)


def _schedule_color(color):
    if color in (0, "X", "x"):
        return 0
    if color in (1, "Z", "z"):
        return 1
    raise ValueError("check color must be 0/X or 1/Z")


def _schedule_geometry_terms(mesh):
    """Collect the S26 comparison terms directly from the fine incidence.

    For each adjacent X/Z pair, commuting to the requested interleaving gives
    one effective cat-to-cat CNOT per shared datum where Z precedes X.
    Even parity is precisely the general condition underlying equation S26;
    for the present L>=3 meshes each nonempty intersection has size two.
    """
    by_data = collections.defaultdict(list)
    by_ancilla = {}
    for a in mesh["ancillas"]:
        color = _schedule_color(a["color"])
        aindex = a["index"]
        entries = []
        for datum, direction in a["data"]:
            entry = (a["check"], color, a["face"], direction, aindex)
            by_data[datum].append(entry)
            entries.append(entry)
        by_ancilla[aindex] = entries
    comparisons = collections.defaultdict(list)
    for datum, entries in by_data.items():
        if len(entries) != 4:
            raise ValueError(f"datum {datum} has {len(entries)} incidences, expected 4")
        for x in entries:
            if x[1] != 0:
                continue
            for z in entries:
                if z[1] == 1:
                    if x[2] != z[2]:
                        raise ValueError("one data square belongs to multiple base faces")
                    comparisons[x[0], z[0]].append((x[2], x[3], z[3]))
    return by_data, by_ancilla, tuple(comparisons.values())


def schedule_constraints(mesh, kind="ZZ"):
    """Compile exact fine-grid commutativity and collision constraints.

    Return domains (bitmasks of the eight allowed D4 options), compatibility
    matrices for neighboring faces, and comparison terms used for direct
    validation.  No coarse NZ rule is inferred from a picture.
    """
    options = schedule_options(kind)
    by_data, by_ancilla, comparisons = _schedule_geometry_terms(mesh)
    nfaces = 1 + max(a["face"] for a in mesh["ancillas"])
    domains = [255] * nfaces
    for entries in tuple(by_data.values()) + tuple(by_ancilla.values()):
        faces = {entry[2] for entry in entries}
        if len(faces) != 1:
            raise ValueError("square-module ancilla spans several faces")
        face = next(iter(faces))
        for value, pair in enumerate(options):
            times = [pair[entry[1]][entry[3]] for entry in entries]
            if len(times) != len(set(times)):
                domains[face] &= ~(1 << value)
    matrices = {}
    for terms in comparisons:
        faces = sorted({term[0] for term in terms})
        if len(terms) % 2:
            raise ValueError("X/Z checks have an odd data overlap")
        if len(faces) == 1:
            face = faces[0]
            for value, pair in enumerate(options):
                parity = sum(pair[0][dx] < pair[1][dz]
                             for _, dx, dz in terms) % 2
                if parity:
                    domains[face] &= ~(1 << value)
        elif len(faces) == 2:
            a, b = faces
            key = (a, b)
            allowed = matrices.setdefault(key, [255] * 8)
            for va, pa in enumerate(options):
                for vb, pb in enumerate(options):
                    parity = 0
                    for face, dx, dz in terms:
                        pair = pa if face == a else pb
                        parity ^= pair[0][dx] < pair[1][dz]
                    if parity:
                        allowed[va] &= ~(1 << vb)
        else:
            raise ValueError("S26 constraint spans more than two faces")
    neighbors = [[] for _ in range(nfaces)]
    allowed = {}
    for (a, b), matrix in matrices.items():
        allowed[a, b] = tuple(matrix)
        allowed[b, a] = tuple(sum(1 << va for va in range(8)
                                  if matrix[va] & (1 << vb))
                              for vb in range(8))
        neighbors[a].append(b)
        neighbors[b].append(a)
    return {"kind": kind.upper(), "options": options,
            "domains": tuple(domains), "allowed": allowed,
            "neighbors": tuple(tuple(sorted(ns)) for ns in neighbors),
            "comparison_terms": comparisons, "nfaces": nfaces}


def _schedule_arc_consistency(domains, constraints):
    queue = collections.deque(constraints["allowed"])
    while queue:
        a, b = queue.popleft()
        matrix = constraints["allowed"][a, b]
        revised = sum(1 << va for va in range(8)
                      if domains[a] & (1 << va) and matrix[va] & domains[b])
        if revised != domains[a]:
            if not revised:
                return False
            domains[a] = revised
            queue.extend((c, a) for c in constraints["neighbors"][a] if c != b)
    return all(domains)


def iter_schedule_assignments(constraints, limit=None, seed=None):
    """Backtrack with AC-3 and MRV; optional seed randomizes traversal.

    A seeded bounded traversal is reproducible randomized search, not an
    assertion of uniform sampling.  Call with limit=None for exhaustive
    enumeration.  Solutions retain all labeled-face D4 choices: tiling
    automorphisms and global time reversal are not quotiented out.
    """
    rng = random.Random(seed) if seed is not None else None
    produced = 0
    initial = list(constraints["domains"])
    if not _schedule_arc_consistency(initial, constraints):
        return

    def walk(domains):
        nonlocal produced
        if limit is not None and produced >= limit:
            return
        unresolved = [i for i, d in enumerate(domains) if _schedule_popcount(d) > 1]
        if not unresolved:
            produced += 1
            yield tuple(d.bit_length() - 1 for d in domains)
            return
        size = min(_schedule_popcount(domains[i]) for i in unresolved)
        candidates = [i for i in unresolved if _schedule_popcount(domains[i]) == size]
        face = rng.choice(candidates) if rng else candidates[0]
        values = [v for v in range(8) if domains[face] & (1 << v)]
        if rng:
            rng.shuffle(values)
        else:
            # Least-constraining value, with numerical tie break.
            values.sort(key=lambda v: (-sum(_schedule_popcount(constraints["allowed"][face, b][v]
                                            & domains[b])
                                           for b in constraints["neighbors"][face]), v))
        for value in values:
            next_domains = list(domains)
            next_domains[face] = 1 << value
            if _schedule_arc_consistency(next_domains, constraints):
                yield from walk(next_domains)
            if limit is not None and produced >= limit:
                return

    yield from walk(initial)


def enumerate_schedules(q, kind="ZZ", L=3, limit=None, seed=None):
    """Enumerate valid square-module schedule assignments for one tiling."""
    constraints = schedule_constraints(geometry(q, L), kind)
    yield from iter_schedule_assignments(constraints, limit=limit, seed=seed)


def _schedule_cycle_counter(constraints):
    """Exact transfer count for the cyclic face graph of the four S2 tilings."""
    neighbors = constraints["neighbors"]
    if not all(len(ns) == 2 for ns in neighbors):
        raise ValueError("exact transfer counter requires a simple cycle face graph")
    order = [0]
    previous, current = 0, min(neighbors[0])
    while current != 0:
        if current in order:
            raise ValueError("face constraint graph has multiple cycles")
        order.append(current)
        following = next(n for n in neighbors[current] if n != previous)
        previous, current = current, following
    if len(order) != len(neighbors):
        raise ValueError("face constraint graph is disconnected")
    domains = constraints["domains"]
    allowed = constraints["allowed"]

    @lru_cache(None)
    def suffix(position, previous_value, first_value):
        if position == len(order):
            return int(bool(allowed[order[-1], order[0]][previous_value]
                            & (1 << first_value)))
        previous_face, face = order[position - 1], order[position]
        values = allowed[previous_face, face][previous_value] & domains[face]
        return sum(suffix(position + 1, value, first_value)
                   for value in range(8) if values & (1 << value))

    roots = [(v, suffix(1, v, v)) for v in range(8)
             if domains[order[0]] & (1 << v)]
    return tuple(order), suffix, roots


def count_schedules(q, kind="ZZ", L=3):
    """Exact number of labeled-face assignments, without materializing them."""
    constraints = schedule_constraints(geometry(q, L), kind)
    _, _, roots = _schedule_cycle_counter(constraints)
    return sum(weight for _, weight in roots)


def sample_schedules(q, kind="ZZ", count=256, L=3, seed=0):
    """Uniformly sample distinct valid labeled-face assignments.

    Transfer counts allow exact uniform draws on the cyclic constraint graphs
    of the four Table S2 tilings.  Repeated draws are discarded, giving a
    uniform subset of the requested size.  No distance is consulted.
    """
    constraints = schedule_constraints(geometry(q, L), kind)
    order, suffix, roots = _schedule_cycle_counter(constraints)
    total = sum(weight for _, weight in roots)
    if count < 0:
        raise ValueError("sample count must be nonnegative")
    if count >= total:
        return list(iter_schedule_assignments(constraints))
    rng = random.Random(seed)

    def weighted_choice(values):
        choice = rng.randrange(sum(weight for _, weight in values))
        for value, weight in values:
            if choice < weight:
                return value
            choice -= weight
        raise AssertionError("weighted draw failed")

    found, result = set(), []
    while len(result) < count:
        first = weighted_choice(roots)
        ordered_values = [first]
        for position in range(1, len(order)):
            previous_face, face = order[position - 1], order[position]
            values = (constraints["allowed"][previous_face, face][ordered_values[-1]]
                      & constraints["domains"][face])
            weighted = [(v, suffix(position + 1, v, first))
                        for v in range(8) if values & (1 << v)]
            ordered_values.append(weighted_choice(weighted))
        assignment = [None] * len(order)
        for face, value in zip(order, ordered_values):
            assignment[face] = value
        assignment = tuple(assignment)
        if assignment not in found:
            found.add(assignment)
            result.append(assignment)
    return result


def validate_schedule(mesh, assignment, kind="ZZ"):
    """Check every fine-grid S26 parity and every qubit/ancilla collision."""
    options = schedule_options(kind)
    by_data, by_ancilla, comparisons = _schedule_geometry_terms(mesh)
    nfaces = 1 + max(a["face"] for a in mesh["ancillas"])
    if len(assignment) != nfaces or any(v not in range(8) for v in assignment):
        return False
    for entries in tuple(by_data.values()) + tuple(by_ancilla.values()):
        times = [options[assignment[face]][color][direction]
                 for _, color, face, direction, _ in entries]
        if len(times) != len(set(times)):
            return False
    for terms in comparisons:
        if sum(options[assignment[face]][0][dx]
               < options[assignment[face]][1][dz]
               for face, dx, dz in terms) % 2:
            return False
    return True


def schedule_times(mesh, assignment, kind="ZZ", reverse=False):
    """Return four disjoint ancilla/data coupling layers (no gate direction)."""
    if not validate_schedule(mesh, assignment, kind):
        raise ValueError("schedule fails fine-grid commutativity or collisions")
    options = schedule_options(kind)
    layers = [[] for _ in range(4)]
    for a in mesh["ancillas"]:
        pair = options[assignment[a["face"]]]
        color = _schedule_color(a["color"])
        for datum, direction in a["data"]:
            time = pair[color][direction]
            if reverse:
                time = 3 - time
            layers[time].append((a["index"], datum, color))
    return tuple(tuple(layer) for layer in layers)


import re
import sys
import stim

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))
import stabcode


PAPER_SQUARE = {
    6: {"ZZ": (6,6), "NZ": (6,8)},
    8: {"ZZ": (6,8), "NZ": (6,8)},
    10: {"ZZ": (6,6), "NZ": (6,8)},
    12: {"ZZ": (6,6), "NZ": (6,8)},
}
CODES = {}
for _q in LINS_SOURCES:
    for _L in (1,3,5):
        for _kind in ("ZZ","NZ"):
            for _fb in (False,True):
                _key = f"q{_q}_L{_L}_{_kind}" + ("_fb" if _fb else "")
                CODES[_key] = (_q,_L,(_q*_L*_L,_q-2,2*_L),
                               PAPER_SQUARE[_q][_kind][int(_fb)] if _L==5 else None)
        CODES[f"q{_q}_L{_L}"] = CODES[f"q{_q}_L{_L}_ZZ"]
    CODES[_q] = CODES[f"q{_q}_L5_ZZ"]


def _key_parts(key):
    if isinstance(key,int):
        if key not in LINS_SOURCES:
            raise KeyError(key)
        return key,5,"ZZ",False
    match = re.fullmatch(r"q(6|8|10|12)_L([1-9][0-9]*)(?:_(ZZ|NZ)(_fb)?)?",str(key))
    if not match:
        raise KeyError(f"unknown hypsurf code {key!r}")
    q,L,kind,fb = match.groups()
    return int(q),int(L),kind or "ZZ",bool(fb)


def matrices(key):
    q,L,_,_ = _key_parts(key)
    mesh = geometry(q,L)
    return list(mesh["hx"]),list(mesh["hz"]),mesh["n"]


def tag(key):
    q,L,kind,fb = _key_parts(key)
    return f"q{q}_L{L}_{kind}" + ("_fb" if fb else "")


def translations(key):
    """No circuit symmetries asserted: the cat-chain cuts break generic translations."""
    _key_parts(key)
    return []


def sector_high(basis):
    if basis not in ("X","Z"):
        raise ValueError("memory basis must be X or Z")
    return basis == "X"


def cat_layers(indices):
    """Linear-path encoding, left middle root, first expand right.

    The ordered cycle is cut before its first incidence. After the first
    edge the two fronts grow concurrently, giving depth ceil(m/2) for m>1.
    Returned pairs are for X-check preparation; Z checks reverse each pair.
    """
    m = len(indices)
    if not m:
        raise ValueError("empty cat")
    center = (m-1)//2
    layers = []
    if m > 1:
        layers.append(((indices[center],indices[center+1]),))
        left,right = center,center+1
        while left>0 or right<m-1:
            layer = []
            if left>0:
                layer.append((indices[left],indices[left-1]))
                left -= 1
            if right<m-1:
                layer.append((indices[right],indices[right+1]))
                right += 1
            layers.append(tuple(layer))
    assert len(layers) == ((m+1)//2 if m>1 else 0)
    return indices[center],tuple(layers)


class _CircuitText:
    """Batch Stim parsing; repeated Python/C++ append calls are slow on this Mac."""
    def __init__(self):
        self.lines = []
        self.targets = {}
    def append(self,name,targets=(),args=None):
        key = tuple(targets)
        encoded = self.targets.get(key)
        if encoded is None:
            encoded = " ".join(str(t) if isinstance(t,int) else f"rec[{t.value}]" for t in key)
            self.targets[key] = encoded
        if args is not None:
            values = args if isinstance(args,(tuple,list)) else (args,)
            name += "(" + ",".join(str(x) for x in values) + ")"
        self.lines.append(name + (" " + encoded if encoded else ""))
    def finish(self):
        return stim.Circuit("\n".join(self.lines))


class _MemoryWriter:
    """Compile ideal CNOT moments to H/CZ/H, then apply Table M4 noise."""
    def __init__(self,mesh,p,p_seam,noise):
        self.circuit = _CircuitText()
        self.mesh,self.p,self.p_seam,self.noise = mesh,p,p_seam,noise
        self.all = list(range(mesh["total_qubits"]))
        self.modules = [j//(mesh["L"]**2) for j in range(mesh["n"])] + [a["face"] for a in mesh["ancillas"]]
        self.measurements = 0

    def channel(self,kind,targets,probability):
        if targets and probability:
            self.circuit.append(kind,targets,probability)

    def tick(self):
        self.circuit.append("TICK")

    def h(self,targets):
        if not targets:
            return
        self.circuit.append("H",targets)
        if self.noise=="full":
            self.channel("DEPOLARIZE1",self.all,self.p/10)
        self.tick()

    def reset(self,targets,x_targets=()):
        if not targets:
            return
        self.circuit.append("R",targets)
        if self.noise=="full":
            self.channel("X_ERROR",targets,2*self.p)
            active = set(targets)
            self.channel("DEPOLARIZE1",[q for q in self.all if q not in active],2*self.p)
        self.tick()
        self.h(list(x_targets))

    def cx(self,pairs):
        if not pairs:
            return
        targets = [v for pair in pairs for v in pair]
        assert len(set(targets)) == len(targets),"gate collision"
        ht = [target for _,target in pairs]
        self.h(ht)
        self.circuit.append("CZ",targets)
        if self.noise!="none":
            bulk,seam = [],[]
            for a,b in pairs:
                (bulk if self.modules[a]==self.modules[b] else seam).extend((a,b))
            self.channel("DEPOLARIZE2",bulk,self.p)
            self.channel("DEPOLARIZE2",seam,self.p_seam)
        if self.noise=="full":
            busy = set(targets)
            self.channel("DEPOLARIZE1",[q for q in self.all if q not in busy],self.p/10)
        self.tick()
        self.h(ht)

    def measure(self,targets,x_targets=()):
        if not targets:
            return {}
        self.h(list(x_targets))
        if self.noise=="full":
            self.channel("DEPOLARIZE1",targets,self.p)
            active = set(targets)
            self.channel("DEPOLARIZE1",[q for q in self.all if q not in active],2*self.p)
        self.circuit.append("M",targets,5*self.p if self.noise=="full" else 0)
        records = {q:self.measurements+i for i,q in enumerate(targets)}
        self.measurements += len(targets)
        self.tick()
        return records

    def detector(self,records,check,round_index,kind):
        self.circuit.append("DETECTOR",[stim.target_rec(i-self.measurements) for i in records],
                            (check,0,round_index,kind))


@lru_cache(None)
def _logical_basis(q,L):
    mesh = geometry(q,L)
    return stabcode.css_logicals(mesh["hx"],mesh["hz"],mesh["n"])


def build(key,basis,rounds=5,p=0.001,p_seam=None,schedule=None,alternating=None,
          assignment=None,multi_rate=True,noise="full"):
    """A square-module memory, with k final-readout logical observables.

    Each measured ancilla has a unique check coordinate. Types 0/1 are
    Z-plaquettes/X-flags; types 3/4 are X-plaquettes/Z-flags. Thus use
    sector_problem(...,high=False) for Z memory and high=True for X memory.
    ``papers/run_parallel.py`` currently cannot pass this required argument.

    Multi-rate corners use prep/couple/read phases 0/1/2 modulo three.
    Pending cats are unencoded and read before the final data measurement;
    an uncoupled pending cat yields root and flag detectors directly.
    """
    q,L,key_kind,key_fb = _key_parts(key)
    if basis not in ("X","Z") or not isinstance(rounds,int) or rounds<1:
        raise ValueError("basis X/Z and a positive integer number of rounds required")
    if noise not in ("full","cx","none"):
        raise ValueError("noise must be full, cx, or none")
    if p_seam is None:
        p_seam = p
    if not (0<=p<=0.1 and 0<=p_seam<=1):
        raise ValueError("p must be in [0,.1], p_seam in [0,1]")
    kind = key_kind if schedule is None else schedule.upper()
    fb = key_fb if alternating is None else bool(alternating)
    mesh = geometry(q,L)
    if assignment is None:
        assignment = next(enumerate_schedules(q,kind,L=max(3,L)))
    assignment = tuple(assignment)
    if not validate_schedule(mesh,assignment,kind):
        raise ValueError("invalid lifted schedule")
    n = mesh["n"]
    roots,encoding = {},{}
    for check,indices in enumerate(mesh["check_ancillas"]):
        root,layers = cat_layers(indices)
        roots[check],encoding[check] = root,layers
    high = set(mesh["high_checks"]) if multi_rate else set()
    full = set(range(mesh["nchecks"]))-high
    writer = _MemoryWriter(mesh,p,p_seam,noise)
    writer.reset(list(range(n)),list(range(n)) if basis=="X" else ())
    pending,coupled,last = set(),set(),{}

    def reset_checks(checks):
        targets,x_targets = [],[]
        for check in sorted(checks):
            color = mesh["check_colors"][check]
            for a in mesh["check_ancillas"][check]:
                targets.append(n+a)
                if (a==roots[check]) == (color=="X"):
                    x_targets.append(n+a)
        writer.reset(targets,x_targets)

    def cat_stage(checks,inverse=False):
        depth = max((len(encoding[c]) for c in checks),default=0)
        for time in range(depth):
            pairs = []
            for check in sorted(checks):
                layers = encoding[check][::-1] if inverse else encoding[check]
                if time<len(layers):
                    for a,b in layers[time]:
                        if mesh["check_colors"][check]=="Z":
                            a,b = b,a
                        pairs.append((n+a,n+b))
            writer.cx(pairs)

    def read_checks(checks,t,uncoupled=()):
        targets,x_targets = [],[]
        for check in sorted(checks):
            color = mesh["check_colors"][check]
            for a in mesh["check_ancillas"][check]:
                targets.append(n+a)
                if (a==roots[check]) == (color=="X"):
                    x_targets.append(n+a)
        records = writer.measure(targets,x_targets)
        for check in sorted(checks):
            color,root = mesh["check_colors"][check],roots[check]
            now = records[n+root]
            if check in uncoupled:
                writer.detector([now],root,t,3 if color=="X" else 0)
            else:
                previous = last.get(check)
                if previous is not None:
                    writer.detector([previous,now],root,t,3 if color=="X" else 0)
                elif color==basis:
                    writer.detector([now],root,t,3 if color=="X" else 0)
                last[check] = now
            for a in mesh["check_ancillas"][check]:
                if a!=root:
                    writer.detector([records[n+a]],a,t,1 if color=="X" else 4)

    for t in range(rounds):
        preparing = full | (high if t%3==0 else set())
        reset_checks(preparing)
        cat_stage(preparing)
        pending.update(preparing & high)
        active = full | (high if t%3==1 else set())
        for layer in schedule_times(mesh,assignment,kind,reverse=fb and t%2==1):
            pairs = []
            for a,data,color in layer:
                if mesh["ancillas"][a]["check"] in active:
                    pairs.append((n+a,data) if color==0 else (data,n+a))
            writer.cx(pairs)
        coupled.update(active & high)
        measuring = full | (high if t%3==2 else set())
        cat_stage(measuring,inverse=True)
        read_checks(measuring,t)
        pending.difference_update(measuring)
        coupled.difference_update(measuring)
    if pending:
        cat_stage(pending,inverse=True)
        read_checks(pending,rounds,uncoupled=pending-coupled)
    records = writer.measure(list(range(n)),list(range(n)) if basis=="X" else ())
    for check,color in enumerate(mesh["check_colors"]):
        if color==basis:
            terms = [records[j] for j in stabcode.bits(mesh["rows"][check])]
            if check in last:
                terms.append(last[check])
            writer.detector(terms,roots[check],rounds+1,3 if color=="X" else 0)
    lx,lz = _logical_basis(q,L)
    for i,logical in enumerate(lx if basis=="X" else lz):
        writer.circuit.append("OBSERVABLE_INCLUDE",
                              [stim.target_rec(records[j]-writer.measurements) for j in stabcode.bits(logical)],i)
    circuit = writer.circuit.finish()
    assert circuit.num_qubits == mesh["total_qubits"]
    assert circuit.num_observables == q-2
    return circuit

