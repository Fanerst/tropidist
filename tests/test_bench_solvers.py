"""Plain-script checks for the benchmark MILP and SAT/MaxSAT adapters.

The CNF checks use exhaustive fault assignments and unit propagation only;
PySAT is deliberately not required.  Integration records and command output
stay under results/bench_dev/solvers and logs/bench_dev/solvers.

Run: OMP_NUM_THREADS=2 .venv/bin/python tests/test_bench_solvers.py
"""
from __future__ import annotations

import itertools
import json
import os
from pathlib import Path
import random
import shlex
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "bench"))
sys.path.insert(0, str(ROOT))
import common
from bench.adapters import sat


RESULTS = ROOT / "results" / "bench_dev" / "solvers"
LOGS = ROOT / "logs" / "bench_dev" / "solvers"


class PropagationFormula:
    """Independent unit propagator, with no SAT package or search fallback."""

    def __init__(self, clauses, nv):
        self.nv = nv
        self.clauses = []
        self.occurrences = [[] for _ in range(nv + 1)]
        self.units = []
        self.contradiction = False
        for original in clauses:
            clause = tuple(dict.fromkeys(original))
            assert all(isinstance(v, int) and 0 < abs(v) <= nv for v in clause)
            if any(-v in clause for v in clause):
                continue
            ci = len(self.clauses)
            self.clauses.append(clause)
            if not clause:
                self.contradiction = True
            elif len(clause) == 1:
                self.units.append(clause[0])
            for literal in clause:
                self.occurrences[abs(literal)].append((ci, literal))
        self.initial_remaining = [len(c) for c in self.clauses]

    def extend(self, e_assignment):
        """Return whether the assigned faults propagate to a satisfied CNF."""
        if self.contradiction:
            return False
        values = [0] * (self.nv + 1)
        remaining = self.initial_remaining.copy()
        satisfied = [False] * len(self.clauses)
        pending = self.units + list(e_assignment)
        while pending:
            literal = pending.pop()
            variable = abs(literal)
            value = 1 if literal > 0 else -1
            if values[variable]:
                if values[variable] != value:
                    return False
                continue
            values[variable] = value
            for ci, occurrence in self.occurrences[variable]:
                remaining[ci] -= 1
                if occurrence * value > 0:
                    satisfied[ci] = True
                if satisfied[ci]:
                    continue
                if remaining[ci] == 0:
                    return False
                if remaining[ci] == 1:
                    pending.extend(v for v in self.clauses[ci] if values[abs(v)] == 0)
        unresolved = [c for c, ok in zip(self.clauses, satisfied) if not ok]
        assert not unresolved, (
            "Auxiliary variables were not determined sufficiently by propagation",
            e_assignment, unresolved[:3],
        )
        return True


def _tiny_problem(h, l, nrows, nobs):
    return common.Prob("encoding_test", "full", nrows, nobs, h, l, {})


def test_encodings(seed=193):
    rng = random.Random(seed)
    cases = [
        _tiny_problem([], [], 0, 0),
        _tiny_problem([0], [0], 0, 0),
        _tiny_problem([0], [1], 0, 1),
        _tiny_problem([1], [1], 1, 1),
        _tiny_problem([1, 1], [1, 0], 3, 3),
        _tiny_problem([0, 0, 0], [1, 2, 3], 2, 2),
    ]
    for _ in range(20):
        n = rng.randrange(1, 10)
        m, nobs = rng.randrange(0, 6), rng.randrange(0, 4)
        cases.append(_tiny_problem(
            [rng.randrange(1 << m) for _ in range(n)],
            [rng.randrange(1 << nobs) for _ in range(n)], m, nobs,
        ))
    # Exercise the largest promised assignment domain, and parity chunk cuts.
    cases.append(_tiny_problem(
        [rng.randrange(16) for _ in range(12)],
        [rng.randrange(4) for _ in range(12)], 4, 2,
    ))
    checks = 0
    for case_id, prob in enumerate(cases):
        n = prob.ncols
        bounds = list(range(n + 1)) if n <= 6 else sorted({0, 1, n // 2, n - 1, n})
        for chunk in (2, 3, 6):
            clauses, nv = sat.build_cnf(prob, xor_chunk=chunk)
            assert nv >= n
            base = PropagationFormula(clauses, nv)
            bounded = []
            for k in bounds:
                limited, limited_nv = sat.add_at_most(clauses, nv, list(range(1, n + 1)), k)
                bounded.append((k, PropagationFormula(limited, limited_nv)))
            for mask in range(1 << n):
                assignment = [j + 1 if (mask >> j) & 1 else -(j + 1) for j in range(n)]
                syndrome = logical = 0
                weight = 0
                for j in range(n):
                    if (mask >> j) & 1:
                        syndrome ^= prob.h[j]
                        logical ^= prob.l[j]
                        weight += 1
                valid = syndrome == 0 and logical != 0
                context = (case_id, n, chunk, mask)
                assert base.extend(assignment) == valid, context
                checks += 1
                for k, formula in bounded:
                    assert formula.extend(assignment) == (valid and weight <= k), context + (k,)
                    checks += 1
    print("ok: %d propagation checks over %d tiny problems" % (checks, len(cases)), flush=True)


def test_wcnf_and_parser():
    RESULTS.mkdir(parents=True, exist_ok=True)
    prob = _tiny_problem([1, 1], [1, 0], 1, 1)
    clauses, nv = sat.build_cnf(prob, xor_chunk=2)
    path = RESULTS / "test_encoding.wcnf"
    sat.write_wcnf(str(path), clauses, nv, evars=[1, 2])
    lines = [line.split() for line in path.read_text().splitlines()
             if line.strip() and not line.lstrip().startswith("c")]
    assert lines[0][:2] == ["p", "wcnf"], lines[0]
    _, _, got_nv, count, top = lines[0]
    assert int(got_nv) == nv
    assert int(count) == len(clauses) + 2
    assert int(top) > 2
    hard, soft = [], []
    for row in lines[1:]:
        numbers = list(map(int, row))
        assert numbers[-1] == 0
        weight, clause = numbers[0], numbers[1:-1]
        if weight == int(top):
            hard.append(clause)
        else:
            soft.append((weight, clause))
    assert hard == clauses
    assert soft == [(1, [-1]), (1, [-2])], soft
    assert len(lines) - 1 == int(count)

    parsed = sat.parse_maxsat_output(
        "c handmade solver output\no 7\no 3\ns OPTIMUM FOUND\n"
        "v 1 -2 3\nv -4 5 0\n"
    )
    assert parsed["status"] == "OPTIMUM FOUND", parsed
    assert parsed["objective"] == 3, parsed
    assert parsed["model"] == [1, -2, 3, -4, 5], parsed
    assert parsed["optimal"] is True and parsed["unsat"] is False, parsed
    incumbent = sat.parse_maxsat_output("o 5\ns SATISFIABLE\nv -1 2 0\n")
    assert incumbent["objective"] == 5 and incumbent["model"] == [-1, 2], incumbent
    assert not incumbent["optimal"] and not incumbent["unsat"], incumbent
    unsat = sat.parse_maxsat_output("s UNSATISFIABLE\n")
    assert unsat["unsat"] and unsat["model"] is None, unsat
    unknown = sat.parse_maxsat_output("s UNKNOWN\n")
    assert not unknown["optimal"] and not unknown["unsat"], unknown
    print("ok: WCNF writer and standard MaxSAT output parser", flush=True)


def _run_adapter(adapter, instance, variant, label, time_limit=120, config="", extra_env=None):
    RESULTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / (label + ".json")
    log = LOGS / (label + ".log")
    if out.exists():
        out.unlink()
    args = ["--instance", str(ROOT / "bench" / "instances" / instance),
            "--variant", variant, "--time-limit", str(time_limit), "--threads", "1",
            "--out", str(out)]
    if config:
        args += ["--config", config]
    command = [sys.executable, str(ROOT / "bench" / "adapters" / (adapter + ".py"))] + args
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "2"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra_env:
        env.update(extra_env)
    print("run: " + shlex.join(command), flush=True)
    try:
        result = subprocess.run(command, cwd=str(ROOT), env=env, capture_output=True,
                                text=True, timeout=time_limit + 10)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        log.write_text("command: " + shlex.join(command) + "\n" + stdout + stderr)
        raise AssertionError("Adapter exceeded wall limit; see %s" % log) from exc
    log.write_text("command: " + shlex.join(command) + "\nexit: %d\n" % result.returncode
                   + result.stdout + result.stderr)
    assert result.returncode == 0, (command, result.returncode, str(log))
    assert out.exists(), ("No result record", command, str(log))
    record = json.loads(out.read_text())
    print("record: %s status=%s bounds=%s,%s seconds=%s" % (
        label, record["status"], record["lower_bound"], record["upper_bound"], record["seconds"]),
        flush=True)
    return record


def _check_exact(record, prob):
    assert record["status"] == "exact", record
    assert record["lower_bound"] == record["upper_bound"], record
    assert isinstance(record["upper_bound"], int) and record["upper_bound"] >= 1, record
    assert record["witness_ok"] is True, record
    assert common.check_witness(prob, record["witness"])["ok"], record
    assert len(record["witness"]) == record["upper_bound"], record
    if prob.distance_kind == "exact":
        assert record["lower_bound"] == prob.distance, record
        assert record["agrees_with_truth"] is True, record


def _enumerated_distance(prob, upper):
    for weight in range(1, upper + 1):
        for columns in itertools.combinations(range(prob.ncols), weight):
            syndrome = logical = 0
            for j in columns:
                syndrome ^= prob.h[j]
                logical ^= prob.l[j]
            if syndrome == 0 and logical != 0:
                return weight
    return None


def test_milp():
    for instance, variant in (("fx_bb72_code", "full"), ("fx_sdbb16_r3", "sector"),
                              ("fx_sdbb16_r3", "collapsed")):
        prob = common.load(str(ROOT / "bench" / "instances" / instance), variant)
        record = _run_adapter("milp", instance, variant,
                              "test_milp_%s_%s" % (instance, variant), config="backend=scipy")
        _check_exact(record, prob)
        if variant == "collapsed":
            # This fixture's collapsed metadata is unknown.  Its declared
            # relaxation relation bounds this exhaustive check by sector truth.
            sector = common.load(str(ROOT / "bench" / "instances" / instance), "sector")
            assert sector.distance_kind == "exact" and sector.distance is not None
            assert record["upper_bound"] <= sector.distance, record
            assert _enumerated_distance(prob, record["upper_bound"]) == record["upper_bound"], record
    print("ok: SciPy MILP exact on code, circuit sector, and independently checked collapsed", flush=True)


def test_sat_unavailable():
    # A shadow package also blocks imports in workers started with spawn.
    # This makes the check reproducible both with and without real PySAT.
    shadow = RESULTS / "missing_pysat"
    package = shadow / "pysat"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text(
        "raise ModuleNotFoundError('PySAT intentionally unavailable in benchmark test')\n")
    pythonpath = str(shadow)
    if os.environ.get("PYTHONPATH"):
        pythonpath += os.pathsep + os.environ["PYTHONPATH"]
    record = _run_adapter("sat", "fx_bb72_code", "full", "test_sat_unavailable",
                          time_limit=2, extra_env={"PYTHONPATH": pythonpath})
    assert record["status"] == "unavailable", record
    assert record["lower_bound"] is None and record["upper_bound"] is None, record
    assert record["witness"] is None, record
    print("ok: missing PySAT produces one unavailable record and exit 0", flush=True)


def main():
    test_encodings()
    test_wcnf_and_parser()
    test_milp()
    test_sat_unavailable()
    print("all benchmark solver tests passed", flush=True)


if __name__ == "__main__":
    main()
