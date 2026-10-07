"""Plain builder checks and exact code-distance checks for arXiv:2603.05481.

The left-right circuit is staggered, so equality to the sequential effective
problem is recorded as a diagnostic, rather than assumed as a theorem.
"""
import collections
import json
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

import lrgross
import stabcode
from cdist import problem, search, symmetry

OUTPUT = os.path.join(ROOT, "results", "papers3", "lrgross", "builder_checks.json")
LABELS = {"N", "E", "S", "W", "NE", "SW"}


def save(report):
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as handle:
        json.dump(report, handle, indent=2)


def time_guard(signum, frame):
    raise TimeoutError("builder and code-distance checks exceeded 570 seconds")


def dem_problem(circuit, dem, name):
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
    return problem.Problem(name, circuit.num_detectors, circuit.num_observables,
                           h, logical,
                           [tuple(coords[i]) for i in range(circuit.num_detectors)],
                           meta, {"raw_mechanisms": raw})


def row_symmetry(p, candidates):
    index = {tuple(m): i for i, m in enumerate(p.row_meta)}
    perms = []
    for candidate in candidates:
        perm = [index.get((float(candidate[int(m[0])]),) + tuple(m[1:]))
                for m in p.row_meta]
        assert all(r is not None for r in perm), "translation changes detector times"
        perms.append(perm)
    sym = symmetry.from_row_perms(p, perms)
    assert sym.get("ok"), sym
    assert sym["n_symmetries_kept"] == len(candidates), sym
    return {"proposed": len(candidates), "kept": sym["n_symmetries_kept"],
            "orbits": len(sym["anchors"])}


def coordinates(circuit, basis, rounds):
    expected = {(i, 0, t, 3 if kind == "Z" else 0)
                for t in range(rounds + 1) for kind in "ZX"
                if t not in (0, rounds) or kind == basis
                for i in range(72)}
    actual = [tuple(c) for c in circuit.get_detector_coordinates().values()]
    assert len(actual) == len(set(actual)) == circuit.num_detectors == 144 * rounds
    assert set(actual) == expected, "detector coordinates or boundary checks differ"


def ideal_layers(circuit, xs, zs, rounds):
    """Inspect physical operations, ignoring the subsequent noise channels.

    Every completed ancilla measurement must follow exactly one support's six
    CNOTs. This checks extraction periods even when colors cross cycle borders.
    """
    rows = {kind: {frozenset(check.values()): i for i, check in enumerate(checks)}
            for kind, checks in (("X", xs), ("Z", zs))}
    assert all(len(rows[kind]) == 72 for kind in "XZ")
    used, pending, assigned = set(), {}, {}
    measured = collections.Counter()
    layers = cnot_layers = cnot_pairs = 0
    layer_has_cnot = False
    for inst in circuit.flattened():
        if inst.name == "TICK":
            layers += bool(used)
            cnot_layers += layer_has_cnot
            used, layer_has_cnot = set(), False
            continue
        if inst.name not in {"R", "RX", "M", "MX", "CX"}:
            continue
        targets = [t.value for t in inst.targets_copy()]
        assert len(targets) == len(set(targets)), (inst.name, "repeated target")
        assert not used.intersection(targets), (inst.name, "qubit reused within layer")
        used.update(targets)
        if inst.name == "CX":
            layer_has_cnot = True
            cnot_pairs += len(targets) // 2
            for control, target in zip(targets[::2], targets[1::2]):
                assert (control < 144) != (target < 144), "CNOT is not data-ancilla"
                kind, ancilla, data = (("Z", target, control) if control < 144
                                       else ("X", control, target))
                entry = pending.setdefault(ancilla, (kind, []))
                assert entry[0] == kind
                entry[1].append(data)
        elif inst.name in {"R", "RX"}:
            for ancilla in targets:
                if ancilla < 144:
                    continue
                assert ancilla not in pending, "reset discards a partial extraction"
        else:
            kind = "X" if inst.name == "MX" else "Z"
            for ancilla in targets:
                if ancilla < 144:
                    continue
                actual_kind, gates = pending.pop(ancilla)
                assert actual_kind == kind and len(gates) == len(set(gates)) == 6
                check = rows[kind].get(frozenset(gates))
                assert check is not None, (kind, ancilla, "gate set is not a check support")
                assert assigned.setdefault(ancilla, (kind, check)) == (kind, check)
                measured[kind, check] += 1
    layers += bool(used)
    cnot_layers += layer_has_cnot
    assert not pending, "unmeasured partial extraction remains"
    assert measured == collections.Counter({(kind, i): rounds for kind in "XZ" for i in range(72)})
    assert len(assigned) == 144
    assert cnot_pairs == rounds * 144 * 6
    return {"ideal_layers": layers, "cnot_layers": cnot_layers, "cnot_pairs": cnot_pairs,
            "all_extractions_match_supports": True, "layer_qubits_disjoint": True}


def check_distance(hx, hz, n, report):
    for basis in "ZX":
        started = time.monotonic()
        p = stabcode.css_distance_problem(hx, hz, n, basis, name="lrgross")
        sym = symmetry.from_row_perms(p, lrgross.code_translations())
        assert sym.get("ok"), sym
        assert sym["n_symmetries_kept"] == len(lrgross.code_translations())
        r = search.distance(p, k_table=3, kmax=12, cover=True, time_limit=90,
                            rank=sym["rank"], anchors=sym["anchors"])
        rec = {"distance": r["distance"], "lower_bound": r["lower_bound"],
               "seconds": time.monotonic() - started,
               "symmetries_kept": sym["n_symmetries_kept"],
               "witness": list(r["solutions"][0]) if r["solutions"] else None,
               "runs": [{"K": x["K"], "status": x["status"], "best": x["best"],
                         "nodes": sum(x["nodes"]), "seconds": x["seconds"]}
                        for x in r["runs"]]}
        report["code_distance"][basis] = rec
        save(report)
        assert r["distance"] == r["lower_bound"] == 12, (basis, rec)
        assert p.check(r["solutions"][0])[0] == 0 and p.check(r["solutions"][0])[1]
        print("code", basis, "exact distance", r["distance"], "seconds", round(rec["seconds"], 3), flush=True)


def column_set(p):
    checks = [int(m[0]) for m in p.row_meta]
    return {(sum(1 << checks[i] for i in stabcode.bits(a)), b)
            for a, b in zip(p.h, p.l)}


def check_printed_schedule(key):
    """Frozen chronological orders read from Figure 12, after each reset."""
    orders = {
        "X": (("SW", "W", "E", "S", "N", "NE"),
              ("W", "E", "SW", "S", "N", "NE"),
              ("SW", "W", "E", "N", "NE", "S")),
        "Z": (("S", "SW", "N", "NE", "E", "W"),
              ("S", "SW", "N", "W", "NE", "E"),
              ("SW", "N", "S", "W", "NE", "E")),
    }
    for kind in "XZ":
        for ci in range(72):
            assert tuple(lrgross.gate_order(kind, ci)) == orders[kind][lrgross.colour(kind, ci)]
    layers = lrgross.schedule(key, 3)
    assert len(layers) == 8 * 3 + 5

    def ideal_event(layer):
        return {name: (layer[name] if name in ("RX", "R", "CX")
                       else [anc for _, _, anc in layer[name]])
                for name in ("RX", "R", "CX", "MX", "M")}

    # Measurement logical-round indices advance; their physical targets repeat.
    assert [ideal_event(e) for e in layers[8:16]] == [ideal_event(e) for e in layers[16:24]]
    return {"printed_chronological_orders": True, "bulk_period": 8,
            "finite_extraction_layers_r3": len(layers)}


def main():
    started = time.monotonic()
    report = {"status": "running", "source": "arXiv:2603.05481v2",
              "code_distance": {}, "instances": {}}
    signal.signal(signal.SIGALRM, time_guard)
    signal.alarm(570)
    save(report)
    try:
        assert "lr11" in lrgross.CODES
        hx, hz, n = lrgross.matrices("lr11")
        assert (n, len(hx), len(hz)) == (144, 72, 72)
        assert stabcode.css_parameters(hx, hz, n) == (144, 12)
        assert stabcode.rank(hx) == stabcode.rank(hz) == 66
        assert {bin(r).count("1") for r in hx + hz} == {6}
        assert {sum((r >> q) & 1 for r in checks) for checks in (hx, hz) for q in range(n)} == {3}
        report["n_k"] = [144, 12]
        report["ranks"] = [66, 66]
        check_distance(hx, hz, n, report)
        for key in lrgross.CODES:
            assert lrgross.matrices(key) == (hx, hz, n)
            assert tuple(lrgross.CODES[key][2]) == (144, 12, 12)
            assert isinstance(lrgross.tag(key), str) and lrgross.tag(key)
            xs, zs = lrgross.supports(key)
            assert len(xs) == len(zs) == 72
            for checks, matrix in ((xs, hx), (zs, hz)):
                for check, row in zip(checks, matrix):
                    assert set(check) == LABELS
                    assert len(set(check.values())) == 6
                    assert all(0 <= q < n for q in check.values())
                    assert sum(1 << q for q in check.values()) == row
            code = lrgross.make_code(key)
            assert (code.n, code.k, code.hx, code.hz) == (144, 12, hx, hz)
            instance = {"paper_n_k_d": list(lrgross.CODES[key][2]),
                        "paper_circuit_distance": lrgross.CODES[key][3],
                        "schedule_checks": check_printed_schedule(key), "circuits": {}}
            report["instances"][str(key)] = instance
            for basis in "ZX":
                for rounds in (3, 6):
                    ideal = lrgross.build(key, basis, rounds, p=0)
                    assert ideal.num_qubits == 288 and ideal.num_observables == 12
                    coordinates(ideal, basis, rounds)
                    layer_info = ideal_layers(ideal, xs, zs, rounds)
                    ideal_dem = ideal.detector_error_model(decompose_errors=False, flatten_loops=True)
                    assert ideal_dem.num_errors == 0
                    dets, obs = ideal.compile_detector_sampler(seed=1234).sample(8, separate_observables=True)
                    assert not dets.any() and not obs.any(), (key, basis, rounds)
                    noise_columns = {}
                    for noise in ("full", "noidle"):
                        t0 = time.monotonic()
                        circuit = lrgross.build(key, basis, rounds, noise=noise)
                        assert circuit.num_qubits == 288 and circuit.num_observables == 12
                        coordinates(circuit, basis, rounds)
                        channels = collections.Counter(inst.name for inst in circuit.flattened())
                        assert channels["DEPOLARIZE2"] > 0
                        assert (channels["DEPOLARIZE1"] > 0) == (noise == "full")
                        dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=True)
                        assert dem.num_errors > 0
                        full = dem_problem(circuit, dem, f"lrgross:{key}:{basis}:{rounds}:{noise}")
                        noise_columns[noise] = set(zip(full.h, full.l))
                        sector = problem.sector_problem(full)
                        assert problem.sector_is_exact(full, sector), "CSS sector is only a relaxation"
                        sym = row_symmetry(sector, lrgross.translations(key))
                        rec = {"rounds": rounds, "noise": noise, "qubits": circuit.num_qubits,
                               "detectors": circuit.num_detectors, "observables": circuit.num_observables,
                               **layer_info, "deterministic_detectors": True,
                               "dem_mechanisms": dem.num_errors, "full_columns": full.ncols,
                               "sector_rows": sector.nrows, "sector_columns": sector.ncols,
                               "sector_reduction_exact": True, "translation_symmetries": sym,
                               "paper_extended_theorem_applicable": True,
                               "sequential_effective_theorem_applicable": False}
                        if hasattr(lrgross, "effective"):
                            try:
                                eff = lrgross.effective(key, basis)
                            except NotImplementedError as exc:
                                rec["effective_diagnostic"] = str(exc)
                            else:
                                eff_columns = set(zip(eff.h, eff.l))
                                rec["effective_columns"] = eff.ncols
                                rec["effective_columns_equal_collapsed_columns"] = (
                                    eff_columns == column_set(problem.collapse_time(sector)))
                                rec["effective_columns_equal_windows"] = {
                                    str(t): eff_columns == column_set(problem.window_problem(sector, t, t))
                                    for t in (0, 1)}
                                assert rec["effective_columns_equal_collapsed_columns"]
                                assert rec["effective_columns_equal_windows"]["1"]
                        rec["seconds"] = time.monotonic() - t0
                        label = f"{basis}_r{rounds}_{noise}"
                        instance["circuits"][label] = rec
                        print(key, label, "DEM", dem.num_errors, "sector exact; symmetries",
                              sym["kept"], "of", sym["proposed"], flush=True)
                        save(report)
                    assert noise_columns["full"] == noise_columns["noidle"]
                    for noise in ("full", "noidle"):
                        instance["circuits"][f"{basis}_r{rounds}_{noise}"]["full_noidle_dem_support_equal"] = True
            a = instance["circuits"]["Z_r3_full"]
            b = instance["circuits"]["Z_r6_full"]
            instance["layers_per_additional_round"] = {
                field: (b[field] - a[field]) / 3 for field in ("ideal_layers", "cnot_layers")}
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        signal.alarm(0)
        report["seconds"] = time.monotonic() - started
        save(report)
    print("PASS: gross [[144,12,12]] and left-right builders;", OUTPUT, flush=True)


if __name__ == "__main__":
    main()
