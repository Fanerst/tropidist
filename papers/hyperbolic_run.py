"""Resumable exact distance of one rebuilt semi-hyperbolic color code.

Usage: hyperbolic_run.py out.json name [max_d] [seconds per threshold]

OMP_NUM_THREADS chooses the kernel thread count (default 2).  The default
whole-invocation budget is 570 seconds; set HYPERBOLIC_TOTAL_SECONDS=0 for a
server run without that budget.  The lookup-table policy is triples below
512 MiB, otherwise pairs below 1 GiB, otherwise singles (HYPERBOLIC_TABLE_GIB
replaces both ceilings).  A conservative
whole-process estimate must also fit HYPERBOLIC_MEMORY_GIB (default 4).
Only exhausted search thresholds initialize a resumed lower bound.  Paper
distances are comparison data, never search certificates or witnesses.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import sys
import time
from fractions import Fraction
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import hyperbolic as codes
if hasattr(sys, "set_int_max_str_digits"):        # check rows of codes with n > 14000 as decimal strings
    sys.set_int_max_str_digits(0)
import stabcode
from cdist import search, symmetry
from cdist.problem import Problem, dedupe

GIB = 1 << 30
MIB = 1 << 20
TABLE_RULE = "triples <=512 MiB; pairs <=1 GiB; otherwise singles; total estimate below memory ceiling"


def _echelon(rows):
    """Sparse integer elimination; highest set bit is each row's pivot."""
    basis = {}
    for value in rows:
        while value:
            pivot = value.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = value
                break
            value ^= basis[pivot]
    return basis


def _columns(rows, n):
    columns = [0] * n
    for i, row in enumerate(rows):
        for j in stabcode.bits(row):
            columns[j] |= 1 << i
    return columns


def _check_self_dual(hx, hz, n):
    assert hx == hz, "this driver requires H_X = H_Z"
    assert all(isinstance(row, int) and 0 <= row < (1 << n) for row in hx)
    columns = _columns(hx, n)
    for row in hx:
        syndrome = 0
        for j in stabcode.bits(row):
            syndrome ^= columns[j]
        assert syndrome == 0, "H H^T is nonzero"
    return _echelon(hx), columns


def _physical_witness(problem, support):
    return [int(problem.col_meta[j][0][1]) for j in support]


def _check_witness(hx, hz, n, witness, basis=None):
    assert hx == hz
    assert len(witness) == len(set(witness)), "repeated physical qubit"
    assert all(isinstance(j, int) and 0 <= j < n for j in witness)
    value = sum(1 << j for j in witness)
    assert all(stabcode.parity(value & row) == 0 for row in hx), "nonzero syndrome"
    basis = _echelon(hx) if basis is None else basis
    while value:
        pivot = value.bit_length() - 1
        if pivot not in basis:
            return
        value ^= basis[pivot]
    raise AssertionError("witness lies in the stabilizer row space")


def _distance_problem(hx, hz, n, name, basis, columns):
    if n <= 2048:
        return stabcode.css_distance_problem(hx, hz, n, "Z", name=name)
    # For a self-dual CSS code a zero-syndrome vector is a stabilizer iff
    # it pairs trivially with every vector of ker(H), since ker(H)^perp
    # is row(H).  Thus a redundant, unpaired basis of ker(H) gives exactly
    # the same distance without css_logicals' quadratic symplectic pairing.
    # Logical bit positions are free physical coordinates, left uncompressed
    # to avoid a dense transpose.  Pivot values follow by forward substitution.
    pivmask = sum(1 << pivot for pivot in basis)
    labels = [0 if j in basis else 1 << j for j in range(n)]
    for pivot in sorted(basis):
        row = basis[pivot] ^ (1 << pivot)
        label = row & ~pivmask
        for lower in stabcode.bits(row & pivmask):
            label ^= labels[lower]
        labels[pivot] = label
    h, l, meta = dedupe(columns, labels, [("data", j) for j in range(n)])
    return Problem(f"{name}:code:Z", len(hx), n, h, l,
                   [(i, 0) for i in range(len(hx))], meta,
                   {"logical_labels": "unpaired redundant nullspace basis",
                    "physical_logicals": n - 2 * len(basis)})


def table_estimate(problem, k_table):
    """Upper bound before syndrome collisions, using search.Table's layout."""
    entries = sum(math.comb(problem.ncols, i) for i in range(k_table + 1))
    slots = 1 << max(10, (2 * entries).bit_length())
    slot_bytes = 17 if 16 < problem.nobs <= 64 else 9
    table_bytes = slots * slot_bytes + 4 * MIB
    rowcounts = [0] * problem.nrows
    nnz = 0
    for column in problem.h:
        for row in stabcode.bits(column):
            rowcounts[row] += 1
            nnz += 1
    pairs_seen = min(math.comb(problem.ncols, 2),
                     sum(math.comb(count, 2) for count in rowcounts))
    words = max(1, (problem.nrows + 63) // 64)
    label_words = max(1, (problem.nobs + 63) // 64)
    # Dense arrays, Python masks/temporary elimination, exclusions, cover
    # scratch and worker buffers; this is an estimate, not an RSS guarantee.
    arrays = 32 * problem.ncols * (words + label_words) + 128 * nnz
    process_bytes = table_bytes + arrays + 256 * pairs_seen + 512 * MIB
    return dict(k_table=k_table, entries_upper=entries, slots=slots,
                bytes_per_slot=slot_bytes, table_bytes=table_bytes,
                process_bytes=process_bytes)


def table_policy(problem, memory_bytes=4 * GIB):
    estimates = [table_estimate(problem, degree) for degree in (3, 2, 1)]
    for estimate in estimates:
        limit = {3: 512 * MIB, 2: GIB, 1: GIB}[estimate["k_table"]]
        if os.environ.get("HYPERBOLIC_TABLE_GIB"):          # server runs: one ceiling for every degree
            limit = float(os.environ["HYPERBOLIC_TABLE_GIB"]) * GIB
        if estimate["table_bytes"] <= limit and estimate["process_bytes"] < memory_bytes:
            return estimate
    raise MemoryError(f"even a singles table exceeds the {memory_bytes / GIB:g} GiB "
                      f"process estimate: {estimates[-1]}")


def _save(path, records, **metadata):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    payload = dict(schema=1, threads_requested=int(os.environ["OMP_NUM_THREADS"]),
                   threads=search.lib().gm_num_threads(), codes=list(records.values()),
                   registry_count=len(codes.CODES), table_rule=TABLE_RULE,
                   peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss *
                   (1 if sys.platform == "darwin" else 1024), **metadata)
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    temporary.replace(path)


def _resumed_lower_bound(previous):
    exhausted = {run["K"] for run in previous.get("runs", [])
                 if run.get("status") == "exhausted" and run.get("best") is None}
    lower = 1
    while lower in exhausted:
        lower += 1
    if previous.get("d") is not None:
        assert lower == previous["d"], "saved exact distance lacks exhausted lower thresholds"
    return lower


def _paper_mismatch(code, result):
    claimed = code.get("d_claimed", code.get("d"))
    if isinstance(claimed, int) and code.get("status") == "certified":
        if result.get("d") is not None and result["d"] != claimed:
            return f"computed d={result['d']}, paper certified d={claimed}"
        if result["lower_bound"] > claimed:
            return f"computed lower bound {result['lower_bound']}, paper certified d={claimed}"
    if isinstance(claimed, (list, tuple)) and len(claimed) == 2:
        if result["lower_bound"] > claimed[1] or (result.get("d") is not None and result["d"] < claimed[0]):
            return f"computed d={result.get('d')}, lower bound={result['lower_bound']}, paper range={claimed}"
    return None


def main(out, name, max_d=40, time_limit=60):
    max_d, time_limit = int(max_d), float(time_limit)
    if not 1 <= max_d <= search.DMAX or not math.isfinite(time_limit) or time_limit <= 0:
        raise ValueError("max_d must be in 1..DMAX and threshold seconds positive and finite")
    if int(os.environ["OMP_NUM_THREADS"]) <= 0:
        raise ValueError("OMP_NUM_THREADS must be positive")
    total_budget = float(os.environ.get("HYPERBOLIC_TOTAL_SECONDS", "570"))
    if not math.isfinite(total_budget) or total_budget < 0:
        raise ValueError("HYPERBOLIC_TOTAL_SECONDS must be nonnegative and finite")
    memory_bytes = float(os.environ.get("HYPERBOLIC_MEMORY_GIB", "4")) * GIB
    if not math.isfinite(memory_bytes) or memory_bytes <= 0:
        raise ValueError("HYPERBOLIC_MEMORY_GIB must be positive and finite")
    invocation_start = time.monotonic()
    deadline = invocation_start + total_budget if total_budget else math.inf
    registry = {code["name"]: code for code in codes.CODES}
    if name not in registry:
        raise ValueError(f"unknown code {name!r}; choose one of {', '.join(registry)}")
    code = registry[name]
    # S16 gives the row count without constructing the fine mesh. Refuse
    # unsupported huge refinements before allocating their wide bitmasks.
    expected_rows = Fraction(code["N"], 2) * (
        code["L"] ** 2 - 1 + sum(Fraction(1, r) for r in code["orders"]))
    assert expected_rows.denominator == 1
    expected_rows = int(expected_rows)
    if expected_rows > 16320:
        raise ValueError(f"{expected_rows} expected check rows exceed the current cdist kernel "
                         "limit of 16320; a kernel extension is required")
    old = {}
    if Path(out).exists():
        old = {record["name"]: record for record in json.loads(Path(out).read_text())["codes"]}
    records = dict(old)
    hx, hz, n = codes.matrices(name)
    basis, columns = _check_self_dual(hx, hz, n)
    k = n - 2 * len(basis)
    assert k > 0, "code has no logical operators"
    assert (n, k) == (code["n"], code["k"]), (name, n, k, code["n"], code["k"])
    digest = hashlib.sha256(repr((hx, hz, n)).encode()).hexdigest()
    prior = old.get(name, {})
    saved = prior.get("distance", {}).get("Z", {}) if prior.get("matrix_sha256") == digest else {}
    start = _resumed_lower_bound(saved)
    result = dict(d=None, lower_bound=start, upper_bound=saved.get("upper_bound"),
                  witness=saved.get("witness"), last=saved.get("last"), stop_reason="max_d",
                  seconds=saved.get("seconds", 0), runs=list(saved.get("runs", [])))
    if result["witness"] is not None:
        _check_witness(hx, hz, n, result["witness"], basis)
        assert len(result["witness"]) == result["upper_bound"]
        assert start <= result["upper_bound"]
        if start == result["upper_bound"]:
            result["d"] = start
    record = dict(code, n=n, k=k, matrix_sha256=digest, self_dual=True,
                  bases_searched=["Z"], checks={"X": len(hx), "Z": len(hz)},
                  row_weights=sorted({bin(row).count("1") for row in hx}),
                  distance={"Z": result}, max_d=max_d, seconds_per_threshold=time_limit)
    records[name] = record

    def save():
        record.update(d=result["d"], lower_bound=result["lower_bound"],
                      upper_bound=result["upper_bound"], seconds=result["seconds"])
        _save(out, records, invocation_seconds=time.monotonic() - invocation_start)

    print(f"{name}: n={n} k={k}; self-dual, searching one basis; lower bound {start}", flush=True)
    if result["d"] is not None:
        result["stop_reason"] = "cached_exact"
        save()
    elif time.monotonic() >= deadline - 2:
        result["stop_reason"] = "invocation_budget"
        save()
    else:
        if len(hx) > 16320:
            raise ValueError(f"{len(hx)} check rows exceed the current cdist kernel limit of 16320")
        problem = _distance_problem(hx, hz, n, name, basis, columns)
        estimate = table_policy(problem, memory_bytes)
        result.update(table_preflight=estimate, k_table=estimate["k_table"], problem_columns=problem.ncols,
                      logical_label_bits=problem.nobs, table_rule=TABLE_RULE)
        print(f"Lookup table degree {estimate['k_table']}: <= {estimate['entries_upper']:,} entries; "
              f"{estimate['slots']:,} slots, estimated table {estimate['table_bytes'] / MIB:.1f} MiB, "
              f"process {estimate['process_bytes'] / MIB:.1f} MiB. Rule: {TABLE_RULE}", flush=True)
        perms = codes.symmetries(name)
        sym = symmetry.from_row_perms(problem, perms)
        result.update(symmetries_candidates=len(perms), symmetries_kept=sym.get("n_symmetries_kept", 0),
                      symmetry_ok=sym.get("ok", False), symmetry_reason=sym.get("reason"),
                      orbits=len(sym["anchors"]) if sym.get("ok") else None)
        kwargs = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {}
        end = min(max_d, result["upper_bound"] - 1) if result["upper_bound"] else max_d
        remaining = deadline - time.monotonic()
        if remaining <= 2:
            result["stop_reason"] = "invocation_budget"
        elif start <= end:
            basis_start = time.monotonic()
            def checkpoint(run):
                result["runs"].append(run)
                result["last"] = run["status"]
                if run["status"] == "exhausted" and run["best"] is None:
                    result["lower_bound"] = run["K"] + 1
                result["seconds"] = saved.get("seconds", 0) + time.monotonic() - basis_start
                save()
            # Reserve time for every possible C call, including a final timeout.
            effective = min(time_limit, max(0.01, (remaining - 2) / (end - start + 1)))
            result["effective_seconds_per_threshold"] = effective
            save()
            found = search.distance(problem, k_table=estimate["k_table"], kmax=end, start=start,
                                    time_limit=effective, cover=True, on_run=checkpoint,
                                    log=lambda line: print(line, flush=True), **kwargs)
            result.update(lower_bound=found["lower_bound"], table_entries=found["table_entries"],
                          table_seconds=found["table_seconds"],
                          seconds=saved.get("seconds", 0) + time.monotonic() - basis_start)
            result["last"] = found["runs"][-1]["status"] if found["runs"] else "max_d"
            result["stop_reason"] = result["last"]
            if found["distance"] is not None:
                result["d"] = found["distance"]
                result["witness_columns"] = list(found["solutions"][0])
                result["witness"] = _physical_witness(problem, found["solutions"][0])
                _check_witness(hx, hz, n, result["witness"], basis)
                assert len(result["witness"]) == result["d"] == result["lower_bound"]
                result["upper_bound"] = result["d"]
        if result["witness"] is not None and len(result["witness"]) == result["lower_bound"]:
            result["d"] = result["lower_bound"]
        save()
    mismatch = _paper_mismatch(code, result)
    if mismatch:
        record["paper_mismatch"] = mismatch
        save()
        raise AssertionError(f"{name}: {mismatch}; stop and inspect the construction")
    print(f"{name}: d={result['d']}; lower bound={result['lower_bound']}; "
          f"upper bound={result['upper_bound']}; {result['stop_reason']}", flush=True)
    return record


if __name__ == "__main__":
    if not 3 <= len(sys.argv) <= 5:
        raise SystemExit(__doc__.splitlines()[2])
    main(*sys.argv[1:])
