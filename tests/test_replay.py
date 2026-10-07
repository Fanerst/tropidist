"""Physical replay vs DEM prediction on random multi-fault sets.

Random DEM mechanisms are mapped to circuit faults, inserted as explicit
Pauli gates / record flips into the noiseless circuit, and simulated.  The
fired detectors and flipped observables must equal the XOR of the DEM terms.
"""
import collections
import os
import random
import sys

import stim

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cdist import replay


def main(names=("bb72_r6_Z", "bb72_r6_X", "bb144_r12_Z"), trials=150, seed=5):
    for name in names:
        circ = stim.Circuit.from_file(f"circuits/{name}.stim")
        dem = circ.detector_error_model(decompose_errors=False, flatten_loops=True)
        nerr = sum(1 for i in dem if i.type == "error")
        rng = random.Random(seed)
        kinds = collections.Counter()
        nontrivial = 0
        for _ in range(trials):
            raw = rng.sample(range(nerr), rng.randint(1, 4))
            dets, obs, _ = replay.check_in_dem(circ, raw)
            faults = replay.physical_faults(circ, raw)
            for f in faults:
                kinds[f["instruction"]] += 1
            d2, o2 = replay.replay(circ, faults)
            assert (dets, obs) == (d2, o2), (name, raw)
            nontrivial += bool(obs)
        print(f"ok: {name}: replay == DEM prediction on {trials} random fault sets "
              f"({nontrivial} flip an observable); fault kinds {dict(kinds)}")


if __name__ == "__main__":
    main()
