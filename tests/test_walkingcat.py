"""Walking Cat reconstruction checks (plain script; no distance searches).

The generating polynomials and the optimized encounter orders below are
literal independent transcriptions of Tables 30 and 10 of arXiv:2604.19481.
Run with: .venv/bin/python tests/test_walkingcat.py
"""
import os
import sys

import stim

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "papers"))

import walkingcat
import stabcode
from cdist import problem, symmetry
from papers.run_parallel import row_perms


# (l, m, ordered monomials of A, ordered monomials of B, [[n,k,d]])
POLYNOMIALS = {
    102: (51, 1, ((22, 0), (26, 0), (37, 0), (50, 0)),
          ((19, 0), (28, 0), (29, 0), (35, 0)), (102, 22, 9)),
    70: (7, 5, ((0, 2), (2, 0), (3, 0), (4, 0)),
         ((0, 1), (1, 0), (3, 0)), (70, 6, 9)),
    54: (27, 1, ((8, 0), (13, 0), (15, 0), (16, 0)),
         ((7, 0), (8, 0), (10, 0), (15, 0)), (54, 2, 10)),
}

# At each encounter: (polynomial family, X-check term, Z-check term).
# Terms are numbered from 1 in the displayed order of Table 30. Z encounters
# use the transpose monomial on the opposite data block.
ORDERS = {
    102: (("B", 1, 4), ("A", 1, 2), ("A", 3, 4), ("B", 2, 3),
          ("B", 3, 2), ("A", 4, 3), ("A", 2, 1), ("B", 4, 1)),
    70: (("B", 1, 3), ("A", 1, 3), ("A", 4, 2), ("B", 2, 2),
         ("A", 3, 1), ("A", 2, 4), ("B", 3, 1)),
    54: (("B", 2, 1), ("A", 1, 4), ("B", 4, 3), ("A", 3, 2),
         ("A", 2, 3), ("B", 3, 4), ("A", 4, 1), ("B", 1, 2)),
}


def shift(site, term, l, m, inverse=False):
    i, j = divmod(site, m)
    a, b = term
    sign = -1 if inverse else 1
    return ((i + sign * a) % l) * m + (j + sign * b) % m


def expected_matrices(key):
    l, m, a, b, _ = POLYNOMIALS[key]
    sites = l * m
    hx, hz = [], []
    for u in range(sites):
        hx.append(sum(1 << shift(u, term, l, m) for term in a) |
                  sum(1 << (sites + shift(u, term, l, m)) for term in b))
        hz.append(sum(1 << shift(u, term, l, m, True) for term in b) |
                  sum(1 << (sites + shift(u, term, l, m, True)) for term in a))
    return hx, hz, 2 * sites


def expected_supports(key):
    l, m, a, b, _ = POLYNOMIALS[key]
    sites = l * m
    xs, zs = [], []
    for u in range(sites):
        x, z = [], []
        for layer, (family, tx, tz) in enumerate(ORDERS[key]):
            terms = a if family == "A" else b
            xblock = 0 if family == "A" else sites
            zblock = sites if family == "A" else 0
            x.append((layer, xblock + shift(u, terms[tx - 1], l, m)))
            z.append((layer, zblock + shift(u, terms[tz - 1], l, m, True)))
        xs.append(x)
        zs.append(z)
    return xs, zs


def expected_translations(key):
    l, m, _, _, _ = POLYNOMIALS[key]
    return {tuple(shift(u, (a, b), l, m) for u in range(l * m))
            for a in range(l) for b in range(m) if a or b}


def from_circuit(circuit, name):
    """Use the undecomposed DEM directly, without creating temporary files."""
    dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=True)
    h, logs = [], []
    for inst in dem:
        if inst.type != "error":
            continue
        a = b = 0
        for target in inst.targets_copy():
            if target.is_relative_detector_id():
                a ^= 1 << target.val
            elif target.is_logical_observable_id():
                b ^= 1 << target.val
            else:
                assert False, "undecomposed DEM contains a separator"
        h.append(a)
        logs.append(b)
    raw = len(h)
    h, logs, meta = problem.dedupe(h, logs, list(range(raw)))
    coords = circuit.get_detector_coordinates()
    p = problem.Problem(name, circuit.num_detectors, circuit.num_observables,
                        h, logs, [tuple(coords[i]) for i in range(circuit.num_detectors)],
                        meta, {"raw_mechanisms": raw})
    return p


def only_two_qubit_noise(circuit):
    """Keep the Pauli faults after two-qubit gates, with identical records."""
    gate_only = stim.Circuit()
    for inst in circuit.flattened():
        if inst.name == "DEPOLARIZE1":
            continue
        args = [0] if inst.name in {"M", "MX"} else inst.gate_args_copy()
        gate_only.append(inst.name, inst.targets_copy(), args)
    return gate_only


def check_translations(p, key, candidates):
    """Certify all translations by their generators on the full sector DEM.

    A composition of retained symmetry maps is a symmetry. Checking the one
    or two generators avoids repeating expensive logical-label elimination
    for every element of the same finite translation group.
    """
    l, m, _, _, _ = POLYNOMIALS[key]
    generators = []
    if l > 1:
        generators.append([shift(u, (1, 0), l, m) for u in range(l * m)])
    if m > 1:
        generators.append([shift(u, (0, 1), l, m) for u in range(l * m)])
    sym = symmetry.from_row_perms(p, row_perms(p, generators))
    assert sym["ok"] and sym["n_symmetries_kept"] == len(generators), (
        key, p.name, sym.get("reason"), sym.get("n_symmetries_kept"), len(generators))
    identity = tuple(range(l * m))
    generated = {identity}
    pending = [identity]
    while pending:
        perm = pending.pop()
        for generator in generators:
            image = tuple(generator[u] for u in perm)
            if image not in generated:
                generated.add(image)
                pending.append(image)
    assert generated - {identity} == {tuple(perm) for perm in candidates}
    return len(generated) - 1, len(generators)


def check_actual_circuit(key, basis, rounds, circuit):
    """Check actual gates and detector records, independently of supports()."""
    hx, hz, n = expected_matrices(key)
    sites = n // 2
    za = list(range(n, n + sites))
    xa = list(range(n + sites, 2 * n))
    assert circuit.num_qubits == 2 * n
    assert circuit.num_observables == POLYNOMIALS[key][4][1]
    assert circuit.num_detectors == rounds * n
    xs, zs = expected_supports(key)
    measurements = []
    gate_layers = []
    layer = []
    occupied = set()
    dets, obs = [], []

    # Noise channels touch the same qubits as their preceding ideal gates;
    # occupancy here concerns the actual ideal operations in each TICK layer.
    ideal = {"R", "RX", "M", "MX", "CX", "CZ"}
    for inst in circuit.flattened():
        targets = inst.targets_copy()
        if inst.name == "TICK":
            if layer:
                gate_layers.append(layer)
            layer = []
            occupied = set()
            continue
        if inst.name in ideal:
            qs = [target.value for target in targets]
            assert all(target.is_qubit_target for target in targets)
            assert len(qs) == len(set(qs)), (key, basis, "repeated qubit in instruction", inst)
            assert not occupied.intersection(qs), (key, basis, "qubit used twice in a layer", inst)
            occupied.update(qs)
            if inst.name in {"M", "MX"}:
                measurements.extend(qs)
            if inst.name in {"CX", "CZ"}:
                assert len(qs) % 2 == 0
                for anc, data in zip(qs[::2], qs[1::2]):
                    assert 0 <= data < n
                    if inst.name == "CX":
                        assert n + sites <= anc < 2 * n, "X check must control its data CNOT"
                        layer.append(("X", anc - n - sites, data))
                    else:
                        assert n <= anc < n + sites, "Z check must use a CZ ancilla"
                        layer.append(("Z", anc - n, data))
        if inst.name == "DETECTOR":
            coords = tuple(inst.gate_args_copy())
            assert len(coords) == 4
            check, zero, t, kind = coords
            assert check == int(check) and 0 <= check < sites and zero == 0
            assert t == int(t) and 0 <= t <= rounds and kind in (0, 3)
            check, t = int(check), int(t)
            memory_kind = 3 if basis == "Z" else 0
            offset = 0 if kind == 3 else sites
            if t == rounds:
                assert kind == memory_kind
                row = hz[check] if basis == "Z" else hx[check]
                expected = {(rounds - 1) * n + offset + check}
                expected.update(rounds * n + q for q in stabcode.bits(row))
            else:
                expected = {t * n + offset + check}
                if t == 0:
                    assert kind == memory_kind
                else:
                    expected.add((t - 1) * n + offset + check)
            assert all(target.is_measurement_record_target for target in targets)
            actual = [len(measurements) + target.value for target in targets]
            assert len(actual) == len(set(actual)) and set(actual) == expected, (
                key, basis, coords, actual, expected)
            dets.append(coords)
        if inst.name == "OBSERVABLE_INCLUDE":
            idx, = inst.gate_args_copy()
            assert idx == int(idx)
            assert all(target.is_measurement_record_target for target in targets)
            obs.append((int(idx), {len(measurements) + target.value for target in targets}))
    if layer:
        gate_layers.append(layer)
    assert measurements == (za + xa) * rounds + list(range(n)), "measurement order"
    assert len(gate_layers) == rounds * len(ORDERS[key])
    for cycle in range(rounds):
        for t in range(len(ORDERS[key])):
            actual = gate_layers[cycle * len(ORDERS[key]) + t]
            expected = [("X", i, xs[i][t][1]) for i in range(sites)]
            expected += [("Z", i, zs[i][t][1]) for i in range(sites)]
            assert len(actual) == n and set(actual) == set(expected), (
                key, basis, cycle, t, "actual gate order differs from Table 10")
    memory_kind = 3 if basis == "Z" else 0
    expected_coords = {(i, 0, t, memory_kind) for i in range(sites)
                       for t in range(rounds + 1)}
    expected_coords.update((i, 0, t, 3 - memory_kind) for i in range(sites)
                           for t in range(1, rounds))
    assert len(dets) == len(set(dets)) and set(dets) == expected_coords
    lx, lz = stabcode.css_logicals(hx, hz, n)
    logs = lz if basis == "Z" else lx
    assert obs == [(i, {rounds * n + q for q in stabcode.bits(row)})
                   for i, row in enumerate(logs)], "all k logicals must use final data measurements"


def main():
    assert set(walkingcat.CODES) == {102, 70, 54}
    for key in (102, 70, 54):
        hx, hz, n = walkingcat.matrices(key)
        assert (hx, hz, n) == expected_matrices(key), (key, "Table 30 matrices")
        assert stabcode.css_parameters(hx, hz, n) == POLYNOMIALS[key][4][:2]
        assert walkingcat.CODES[key][2] == POLYNOMIALS[key][4]
        assert walkingcat.CODES[key][3] == 9
        assert len({walkingcat.tag(k) for k in walkingcat.CODES}) == 3
        assert all(stabcode.parity(x & z) == 0 for x in hx for z in hz)
        assert walkingcat.supports(key) == expected_supports(key), (key, "Table 10 supports")
        candidates = walkingcat.translations(key)
        assert len(candidates) == len(expected_translations(key))
        assert {tuple(perm) for perm in candidates} == expected_translations(key)
        for basis in ("Z", "X"):
            for rounds in (2, 6):
                clean = walkingcat.build(key, basis, rounds, p=0)
                check_actual_circuit(key, basis, rounds, clean)
                clean.detector_error_model(decompose_errors=False)
                det, obs = clean.compile_detector_sampler(seed=12345).sample(
                    32, separate_observables=True)
                assert not det.any() and not obs.any(), "noiseless detectors/logicals must be deterministic"
                noisy = walkingcat.build(key, basis, rounds, p=0.001)
                p = from_circuit(noisy, f"walkingcat:{key}:{basis}:r{rounds}")
                sector = problem.sector_problem(p)
                assert problem.sector_is_exact(p, sector), (key, basis, "sector must preserve distance")
                assert sector.nrows == (rounds + 1) * (n // 2)
                nsym, ngen = check_translations(sector, key, candidates)
                if rounds == 6:
                    gate_only = from_circuit(only_two_qubit_noise(noisy), p.name + ":gate-only")
                    assert set(zip(p.h, p.l)) == set(zip(gate_only.h, gate_only.l)), (
                        key, basis, "non-gate Pauli locations change the DEM mechanism support")
                    print(f"Q{key} {basis}: (n,k)={POLYNOMIALS[key][4][:2]}, "
                          f"qubits={noisy.num_qubits}, 2q layers/cycle={len(ORDERS[key])}, "
                          f"detectors={noisy.num_detectors}, "
                          f"DEM mechanisms={p.notes['raw_mechanisms']}, "
                          f"sector exact, symmetries={nsym}/{len(candidates)} "
                          f"(certified by {ngen} generators), "
                          "gate-only DEM support identical", flush=True)
    print("ok: Walking Cat polynomials, Table 10 gate orders, layers, detectors, DEMs, and symmetries")


if __name__ == "__main__":
    import signal
    signal.alarm(600)
    main()
