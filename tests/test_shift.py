"""Lightweight builder checks for the lead-approved shift reconstruction.

Nominal twisted codes use the corrected lattice dimensions.  Literal Table I
dimension orderings remain separate audit facts, and cannot build experiments.
The dynamic and mixed experiments implement the literal Table III inverse x
shift.  These checks use no distance searches and leave source_audit.json alone.
"""
import json
import itertools
import os
import signal
import sys
import time

sys.dont_write_bytecode = True
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "papers"))

import shift
import stabcode
from cdist import problem, symmetry


NOMINAL = {"72": (72, 12), "120": (120, 8),
           "144": (144, 12), "170": (170, 16)}
LITERAL = {"120lit": (120, 0), "170lit": (170, 0)}
OUTPUT = os.path.join(ROOT, "results", "papers3", "shift", "builder_checks.json")


def reduce_mod(v, basis, pivots):
    for b, p in zip(basis, pivots):
        if (v >> p) & 1:
            v ^= b
    return v


def conjugate(v, gates, kind):
    """Exact CNOT conjugation of an X-only or Z-only Pauli bitmask."""
    for targets in gates:
        for control, target in zip(targets[::2], targets[1::2]):
            source, dest = (control, target) if kind == "X" else (target, control)
            if (v >> source) & 1:
                v ^= 1 << dest
    return v


def permute(v, images):
    return sum(1 << images[j] for j in stabcode.bits(v))


def logical_map_check(key, suffix, rounds, numbering=None):
    """Check all logical generators, not only uniformly prepared memories.

    On the code space all measured ancillas have deterministic eigenvalues;
    ideal measurements and reinitializations can therefore be omitted when
    checking the CNOT unitary modulo code and prepared-ancilla stabilizers.
    CSS CNOT conjugation introduces no Pauli sign.
    """
    variant = key + suffix
    hx, hz, n = shift.matrices(variant)
    count = n // 2
    kinds = list(shift.cycle_kinds(variant, rounds))
    assert kinds.count("first") == kinds.count("second") == 1
    dx, dy = shift.pair_shift(key, numbering)
    expected = ([shift.qubit(key, "R", u, dx, dy) for u in range(count)] +
                [shift.qubit(key, "L", u, dx, dy) for u in range(count)])
    assert shift.data_map(variant, rounds, numbering=numbering) == expected
    gates = [targets for t in range(rounds)
             for targets in shift.layers(variant, t, rounds=rounds, numbering=numbering)]
    lx, lz = stabcode.css_logicals(hx, hz, n)
    report = {"rounds": rounds, "cycle_kinds": kinds, "shift": shift.monomial(dx, dy)}
    for kind, checks, logs, block in (("X", hx, lx, "X"), ("Z", hz, lz, "Z")):
        stabs = checks + [1 << shift.qubit(key, block, u) for u in range(count)]
        span, pivots = stabcode.rref(stabs)
        assert all(reduce_mod(conjugate(v, gates, kind), span, pivots) == 0
                   for v in stabs), (variant, kind, "stabilizers not preserved")
        matches = sum(reduce_mod(conjugate(v, gates, kind) ^ permute(v, expected),
                                 span, pivots) == 0 for v in logs)
        assert matches == len(logs), (variant, kind, matches, len(logs))
        report[kind] = {"generators": len(logs), "translation_matches": matches,
                        "stabilizers_preserved": True}
        if (dx, dy) == (-1, 0):
            report[kind]["inverse_x_matches"] = matches
    return report


def numbering_check():
    """Enumerate schedule validity without searches; test the moving frame."""
    default = ((1, 2, 3), (1, 2, 3))
    assert shift.normalize_numbering() == default
    for bad in (((1, 1, 3), (1, 2, 3)), ((0, 1, 2), (1, 2, 3)),
                ((1, 2), (1, 2, 3)), ((1.0, 2, 3), (1, 2, 3)), None):
        if bad is None:
            continue
        assert rejection_check("72d", "Z", 2, numbering=bad)
    for suffix in ("s", "d", "m", "b", "b1", "b2"):
        for basis in "ZX":
            assert shift.build("72" + suffix, basis, 2) == shift.build(
                "72" + suffix, basis, 2, numbering=default)
    rows = []
    for pa in itertools.permutations((1, 2, 3)):
        for pb in itertools.permutations((1, 2, 3)):
            numbering = (pa, pb)
            a, b = shift.numbered_terms("72", numbering)
            assert a == tuple(shift.DEFINITIONS["72"][3][i - 1] for i in pa)
            assert b == tuple(shift.DEFINITIONS["72"][4][i - 1] for i in pb)
            row = {"A": pa, "B": pb}
            for suffix in ("s", "d"):
                valid = True
                failures = {}
                for basis in "ZX":
                    try:
                        for t in range(2):
                            for targets in shift.layers("72" + suffix, t, rounds=2, numbering=numbering):
                                assert len(targets) == len(set(targets))
                        circuit = shift.build("72" + suffix, basis, 2, p=0, numbering=numbering)
                        dem = circuit.detector_error_model(decompose_errors=False)
                        assert dem.num_errors == 0
                    except ValueError as exc:
                        valid = False
                        failures[basis] = str(exc).splitlines()[0]
                row["valid_" + suffix] = valid
                row["failures_" + suffix] = failures
            if row["valid_d"]:
                row["logical_action"] = logical_map_check("72", "d", 2, numbering)
                logical_map_check("72", "m", 4, numbering)
            rows.append(row)
    return {"cases": rows, "valid_s": sum(r["valid_s"] for r in rows),
            "valid_d": sum(r["valid_d"] for r in rows), "numberings": len(rows)}


def dem_problem(circuit, dem, name):
    """The project's undecomposed DEM parser, using an in-memory circuit."""
    h, logical = [], []
    for inst in dem:
        if inst.type != "error":
            continue
        a = b = 0
        for target in inst.targets_copy():
            if target.is_relative_detector_id():
                a ^= 1 << target.val
            elif target.is_logical_observable_id():
                b ^= 1 << target.val
        h.append(a)
        logical.append(b)
    raw = len(h)
    h, logical, meta = problem.dedupe(h, logical, list(range(raw)))
    coords = circuit.get_detector_coordinates()
    rows = [tuple(coords.get(i, ())) for i in range(circuit.num_detectors)]
    return problem.Problem(name, circuit.num_detectors, circuit.num_observables,
                           h, logical, rows, meta, {"raw_mechanisms": raw})


def sector_symmetry_counts(sector, candidates):
    """Apply precisely the row-coordinate convention used by run_parallel."""
    index = {tuple(m): i for i, m in enumerate(sector.row_meta)}
    row_perms = []
    for cells in candidates:
        perm = [index.get((float(cells[int(m[0])]),) + tuple(m[1:]))
                for m in sector.row_meta]
        if all(j is not None for j in perm):
            row_perms.append(perm)
    sym = symmetry.from_row_perms(sector, row_perms)
    return {"proposed": len(candidates), "coordinate_permutations": len(row_perms),
            "valid": sym.get("ok", False),
            "kept": sym.get("n_symmetries_kept"),
            "orbits": len(sym["anchors"]) if sym.get("ok") else None,
            "reason": sym.get("reason")}


def detector_coordinates_check(circuit, n, basis, rounds):
    count = n // 2
    expected = {(u, 0, t, 3 if kind == "Z" else 0)
                for t in range(rounds + 1) for kind in "ZX"
                if t not in (0, rounds) or kind == basis
                for u in range(count)}
    actual = [tuple(v) for v in circuit.get_detector_coordinates().values()]
    assert len(actual) == circuit.num_detectors == n * rounds
    assert len(set(actual)) == len(actual)
    assert set(actual) == expected


def rejection_check(key, basis, rounds, **kwargs):
    try:
        shift.build(key, basis, rounds, **kwargs)
    except ValueError:
        return True
    raise AssertionError((key, basis, rounds, "invalid experiment accepted"))


def save(report):
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(report, f, indent=2)


def main():
    def timed_out(signum, frame):
        raise TimeoutError("builder checks reached the 570-second local wall limit")

    signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(570)
    started = time.monotonic()
    report = {"status": "running", "source": "arXiv:2601.09911v1",
              "nominal_dimensions": "corrected using cited base-code lattice",
              "dynamic_shift": "x^-1", "nominal": {}, "literal_audit_facts": {}}
    save(report)
    try:
        for key, expected in LITERAL.items():
            hx, hz, n = shift.matrices(key)
            actual = stabcode.css_parameters(hx, hz, n)
            assert actual == expected, (key, actual, expected)
            assert {bin(v).count("1") for v in hx + hz} == {6}
            assert shift.tag(key) == key
            checks = [rejection_check(key, basis, 6, p=p, noise=noise)
                      for basis in "ZX" for p in (0, 0.001)
                      for noise in ("full", "noidle")]
            report["literal_audit_facts"][key] = {
                "n_k": actual, "ranks": [stabcode.rank(hx), stabcode.rank(hz)],
                "definition": shift.DEFINITIONS[key], "build_forbidden": all(checks)}

        for key, expected in NOMINAL.items():
            hx, hz, n = shift.matrices(key)
            actual = stabcode.css_parameters(hx, hz, n)  # asserts the CSS condition
            assert actual == expected, (key, actual, expected)
            assert {bin(v).count("1") for v in hx + hz} == {6}
            assert shift.matrices(int(key)) == (hx, hz, n)
            assert shift.tag(int(key)) == key
            assert shift.CODES[int(key)][2][:2] == expected
            rec = {"n_k": actual, "paper_n_k_d": shift.CODES[key][2],
                   "definition": shift.DEFINITIONS[key],
                   "ranks": [stabcode.rank(hx), stabcode.rank(hz)],
                   "css": True, "circuits": {}, "logical_maps": {}}
            report["nominal"][key] = rec
            for variant in (key, key + "s", key + "d", key + "m", key + "b",
                            key + "b1", key + "b2"):
                assert shift.tag(variant) == variant
                assert shift.matrices(variant) == (hx, hz, n)
                assert shift.CODES[variant][2][:2] == expected

            assert shift.BASE_FIRST == tuple(
                tuple((c, p, t, False) for c, p, t, _ in layer)
                for layer in shift.DYNAMIC_ODD)
            assert shift.BASE_SECOND == tuple(
                tuple((c, p, t, False) for c, p, t, _ in layer)
                for layer in shift.DYNAMIC_EVEN)
            assert shift.layers(key + "b") == shift.layers(key + "b2")
            assert shift.data_map(key + "b", 2) == list(range(n))
            invalid = {}
            for basis in "ZX":
                assert shift.build(key + "b", basis, 2) == shift.build(key + "b2", basis, 2)
                for noise in ("full", "noidle"):
                    circuit = shift.build(key + "b1", basis, 2, noise=noise)
                    for t in range(2):
                        for targets in shift.layers(key + "b1", t, rounds=2):
                            assert len(targets) == len(set(targets))
                    try:
                        circuit.detector_error_model(decompose_errors=False)
                    except ValueError as exc:
                        assert "non-deterministic" in str(exc)
                        invalid[basis + "_" + noise] = str(exc).splitlines()[0]
                    else:
                        raise AssertionError((key + "b1", basis, "invalid unreversal unexpectedly deterministic"))
            rec["literal_base_first_invalid"] = invalid

            for suffix in ("s", "d", "m", "b"):
                variant = key + suffix
                # Exercise every distinct transition using the shortest
                # sequence containing it. Six-cycle distances and symmetries
                # are independently checked by run_parallel's local batch.
                rounds = 2 if suffix in ("s", "b") else 4
                kinds = list(shift.cycle_kinds(variant, rounds))
                assert len(kinds) == rounds
                if suffix == "s":
                    assert kinds == ["s"] * rounds
                elif suffix == "b":
                    assert kinds == ["b2"] * rounds
                elif suffix == "d":
                    assert kinds == ["first", "second"] * (rounds // 2)
                else:
                    expected_kinds = ["s"] * rounds
                    expected_kinds[rounds // 2 - 1:rounds // 2 + 1] = ["first", "second"]
                    assert kinds == expected_kinds
                layer_counts = []
                for t, kind in enumerate(kinds):
                    layers = shift.layers(variant, t, rounds=rounds)
                    layer_counts.append(len(layers))
                    assert len(layers) == (8 if kind == "first" else 7)
                    for targets in layers:
                        assert len(targets) % 2 == 0
                        assert len(targets) == len(set(targets)), (variant, t)
                        assert all(0 <= q < 2 * n for q in targets)
                if suffix in ("d", "m"):
                    assert rejection_check(variant, "Z", 3, p=0)

                for basis in "ZX":
                    ideal = shift.build(variant, basis, rounds, p=0)
                    ideal_dem = ideal.detector_error_model(decompose_errors=False, flatten_loops=True)
                    assert ideal_dem.num_errors == 0
                    assert ideal.num_qubits == 2 * n
                    assert ideal.num_observables == actual[1]
                    detector_coordinates_check(ideal, n, basis, rounds)
                    dets, obs = ideal.compile_detector_sampler(seed=1234).sample(
                        4, separate_observables=True)
                    assert not dets.any() and not obs.any(), (variant, basis)

                    supports = {}
                    full_sym = None
                    for noise in ("full", "noidle"):
                        t0 = time.monotonic()
                        circuit = shift.build(variant, basis, rounds, noise=noise)
                        assert circuit.num_qubits == 2 * n
                        assert circuit.num_observables == actual[1]
                        detector_coordinates_check(circuit, n, basis, rounds)
                        dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=True)
                        assert dem.num_errors > 0
                        full = dem_problem(circuit, dem, f"shift:{variant}:{basis}:{noise}")
                        assert full.notes["raw_mechanisms"] == dem.num_errors
                        sector = problem.sector_problem(full)
                        exact = problem.sector_is_exact(full, sector)
                        assert exact, (variant, basis, noise, "CSS sector only a relaxation")
                        supports[noise] = set(zip(full.h, full.l))
                        if noise == "noidle":
                            assert supports[noise] == supports["full"], (variant, basis, "idle support differs")
                            # Identical columns and row coordinates imply the
                            # same sector symmetries, without repeating the
                            # expensive logical-label consistency elimination.
                            sym = dict(full_sym)
                            sym["method"] = "inferred from verified full/noidle support identity"
                        else:
                            sym = {"proposed": len(shift.translations(variant)), "kept": None,
                                   "reason": "circuit symmetries measured by run_parallel, not repeated in transition tests"}
                            full_sym = sym
                        label = f"{variant}_{basis}_{noise}"
                        rec["circuits"][label] = {
                            "rounds": rounds, "cycle_kinds": kinds,
                            "qubits": circuit.num_qubits, "detectors": circuit.num_detectors,
                            "observables": circuit.num_observables,
                            "cnot_layers_per_cycle": layer_counts,
                            "ideal_deterministic": True, "noisy_dem_builds": True,
                            "dem_mechanisms": dem.num_errors, "full_columns": full.ncols,
                            "sector_rows": sector.nrows, "sector_columns": sector.ncols,
                            "sector_reduction_exact": exact, "translation_symmetries": sym,
                            "full_noidle_support_equal": True if noise == "noidle" else None,
                            "seconds": time.monotonic() - t0}
                        print(label, "DEM", dem.num_errors, "sector exact", exact,
                              "symmetries", sym["kept"], "of", sym["proposed"], flush=True)
                        save(report)

            rec["logical_maps"][key + "d"] = logical_map_check(key, "d", 2)
            rec["logical_maps"][key + "m"] = logical_map_check(key, "m", 6)
            print(key, "(n,k)", actual, "all builder and inverse-shift checks passed", flush=True)
            save(report)
        report["status"] = "passed"
        report["numberings_72"] = numbering_check()
        report["seconds"] = time.monotonic() - started
        save(report)
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = type(exc).__name__ + ": " + str(exc)
        report["seconds"] = time.monotonic() - started
        save(report)
        raise
    print("Builder checks passed:", OUTPUT, flush=True)
    signal.alarm(0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
