"""Why a dead check costs one unit: put the fault set of weight 9 of a chip into the perfect circuit (same qubits, same ticks) and see which detectors fire there."""
import json
import sys

import stim

sys.path[:0] = ["results/defect_study"]
import chip


def strip_noise(c):
    out = stim.Circuit()
    for inst in c.flattened():
        if inst.name in ("X_ERROR", "Y_ERROR", "Z_ERROR", "DEPOLARIZE1", "DEPOLARIZE2"):
            continue
        out.append(inst)
    return out


def inject(c, faults):
    """Noise-free circuit with the Pauli faults at their ticks (after everything before that tick); measurement flips as faults on the outcome."""
    by = {}
    for f in faults:
        by.setdefault(f["tick"], []).append(f)
    out = stim.Circuit()
    tick = 0
    for inst in c.flattened():
        if inst.name == "TICK":
            for f in by.get(tick, []):
                for q, p in f["paulis"].items():
                    out.append({"X": "X_ERROR", "Y": "Y_ERROR", "Z": "Z_ERROR"}[p], [int(q)], 1.0)
            tick += 1
        out.append(inst)
    return out


def rows(basis, cycles, dx, dz):
    return [json.loads(l) for l in open("results/defect_study/rec/rec_a.jsonl")
            if (lambda r: r["basis"] == basis and r["cycles"] == cycles and r["dead_x"] == dx and r["dead_z"] == dz)(json.loads(l))]


r = rows("Z", 3, [], [0])[0]
print("weight", r["ub"], "replay", r["replay_ok"])
for f in r["faults"]:
    print(f)


def fire(c, faults, perfect=True):
    d = inject(strip_noise(c), faults)
    det, obs = d.compile_detector_sampler().sample(1, separate_observables=True)
    coords = c.get_detector_coordinates()
    return [tuple(coords[i]) for i, v in enumerate(det[0]) if v], [i for i, v in enumerate(obs[0]) if v]


def inject_fix():
    global inject

    def inj(c, faults):
        by = {}
        for f in faults:
            by.setdefault(f["tick"], []).append(f)
        out = stim.Circuit()
        tick = 0
        for inst in c.flattened():
            if inst.name == "TICK":
                for f in by.get(tick, []):
                    for p, q in f["paulis"]:
                        out.append({"X": "X_ERROR", "Y": "Y_ERROR", "Z": "Z_ERROR"}[p], [int(q)], 1.0)
                tick += 1
            out.append(inst)
        return out
    inject = inj


inject_fix()
for cyc in (2, 3, 4, 6, 10):
    r = rows("Z", cyc, [], [0])[0]
    chip_c = chip.build_chip("gross", "Z", cyc, 1e-3, None, (), (0))if False else chip.build_chip("gross", "Z", cyc, 1e-3, None, (), (0,))
    perfect_c = chip.build_chip("gross", "Z", cyc, 1e-3, None, (), ())
    a = fire(chip_c, r["faults"])
    b = fire(perfect_c, r["faults"])
    print("C", cyc, "weight", r["ub"], "on the chip: detectors", a[0], "observables", a[1])
    print("   in the perfect circuit: Z detectors", [x for x in b[0] if x[3] == 3], "observables", b[1], "ticks", sorted(f["tick"] for f in r["faults"]))
