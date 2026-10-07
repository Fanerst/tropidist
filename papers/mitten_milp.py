"""Independent solver cross-check (SciPy / HiGHS mixed-integer program) of the
mitten distance problem built from the published matrices and schedule.

Usage: python papers/mitten_milp.py "[[150,30,10]]" Z out.json seconds
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tests"))

import mitten_effective
from crosscheck_milp import solve

name, basis, out, seconds = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
eff = mitten_effective.effective_problem(os.path.join(HERE, "mitten", "mitten", name), basis)
r = solve(eff, seconds)
r.update({"code": name, "basis": basis, "rows": eff.nrows, "columns": eff.ncols})
print(r, flush=True)
json.dump(r, open(out, "w"), indent=1)
