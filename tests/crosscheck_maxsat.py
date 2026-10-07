"""Independent cross-check: Stim's MaxSAT formulation of the shortest
undetectable logical error, solved with RC2 (PySAT).  Uses none of cdist."""
import json
import sys
import time

import stim
from pysat.examples.rc2 import RC2
from pysat.formula import WCNF


def main(path, out=None):
    circuit = stim.Circuit.from_file(path)
    t = time.time()
    wcnf_text = circuit.shortest_error_sat_problem()
    wcnf = WCNF(from_string=wcnf_text)
    print(f"{path}: vars={wcnf.nv} hard={len(wcnf.hard)} soft={len(wcnf.soft)} (built in {time.time() - t:.1f}s)", flush=True)
    t = time.time()
    with RC2(wcnf) as solver:
        model = solver.compute()
        cost = solver.cost
    dt = time.time() - t
    print(f"{path}: MaxSAT optimum (shortest undetectable logical error) = {cost}  [{dt:.1f}s]", flush=True)
    if out:
        json.dump({"circuit": path, "maxsat_distance": cost, "seconds": dt, "solver": "PySAT RC2"}, open(out, "w"))


if __name__ == "__main__":
    main(*sys.argv[1:])
