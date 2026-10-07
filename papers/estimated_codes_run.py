"""Exact CSS code distances for estimated_codes; resumable JSON checkpoints.

Usage: estimated_codes_run.py out.json [max_d] [seconds per threshold] [only]
OMP_NUM_THREADS selects the kernel thread count (default 2).  On this shared
laptop, the default whole-invocation budget is 570 seconds.  Set
ESTDIST_TOTAL_SECONDS=0 on the lead's server to remove that budget.  Timed-out
bases resume at their independently exhausted lower bound when matrix hashes
match.  Paper distance bounds never initialize the certified lower bound.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import estimated_codes as codes
import stabcode
from cdist import search, symmetry


def _save(path, records, **metadata):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(dict(schema=1, threads_requested=int(os.environ["OMP_NUM_THREADS"]),
                                   threads=search.lib().gm_num_threads(), codes=records,
                                   registry_count=len(codes.CODES),
                                   peak_rss_bytes=(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss *
                                                   (1 if sys.platform == "darwin" else 1024)),
                                   **metadata), indent=2) + "\n")
    tmp.replace(path)


def _physical_witness(p, support):
    return [int(p.col_meta[j][0][1]) for j in support]


def _check_witness(hx, hz, n, basis, witness):
    if len(set(witness)) != len(witness) or any(j < 0 or j >= n for j in witness):
        raise AssertionError("invalid physical support")
    v = sum(1 << j for j in witness)
    checks, stabilizers = (hz, hx) if basis == "Z" else (hx, hz)
    assert all(not stabcode.parity(v & row) for row in checks)
    assert stabcode.rank(stabilizers + [v]) > stabcode.rank(stabilizers)


def main(out, max_d=12, time_limit=300, only=""):
    max_d, time_limit = int(max_d), float(time_limit)
    if not 1 <= max_d <= search.DMAX or time_limit <= 0:
        raise ValueError("max_d must be in 1..DMAX and threshold seconds positive")
    if int(os.environ["OMP_NUM_THREADS"]) <= 0:
        raise ValueError("OMP_NUM_THREADS must be positive")
    total_budget = float(os.environ.get("ESTDIST_TOTAL_SECONDS", "570"))
    invocation_start = time.monotonic()
    deadline = invocation_start + total_budget if total_budget > 0 else math.inf
    old = {}
    if Path(out).exists():
        old = {r["name"]: r for r in json.loads(Path(out).read_text())["codes"]}
    selected = [c for c in codes.CODES if only in c["name"]]
    if not selected:
        raise ValueError(f"no code matches {only!r}")
    records = dict(old)
    for code in selected:
        if time.monotonic() >= deadline - 2:
            print("Invocation budget reached; rerun to resume the saved certificates.", flush=True)
            break
        started = time.monotonic()
        name = code["name"]
        hx, hz, n = codes.matrices(name)
        _, k = stabcode.css_parameters(hx, hz, n)
        digest = hashlib.sha256(repr((hx, hz, n)).encode()).hexdigest()
        previous = old.get(name, {})
        rec = dict(code, n=n, k=k, paper_n=code.get("paper_n", code["n"]),
                   paper_k=code.get("paper_k", code["k"]),
                   matrix_sha256=digest, row_weights=sorted({bin(r).count("1") for r in hx + hz}),
                   row_weights_by_type={"X": sorted({bin(r).count("1") for r in hx}),
                                        "Z": sorted({bin(r).count("1") for r in hz})},
                   checks={"X": len(hx), "Z": len(hz)}, distance={}, max_d=max_d,
                   seconds_per_threshold=time_limit)
        if previous.get("matrix_sha256") == digest:
            rec["distance"] = previous.get("distance", {})
        records[name] = rec
        rec["parameters_match_paper"] = (n, k) == (rec["paper_n"], rec["paper_k"])
        if k == 0:
            rec["skipped"] = "Literal paper definition rebuilds k=0; no logical distance exists."
            rec["seconds"] = time.monotonic() - started
            rec["d"] = None
            rec["lower_bound"] = None
            _save(out, list(records.values()))
            print(name, rec["skipped"], flush=True)
            continue
        # An exact code minimum already closes the requested problem, even
        # when the other basis has only a larger certified lower bound.
        saved = rec["distance"]
        if all(b in saved for b in "ZX"):
            lower = min(saved[b].get("lower_bound", 1) for b in "ZX")
            known = [r["upper_bound"] for r in saved.values() if r.get("upper_bound") is not None]
            if known and lower == min(known):
                for basis in "ZX":
                    prior = saved[basis]
                    if prior.get("witness") is not None:
                        _check_witness(hx, hz, n, basis, prior["witness"])
                        assert len(prior["witness"]) == prior["upper_bound"]
                    if prior.get("upper_bound") is not None:
                        assert prior.get("witness") is not None
                rec.update(d=lower, lower_bound=lower, upper_bound=lower,
                           seconds=sum(r.get("seconds", 0) for r in saved.values()))
                print(f"{name}: cached exact code distance {lower}", flush=True)
                _save(out, list(records.values()), invocation_seconds=time.monotonic() - invocation_start)
                continue
        for basis in "ZX":
            prior = rec["distance"].get(basis, {})
            if prior.get("d") is not None:
                _check_witness(hx, hz, n, basis, prior["witness"])
                continue
            basis_started = time.monotonic()
            # A table of degree three below 301 columns needs <= 272 MiB;
            # larger instances use degree two, including >64 logical labels.
            p = stabcode.css_distance_problem(hx, hz, n, basis, name=name)
            perms = codes.symmetries(name)
            sym = symmetry.from_row_perms(p, perms)
            kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {}
            k_table = 3 if n <= 300 else 2
            start = prior.get("lower_bound", 1)
            result = dict(d=None, lower_bound=start, last=prior.get("last"),
                          stop_reason="max_d", witness=prior.get("witness"),
                          upper_bound=prior.get("upper_bound"), seconds=prior.get("seconds", 0),
                          runs=list(prior.get("runs", [])), k_table=k_table,
                          symmetries_candidates=len(perms),
                          symmetries_kept=sym.get("n_symmetries_kept", 0),
                          symmetry_ok=sym.get("ok", False), symmetry_reason=sym.get("reason"),
                          orbits=len(sym["anchors"]) if sym.get("ok") else None,
                          problem_columns=p.ncols)
            if name in codes.CONTROL_WITNESSES:
                result["witness"] = codes.control_witness(name, basis)
                _check_witness(hx, hz, n, basis, result["witness"])
                result["upper_bound"] = len(result["witness"])
            rec["distance"][basis] = result
            if result["witness"] is not None:
                _check_witness(hx, hz, n, basis, result["witness"])
                assert len(result["witness"]) == result["upper_bound"]
                assert start <= result["upper_bound"]
            # A verified logical support already supplies an upper bound;
            # exhausting through one less certifies it without another hit.
            end = min(max_d, result["upper_bound"] - 1) if result["upper_bound"] else max_d
            print(f"{name} {basis}: n={n} k={k}; symmetries {result['symmetries_kept']}/{len(perms)}", flush=True)
            remaining = deadline - time.monotonic()
            if remaining <= 2:
                result["stop_reason"] = "invocation_budget"
            elif start <= end:
                last_save = time.monotonic()
                def checkpoint(run):
                    nonlocal last_save
                    result["runs"].append(run)
                    result["last"] = run["status"]
                    if run["status"] == "exhausted":
                        result["lower_bound"] = run["K"] + 1
                    result["seconds"] = prior.get("seconds", 0) + time.monotonic() - basis_start
                    if time.monotonic() - last_save >= 5:
                        _save(out, list(records.values()))
                        last_save = time.monotonic()
                basis_start = basis_started
                # Divide the remaining invocation budget among all possible
                # thresholds, so the C calls cannot overrun the local limit.
                threshold_limit = min(time_limit, max(0.01, (remaining - 2) / (end - start + 1)))
                result["effective_seconds_per_threshold"] = threshold_limit
                r = search.distance(p, k_table=k_table, kmax=end, cover=True,
                                    time_limit=threshold_limit, start=start, on_run=checkpoint,
                                    log=lambda line: print(line, flush=True), **kw)
                result["lower_bound"] = r["lower_bound"]
                result["last"] = r["runs"][-1]["status"] if r["runs"] else "max_d"
                result["stop_reason"] = result["last"]
                result["table_entries"] = r["table_entries"]
                result["table_seconds"] = r["table_seconds"]
                result["seconds"] = prior.get("seconds", 0) + time.monotonic() - basis_start
                if r["distance"] is not None:
                    result["d"] = r["distance"]
                    result["witness"] = _physical_witness(p, r["solutions"][0])
                    result["witness_columns"] = list(r["solutions"][0])
                    _check_witness(hx, hz, n, basis, result["witness"])
                    assert len(result["witness"]) == result["d"] == result["lower_bound"]
                    result["upper_bound"] = result["d"]
            # Exhausted smaller weights plus an independently verified known
            # witness can also close a basis without a new kernel hit.
            if (result["witness"] is not None and
                    len(result["witness"]) == result["lower_bound"]):
                result["d"] = result["lower_bound"]
            _save(out, list(records.values()))
        ds = [rec["distance"][b].get("d") for b in "ZX"]
        lbs = [rec["distance"][b]["lower_bound"] for b in "ZX"]
        rec["d"] = min(ds) if all(d is not None for d in ds) else None
        rec["lower_bound"] = min(lbs)
        ubs = [r.get("upper_bound") for r in rec["distance"].values() if r.get("upper_bound") is not None]
        rec["upper_bound"] = min(ubs) if ubs else None
        if rec["upper_bound"] == rec["lower_bound"]:
            rec["d"] = rec["lower_bound"]
        rec["seconds"] = sum(r.get("seconds", 0) for r in rec["distance"].values())
        print(f"{name}: d={ds}; lower bounds={lbs}; paper {code['d_claimed']} ({code['status']})", flush=True)
        _save(out, list(records.values()), invocation_seconds=time.monotonic() - invocation_start)
    return list(records.values())


if __name__ == "__main__":
    main(*sys.argv[1:])
