"""Plain-script checks of the seven Table 2 codes (requires GAP/cache).

--schedule-only checks the implementation on explicit commuting circulants;
these are synthetic fixtures, NOT reconstructions of the paper's seven codes.
"""
import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "papers"))
sys.path.insert(0, str(ROOT))

import coset
import stabcode
from cdist import problem, symmetry
from papers.run_parallel import row_perms


def check_layers(layers, A, B):
    hx, hz, n = coset._matrices(A, B)
    m = n // 2
    gotx, gotz = [0] * m, [0] * m
    cx_count = 0
    for ops in layers:
        used = set()
        for name, targets in ops:
            assert len(set(targets)) == len(targets)
            assert not used.intersection(targets), "two operations touch one qubit in a layer"
            used.update(targets)
            if name == "CX":
                for control, target in zip(targets[::2], targets[1::2]):
                    cx_count += 1
                    if control >= n + m:
                        assert target < n
                        i = control - n - m
                        gotx[i] ^= 1 << target
                    else:
                        assert control < n and n <= target < n + m
                        i = target - n
                        gotz[i] ^= 1 << control
    assert gotx == hx and gotz == hz, "schedule does not measure the Construction 1 matrices"
    assert cx_count == n * (len(A) + len(B))
    assert len(layers) == len(A) + len(B) + 2


def inspect(A, B, expected=None, name="synthetic"):
    hx, hz, n = coset._matrices(A, B)
    parameters = stabcode.css_parameters(hx, hz, n)
    if expected is not None:
        assert parameters == expected[:2], (name, parameters, expected)
    w = len(A) + len(B)
    weights = sorted({bin(r).count("1") for r in hx + hz})
    # Proposition III.1 bounds stabilizer weights by the number of terms;
    # nonregular actions can cause cancellations. Table 3 gives maximum w.
    assert max(weights) == w and all(v <= w and v % 2 == w % 2 for v in weights)
    for checks in (hx, hz):
        column_weights = [sum((r >> j) & 1 for r in checks) for j in range(n)]
        assert max(column_weights) <= max(len(A), len(B))
    check_layers(coset._schedule(A, B), A, B)
    cps = coset._centralizer(A + B)
    for cp in cps:
        assert sorted(cp) == list(range(n // 2))
        assert all(cp[g[i]] == g[cp[i]] for g in A + B for i in range(n // 2))
    for basis in "ZX":
        circ = coset._build(A, B, basis, 3, 0.001)
        dem = circ.detector_error_model(decompose_errors=False)
        assert circ.num_qubits == 2 * n
        assert circ.num_observables == parameters[1]
        assert circ.num_detectors == 3 * n
        assert circ.num_ticks == 3 * (w + 2) + 2
        coords = circ.get_detector_coordinates()
        assert all(len(v) == 4 and v[1] == 0 and v[2] in range(4) and v[3] in (0, 3)
                   and 0 <= v[0] < n // 2 for v in coords.values())
        assert any(v[2] == 3 for v in coords.values())
        # Inspect primitive operations between TICKs, excluding noise/annotations.
        used = set()
        for inst in circ.flattened():
            if inst.name == "TICK":
                used.clear()
            elif inst.name in ("R", "RX", "M", "MX", "CX"):
                qs = [t.value for t in inst.targets_copy()]
                assert len(set(qs)) == len(qs) and not used.intersection(qs)
                used.update(qs)
        path = ROOT / "circuits" / "papers" / f"coset_{name}_r3_{basis}.stim"
        path.parent.mkdir(parents=True, exist_ok=True)
        circ.to_file(path)
        full = problem.load_dem_problem(path, name=f"{name}:{basis}")
        sector = problem.sector_problem(full)
        exact = problem.sector_is_exact(full, sector)
        assert exact, "sector reduction is only a relaxation"
        sym = symmetry.from_row_perms(sector, row_perms(sector, cps))
        kept = sym.get("n_symmetries_kept") if sym.get("ok") else None
        if cps and expected is not None:
            assert kept == len(cps), (name, basis, kept, len(cps), sym.get("reason"))
        print(name, basis, "(n,k)", parameters, "weights", weights, "qubits", circ.num_qubits,
              "layers/cycle", w + 2, "detectors", circ.num_detectors, "DEM mechanisms", dem.num_errors,
              "sector exact", exact, "symmetries", kept, "/", len(cps), flush=True)


def synthetic():
    for m, aa, bb in ((6, (0, 1, 2), (0, 2, 4)), (8, (0, 1, 2, 3), (0, 1, 4, 5))):
        A = tuple(tuple((i + s) % m for i in range(m)) for s in aa)
        B = tuple(tuple((i + s) % m for i in range(m)) for s in bb)
        inspect(A, B, name=f"synthetic_weight{len(aa) + len(bb)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule-only", action="store_true")
    args = parser.parse_args()
    if args.schedule_only:
        synthetic()
        print("Synthetic schedule checks passed; the paper's seven codes were not checked.")
        return 0
    blocked = []
    for key, entry in coset.CODES.items():
        try:
            A, B = coset.operators(key)
            inspect(A, B, expected=entry[2], name=f"coset{key}")
        except coset.ReconstructionUnavailable as exc:
            blocked.append(key)
            print(f"BLOCKED coset{key}: {exc}", file=sys.stderr, flush=True)
    if blocked:
        print(f"FAIL: {len(blocked)} paper-code checks blocked; no blocked check reported as passing.", file=sys.stderr)
        return 2
    print("All seven paper codes passed both bases at 3 rounds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
