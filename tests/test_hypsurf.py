"""Plain verification of the Table S2 square-module reconstruction.

Run with .venv/bin/python tests/test_hypsurf.py. The code-distance checks
are an exact breadth-first search of the double-cover syndrome graphs,
independent of the circuit builder and without exponential lookup tables.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, deque
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("OMP_NUM_THREADS", "2")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "papers"))
sys.path.insert(0, str(ROOT))

import hypsurf as codes
import stabcode
from cdist import problem


def _order(permutation):
    from math import lcm
    seen = set()
    order = 1
    for start in range(len(permutation)):
        if start in seen:
            continue
        current, length = start, 0
        while current not in seen:
            seen.add(current)
            length += 1
            current = permutation[current]
        assert current == start
        order = lcm(order, length)
    return order


def _generated_order(generators):
    """Explicitly enumerate the generated permutation group (N <= 96)."""
    identity = tuple(range(len(generators[0])))
    seen = {identity}
    todo = [identity]
    while todo:
        permutation = todo.pop()
        for generator in generators:
            image = tuple(generator[value] for value in permutation)
            if image not in seen:
                seen.add(image)
                todo.append(image)
    return len(seen)


def tiling_checks(q):
    base = codes.tiling(q)
    n = base["ntri"]
    generators = [base[name] for name in "abc"]
    assert n == 8 * q
    for permutation in generators:
        assert sorted(permutation) == list(range(n))
        assert all(permutation[permutation[i]] == i and permutation[i] != i for i in range(n))
    assert _generated_order(generators) == n, "not a regular quotient action"
    reachable, todo = {0}, [0]
    while todo:
        current = todo.pop()
        for generator in generators:
            image = generator[current]
            if image not in reachable:
                reachable.add(image)
                todo.append(image)
    assert len(reachable) == n
    for (first, second), expected in zip(((0, 1), (1, 2), (2, 0)), (2, 4, q)):
        assert _order(tuple(generators[second][generators[first][i]] for i in range(n))) == expected
    assert len(base["faces"]) == q and all(len(face) == 8 for face in base["faces"])
    assert len(base["edges"]) == 2 * q and all(len(edge) == 4 for edge in base["edges"])
    assert len(base["vertices"]) == 4 and all(len(vertex) == 2 * q for vertex in base["vertices"])
    assert len(base["side_pairs"]) == 2 * q
    assert len(base["corner_cycles"]) == 4
    assert all(len(set(cycle)) == q for cycle in base["corner_cycles"])


def mesh_checks(q, L):
    mesh = codes.geometry(q, L)
    n, hx, hz = mesh["n"], mesh["hx"], mesh["hz"]
    assert n == q * L * L
    assert mesh["nchecks"] == q * (L * L - 1) + 4, "S23"
    assert n - stabcode.rank(hx) - stabcode.rank(hz) == q - 2, "S25"
    assert len(mesh["ancillas"]) == q * (L + 1) ** 2
    assert mesh["total_qubits"] == n + len(mesh["ancillas"])
    assert mesh["total_qubits"] == q * (2 * L * L + 2 * L + 1)
    assert all(isinstance(row, int) and 0 < row < (1 << n) for row in hx + hz)
    assert all(bin(x & z).count("1") % 2 == 0 for x in hx for z in hz)
    assert Counter(bin(row).count("1") for row in mesh["rows"]) == +Counter({4: mesh["nchecks"] - 4, q: 4})
    for qubit, corners in enumerate(mesh["data_corners"]):
        assert len(set(corners)) == 4
        colors = [mesh["check_colors"][check] for check in corners]
        assert colors in (["X", "Z", "X", "Z"], ["Z", "X", "Z", "X"])
        for check in corners:
            assert mesh["rows"][check] >> qubit & 1
    seen_ancillas = set()
    for check, indices in enumerate(mesh["check_ancillas"]):
        assert not seen_ancillas.intersection(indices)
        seen_ancillas.update(indices)
        expected = q if check in mesh["high_checks"] else (2 if len(indices) == 2 else 1)
        assert len(indices) == expected
        incidence_support = 0
        for index in indices:
            ancilla = mesh["ancillas"][index]
            assert ancilla["index"] == index and ancilla["check"] == check
            assert ancilla["color"] == mesh["check_colors"][check]
            assert len({direction for _, direction in ancilla["data"]}) == len(ancilla["data"])
            for data, direction in ancilla["data"]:
                assert data // (L * L) == ancilla["face"]
                assert 0 <= direction < 4
                incidence_support ^= 1 << data
        assert incidence_support == mesh["rows"][check]
    assert len(seen_ancillas) == mesh["nancillas"]
    return mesh


def exact_graph_distance(hx, hz, n, basis):
    """Exact any-logical distance by BFS in labeled syndrome double covers.

    Each data column has exactly two detectors, so a zero-syndrome error
    is an even subgraph, hence a sum of cycles. A nonzero logical label
    implies one cycle has an odd label in at least one logical bit. For
    each such bit, BFS from (v,0) to (v,1) finds the shortest odd closed
    walk. Minimizing over v and logical bits therefore finds the exact
    distance. Multiedges are retained. A physical witness is checked below.
    """
    model = stabcode.css_distance_problem(hx, hz, n, basis)
    adjacency = [[] for _ in range(model.nrows)]
    for column, (syndrome, logical) in enumerate(zip(model.h, model.l)):
        ends = stabcode.bits(syndrome)
        assert len(ends) == 2, "double-cover solver requires column weight two"
        first, second = ends
        adjacency[first].append((second, logical, column))
        adjacency[second].append((first, logical, column))
    best, witness = n + 1, None
    states = 2 * model.nrows
    for bit in range(model.nobs):
        for source in range(model.nrows):
            initial, target = 2 * source, 2 * source + 1
            distance = [-1] * states
            distance[initial] = 0
            parent = [None] * states
            todo = deque([initial])
            while todo:
                state = todo.popleft()
                if distance[state] + 1 >= best:
                    continue
                vertex, sheet = divmod(state, 2)
                for neighbor, logical, column in adjacency[vertex]:
                    image = 2 * neighbor + (sheet ^ ((logical >> bit) & 1))
                    if distance[image] >= 0:
                        continue
                    distance[image] = distance[state] + 1
                    parent[image] = (state, column)
                    if image == target:
                        best = distance[image]
                        mask = 0
                        current = image
                        while current != initial:
                            previous, edge = parent[current]
                            mask ^= 1 << edge
                            current = previous
                        witness = stabcode.bits(mask)
                        todo.clear()
                        break
                    todo.append(image)
    assert witness is not None
    syndrome, logical = model.check(witness)
    assert syndrome == 0 and logical != 0 and len(witness) == best
    physical = [model.col_meta[column][0][1] for column in witness]
    support = sum(1 << qubit for qubit in physical)
    detector_rows, stabilizer_rows = (hz, hx) if basis == "Z" else (hx, hz)
    assert all(bin(support & row).count("1") % 2 == 0 for row in detector_rows)
    assert stabcode.rank(list(stabilizer_rows) + [support]) == stabcode.rank(stabilizer_rows) + 1
    assert len(set(physical)) == best
    return {"d": best, "witness": physical,
            "method": "exact BFS of every single-logical-bit double cover, all graph vertices"}


def _dem_checks(circuit):
    # This also raises on any nondeterministic detector or observable.
    dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=True)
    mechanisms = 0
    for instruction in dem:
        if instruction.type != "error":
            continue
        detectors, observables = set(), set()
        for target in instruction.targets_copy():
            if target.is_relative_detector_id():
                value = target.val
                if value in detectors:
                    detectors.remove(value)
                else:
                    detectors.add(value)
            elif target.is_logical_observable_id():
                value = target.val
                if value in observables:
                    observables.remove(value)
                else:
                    observables.add(value)
        assert detectors or not observables, "one fault flips a logical with no detector"
        mechanisms += 1
    coordinates = circuit.get_detector_coordinates()
    assert len(coordinates) == circuit.num_detectors
    assert all(len(coordinate) == 4 and coordinate[1] == 0 for coordinate in coordinates.values())
    assert len({tuple(coordinate) for coordinate in coordinates.values()}) == circuit.num_detectors
    return mechanisms


def main():
    assert 1 <= int(os.environ["OMP_NUM_THREADS"]) <= 2
    distances, circuits, sectors = [], [], []
    for q in (6, 8, 10, 12):
        tiling_checks(q)
        for L in (1, 3, 5):
            mesh = mesh_checks(q, L)
            for basis in ("X", "Z"):
                result = exact_graph_distance(mesh["hx"], mesh["hz"], mesh["n"], basis)
                assert result["d"] == 2 * L, (q, L, basis, result)
                distances.append(dict(q=q, L=L, basis=basis, n=mesh["n"], k=q - 2, **result))
            print(f"OK exact code: {{4,{q}}}, L={L}, [[{mesh['n']},{q - 2},{2 * L}]], both bases", flush=True)
        mesh = codes.geometry(q, 5)
        for kind in ("ZZ", "NZ"):
            assert codes.count_schedules(q, kind, L=5) == 4 ** q
            constraints = codes.schedule_constraints(mesh, kind)
            assignments = list(codes.iter_schedule_assignments(constraints, limit=8))
            assert assignments, (q, kind, "no valid schedule")
            sampled = codes.sample_schedules(q, kind, count=8, L=5, seed=261003682)
            assert len(set(sampled)) == 8
            assert sampled == codes.sample_schedules(q, kind, count=8, L=5, seed=261003682)
            assignments.extend(sampled)
            for assignment in assignments:
                assert codes.validate_schedule(mesh, assignment, kind)
            assignment = assignments[0]
            for alternating in (False, True):
                for basis in ("X", "Z"):
                    circuit = codes.build(q, basis, 5, p=0.001, p_seam=0.003,
                                          schedule=kind, alternating=alternating,
                                          assignment=assignment, multi_rate=True)
                    assert circuit.num_qubits == {6: 366, 8: 488, 10: 610, 12: 732}[q]
                    assert circuit.num_observables == q - 2
                    count = _dem_checks(circuit)
                    circuits.append(dict(q=q, schedule=kind, alternating=alternating, basis=basis,
                                         qubits=circuit.num_qubits, detectors=circuit.num_detectors,
                                         observables=circuit.num_observables, mechanisms=count))
                    print(f"OK circuit: {{4,{q}}} {kind} {'alternating' if alternating else 'standard'} {basis}", flush=True)
    with TemporaryDirectory(prefix="hypsurf-test-") as directory:
        for L in (1, 3):
            for basis in ("X", "Z"):
                circuit = codes.build(f"q6_L{L}", basis, 5, p=0.001, p_seam=0.003)
                _dem_checks(circuit)
                path = Path(directory) / f"smallest_L{L}_{basis}.stim"
                circuit.to_file(path)
                full = problem.load_dem_problem(str(path))
                zero_classes = {metadata[3] >= 3 for metadata in full.row_meta if metadata[2] == 0}
                if L == 3:
                    assert zero_classes == {False, True}, "round zero must retain both flag sectors"
                    try:
                        problem.sector_problem(full)
                    except AssertionError:
                        pass
                    else:
                        raise AssertionError("default high inference should reject both round-zero classes")
                high = basis == "X"
                sector = problem.sector_problem(full, high=high)
                assert problem.sector_is_exact(full, sector), (L, basis, "sector is only a relaxation")
                collapsed = problem.collapse_time(sector)
                assert collapsed.nrows == len({(metadata[0], metadata[1]) for metadata in sector.row_meta})
                sectors.append(dict(L=L, basis=basis, high=high, full_rows=full.nrows, sector_rows=sector.nrows,
                                    sector_columns=sector.ncols, exact=True, collapsed_rows=collapsed.nrows))
    output = ROOT / "results/papers4/hypsurf/verification.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(code_distances=distances, circuits=circuits, sectors=sectors), indent=2) + "\n")
    print(f"PASS: 4 regular tilings, 12 meshes, {len(distances)} exact code distances, "
          f"{len(circuits)} deterministic square circuit variants, and {len(sectors)} exact CSS sectors", flush=True)


if __name__ == "__main__":
    main()
