"""Plain structural verification and bounded exact checks of rebuilt tilings.

Run: .venv/bin/python tests/test_hyperbolic.py
Each selected distance check gets at most 55 seconds for all its thresholds.
Large epimorphism codes get base-tiling checks; refinements through L=4 are
checked directly for N <= 1344, keeping this laptop test below 4 GiB.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, deque
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("OMP_NUM_THREADS", "2")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "papers"))
sys.path.insert(0, str(ROOT))
import hyperbolic as codes
import hyperbolic_run as runner
import stabcode
from cdist import search, symmetry


def _orbit(generators, start=0):
    seen = {start}
    todo = deque([start])
    while todo:
        point = todo.popleft()
        for perm in generators:
            image = perm[point]
            if image not in seen:
                seen.add(image)
                todo.append(image)
    return seen


def _perm_order(perm):
    from math import gcd
    visited = set()
    order = 1
    for point in range(len(perm)):
        if point in visited:
            continue
        current, size = point, 0
        while current not in visited:
            visited.add(current)
            current = perm[current]
            size += 1
        assert current == point
        order = order * size // gcd(order, size)
    return order


def tiling_structure(triple):
    n = triple.N
    generators = triple.generators
    assert len(generators) == 3
    for perm in generators:
        assert sorted(perm) == list(range(n))
        assert all(perm[perm[j]] == j and perm[j] != j for j in range(n))
    assert len(_orbit(generators)) == n, "right action is not transitive"
    # A transitive commuting left action is a direct regularity certificate:
    # a right word fixing 0 fixes every left translate of 0, so is identity.
    left_generators = triple.left_generators()
    assert len(_orbit(left_generators)) == n, "left action is not transitive"
    for left in left_generators:
        assert sorted(left) == list(range(n))
        for right in generators:
            assert all(left[right[g]] == right[left[g]] for g in range(n))
    for (x, y), expected in zip(((0, 1), (1, 2), (2, 0)), triple.orders):
        assert _perm_order([generators[y][generators[x][g]] for g in range(n)]) == expected
        unseen = set(range(n))
        faces = []
        while unseen:
            face = _orbit((generators[x], generators[y]), min(unseen))
            assert len(face) == 2 * expected
            unseen.difference_update(face)
            faces.append(face)
        assert len(faces) * 2 * expected == n
    reciprocal_sum = sum(Fraction(1, order) for order in triple.orders)
    expected_k = 4 + n * (1 - reciprocal_sum)
    assert expected_k.denominator == 1
    if triple.orientable:
        assert int(expected_k) % 4 == 0
    return int(expected_k)


def _refined_edge_count(triple, L):
    """Enumerate lattice edges and glue base sides, retaining multiedges.

    This uses barycentric coordinates directly and does not inspect the
    builder's union-find, rows, small-triangle list or fine-mesh cache.
    """
    local_edges = set()
    for i in range(L):
        for j in range(L - i):
            k = L - i - j
            triangles = [((i, j, k), (i + 1, j, k - 1), (i, j + 1, k - 1))]
            if k >= 2:
                triangles.append(((i + 1, j, k - 1), (i, j + 1, k - 1),
                                  (i + 1, j + 1, k - 2)))
            for corners in triangles:
                for x, y in ((0, 1), (1, 2), (2, 0)):
                    local_edges.add(tuple(sorted((corners[x], corners[y]))))
    edges = set()
    for endpoints in local_edges:
        side = next((side for side in range(3)
                     if endpoints[0][side] == endpoints[1][side] == 0), None)
        for g in range(triple.N):
            # Reflection across a base side fixes barycentric position on
            # that side. Internal edges belong to one specific base triangle.
            owner = g if side is None else min(g, triple.generators[side][g])
            edges.add((3 if side is None else side, owner, endpoints))
    return len(edges)


def code_structure(triple, L, expected_k):
    rows, n = codes.color_code(triple, L)
    assert n == triple.N * L * L, "S14"
    assert 3 * n % 2 == 0
    assert _refined_edge_count(triple, L) == 3 * n // 2, "S15"
    count = Fraction(triple.N, 2) * (L * L - 1 + sum(Fraction(1, r) for r in triple.orders))
    assert count.denominator == 1 and len(rows) == int(count), "S16"
    assert len(set(rows)) == len(rows), "duplicate check supports"
    assert all(isinstance(row, int) and 0 < row < (1 << n) for row in rows)
    columns = runner._columns(rows, n)
    assert all(bin(column).count("1") == 3 for column in columns), "column weight is not 3"
    # Sparse product checks H H^T directly without a quadratic row-pair loop.
    for row in rows:
        syndrome = 0
        for qubit in stabcode.bits(row):
            syndrome ^= columns[qubit]
        assert syndrome == 0, "H H^T is nonzero"
    assert n - 2 * len(runner._echelon(rows)) == expected_k, "S13"
    corners = sum(triple.N // (2 * order) for order in triple.orders)
    expected_weights = Counter()
    for order in triple.orders:
        expected_weights[2 * order] += triple.N // (2 * order)
    expected_weights[6] += len(rows) - corners
    assert Counter(bin(row).count("1") for row in rows) == +expected_weights
    permutations = codes.symmetries(triple, L)
    assert len(permutations) == len(triple.left_generators())
    for row_perm, left in zip(permutations, triple.left_generators()):
        assert sorted(row_perm) == list(range(len(rows)))
        # Use the independently induced qubit action g,i -> h*g,i; verify
        # every advertised row permutation maps the whole row set onto itself.
        for qubit, column in enumerate(columns):
            image = 0
            for row in stabcode.bits(column):
                image |= 1 << row_perm[row]
            base, offset = divmod(qubit, L * L)
            assert image == columns[left[base] * L * L + offset]
    return n


def _resource_policy_checks():
    # No table is allocated by this check. With >64 label bits the kernel
    # uses 9-byte slots; these instances isolate table-size selection.
    small = SimpleNamespace(ncols=144, nobs=8, nrows=0, h=[])
    medium = SimpleNamespace(ncols=1000, nobs=100, nrows=0, h=[])
    large = SimpleNamespace(ncols=20000, nobs=100, nrows=0, h=[])
    assert runner.table_policy(small)["k_table"] == 3
    assert runner.table_policy(medium)["k_table"] == 2
    assert runner.table_policy(large)["k_table"] == 1
    assert runner._resumed_lower_bound({"lower_bound": 99, "runs": []}) == 1
    assert runner._resumed_lower_bound({"runs": [{"K": 1, "status": "exhausted", "best": None},
                                                        {"K": 2, "status": "timeout", "best": None}]}) == 2


def _large_label_checks():
    # This branch does not need paired logicals. Embed two orthogonal even
    # rows in a 2049-coordinate self-dual code to exercise the large builder.
    rows, n = [3, 12], 2049
    basis, columns = runner._check_self_dual(rows, rows, n)
    problem = runner._distance_problem(rows, rows, n, "label_control", basis, columns)
    physical_to_column = {physical: column for column, metadata in enumerate(problem.col_meta)
                          for _, physical in metadata}
    for support, expected_logical in (([0, 1], False), ([2, 3], False),
                                       ([0, 1, 2, 3], False), ([4], True), ([0], True)):
        # dedupe merges equal physical columns; sums use each merged column
        # with its parity, so two equivalent physical qubits cancel here.
        multiplicities = Counter(physical_to_column[j] for j in support)
        syndrome, logical = problem.check([j for j, count in multiplicities.items() if count % 2])
        assert bool(logical) == expected_logical
        assert bool(syndrome) == (support == [0])


def _checkpoint_checks():
    verified = 0
    for path in sorted((ROOT / "results/papers4/hyperbolic").glob("*.json")):
        payload = json.loads(path.read_text())
        if not isinstance(payload, dict):
            continue
        for record in payload.get("codes", []):
            if "matrix_sha256" not in record or "distance" not in record:
                continue
            hx, hz, n = codes.matrices(record["name"])
            assert hx == hz
            basis = runner._echelon(hx)
            assert n - 2 * len(basis) == record["k"]
            for result in record["distance"].values():
                lower = runner._resumed_lower_bound(result)
                assert lower == result["lower_bound"]
                if result.get("witness") is not None:
                    runner._check_witness(hx, hz, n, result["witness"], basis)
                    assert len(result["witness"]) == result["upper_bound"]
                    verified += 1
                if result.get("d") is not None:
                    assert result["d"] == result["lower_bound"] == result["upper_bound"]
    return verified


def structural_checks():
    """Run structural checks only and return one verified record per mesh."""
    triples = codes.available_tilings() if hasattr(codes, "available_tilings") else list(codes.TILINGS.values())
    # of the GAP/LINS tilings (hundreds) only those that carry a row of the paper are checked here
    labelled = {c["tiling"] for c in codes.CODES if c.get("paper_label")}
    triples = [t for t in triples if not t.name.startswith("lins") or t.name in labelled]
    records = []
    for triple in triples:
        k = tiling_structure(triple)
        for L in (range(1, 5) if triple.N <= 1344 else (1,)):
            n = code_structure(triple, L, k)
            records.append(dict(tiling=triple.name, N=triple.N, L=L, n=n, k=k,
                                edges=3 * n // 2, edge_count_method="independent barycentric edge enumeration",
                                orientable=triple.orientable, status="passed"))
        print(f"OK structural: {triple.name}, N={triple.N}, k={k}, orientable={triple.orientable}", flush=True)
        # Fine meshes contain wide Python integers; don't retain meshes of
        # completed tilings in the test process's construction cache.
        if hasattr(codes, "_fine") and hasattr(codes._fine, "cache_clear"):
            codes._fine.cache_clear()
    return records


def main():
    assert int(os.environ["OMP_NUM_THREADS"]) > 0
    names = [code["name"] for code in codes.CODES]
    assert len(names) == len(set(names))
    structural = structural_checks()
    _resource_policy_checks()
    _large_label_checks()
    required = {"bolza_L1": 2, "bolza_L2": 6, "bolza_L3": 8, "bolza_L4": 12}
    # Every order-32 cover is checked; metadata may leave its paper identity
    # unresolved, so only identified certified covers are compared here.
    for code in codes.CODES:
        if code.get("N") == 32 and code["L"] <= 3 and code.get("status") == "certified":
            required[code["name"]] = code["d_claimed"]
    exact = 0
    for name, expected in required.items():
        hx, hz, n = codes.matrices(name)
        assert hx == hz
        problem = stabcode.css_distance_problem(hx, hz, n, "Z", name=name)
        sym = symmetry.from_row_perms(problem, codes.symmetries(name))
        kwargs = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {}
        estimate = runner.table_policy(problem)
        result = search.distance(problem, k_table=estimate["k_table"], kmax=expected,
                                 time_limit=55 / expected, cover=True, **kwargs)
        assert result["distance"] == expected, (name, result["distance"], result["lower_bound"],
                                                 result["runs"][-1]["status"])
        support = runner._physical_witness(problem, result["solutions"][0])
        runner._check_witness(hx, hz, n, support)
        exact += 1
        print(f"OK exact: {name} [[{n},{n - 2 * len(runner._echelon(hx))},{expected}]]", flush=True)
    witnesses = _checkpoint_checks()
    print(f"PASS: {len({record['tiling'] for record in structural})} regular smooth tilings, {len(structural)} meshes; "
          f"{exact} exact distances; {witnesses} saved witnesses; memory policy and resume checks", flush=True)


if __name__ == "__main__":
    main()
