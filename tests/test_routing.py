"""Plain-script checks of the paper's routing geometry and memory circuits.

Run with: OMP_NUM_THREADS=2 .venv/bin/python tests/test_routing.py
Code-distance searches are recorded separately under results/papers3/routing.
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "papers"))

import routing
import stabcode
from cdist import problem
from papers.run_parallel import sym_of


def check_routing(key):
    """Track physical labels independently, including reversed contact order."""
    l, m, vx, vz = routing.CODES[key][0]
    data, xa, za = routing.geometry(key)
    assert data == tuple(x * m + y for x in range(l) for y in range(m)
                         if (x + y) % 2 == 0)
    assert xa == tuple(x * m + y for x in range(l) for y in range(m)
                       if x % 2 == 1 and y % 2 == 0)
    assert za == tuple(x * m + y for x in range(l) for y in range(m)
                       if x % 2 == 0 and y % 2 == 1)
    data_index = {q: i for i, q in enumerate(data)}
    x_index, z_index = {q: i for i, q in enumerate(xa)}, {q: i for i, q in enumerate(za)}
    at, pos = list(range(l * m)), list(range(l * m))
    forward, backward, moved, xs, zs = routing.routing(key)
    assert len(forward) == len(backward) == len(vx) == len(vz)
    collected = []
    for cycle, vectors_x, vectors_z in (
            (forward, vx, vz),
            (backward, tuple((-a, -b) for a, b in vx[::-1]),
             tuple((-a, -b) for a, b in vz[::-1]))):
        cx, cz = [[] for _ in xa], [[] for _ in za]
        for pairs, v, w in zip(cycle, vectors_x, vectors_z):
            touched = [q for pair in pairs for q in pair]
            assert len(touched) == l * m == len(set(touched)), (key, "layer conflict")
            for control, target in pairs:
                clabel, tlabel = at[control], at[target]
                if clabel in x_index:
                    anc, dsite, dlabel, vector = control, target, tlabel, v
                    cx[x_index[clabel]].append(data_index[dlabel])
                else:
                    assert tlabel in z_index and clabel in data_index
                    anc, dsite, dlabel, vector = target, control, clabel, w
                    cz[z_index[tlabel]].append(data_index[dlabel])
                x, y = divmod(anc, m)
                dx, dy = vector
                assert dsite == ((x + dx) % l) * m + (y + dy) % m
            for a, b in pairs:
                at[a], at[b] = at[b], at[a]
                pos[at[a]], pos[at[b]] = a, b
        collected.append((tuple(map(tuple, cx)), tuple(map(tuple, cz))))
        if cycle is forward:
            assert tuple(pos) == moved
    assert pos == list(range(l * m)), (key, "backward did not restore labels")
    assert collected[0] == (xs, zs)
    assert collected[1] == (tuple(g[::-1] for g in xs), tuple(g[::-1] for g in zs))
    hx, hz, n = routing.matrices(key)
    assert hx == [sum(1 << q for q in g) for g in xs]
    assert hz == [sum(1 << q for q in g) for g in zs]
    assert all(bin(row).count("1") == len(vx) for row in hx + hz)
    assert stabcode.css_parameters(hx, hz, n) == routing.CODES[key][2][:2]
    return n, len(vx)


def dem_problem(circuit, dem, name):
    """Use the full undecomposed signatures, without writing a circuit file."""
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
            else:
                assert False, "undecomposed DEM unexpectedly contains a separator"
        h.append(a)
        logical.append(b)
    raw = len(h)
    h, logical, metadata = problem.dedupe(h, logical, list(range(raw)))
    coords = circuit.get_detector_coordinates()
    return problem.Problem(name, circuit.num_detectors, circuit.num_observables,
                           h, logical, [tuple(coords[i]) for i in range(circuit.num_detectors)],
                           metadata, {"raw_mechanisms": raw})


def check_circuit(key, basis, rounds, n, layers):
    probability = 0.001
    circuit = routing.build(key, basis, rounds, p=probability)
    assert circuit.num_qubits == 2 * n
    assert circuit.num_observables == routing.CODES[key][2][1]
    hx, hz, _ = routing.matrices(key)
    nx, nz = len(hx), len(hz)
    expected = []
    for t in range(rounds):
        for count, kind, color in ((nz, "Z", 3), (nx, "X", 0)):
            if t or basis == kind:
                expected.extend((i, 0, t, color) for i in range(count))
    expected.extend((i, 0, rounds, 3 if basis == "Z" else 0)
                    for i in range(nz if basis == "Z" else nx))
    assert list(map(tuple, circuit.get_detector_coordinates().values())) == expected
    assert circuit.num_detectors == n * rounds

    instructions = list(circuit)
    forward, backward, _, _, _ = routing.routing(key)
    expected_layers = [pairs for t in range(rounds)
                       for pairs in (forward if t % 2 == 0 else backward)]
    gate_layers = 0
    for i, inst in enumerate(instructions):
        if inst.name == "CXSWAP":
            targets = inst.targets_copy()
            assert len(targets) == 2 * n == len({q.value for q in targets})
            assert [q.value for q in targets] == [q for pair in expected_layers[gate_layers] for q in pair]
            # One atomic noisy CXSWAP; DEPOLARIZE2 includes all 15 Paulis.
            assert instructions[i + 1].name == "DEPOLARIZE2"
            assert instructions[i + 1].targets_copy() == targets
            assert instructions[i + 1].gate_args_copy() == [probability]
            assert instructions[i + 2].name == "TICK"
            gate_layers += 1
        elif inst.name == "DEPOLARIZE2":
            assert instructions[i - 1].name == "CXSWAP"
        elif inst.name in ("R", "RX"):
            flip = instructions[i + 1]
            assert flip.name == ("X_ERROR" if inst.name == "R" else "Z_ERROR")
            assert flip.targets_copy() == inst.targets_copy()
        elif inst.name in ("M", "MX"):
            flip = instructions[i - 1]
            assert flip.name == ("X_ERROR" if inst.name == "M" else "Z_ERROR")
            assert flip.targets_copy() == inst.targets_copy()
    assert gate_layers == rounds * layers
    assert all(inst.name not in ("CX", "SWAP", "ISWAP") for inst in instructions)
    assert sum(inst.name == "DEPOLARIZE1" for inst in instructions) == 2 * rounds
    assert all(inst.gate_args_copy() == [probability] for inst in instructions
               if inst.name in ("X_ERROR", "Z_ERROR", "DEPOLARIZE1", "DEPOLARIZE2"))

    # Final data readout follows initial labels at the correct physical sites.
    data, _, _ = routing.geometry(key)
    moved = routing.routing(key)[2]
    final_positions = moved if rounds % 2 else tuple(range(2 * n))
    readout = [inst for inst in instructions if inst.name == ("M" if basis == "Z" else "MX")][-1]
    assert [q.value for q in readout.targets_copy()] == [final_positions[q] for q in data]
    ideal = circuit.without_noise()
    assert not ideal.compile_detector_sampler(seed=197).sample(16, append_observables=True).any()
    ideal.detector_error_model(decompose_errors=False)
    return circuit, circuit.detector_error_model(decompose_errors=False, flatten_loops=True)


def translation_generators(key, check_perms):
    """Check the entire group, then test only two generators in the DEM.

    Composition preserves the syndrome-column set and the logical-label
    relation checked by sym_of, so redundant Gaussian elimination for every
    group element is unnecessary in this small smoke test.
    """
    l, m, _, _ = routing.CODES[key][0]
    a, b = l // 2, m // 2
    expected = {tuple(((x + dx) % a) * b + (y + dy) % b
                      for x in range(a) for y in range(b))
                for dx in range(a) for dy in range(b) if dx or dy}
    assert len(check_perms) == a * b - 1
    assert {tuple(p) for p in check_perms} == expected
    return [[((x + 1) % a) * b + y for x in range(a) for y in range(b)],
            [x * b + (y + 1) % b for x in range(a) for y in range(b)]]


def main():
    start = time.monotonic()
    assert len({routing.tag(key) for key in routing.CODES}) == len(routing.CODES)
    for key in routing.CODES:
        n, layers = check_routing(key)
        for basis in ("Z", "X"):
            # Odd rounds end on moved sites; even rounds end at initial sites.
            check_circuit(key, basis, 2, n, layers)
            circuit, dem = check_circuit(key, basis, 3, n, layers)
            full = dem_problem(circuit, dem, f"routing{routing.tag(key)}:{basis}")
            sector = problem.sector_problem(full)
            assert problem.sector_is_exact(full, sector), (key, basis, "inexact CSS sector")
            check_perms = routing.translations(key)
            assert len(check_perms) == n // 2 - 1
            generators = translation_generators(key, check_perms)
            sym, _ = sym_of(sector, generators)
            assert sym.get("ok") and sym["n_symmetries_kept"] == len(generators), (key, basis, sym)
            print(f"{routing.tag(key)} {basis}: qubits={circuit.num_qubits} layers={layers} "
                  f"detectors={circuit.num_detectors} DEM={full.notes['raw_mechanisms']} "
                  f"sector=exact translations={len(check_perms)}/{len(check_perms)} "
                  f"(both generators verified)", flush=True)
    print(f"ok: all routing geometry/circuit checks ({time.monotonic() - start:.2f}s)")


if __name__ == "__main__":
    main()
