"""Plain-script checks for the literal STAR codes and depth-eight circuits.

Run: OMP_NUM_THREADS=2 .venv/bin/python tests/test_star.py
The exact code search uses one CSS sector: H_X == H_Z proves equality of
the two sector distances. Circuit checks exercise both memory bases.
"""
import os
import sys
import time
from collections import Counter

os.environ.setdefault("OMP_NUM_THREADS", "2")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "papers"))

import numpy as np
import sdbb_parallel
import selfdual_bb
import star
import stabcode
from cdist import problem, search, symmetry
from papers import run_parallel


def permute(mask, perm):
    return sum(1 << perm[q] for q in stabcode.bits(mask))


def triangle_counts(h):
    """Qubit/check relabelling invariant of the check-intersection graph."""
    neighbors = [{j for j, other in enumerate(h) if i != j and row & other}
                 for i, row in enumerate(h)]
    return Counter(sum(j in neighbors[k] for j in neighbors[i]
                       for k in neighbors[i] if k < j)
                   for i in range(len(h)))


def expect_value_error(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def check_matrices_and_distance(n):
    hx, hz, nq = star.matrices(n)
    assert hx == hz
    assert nq == n and len(hx) == n // 2
    assert all(bin(row).count("1") == 8 for row in hx)
    assert stabcode.css_parameters(hx, hz, nq) == (n, 6)
    assert all(stabcode.parity(x & z) == 0 for x in hx for z in hz)

    # Independently use the rectangular BB constructor, whose indexing is
    # cell=i*m+j. STAR Torus indexing is cell=3*j+i, so compare after this
    # explicit row and column permutation.
    m, nc = n // 6, n // 2
    f = [(0, 0), (0, 3), (1, 2), (1, 4)]
    expected_x, expected_z, expected_n = stabcode.bb_matrices(
        3, m, f, [(-x, -y) for x, y in f])
    assert expected_n == n
    cp = [3 * j + i for i in range(3) for j in range(m)]
    dp = cp + [nc + q for q in cp]
    for expected, actual in ((expected_x, hx), (expected_z, hz)):
        assert all(permute(row, dp) == actual[cp[s]]
                   for s, row in enumerate(expected))

    row = next(c for c in selfdual_bb.CODES if c[0] == n)
    oldx, oldz, oldn, old_torus, _ = selfdual_bb.build(row[3], row[4], row[5])
    assert oldn == n
    if n == 42:
        # Pair-overlap counts alone coincide, but this stronger invariant
        # excludes every qubit/check permutation, not only affine maps.
        assert triangle_counts(oldx) == Counter({39: 21})
        assert triangle_counts(hx) == Counter({45: 21})
        expect_value_error(lambda: star.selfdual_relabelling(n))
        expect_value_error(lambda: star.mirror_schedule(n))
        print("42: inequivalent printed check matrices; triangles/check 39 (selfdual), 45 (STAR)", flush=True)
    else:
        cp, dp = star.selfdual_relabelling(n)
        t = star.torus(n)
        # Assert the independently derived affine map and the separate data
        # shifts, in addition to checking every individual check row.
        expected_cp = [t.index(-x, x + y) for x, y in old_torus.points]
        expected_dp = [t.index(-x + 1, x + y + 2) for x, y in old_torus.points]
        expected_dp += [nc + t.index(-x - 1, x + y - 2)
                        for x, y in old_torus.points]
        assert cp == expected_cp and dp == expected_dp
        assert sorted(cp) == list(range(nc))
        assert sorted(dp) == list(range(n))
        for old, new in ((oldx, hx), (oldz, hz)):
            assert all(permute(v, dp) == new[cp[s]] for s, v in enumerate(old))
        old_xs, old_zs, _ = sdbb_parallel.supports(n)
        new_xs, new_zs, _ = star.supports(n, star.mirror_schedule(n))
        for old, new in ((old_xs, new_xs), (old_zs, new_zs)):
            assert all([(layer, dp[q]) for layer, q in support] == new[cp[s]]
                       for s, support in enumerate(old))

    p = stabcode.css_distance_problem(hx, hz, nq, "Z", name=f"star{n}")
    sym = symmetry.from_row_perms(p, star.translations(n))
    assert sym["ok"] and sym["n_symmetries_kept"] == nc - 1
    start = time.monotonic()
    result = search.distance(p, k_table=2, kmax=star.CODES[n][2][2],
                             time_limit=90, cover=True,
                             rank=sym["rank"], anchors=sym["anchors"])
    assert result["distance"] == star.CODES[n][2][2], result
    assert result["lower_bound"] == result["distance"]
    assert result["solutions"]
    assert search.verify(p, result["solutions"][0])
    print(f"{n}: [[{n},6,{result['distance']}]], exact CSS search, "
          f"{time.monotonic() - start:.3f}s, "
          f"{sym['n_symmetries_kept']}/{nc - 1} code symmetries", flush=True)


def dem_problem(circuit, name):
    dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=True)
    h, l = [], []
    for instruction in dem:
        if instruction.type != "error":
            continue
        det = obs = 0
        for target in instruction.targets_copy():
            if target.is_relative_detector_id():
                det ^= 1 << target.val
            elif target.is_logical_observable_id():
                obs ^= 1 << target.val
        h.append(det)
        l.append(obs)
    mechanisms = len(h)
    hh, ll, meta = problem.dedupe(h, l, list(range(mechanisms)))
    coordinates = circuit.get_detector_coordinates()
    p = problem.Problem(name, circuit.num_detectors, circuit.num_observables,
                        hh, ll, [tuple(coordinates[i])
                                 for i in range(circuit.num_detectors)], meta,
                        {"raw_mechanisms": mechanisms})
    return p


def check_circuit(n, schedule_name, rounds=6):
    schedule = None if schedule_name == "paper" else star.mirror_schedule(n)
    xs, zs, _ = star.supports(n, schedule)
    hx, hz, _ = star.matrices(n)
    assert [sum(1 << q for _, q in support) for support in xs] == hx
    assert [sum(1 << q for _, q in support) for support in zs] == hz
    gates = star.layers(n, schedule)
    assert len(gates) == 8
    for layer in gates:
        assert len(layer) == 2 * n
        assert len(set(layer)) == len(layer)
        assert set(layer) == set(range(2 * n))
        for control, target in zip(layer[::2], layer[1::2]):
            assert (control < n) != (target < n)
    for basis in "ZX":
        full = star.build(n, basis, rounds, noise="full", schedule=schedule)
        noidle = star.build(n, basis, rounds, noise="noidle", schedule=schedule)
        # There is no inactive qubit in any entangling layer, so removing
        # entangling-layer idle channels changes no circuit instruction.
        assert full == noidle
        assert full.num_qubits == 2 * n
        assert full.num_observables == 6
        assert full.num_detectors == n * rounds
        actual_layers = [tuple(t.value for t in inst.targets_copy())
                         for inst in full.flattened() if inst.name == "CX"]
        assert actual_layers == [tuple(layer) for layer in gates] * rounds
        assert full.num_ticks == 1 + 10 * rounds
        detectors, observables = full.without_noise().compile_detector_sampler().sample(
            16, separate_observables=True)
        assert not np.any(detectors) and not np.any(observables)
        coordinates = full.get_detector_coordinates()
        expected_coordinates = {(i, 0, t, coord)
                                for t in range(rounds + 1)
                                for coord, check_basis in ((3, "Z"), (0, "X"))
                                if t not in (0, rounds) or basis == check_basis
                                for i in range(n // 2)}
        assert {tuple(coord) for coord in coordinates.values()} == expected_coordinates
        p = dem_problem(full, f"star{n}:{schedule_name}:{basis}")
        sector = problem.sector_problem(p)
        assert problem.sector_is_exact(p, sector)
        sym, _ = run_parallel.sym_of(sector, star.translations(n))
        assert sym["ok"] and sym["n_symmetries_kept"] == n // 2 - 1
        print(f"{n} {schedule_name} {basis} full=noidle: "
              f"qubits={full.num_qubits}, CNOT layers/cycle=8, "
              f"detectors={full.num_detectors}, "
              f"DEM mechanisms={p.notes['raw_mechanisms']}, "
              f"sector exact, symmetries={sym['n_symmetries_kept']}/{n // 2 - 1}",
              flush=True)


def check_schedule_family():
    schedules = star.valid_schedules(42)
    assert len(schedules) == 212
    assert len({(tuple(s["X"]), tuple(s["Z"])) for s in schedules}) == 212
    assert star.PAPER_SCHEDULE in schedules
    assert all(star.schedule_is_valid(42, schedule) for schedule in schedules)
    assert all(len(layer) == len(set(layer))
               for schedule in schedules for layer in star.layers(42, schedule))
    for n in (66, 78):
        schedule = star.mirror_schedule(n)
        assert star.schedule_is_valid(n, schedule)
        assert schedule not in schedules
        # The grammar fixes both X internal orders as ascending. Jointly
        # rename monomial i in Li and Ri using the mirror's X-left order;
        # its X-right order is then ascending too, and it is a grammar
        # member. This is schedule-grammar equivalence, not a change to the
        # physical polynomial or transported circuit.
        left_order = [int(label[1:]) for label in schedule["X"] if label[0] == "L"]
        rename = {a: b for b, a in enumerate(left_order, 1)}
        normalized = {basis: tuple(label[0] + str(rename[int(label[1:])])
                                   for label in order)
                      for basis, order in schedule.items()}
        assert normalized in schedules
    print("212 inferred-grammar schedules: unique, disjoint, symbolically clean; "
          "paper schedule included, 66/78 mirrors included after joint monomial renaming",
          flush=True)


def check_rejected_schedules():
    invalid = {"X": star.PAPER_SCHEDULE["X"], "Z": star.PAPER_SCHEDULE["X"]}
    expect_value_error(lambda: star.layers(42, invalid))
    # Swap two same-half Z couplings: layers remain disjoint and supports
    # unchanged, but ancilla back-action no longer cancels.
    unclean = {basis: list(order) for basis, order in star.PAPER_SCHEDULE.items()}
    unclean["Z"][0], unclean["Z"][2] = unclean["Z"][2], unclean["Z"][0]
    assert len(star.layers(42, unclean)) == 8
    assert not star.schedule_is_valid(42, unclean)
    for basis in "ZX":
        expect_value_error(lambda: star.build(42, basis, 2, schedule=unclean))
    print("Invalid overlapping and disjoint-but-unclean schedules rejected", flush=True)


def main():
    check_schedule_family()
    for n in (42, 66, 78):
        check_matrices_and_distance(n)
        check_circuit(n, "paper")
        if n != 42:
            check_circuit(n, "mirror")
    check_rejected_schedules()
    print("STAR tests passed", flush=True)


if __name__ == "__main__":
    main()
