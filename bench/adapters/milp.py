"""Exact integer-programming adapters for binary parity distance.

config: backend=scipy (default), highspy, gurobi, or cpsat; mode=optimize
(default) or decision; dump=<directory> writes an LP and does not solve.
All models use bounded integer parity slacks, binary fault and logical bits,
and the solver's native thread setting. Optional packages are never required
by the default SciPy/HiGHS adapter.
"""
from __future__ import annotations

import math
import importlib.util
import multiprocessing as mp
import os
import queue
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common


def formulation(prob):
    """Sparse rows in variable order e, s, y, w; no solver dependencies."""
    n, m, q = prob.ncols, prob.nrows, prob.nobs
    rows = [[] for _ in range(m + q + 1)]
    hd, ld = [0] * m, [0] * q
    for j, (h, l) in enumerate(zip(prob.h, prob.l)):
        for r in common.bits(h):
            rows[r].append((j, 1))
            hd[r] += 1
        for r in common.bits(l):
            rows[m + r].append((j, 1))
            ld[r] += 1
    for r in range(m):
        rows[r].append((n + r, -2))
    for r in range(q):
        rows[m + r].extend([(n + m + r, -1), (n + m + q + r, -2)])
        rows[-1].append((n + m + r, 1))
    return dict(rows=rows, lo=[0] * (m + q) + [1], hi=[0] * (m + q) + [q],
                ub=[1] * n + [d // 2 for d in hd] + [1] * q + [d // 2 for d in ld],
                names=(["e_%d" % j for j in range(n)] + ["s_%d" % r for r in range(m)]
                       + ["y_%d" % i for i in range(q)] + ["w_%d" % i for i in range(q)]),
                binary=set(range(n)) | set(range(n + m, n + m + q)))


def write_lp(path, prob, model, decision_k=None):
    """Portable CPLEX LP syntax, also usable without a backend installed."""
    def expression(row):
        return " ".join(("+" if v > 0 else "-") + " %d %s" % (abs(v), model["names"][j])
                        for j, v in row) or "0"

    with open(path, "w") as f:
        f.write("Minimize\n obj: " + (expression([(j, 1) for j in range(prob.ncols)])
                                         if decision_k is None else "0") + "\nSubject To\n")
        for r, row in enumerate(model["rows"]):
            sense = "=" if r < prob.nrows + prob.nobs else ">="
            f.write(" c_%d: %s %s %d\n" % (r, expression(row), sense, model["lo"][r]))
        if decision_k is not None:
            f.write(" weight: %s <= %d\n" % (expression([(j, 1) for j in range(prob.ncols)]), decision_k))
        f.write("Bounds\n")
        for name, upper in zip(model["names"], model["ub"]):
            f.write(" 0 <= %s <= %d\n" % (name, upper))
        f.write("Binary\n " + " ".join(model["names"][j] for j in sorted(model["binary"])) + "\n")
        f.write("General\n " + " ".join(name for j, name in enumerate(model["names"])
                                           if j not in model["binary"]) + "\nEnd\n")


def rounded_bound(value):
    """Conservative integer ceiling, allowing only solver floating point noise."""
    if value is None or not math.isfinite(float(value)):
        return None
    return max(0, int(math.ceil(float(value) - 1e-7)))


def _sparse(model, ncols, decision_k):
    import numpy as np
    from scipy.sparse import coo_matrix
    rows = model["rows"] + ([[(j, 1) for j in range(ncols)]] if decision_k is not None else [])
    rr, cc, vv = [], [], []
    for r, row in enumerate(rows):
        for j, value in row:
            rr.append(r)
            cc.append(j)
            vv.append(value)
    mat = coo_matrix((np.asarray(vv, dtype=float), (rr, cc)), shape=(len(rows), len(model["ub"]))).tocsc()
    lo = np.asarray(model["lo"] + ([0] if decision_k is not None else []), dtype=float)
    hi = np.asarray(model["hi"] + ([decision_k] if decision_k is not None else []), dtype=float)
    cost = np.zeros(len(model["ub"]))
    if decision_k is None:
        cost[:ncols] = 1
    return mat, lo, hi, cost


def _scipy(prob, model, threads, deadline, decision_k, progress):
    import warnings
    import numpy as np
    import scipy
    from scipy.optimize import Bounds, LinearConstraint, milp
    mat, lo, hi, cost = _sparse(model, prob.ncols, decision_k)
    with warnings.catch_warnings():
        # SciPy intentionally forwards unknown options to the underlying HiGHS.
        warnings.filterwarnings("ignore", message="Unrecognized options detected.*", category=RuntimeWarning)
        r = milp(cost, integrality=np.ones(len(cost)), bounds=Bounds(np.zeros(len(cost)), model["ub"]),
                 constraints=LinearConstraint(mat, lo, hi), options={"time_limit": max(.001, deadline - time.time()),
                     "threads": threads, "mip_rel_gap": 0.0, "mip_abs_gap": 0.0})
    wit = [j for j in range(prob.ncols) if r.x[j] > .5] if r.x is not None else None
    return dict(witness=wit, dual=getattr(r, "mip_dual_bound", None), infeasible=r.status == 2,
                optimal=r.status == 0, timed_out=r.status == 1, error=r.status not in (0, 1, 2),
                message=str(r.message), version=scipy.__version__)


def _highspy(prob, model, threads, deadline, decision_k, progress):
    import numpy as np
    import highspy
    mat, lo, hi, cost = _sparse(model, prob.ncols, decision_k)
    h = highspy.Highs()
    for key, value in (("output_flag", False), ("threads", threads), ("mip_rel_gap", 0.0), ("mip_abs_gap", 0.0)):
        if h.setOptionValue(key, value) == highspy.HighsStatus.kError:
            raise RuntimeError("HiGHS rejected option %s" % key)
    nv = len(cost)
    h.addVars(nv, np.zeros(nv), np.asarray(model["ub"], dtype=float))
    h.changeColsCost(nv, np.arange(nv, dtype=np.int32), cost)
    h.changeColsIntegrality(nv, np.arange(nv, dtype=np.int32), [highspy.HighsVarType.kInteger] * nv)
    mat = mat.tocsr()
    h.addRows(len(lo), lo, hi, mat.nnz, mat.indptr.astype(np.int32), mat.indices.astype(np.int32), mat.data)
    h.setOptionValue("time_limit", max(.001, deadline - time.time()))
    h.run()
    st, info, sol = h.getModelStatus(), h.getInfo(), h.getSolution()
    feasible = (sol.value_valid and info.primal_solution_status == highspy.SolutionStatus.kSolutionStatusFeasible)
    wit = [j for j in range(prob.ncols) if sol.col_value[j] > .5] if feasible else None
    optimal, infeasible = st == highspy.HighsModelStatus.kOptimal, st == highspy.HighsModelStatus.kInfeasible
    timeout = st in (highspy.HighsModelStatus.kTimeLimit, highspy.HighsModelStatus.kIterationLimit)
    return dict(witness=wit, dual=getattr(info, "mip_dual_bound", None) if info.valid else None, infeasible=infeasible,
                optimal=optimal, timed_out=timeout, error=not (optimal or infeasible or timeout),
                message=h.modelStatusToString(st), version=h.version())


def _gurobi(prob, model, threads, deadline, decision_k, progress):
    import gurobipy as gp
    g = gp.Model("binary_parity_distance")
    g.Params.OutputFlag = 0
    g.Params.Threads = threads
    g.Params.MIPGap = 0.0
    g.Params.MIPGapAbs = 0.0
    variables = [g.addVar(lb=0, ub=upper, vtype=gp.GRB.BINARY if j in model["binary"] else gp.GRB.INTEGER,
                           name=model["names"][j]) for j, upper in enumerate(model["ub"])]
    for r, row in enumerate(model["rows"]):
        expr = gp.LinExpr([v for j, v in row], [variables[j] for j, v in row])
        g.addConstr(expr == 0 if r < prob.nrows + prob.nobs else expr >= 1)
    weight = gp.quicksum(variables[:prob.ncols])
    if decision_k is not None:
        g.addConstr(weight <= decision_k)
    else:
        g.setObjective(weight, gp.GRB.MINIMIZE)
    last_bound = [None]

    def callback(m, where):
        if where == gp.GRB.Callback.MIPSOL:
            vals = m.cbGetSolution(variables[:prob.ncols])
            progress(dict(witness=[j for j, v in enumerate(vals) if v > .5]))
        elif decision_k is None and where == gp.GRB.Callback.MIP:
            bound = m.cbGet(gp.GRB.Callback.MIP_OBJBND)
            rb = rounded_bound(bound) if abs(bound) < 1e99 else None
            if rb is not None and (last_bound[0] is None or rb > last_bound[0]):
                last_bound[0] = rb
                progress(dict(dual=bound))

    g.Params.TimeLimit = max(.001, deadline - time.time())
    g.optimize(callback)
    st = g.Status
    wit = [j for j in range(prob.ncols) if variables[j].X > .5] if g.SolCount else None
    dual = g.ObjBound if decision_k is None and abs(g.ObjBound) < 1e99 else None
    result = dict(witness=wit, dual=dual, infeasible=st == gp.GRB.INFEASIBLE, optimal=st == gp.GRB.OPTIMAL,
                  timed_out=st == gp.GRB.TIME_LIMIT, error=st not in (gp.GRB.INFEASIBLE, gp.GRB.OPTIMAL, gp.GRB.TIME_LIMIT),
                  message="Gurobi status %s" % st, version=".".join(map(str, gp.gurobi.version())))
    g.dispose()
    return result


def _cpsat(prob, model, threads, deadline, decision_k, progress):
    import ortools
    from ortools.sat.python import cp_model
    cp = cp_model.CpModel()
    variables = [cp.NewBoolVar(name) if j in model["binary"] else cp.NewIntVar(0, upper, name)
                 for j, (name, upper) in enumerate(zip(model["names"], model["ub"]))]
    for r, row in enumerate(model["rows"]):
        expr = sum(v * variables[j] for j, v in row)
        cp.Add(expr == 0 if r < prob.nrows + prob.nobs else expr >= 1)
    weight = sum(variables[:prob.ncols])
    if decision_k is None:
        cp.Minimize(weight)
    else:
        cp.Add(weight <= decision_k)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = threads
    solver.parameters.max_time_in_seconds = max(.001, deadline - time.time())

    class Incumbent(cp_model.CpSolverSolutionCallback):
        def on_solution_callback(self):
            progress(dict(witness=[j for j in range(prob.ncols) if self.Value(variables[j])],
                          dual=self.BestObjectiveBound() if decision_k is None else None))

    st = solver.Solve(cp, Incumbent())
    wit = [j for j in range(prob.ncols) if solver.Value(variables[j])] if st in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None
    return dict(witness=wit, dual=solver.BestObjectiveBound() if decision_k is None else None,
                infeasible=st == cp_model.INFEASIBLE, optimal=st == cp_model.OPTIMAL,
                timed_out=st in (cp_model.UNKNOWN, cp_model.FEASIBLE), error=st == cp_model.MODEL_INVALID,
                message=solver.StatusName(st), version=ortools.__version__)


def _worker(prob, cfg, threads, deadline, messages):
    """Isolated native solver: parent can enforce time even during import/build."""
    def emit(rec):
        messages.put(("progress", rec))
    try:
        backend, mode = cfg.get("backend", "scipy"), cfg.get("mode", "optimize")
        solve = {"scipy": _scipy, "highspy": _highspy, "gurobi": _gurobi, "cpsat": _cpsat}[backend]
        model = formulation(prob)
        if time.time() >= deadline:
            messages.put(("done", dict(status="timeout", message="time limit during model construction")))
            return
        for k in (range(1, prob.ncols + 1) if mode == "decision" else [None]):
            if time.time() >= deadline:
                messages.put(("done", dict(status="timeout", message="time limit between decisions")))
                return
            r = solve(prob, model, threads, deadline, k, emit)
            if k is None:
                emit(r)
                status = "error" if r["error"] else "timeout" if r["timed_out"] else "bounds"
            elif r["infeasible"]:
                messages.put(("progress", dict(lower=k + 1, infeasible_k=k)))
                continue
            else:
                emit(dict(witness=r["witness"]))
                status = "error" if r["error"] else "timeout" if r["timed_out"] and r["witness"] is None else "bounds"
            messages.put(("done", dict(status=status, message=r["message"], version=r["version"])))
            return
        messages.put(("done", dict(status="bounds", message="all weights infeasible: no undetected logical fault set")))
    except ImportError as exc:
        messages.put(("done", dict(status="unavailable", message=str(exc))))
    except Exception:
        messages.put(("done", dict(status="error", message=traceback.format_exc(limit=4))))


def main():
    a = common.adapter_args(__doc__)
    tr = common.Trace()  # Includes instance loading, imports, model build and solving.
    deadline = tr.t0 + max(0.0, a.time_limit)
    os.environ["OMP_NUM_THREADS"] = str(a.threads)
    os.environ["OPENBLAS_NUM_THREADS"] = str(a.threads)
    prob = common.load(a.instance, a.variant)
    cfg = dict(a.cfg)
    backend, mode = cfg.setdefault("backend", "scipy"), cfg.setdefault("mode", "optimize")
    cfg["threads_honoured"] = backend in ("scipy", "highspy", "gurobi", "cpsat")
    notes = ("threads honoured through " + {"scipy": "HiGHS threads option (forwarded by SciPy)",
              "highspy": "HiGHS threads", "gurobi": "Gurobi Threads", "cpsat": "CP-SAT num_search_workers"}.get(backend, "unknown backend"))
    witness, status, version = None, "error", None
    if a.threads < 1 or backend not in ("scipy", "highspy", "gurobi", "cpsat") or mode not in ("optimize", "decision"):
        cfg["threads_honoured"] = None
        notes += "; invalid threads, backend or mode"
    elif cfg.get("dump"):
        os.makedirs(cfg["dump"], exist_ok=True)
        path = os.path.join(cfg["dump"], "%s__%s.lp" % (prob.name, prob.variant))
        write_lp(path, prob, formulation(prob), 1 if mode == "decision" else None)
        notes = "dumped %s; no solver run; threads unused%s" % (path, "; decision LP is K=1, edit weight RHS for other K" if mode == "decision" else "")
        status = "bounds"
        cfg["threads_honoured"] = None
    elif importlib.util.find_spec({"scipy": "scipy", "highspy": "highspy",
                                  "gurobi": "gurobipy", "cpsat": "ortools"}[backend]) is None:
        status = "unavailable"
        cfg["threads_honoured"] = None
        notes = "%s backend is not installed; no solver run; threads unused" % backend
    else:
        context = mp.get_context("spawn")
        messages = context.Queue()
        child = context.Process(target=_worker, args=(prob, cfg, a.threads, deadline, messages))
        child.start()
        done = False
        if mode == "decision":
            tr.lb(1)  # Logical nonzero excludes the all-zero vector.
        while not done:
            # Native limits use the remaining budget; grace only allows record delivery.
            remaining = deadline + 1.0 - time.time()
            if remaining <= 0:
                status = "timeout"
                notes += "; wall-time watchdog stopped worker"
                break
            try:
                kind, r = messages.get(timeout=min(.1, remaining))
            except queue.Empty:
                if not child.is_alive():
                    status = "error"
                    notes += "; solver worker exited without a result (exit %s)" % child.exitcode
                    break
                continue
            if kind == "done":
                status, version = r["status"], r.get("version")
                notes += "; " + r.get("message", "")
                done = True
                continue
            candidate = r.get("witness")
            if candidate is not None:
                if not common.check_witness(prob, candidate)["ok"]:
                    status = "error"
                    notes += "; solver returned an invalid incumbent"
                    break
                if tr.upper is None or len(candidate) < tr.upper:
                    witness = candidate
                    tr.ub(len(candidate))
            lower = r.get("lower") if mode == "decision" else rounded_bound(r.get("dual"))
            if lower is not None:
                tr.lb(lower)
        if child.is_alive():
            child.terminate()
        child.join(timeout=.5)
        if child.is_alive():
            child.kill()
            child.join(timeout=.5)
        messages.close()
        if status == "unavailable":
            cfg["threads_honoured"] = None
            tr.lower = tr.upper = None
            tr.events = []
            witness = None
            notes = "backend unavailable; no solver run; threads unused; " + notes
        if status != "error" and tr.upper is not None and tr.lower == tr.upper:
            status = "exact"
        if tr.upper is not None and tr.lower is not None and tr.lower > tr.upper:
            status = "error"
            notes += "; discarded solver bound %s, which exceeds incumbent %s" % (tr.lower, tr.upper)
            tr.events = [event for event in tr.events if event.get("lb", 0) <= tr.upper]
            valid_lower = [event["lb"] for event in tr.events if "lb" in event]
            tr.lower = max(valid_lower) if valid_lower else None
    rec = common.save_result(a.out, prob, "milp", tr, status, a.threads, a.time_limit,
                             witness=witness, config=cfg, notes=notes, version=version)
    print(rec["status"], tr.lower, tr.upper, tr.seconds())


if __name__ == "__main__":
    main()
