"""Plain-script checks for Stim-generated benchmark circuits and graph distances.

Run: .venv/bin/python tests/test_bench_stim_families.py
All test exports and certificates are temporary; no solver search is run.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from itertools import combinations
import json
import os
from pathlib import Path
import random
import sys
import tempfile
from unittest.mock import patch

sys.dont_write_bytecode = True
for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                  "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "2"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import stim
from bench import common, instances, stim_families
from cdist import problem

NOISE = dict(after_clifford_depolarization=0.001,
             before_round_data_depolarization=0.001,
             before_measure_flip_probability=0.001,
             after_reset_flip_probability=0.001)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def original_circuit(family, distance):
    generator = {"surface": "surface_code:rotated_memory_z",
                 "stim_color": "color_code:memory_xyz"}[family]
    return stim.Circuit.generated(generator, distance=distance, rounds=distance, **NOISE)


def dem_without_coordinates(circuit):
    dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=True).flattened()
    return [(instruction.type, tuple(instruction.args_copy()),
             tuple(str(target) for target in instruction.targets_copy()))
            for instruction in dem if instruction.type != "detector"]


def measured_check_types(circuit):
    """Infer CSS types from the measured ancilla gadget, independently of its coordinates.

    X-check ancillas are Hadamarded around their CX interactions, while
    Z-check ancillas have no basis rotation.  Control/target roles corroborate
    this interpretation of the physical Z measurement/reset instruction.
    """
    first_round = []
    for instruction in circuit.flattened():
        first_round.append(instruction)
        if instruction.name == "MR":
            ancillas = {target.value for target in instruction.targets_copy()}
            break
    else:
        raise AssertionError("surface circuit has no measurement/reset round")
    hadamards = {target.value for instruction in first_round if instruction.name == "H"
                 for target in instruction.targets_copy()} & ancillas
    controls, targets = set(), set()
    for instruction in first_round:
        if instruction.name == "CX":
            qubits = [target.value for target in instruction.targets_copy()]
            controls.update(qubits[::2])
            targets.update(qubits[1::2])
    require(controls & ancillas == hadamards, "X-check CX roles disagree with basis rotations")
    require(targets & ancillas == ancillas - hadamards, "Z-check CX roles disagree with basis rotations")
    coords = circuit.get_final_qubit_coordinates()
    return {tuple(coords[qubit]): 0 if qubit in hadamards else 3 for qubit in ancillas}


def validate_rewrite(original, rewritten, check_perms):
    before, after = list(original.flattened()), list(rewritten)
    require(len(before) == len(after), "rewrite changed flattened instruction count")
    for index, (old, new) in enumerate(zip(before, after)):
        require(isinstance(new, stim.CircuitInstruction), "rewrite retains a repeat block")
        require(new.name != "SHIFT_COORDS", "rewrite retains a coordinate shift")
        if old.name == "DETECTOR":
            require(new.name == old.name and new.targets_copy() == old.targets_copy(),
                    "rewrite changed detector targets at instruction %d" % index)
        else:
            require(str(new) == str(old), "rewrite changed non-detector instruction %d" % index)
    require(dem_without_coordinates(original) == dem_without_coordinates(rewritten),
            "detector error model changed beyond coordinates")
    require((rewritten.num_qubits, rewritten.num_detectors, rewritten.num_observables)
            == (original.num_qubits, original.num_detectors, original.num_observables),
            "rewrite changed circuit dimensions")
    old_coords, new_coords = original.get_detector_coordinates(), rewritten.get_detector_coordinates()
    types, locations, checks = measured_check_types(original), {}, {}
    for detector in range(original.num_detectors):
        old, new = old_coords[detector], new_coords[detector]
        require(len(new) == 4 and new[1] == 0, "detector lacks (check, 0, round, type) coordinates")
        require(new[0] == int(new[0]) and new[0] >= 0, "invalid check index")
        require(new[2] == old[2], "detector round changed")
        xy, key = tuple(old[:2]), (int(new[0]), int(new[3]))
        require(new[3] == types[xy], "detector CSS type disagrees with measured ancilla gadget")
        require(locations.setdefault(xy, key) == key, "check index changes over time")
        require(checks.setdefault(key, xy) == xy, "two checks share a type/index pair")
    require(set(locations) == set(types), "not every measured check is represented")
    require(len({tuple(coords) for coords in new_coords.values()}) == rewritten.num_detectors,
            "rewritten detector coordinates are not unique")
    for typ in (0, 3):
        ids = [index for index, check_type in checks if check_type == typ]
        require(sorted(ids) == list(range(len(ids))), "indices are not contiguous within each type")
    require({coords[3] for coords in new_coords.values() if coords[2] == 0} == {3},
            "round zero does not identify the Z memory sector")
    # A single cp[c] must represent the same operation inside both type-index
    # spaces.  The task explicitly allows no candidates to survive indexing.
    xs, ys = zip(*locations)
    xsum, ysum = min(xs) + max(xs), min(ys) + max(ys)
    transforms = (lambda xy: (xsum - xy[0], ysum - xy[1]),
                  lambda xy: (xsum - xy[0], xy[1]),
                  lambda xy: (xy[0], ysum - xy[1]))
    for perm in check_perms:
        require(sorted(perm) == list(range(len(perm))), "candidate check permutation is not bijective")
        require(all(index < len(perm) and (perm[index], typ) in checks for index, typ in checks),
                "candidate maps outside a CSS type-index space")
        require(any(all(checks[(perm[index], typ)] == transform(xy)
                        for (index, typ), xy in checks.items()) for transform in transforms),
                "candidate is not a type-preserving geometric patch symmetry")


def test_surface_rewrite():
    for distance in (3, 5):
        original = original_circuit("surface", distance)
        require(str(stim_families.generated_circuit("surface", distance)) == str(original),
                "surface generator arguments differ from the requested circuit")
        rewritten, perms = stim_families.surface_circuit(distance)
        validate_rewrite(original, rewritten, perms)
        direct, direct_perms = stim_families.rewrite_surface_detectors(original)
        require(str(direct) == str(rewritten) and direct_perms == perms,
                "surface convenience builder differs from direct rewrite")
        print("PASS surface_d%d: coordinate-only rewrite and unchanged DEM" % distance, flush=True)
    # Relocate coordinates by an odd parity translation.  Check types must
    # still come from the measured circuit, not coordinate parity formulas.
    relocated = stim.Circuit()
    for instruction in original_circuit("surface", 3).flattened():
        args = instruction.gate_args_copy()
        if instruction.name in ("QUBIT_COORDS", "DETECTOR"):
            args[0] += 1
            args[1] += 2
        relocated.append(instruction.name, instruction.targets_copy(), args)
    rewritten, perms = stim_families.rewrite_surface_detectors(relocated)
    validate_rewrite(relocated, rewritten, perms)
    print("PASS relocated surface circuit: CSS types read from measurements", flush=True)


def brute_force_distance(h, l, maximum=None):
    for weight in range(1, min(len(h), maximum if maximum is not None else len(h)) + 1):
        for columns in combinations(range(len(h)), weight):
            syndrome = logical = 0
            for column in columns:
                syndrome ^= h[column]
                logical ^= l[column]
            if syndrome == 0 and logical != 0:
                return weight
    return None


def test_surface_distance():
    circuit, _ = stim_families.surface_circuit(3)
    with tempfile.TemporaryDirectory(prefix="stim-distance-") as directory:
        path = Path(directory) / "surface_d3.stim"
        circuit.to_file(str(path))
        full = problem.load_dem_problem(str(path), "surface_d3")
    sector = problem.sector_problem(full)
    require(problem.sector_is_exact(full, sector), "surface sector reduction is not exact")
    for variant, prob in (("sector", sector), ("collapsed", problem.collapse_time(sector))):
        require(prob.nobs == 1 and max((bin(mask).count("1") for mask in prob.h), default=0) <= 2,
                variant + " is not graph-like with one observable")
        found = stim_families.graphlike_distance(prob.h, prob.l, prob.nrows)
        enumerated = brute_force_distance(prob.h, prob.l, maximum=3)
        require(enumerated is not None and found == enumerated,
                variant + " distance disagrees with subset enumeration through weight three")
        if variant == "sector":
            require(found == 3, "computed surface_d3 sector distance differs from three")
        print("PASS surface_d3 %s: %d x %d; enumerated exact distance %d" %
              (variant, prob.nrows, prob.ncols, found), flush=True)


def test_graphlike_distance():
    fixtures = [([1, 1], [0, 1], 1), ([3, 6, 5], [1, 0, 0], 3),
                ([0, 1], [1, 0], 1), ([0, 1, 2, 3], [0, 1, 0, 0], 2),
                ([], [], 0), ([1, 2, 3], [0, 0, 0], 2), ([0], [1], 0),
                ([3, 6, 12, 9], [1, 0, 0, 0], 4),
                ([3, 6, 5, 24, 48, 96, 192, 136], [0, 0, 0, 1, 0, 0, 0, 0], 8)]
    rng = random.Random(260322532)
    for _ in range(40):
        nrows = rng.randint(1, 5)
        h, l = ([1, 1], [0, 1]) if nrows == 1 else ([1, 2, 3], [1, 0, 0])
        h, l = list(h), list(l)
        for _ in range(rng.randint(1, 10 - len(h))):
            rows = rng.sample(range(nrows), rng.randint(0, min(nrows, 2)))
            h.append(sum(1 << row for row in rows))
            l.append(rng.randrange(2))
        fixtures.append((h, l, nrows))
    for h, l, nrows in fixtures:
        expected, actual = brute_force_distance(h, l), stim_families.graphlike_distance(h, l, nrows)
        require(actual == expected, "graph distance differs from brute force: %r" %
                ((h, l, nrows, actual, expected),))
    for h, l, nrows in (([7], [1], 3), ([1, 1], [1, 2], 1), ([0, 7], [1, 0], 3),
                       ([0, 1], [1, 2], 1)):
        try:
            stim_families.graphlike_distance(h, l, nrows)
        except instances.NeedsLead:
            pass
        else:
            raise AssertionError("unsupported graph problem did not raise NeedsLead: %r" % ((h, l, nrows),))
    print("PASS graphlike_distance: 49 enumerated problems and unsupported-input checks", flush=True)


def test_registry_and_exports():
    for family, prefix, distances in (("surface", "surface", range(3, 26, 2)),
                                      ("stim_color", "color", range(3, 12, 2))):
        for distance in distances:
            name, spec = "%s_d%d" % (prefix, distance), instances.INSTANCES["%s_d%d" % (prefix, distance)]
            require(spec["status"] == "ready", name + " is not ready")
            require(spec["track"] == "circuit" and spec["family"] == family, name + " has incorrect family/track")
            require(spec["rounds"] == distance and spec["basis"] == "Z" and spec["k"] == 1,
                    name + " has incorrect experiment metadata")
            expected_variants = ("full", "sector", "collapsed") if family == "surface" else ("full",)
            require(tuple(spec["variants"]) == expected_variants, name + " advertises the wrong registry variants")
            require(spec["generator"] == {"surface": "surface_code:rotated_memory_z",
                                          "stim_color": "color_code:memory_xyz"}[family]
                    and spec["noise"] == NOISE, name + " has incorrect generator/noise metadata")
            if family == "surface":
                require(spec["n"] == distance * distance, name + " has incorrect data-qubit count")
    for distance in (3, 5, 7):
        require(str(stim_families.generated_circuit("stim_color", distance))
                == str(original_circuit("stim_color", distance)), "color circuit changed from Stim generation")
    with tempfile.TemporaryDirectory(prefix="stim-exports-") as directory:
        root = Path(directory)
        for name in ("surface_d3", "color_d3"):
            try:
                instances.build(name, root=root / "limited", max_cols=1)
            except instances.TooLarge:
                pass
            else:
                raise AssertionError(name + " ignored max_cols=1")
            require(not (root / "limited" / name).exists(), "TooLarge left a completed export")
            meta = instances.build(name, root=root / "exports")
            require(set(meta["variants"]) == ({"full", "sector", "collapsed"} if name.startswith("surface") else {"full"}),
                    name + " exported the wrong variants")
            if name == "color_d3" and not (ROOT / "results" / "bench_truth" / (name + ".json")).is_file():
                require(meta["variants"]["full"]["distance"] is None
                        and meta["variants"]["full"]["distance_kind"] == "unknown",
                        "color export without a certificate should have unknown truth")
            hashes = meta.get("source_sha256", {})
            require(hashes, name + " has no source hashes")
            for source, expected in hashes.items():
                require(hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == expected,
                        name + " source hash differs from source contents")
            for variant in meta["variants"]:
                loaded = common.load(str(root / "exports" / name), variant)
                require((loaded.nrows, loaded.ncols, loaded.nobs)
                        == tuple(meta["variants"][variant][key] for key in ("rows", "cols", "obs")),
                        name + " dimensions differ from exported metadata")
                if name.startswith("surface"):
                    require(loaded.distance_kind == "exact" and loaded.distance is not None,
                            variant + " surface truth is not exact")
                    require("graphlike_distance" in loaded.meta["variants"][variant]["distance_source"],
                            variant + " surface distance lacks its graph source")
                    if variant != "full":
                        require(loaded.distance == stim_families.graphlike_distance(loaded.h, loaded.l, loaded.nrows),
                                variant + " surface truth differs from its exported graph")
    print("PASS all 17 registry entries; temporary d3 exports, source hashes, and TooLarge", flush=True)


def test_color_certificates():
    # Patch only the registry's root so no real truth file is created or changed.
    with tempfile.TemporaryDirectory(prefix="stim-truth-") as directory:
        root = Path(directory)
        with patch.object(instances, "ROOT", root):
            spec = deepcopy(instances.INSTANCES["color_d3"])
            instances._prepare(spec)
            require(spec.get("truth", {}).get("full", (None, "unknown", None))
                    == (None, "unknown", None), "missing color truth should be unknown")
            path = root / "results" / "bench_truth" / "color_d3.json"
            path.parent.mkdir(parents=True)
            for record, expected in (({"certified_lower_bound": 3, "certified_upper_bound": 3}, (3, "exact")),
                                     ({"certified_lower_bound": 2, "certified_upper_bound": 3}, (2, "lower_bound"))):
                path.write_text(json.dumps(record))
                spec = deepcopy(instances.INSTANCES["color_d3"])
                instances._prepare(spec)
                require(spec["truth"]["full"][:2] == expected, "color truth reading differs from certified bounds")
                require("results/bench_truth/color_d3.json" in spec["truth"]["full"][2],
                        "color truth source does not identify its certificate")
    print("PASS absent and present color truth certificates", flush=True)


def main():
    test_surface_rewrite()
    test_surface_distance()
    test_graphlike_distance()
    test_registry_and_exports()
    test_color_certificates()
    print("All Stim family checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
