"""Independent cross-check with a third-party solver: the distance problem as
a mixed-integer program (SciPy / HiGHS).  Shares only the problem import.

    minimise sum_j e_j   s.t.  H e = 2 y,   L e = 2 z + u,   sum_i u_i >= 1,
    e, u binary;  y, z nonnegative integers.

Usage: python tests/crosscheck_milp.py out.json name:problem[:time_limit] ...
       problem = collapsed | fold2 | fold3 | sector
"""
import json
import os
import sys
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cdist import problem


def solve(p, time_limit):
    n, m, k = p.ncols, p.nrows, p.nobs
    rows_used = sorted({i for a in p.h for i in range(m) if (a >> i) & 1}) if m <= 4096 else list(range(m))
    ridx = {r: i for i, r in enumerate(rows_used)}
    mr = len(rows_used)
    nv = n + mr + k + k           # e, y, z, u
    A = lil_matrix((mr + k + 1, nv))
    for j, a in enumerate(p.h):
        x = a
        while x:
            low = x & -x
            A[ridx[low.bit_length() - 1], j] = 1
            x ^= low
    for i in range(mr):
        A[i, n + i] = -2
    for j, b in enumerate(p.l):
        for i in range(k):
            if (b >> i) & 1:
                A[mr + i, j] = 1
    for i in range(k):
        A[mr + i, n + mr + i] = -2
        A[mr + i, n + mr + k + i] = -1
        A[mr + k, n + mr + k + i] = 1
    lo = np.zeros(mr + k + 1)
    hi = np.zeros(mr + k + 1)
    lo[-1], hi[-1] = 1, k
    c = np.zeros(nv)
    c[:n] = 1
    ub = np.concatenate([np.ones(n), np.full(mr, 8.0), np.full(k, n), np.ones(k)])
    t = time.time()
    r = milp(c, constraints=LinearConstraint(A.tocsr(), lo, hi), integrality=np.ones(nv),
             bounds=Bounds(np.zeros(nv), ub), options={"time_limit": time_limit, "mip_rel_gap": 0.0})
    dt = time.time() - t
    val = None if r.x is None else int(round(r.fun))
    return {"status": int(r.status), "message": r.message, "objective": val,
            "proved_optimal": r.status == 0, "dual_bound": getattr(r, "mip_dual_bound", None), "seconds": round(dt, 1)}


def main(out, *specs):
    res = json.load(open(out)) if os.path.exists(out) else {}
    for spec in specs:
        parts = spec.split(":")
        name, which = parts[0], parts[1]
        tl = float(parts[2]) if len(parts) > 2 else 600.0
        full = problem.load_dem_problem(f"circuits/{name}.stim")
        q = problem.sector_problem(full)
        p = {"collapsed": lambda: problem.collapse_time(q), "fold2": lambda: problem.fold_time(q, 2),
             "fold3": lambda: problem.fold_time(q, 3), "sector": lambda: q}[which]()
        r = solve(p, tl)
        r.update({"rows": p.nrows, "columns": p.ncols})
        res[f"{name}:{which}"] = r
        print(name, which, r, flush=True)
        json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
