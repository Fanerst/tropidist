"""Exact SAT/MaxSAT distance adapter.

config: mode=incremental (default) or maxsat; solver=cadical153 for incremental,
solver=rc2 for MaxSAT; xor_chunk=6; encoding=matrix (default) or stim (MaxSAT,
full circuit variant only); binary=/path/to/maxsat; binary_args='...'; dump=dir.
RC2 options: adapt=0, exhaust=1, minz=0, trim=0 (configurable).
An external binary receives binary_args followed by the WCNF path. Arguments can
contain {threads} and {time_limit}; generic external binaries have no standard
thread option. PySAT's solver interfaces are single threaded.

The pure helpers build_cnf, add_at_most, write_wcnf and parse_maxsat_output do not
import PySAT. Error variables are always 1..prob.ncols in the matrix encoding.
"""
from __future__ import annotations

import itertools
import importlib
import importlib.util
import json
import math
import multiprocessing
import os
import queue
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common


def _xor(clauses, inputs, parity):
    """Forbid exactly the assignments whose XOR differs from parity."""
    for values in itertools.product((0, 1), repeat=len(inputs)):
        if sum(values) % 2 != parity:
            clauses.append([-v if b else v for v, b in zip(inputs, values)])


def build_cnf(prob, xor_chunk=6):
    """Return (clauses, nv), with error variables 1..ncols.

    Long XORs are split into gates of at most xor_chunk inputs. Gate outputs,
    observable parities and the forced-true observable selector are fully
    defined: fixing all error variables propagates every auxiliary variable.
    """
    xor_chunk = int(xor_chunk)
    if not 2 <= xor_chunk <= 16:
        raise ValueError("xor_chunk must be between 2 and 16")
    clauses, nv = [], prob.ncols

    def parity(inputs, output=None):
        nonlocal nv
        inputs = list(inputs)
        while len(inputs) > xor_chunk:
            group, inputs = inputs[:xor_chunk], inputs[xor_chunk:]
            nv += 1
            _xor(clauses, group + [nv], 0)
            inputs.insert(0, nv)
        if output is None:
            _xor(clauses, inputs, 0)
        else:
            _xor(clauses, inputs + [output], 0)

    hrows = [[] for _ in range(prob.nrows)]
    lrows = [[] for _ in range(prob.nobs)]
    for j, (h, l) in enumerate(zip(prob.h, prob.l), 1):
        for r in common.bits(h):
            hrows[r].append(j)
        for r in common.bits(l):
            lrows[r].append(j)
    for row in hrows:
        parity(row)
    observables = []
    for row in lrows:
        nv += 1
        out = nv
        observables.append(out)
        parity(row, out)
    nv += 1
    selector = nv
    clauses.append([-selector] + observables)
    clauses.extend([[-y, selector] for y in observables])
    clauses.append([selector])
    return clauses, nv


def add_at_most(clauses, nv, evars, k):
    """Return a copied CNF and new nv with a deterministic unary counter <= k.

    This package-free counter is intended for dumps and encoding verification.
    Actual incremental runs use PySAT's incremental totalizer instead.
    """
    out, evars, k = [list(c) for c in clauses], list(evars), int(k)
    if k < 0:
        out.append([])
        return out, nv
    if k >= len(evars):
        return out, nv
    if k == 0:
        out.extend([[-v] for v in evars])
        return out, nv
    previous = []
    for i, x in enumerate(evars):
        current = []
        for j in range(min(i + 1, k + 1)):
            if i == 0:
                current.append(x)
                continue
            nv += 1
            y = nv
            current.append(y)
            if j == 0:                         # y <=> previous[0] OR x
                a = previous[0]
                out.extend([[-a, y], [-x, y], [-y, a, x]])
            elif j == len(previous):            # y <=> x AND previous[j-1]
                b = previous[j - 1]
                out.extend([[-x, -b, y], [-y, x], [-y, b]])
            else:                              # y <=> a OR (x AND b)
                a, b = previous[j], previous[j - 1]
                out.extend([[-a, y], [-x, -b, y], [-y, a, x], [-y, a, b]])
        previous = current
    out.append([-previous[k]])
    return out, nv


def write_cnf(path, clauses, nv):
    with open(path, "w") as f:
        f.write("p cnf %d %d\n" % (nv, len(clauses)))
        for clause in clauses:
            f.write(" ".join(map(str, clause)) + " 0\n")


def write_wcnf(path, clauses, nv, evars=None):
    """Write hard clauses and weight-one soft (-e) units; return top weight."""
    evars = list(range(1, nv + 1) if evars is None else evars)
    soft = [(1, [-v]) for v in evars]
    return _write_weighted(path, clauses, soft, nv)


def _write_weighted(path, hard, soft, nv):
    top = 1 + sum(weight for weight, _ in soft)
    with open(path, "w") as f:
        f.write("p wcnf %d %d %d\n" % (nv, len(hard) + len(soft), top))
        for weight, clause in soft:
            f.write("%d %s 0\n" % (weight, " ".join(map(str, clause))))
        for clause in hard:
            f.write("%d %s 0\n" % (top, " ".join(map(str, clause))))
    return top


def read_wcnf(text):
    """Read the traditional weighted DIMACS format returned by Stim."""
    nv, top, hard, soft = None, None, [], []
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0] == "c":
            continue
        if parts[0] == "p":
            if len(parts) != 5 or parts[1] != "wcnf":
                raise ValueError("expected traditional p wcnf header")
            nv, top = int(parts[2]), int(parts[4])
            continue
        if top is None or parts[-1] != "0":
            raise ValueError("malformed weighted DIMACS clause")
        weight, clause = int(parts[0]), list(map(int, parts[1:-1]))
        if weight >= top:
            hard.append(clause)
        else:
            soft.append((weight, clause))
    if nv is None:
        raise ValueError("missing weighted DIMACS header")
    return hard, soft, nv


def parse_maxsat_output(text):
    """Parse standard o/s/v lines, including split models and bitstring models.

    An o line is an incumbent objective, never a certified lower bound. Only
    s OPTIMUM FOUND certifies it. No objective is inferred from an UNSAT line.
    """
    status, objective, model = None, None, None
    pending, complete = [], False
    for line in text.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        if parts[0] == "o" and len(parts) > 1:
            try:
                value = float(parts[1])
                if math.isfinite(value) and value.is_integer() and value >= 0:
                    objective = int(value)
            except ValueError:
                pass
        elif parts[0] == "s":
            status = " ".join(parts[1:]).upper()
        elif parts[0] == "v":
            if complete:
                pending = []
                complete = False
            tokens = parts[1:]
            if len(tokens) == 1 and len(tokens[0]) > 1 and set(tokens[0]) <= {"0", "1"}:
                pending = [i if c == "1" else -i for i, c in enumerate(tokens[0], 1)]
                complete = True
            else:
                try:
                    values = list(map(int, tokens))
                except ValueError:
                    continue
                pending.extend(v for v in values if v)
                complete = bool(values and values[-1] == 0)
            model = list(pending)
    return {"status": status, "objective": objective, "model": model,
            "optimal": status == "OPTIMUM FOUND", "unsat": status == "UNSATISFIABLE"}


def _stim_encoding(instance, prob):
    import stim
    if prob.variant != "full" or prob.meta.get("track") != "circuit":
        raise ValueError("encoding=stim requires the full variant of a circuit instance")
    circuit = stim.Circuit.from_file(os.path.join(instance, "circuit.stim"))
    hard, soft, nv = read_wcnf(circuit.shortest_error_sat_problem())
    index = {(h, l): j for j, (h, l) in enumerate(zip(prob.h, prob.l))}
    errors = []
    # The model Stim builds for its WCNF keeps loops folded, so mechanisms with equal symptoms in
    # different loop iterations stay separate variables; several variables may map to one column.
    dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=False,
                                       approximate_disjoint_errors=True).flattened()
    for instruction in dem:
        if instruction.type != "error":
            continue
        h = l = 0
        for target in instruction.targets_copy():
            if target.is_relative_detector_id():
                h ^= 1 << target.val
            elif target.is_logical_observable_id():
                l ^= 1 << target.val
        if (h, l) != (0, 0) and (h, l) not in index:
            raise ValueError("Stim DEM error signature is absent from the full variant")
        errors.append(index.get((h, l)))
    # Stim assigns error variables in its flattened DEM error order. Guard the
    # invariant before using it, so an incompatible Stim format fails honestly.
    evars = [-clause[0] for weight, clause in soft
             if weight == 1 and len(clause) == 1 and clause[0] < 0]
    if len(soft) != len(errors) or evars != list(range(1, len(errors) + 1)):
        raise ValueError("unsupported Stim error-variable numbering")
    return hard, soft, nv, dict(zip(evars, errors)), stim.__version__


def _model_witness(model, mapping, prob):
    if model is None:
        return None
    # Merged DEM signatures cancel modulo two if an intermediate incumbent
    # selects duplicate mechanisms. Optimal models never need such pairs.
    support = set()
    for variable in set(v for v in model if v > 0):
        col = mapping.get(variable)
        if col is not None:
            if col in support:
                support.remove(col)
            else:
                support.add(col)
    witness = sorted(support)
    return witness if common.check_witness(prob, witness)["ok"] else None


def _extend_model(hard, model, nv):
    """Validate/complete a solver model by unit propagation of the hard CNF."""
    if model is None:
        return None
    values = [0] * (nv + 1)
    occurrences = [[] for _ in range(nv + 1)]
    clauses = []
    pending = list(model)
    for original in hard:
        clause = list(dict.fromkeys(original))
        if any(-lit in clause for lit in clause):
            continue
        if not clause:
            return None
        ci = len(clauses)
        clauses.append(clause)
        if len(clause) == 1:
            pending.append(clause[0])
        for literal in clause:
            occurrences[abs(literal)].append((ci, literal))
    remaining = [len(c) for c in clauses]
    satisfied = [False] * len(clauses)
    while pending:
        literal = pending.pop()
        var, value = abs(literal), 1 if literal > 0 else -1
        if not 0 < var <= nv:
            return None
        if values[var]:
            if values[var] != value:
                return None
            continue
        values[var] = value
        for ci, occurrence in occurrences[var]:
            remaining[ci] -= 1
            if occurrence * value > 0:
                satisfied[ci] = True
            if satisfied[ci]:
                continue
            if remaining[ci] == 0:
                return None
            if remaining[ci] == 1:
                pending.extend(v for v in clauses[ci] if not values[abs(v)])
    return values if all(satisfied) else None


def _send(q, kind, **fields):
    q.put(dict(kind=kind, **fields))


def _incremental(prob, hard, nv, cfg, q):
    import pysat
    from pysat.card import ITotalizer
    from pysat.solvers import Solver
    name = cfg.get("solver", "cadical153")
    _send(q, "meta", version=getattr(pysat, "__version__", None),
          notes="PySAT %s ignores threads (single-threaded solver interface)" % name)
    evars = list(range(1, prob.ncols + 1))
    if not evars:
        _send(q, "done", status="bounds", notes="empty error set cannot flip an observable")
        return
    with Solver(name=name, bootstrap_with=hard) as solver:
        with ITotalizer(lits=evars, ubound=min(1, max(0, prob.ncols - 1)), top_id=nv) as counter:
            solver.append_formula(counter.cnf.clauses)
            for k in range(1, prob.ncols + 1):
                if k < prob.ncols:
                    if len(counter.rhs) <= k:
                        counter.increase(ubound=k, top_id=counter.top_id)
                        if counter.nof_new:
                            solver.append_formula(counter.cnf.clauses[-counter.nof_new:])
                    assumptions = [-counter.rhs[k]]
                else:
                    assumptions = []
                answer = solver.solve(assumptions=assumptions)
                if answer:
                    witness = _model_witness(solver.get_model(), {v: v - 1 for v in evars}, prob)
                    if witness is None:
                        raise ValueError("SAT model failed the matrix witness check")
                    _send(q, "ub", value=len(witness), witness=witness)
                    _send(q, "done", status="exact")
                    return
                _send(q, "lb", value=k + 1)
    _send(q, "done", status="bounds", notes="hard constraints have no logical witness")


def _rc2(prob, hard, soft, nv, mapping, cfg, q):
    import pysat
    from pysat.examples.rc2 import RC2
    from pysat.formula import WCNF
    if cfg.get("solver", "rc2") != "rc2":
        raise ValueError("mode=maxsat without binary requires solver=rc2")
    name = cfg.get("rc2_solver", "cadical153")
    options = {}
    for key, default in (("adapt", "0"), ("exhaust", "1"), ("minz", "0")):
        value = str(cfg.get(key, default))
        if value not in ("0", "1"):
            raise ValueError("RC2 %s must be 0 or 1" % key)
        options[key] = value == "1"
    options["trim"] = int(cfg.get("trim", 0))
    if options["trim"] < 0:
        raise ValueError("RC2 trim must be nonnegative")
    _send(q, "meta", version=getattr(pysat, "__version__", None),
          notes="PySAT RC2/%s ignores threads (single-threaded solver interface); " % name +
          "RC2 " + " ".join("%s=%d" % (key, value) for key, value in options.items()))
    formula = WCNF()
    for clause in hard:
        formula.append(clause)
    for weight, clause in soft:
        formula.append(clause, weight=weight)
    formula.nv = max(formula.nv, nv)

    class ReportingRC2(RC2):
        @property
        def cost(self):
            return self._reported_cost

        @cost.setter
        def cost(self, value):
            self._reported_cost = value
            # RC2 updates cost when an UNSAT core or an intrinsic at-most-one
            # constraint proves a new bound, including during core exhaustion.
            if value:
                _send(q, "lb", value=int(value))

    with ReportingRC2(formula, solver=name, **options) as solver:
        model = solver.compute()
        if model is None:
            _send(q, "lb", value=prob.ncols + 1)
            _send(q, "done", status="bounds", notes="hard constraints have no logical witness")
            return
        witness = _model_witness(model, mapping, prob)
        if witness is None:
            raise ValueError("RC2 model failed the matrix witness check")
        _send(q, "lb", value=int(solver.cost))
        _send(q, "ub", value=len(witness), witness=witness)
        _send(q, "done", status="exact" if solver.cost == len(witness) else "bounds")


def _external(prob, hard, soft, nv, mapping, cfg, threads, deadline, q):
    binary = cfg["binary"]
    if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
        _send(q, "done", status="unavailable", notes="external MaxSAT binary is not executable: " + binary)
        return
    arguments = shlex.split(cfg.get("binary_args", ""))
    note = ("external threads passed through binary_args; honouring them is binary-specific"
            if "{threads}" in cfg.get("binary_args", "") else
            "external backend has no standard thread option; threads ignored")
    _send(q, "meta", notes=note)
    with tempfile.TemporaryDirectory(prefix="bench_maxsat_") as tmp:
        path = os.path.join(tmp, "problem.wcnf")
        _write_weighted(path, hard, soft, nv)
        command = [binary] + [s.replace("{threads}", str(threads)).replace(
            "{time_limit}", str(max(0.01, deadline - time.monotonic()))) for s in arguments] + [path]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, bufsize=1)
        lines, updates = [], queue.Queue()

        def reader():
            for line in process.stdout:
                updates.put(line)
            updates.put(None)

        threading.Thread(target=reader, daemon=True).start()
        finished, timed_out = False, False
        last_ub = None
        while not finished:
            if time.monotonic() >= deadline - 0.1 and process.poll() is None:
                timed_out = True
                process.kill()
            try:
                line = updates.get(timeout=0.02)
            except queue.Empty:
                continue
            if line is None:
                finished = True
                continue
            lines.append(line)
            if line.lstrip().startswith(("v ", "s ", "o ")):
                result = parse_maxsat_output("".join(lines))
                if result["optimal"] and result["objective"] is not None:
                    _send(q, "lb", value=result["objective"])
                witness = _model_witness(result["model"], mapping, prob)
                if witness is not None and (last_ub is None or len(witness) < last_ub):
                    last_ub = len(witness)
                    _send(q, "ub", value=last_ub, witness=witness)
        process.wait()
        result = parse_maxsat_output("".join(lines))
        witness = _model_witness(result["model"], mapping, prob)
        if result["optimal"]:
            optimum = result["objective"]
            extended = _extend_model(hard, result["model"], nv)
            complete_soft = extended is not None and all(
                extended[abs(lit)] for _, clause in soft for lit in clause)
            cost = (sum(weight for weight, clause in soft
                        if not any(extended[abs(lit)] * lit > 0 for lit in clause))
                    if complete_soft else None)
            if optimum is None:
                optimum = cost
            if optimum is not None:
                _send(q, "lb", value=optimum)
                status = "exact" if witness is not None and optimum == len(witness) else "bounds"
            else:
                status = "bounds"
                _send(q, "meta", notes="optimum output lacks an objective and validated complete soft-variable model; bound withheld")
            if cost is not None and optimum != cost:
                status = "error"
                _send(q, "invalidate_external_bound")
                _send(q, "meta", notes="reported optimum disagrees with validated model cost")
        elif result["unsat"]:
            _send(q, "lb", value=prob.ncols + 1)
            status = "bounds"
        elif timed_out:
            status = "timeout"
        elif process.returncode not in (0, 10, 20, 30):
            status = "error"
        else:
            status = "bounds"
        _send(q, "done", status=status,
              notes="external exit=%s; status=%s" % (process.returncode, result["status"]))


def _worker(prob, instance, cfg, threads, deadline, q):
    # A process watchdog handles solvers whose Python wrappers cannot interrupt
    # a native solve. A new process group also lets it stop external descendants.
    if hasattr(os, "setsid"):
        os.setsid()
    try:
        mode = cfg.get("mode", "incremental")
        encoding = cfg.get("encoding", "matrix")
        if mode not in ("incremental", "maxsat"):
            raise ValueError("mode must be incremental or maxsat")
        if encoding not in ("matrix", "stim") or (encoding == "stim" and mode != "maxsat"):
            raise ValueError("encoding=stim is supported only in mode=maxsat")
        if encoding == "stim":
            hard, soft, nv, mapping, version = _stim_encoding(instance, prob)
            _send(q, "meta", version="stim " + version,
                  notes="Stim circuit WCNF variables mapped by flattened DEM (detectors, observables) signatures")
        else:
            hard, nv = build_cnf(prob, int(cfg.get("xor_chunk", 6)))
            mapping = {j + 1: j for j in range(prob.ncols)}
            soft = [(1, [-v]) for v in mapping]
        if time.monotonic() >= deadline:
            _send(q, "done", status="timeout", notes="time limit reached while building encoding")
            return
        if "dump" in cfg:
            os.makedirs(cfg["dump"], exist_ok=True)
            if mode == "incremental":
                clauses, nvars = add_at_most(hard, nv, mapping, int(cfg.get("k", 1)))
                path = os.path.join(cfg["dump"], "problem.cnf")
                write_cnf(path, clauses, nvars)
            else:
                path = os.path.join(cfg["dump"], "problem.wcnf")
                _write_weighted(path, hard, soft, nv)
            with open(os.path.join(cfg["dump"], "variables.json"), "w") as f:
                json.dump({"error_variable_to_column": mapping, "encoding": encoding,
                           "variant": prob.variant}, f, indent=1)
            _send(q, "done", status="bounds", notes="encoding dumped to " + path + "; no solver run; threads unused")
        elif mode == "incremental":
            _incremental(prob, hard, nv, cfg, q)
        elif cfg.get("binary"):
            _external(prob, hard, soft, nv, mapping, cfg, threads, deadline, q)
        else:
            _rc2(prob, hard, soft, nv, mapping, cfg, q)
    except (ImportError, ModuleNotFoundError) as error:
        _send(q, "done", status="unavailable", notes=str(error) + "; PySAT threads ignored")
    except Exception as error:
        # PySAT raises NoSuchSolverError for unknown/unbuilt names; these are
        # unavailable backends, rather than failures of the distance problem.
        unavailable = type(error).__name__ in ("NoSuchSolverError", "SolverNamesError")
        _send(q, "done", status="unavailable" if unavailable else "error",
              notes=type(error).__name__ + ": " + str(error))


def _stop(process):
    if process.is_alive():
        try:
            if hasattr(os, "killpg"):
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.terminate()
        except ProcessLookupError:
            pass
        except OSError:
            process.terminate()
    process.join(timeout=0.2)


def main():
    tr = common.Trace()
    started = time.monotonic()
    a = common.adapter_args(__doc__)
    prob = common.load(a.instance, a.variant)
    mode = a.cfg.get("mode", "incremental")
    method = "sat_" + mode
    status, witness, version, notes = "timeout", None, None, []
    # Zero errors cannot flip a logical observable. This trivial certificate is
    # independent of package availability and of the instance's ground truth.
    needs_pysat = "dump" not in a.cfg and not (mode == "maxsat" and a.cfg.get("binary"))
    if needs_pysat:
        notes.append("PySAT threads ignored (single-threaded solver interface)")
        try:
            if importlib.util.find_spec("pysat") is None:
                raise ModuleNotFoundError("No module named 'pysat'")
            importlib.import_module("pysat")
        except (ImportError, ModuleNotFoundError) as error:
            status = "unavailable"
            notes.append(str(error))
    else:
        notes.append("threads unused while building/dumping encoding")
    if status != "unavailable":
        tr.lb(1)
    deadline = started + max(0.0, a.time_limit)
    if status != "unavailable" and time.monotonic() < deadline:
        context = multiprocessing.get_context("spawn")
        messages = context.Queue()
        process = context.Process(target=_worker,
                                  args=(prob, a.instance, a.cfg, a.threads, deadline, messages))
        process.start()
        done = False
        while not done:
            # Allow one second for final external-output parsing and cleanup.
            if time.monotonic() >= deadline + 1.0:
                notes.append("whole-run wall-time watchdog stopped the solver")
                break
            try:
                event = messages.get(timeout=0.02)
            except queue.Empty:
                if not process.is_alive():
                    status = "error"
                    notes.append("solver worker exited without a final record (exit=%s)" % process.exitcode)
                    break
                continue
            if event["kind"] == "lb":
                tr.lb(event["value"])
            elif event["kind"] == "ub":
                if common.check_witness(prob, event["witness"])["ok"]:
                    if tr.upper is None or event["value"] < tr.upper:
                        witness = event["witness"]
                        tr.ub(event["value"])
            elif event["kind"] == "invalidate_external_bound":
                tr.lower = 1
                tr.events = [e for e in tr.events if "lb" not in e or e["lb"] <= 1]
            else:
                if event.get("version"):
                    version = (event["version"] if version is None else
                               version + "; " + event["version"])
                if event.get("notes"):
                    notes.append(event["notes"])
                if event["kind"] == "done":
                    status, done = event["status"], True
        _stop(process)
        messages.close()
    elif status != "unavailable":
        notes.append("whole-run time limit reached while loading instance")
    if status == "unavailable":
        tr.lower = tr.upper = None
        tr.events = []
        witness = None
    if status != "error" and tr.upper is not None and tr.lower == tr.upper:
        status = "exact"
    if status == "exact" and (witness is None or tr.lower != tr.upper):
        status = "error"
        notes.append("solver claimed exact without matching certified bounds")
    if tr.lower is not None and tr.upper is not None and tr.lower > tr.upper:
        status = "error"
        notes.append("reported certified lower bound exceeds the validated witness weight")
        tr.events = [e for e in tr.events if "lb" not in e or e["lb"] <= tr.upper]
        tr.lower = max((e["lb"] for e in tr.events if "lb" in e), default=None)
    common.save_result(a.out, prob, method, tr, status, a.threads, a.time_limit,
                       witness=witness, config=a.cfg, notes="; ".join(notes), version=version)
    print(status, tr.lower, tr.upper, tr.seconds())


if __name__ == "__main__":
    main()
