"""Exact CSS code-distance checks for the routing-code matrices.

Usage (all short instances, Z first and then X):
  OMP_NUM_THREADS=2 .venv/bin/python papers/routing_run.py code [seconds_per_threshold] [wall_budget]

Each basis runs in a fresh subprocess with a 590-second wall limit. Completed
thresholds are saved immediately, so an external timeout preserves certificates.
The runner may be repeated: exhausted thresholds and verified distances resume.
This file does not replace the circuit-distance runner, papers/run_parallel.py.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import routing
import stabcode
from cdist import search, symmetry

OUT = HERE.parent / "results/papers3/routing/code_distances.json"
KEYS = (54, 70, 80, 90, 100, 110, "140_12", "140_13")


def read_result():
    if OUT.exists():
        return json.loads(OUT.read_text())
    return {
        "source": "https://arxiv.org/abs/2606.25330v2",
        "method": "exact iterative-deepening CSS code-capacity search; k_table=3, cover=True, labelfree=True",
        "threads_requested": 2,
        "codes": {},
        "commands": [],
    }


def save(result):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result["worker_wall_seconds_total"] = round(sum(command.get("seconds", 0.)
                                                      for command in result["commands"]), 3)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result, indent=2) + "\n")
    tmp.replace(OUT)


def emit(message):
    print(message, flush=True)


def key_arg(value):
    return int(value) if value.isdigit() else value


def code_record(result, key):
    hx, hz, n = routing.matrices(key)
    rebuilt = stabcode.css_parameters(hx, hz, n)
    ident = str(key)
    rec = result["codes"].setdefault(ident, {
        "key": key,
        "tag": routing.tag(key),
        "paper_parameters": list(routing.CODES[key][2]),
        "rebuilt_parameters": list(rebuilt),
        "row_weights": sorted({bin(r).count("1") for r in hx + hz}),
        "notes": routing.CODES[key][1],
        "distance": {},
    })
    return rec, hx, hz, n


def worker(key, basis, time_limit):
    result = read_result()
    rec, hx, hz, n = code_record(result, key)
    prior = rec["distance"].get(basis, {})
    if prior.get("distance") is not None:
        emit(f"{key} {basis}: already exact d={prior['distance']}")
        return
    p = stabcode.css_distance_problem(hx, hz, n, basis, name=f"routing:{key}")
    candidates = routing.translations(key)
    sym = symmetry.from_row_perms(p, candidates)
    kwargs = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {}
    cap = max(13, routing.CODES[key][2][2])
    slots = 2 ** max(10, math.ceil(math.log2(sum(math.comb(p.ncols, j) for j in range(4)) / .5 + 1)))
    run = {
        "distance": None,
        "lower_bound": prior.get("lower_bound", 1),
        "status": "running",
        "columns": p.ncols,
        "rows": p.nrows,
        "observables": p.nobs,
        "candidate_symmetries": len(candidates),
        "surviving_symmetries": sym.get("n_symmetries_kept", 0),
        "column_orbits": len(sym["anchors"]) if sym.get("ok") else None,
        "symmetry_error": sym.get("reason"),
        "table_slots": slots,
        "table_storage_bytes": slots * 9,
        "seconds_per_threshold": time_limit,
        "runs": list(prior.get("runs", [])),
        "attempts": list(prior.get("attempts", [])),
    }
    attempt = {"start_threshold": run["lower_bound"], "seconds_per_threshold": time_limit, "status": "running"}
    run["attempts"].append(attempt)
    rec["distance"][basis] = run
    save(result)
    emit(f"{key} {basis}: rebuilt {rec['rebuilt_parameters']}; symmetries {run['surviving_symmetries']}/{len(candidates)}; "
         f"orbits {run['column_orbits']}; start K={run['lower_bound']}")
    start = time.monotonic()

    def completed(threshold):
        run["runs"].append(threshold)
        if threshold["status"] == "exhausted":
            run["lower_bound"] = threshold["K"] + 1
        run["seconds"] = round(time.monotonic() - start, 3)
        save(result)

    answer = search.distance(p, k_table=3, kmax=cap, cover=True, labelfree=True,
                             time_limit=time_limit, start=run["lower_bound"],
                             on_run=completed, log=emit, **kwargs)
    run["lower_bound"] = answer["lower_bound"]
    run["distance"] = answer["distance"]
    run["table_build_seconds"] = answer["table_seconds"]
    run["table_entries"] = answer["table_entries"]
    run["exclusion_pairs"] = answer["exclusion_pairs"]
    run["threads_observed"] = search.lib().gm_num_threads()
    run["seconds"] = round(time.monotonic() - start, 3)
    run["status"] = "exact" if answer["distance"] is not None else answer["runs"][-1]["status"]
    attempt["status"] = run["status"]
    attempt["seconds"] = run["seconds"]
    if answer["solutions"]:
        witness = list(answer["solutions"][0])
        syndrome, logical = p.check(witness)
        assert syndrome == 0 and logical != 0 and len(set(witness)) == len(witness)
        data_qubits = [p.col_meta[j][0][1] for j in witness]
        data_support = sum(1 << j for j in data_qubits)
        checks, logs = (hz, stabcode.css_logicals(hx, hz, n)[1]) if basis == "Z" else (hx, stabcode.css_logicals(hx, hz, n)[0])
        assert all(stabcode.parity(check & data_support) == 0 for check in checks)
        assert any(stabcode.parity(log & data_support) for log in logs)
        assert len(data_qubits) == answer["distance"]
        run["witness_columns"] = witness
        run["witness_data_qubits"] = data_qubits
        run["witness_syndrome"] = syndrome
        run["witness_logical"] = logical
        run["witness_verified"] = True
    ds = [rec["distance"].get(b, {}).get("distance") for b in "ZX"]
    if all(d is not None for d in ds):
        rec["distance_both_bases"] = min(ds)
    save(result)
    emit(f"{key} {basis}: status={run['status']} d={run['distance']} lower_bound={run['lower_bound']} "
         f"witness_verified={run.get('witness_verified', False)} {run['seconds']}s")


def main(time_limit=90, wall_budget=1400):
    os.environ["OMP_NUM_THREADS"] = "2"
    time_limit, wall_budget = float(time_limit), float(wall_budget)
    started = time.monotonic()
    launched = 0
    previous_seconds = read_result().get("runner_seconds", 0.)
    for basis in "ZX":
        for key in KEYS:
            result = read_result()
            rec, _, _, _ = code_record(result, key)
            if rec["distance"].get(basis, {}).get("distance") is not None:
                continue
            remaining = wall_budget - (time.monotonic() - started)
            if remaining < 3:
                result["runner_status"] = "wall_budget_reached"
                result["last_invocation_seconds"] = round(time.monotonic() - started, 3)
                if launched:
                    result["runner_seconds"] = round(previous_seconds + result["last_invocation_seconds"], 3)
                save(result)
                emit("overall wall budget reached; completed thresholds preserved")
                return
            command = [sys.executable, str(Path(__file__).resolve()), "worker", str(key), basis, str(time_limit)]
            timeout = min(590., remaining)
            command_record = {"argv": command, "OMP_NUM_THREADS": "2", "wall_limit_seconds": timeout}
            launched += 1
            result["commands"].append(command_record)
            save(result)
            step_started = time.monotonic()
            emit("COMMAND " + " ".join(command))
            try:
                child = subprocess.run(command, timeout=timeout, check=False)
                status = {"exit_code": child.returncode}
            except subprocess.TimeoutExpired:
                status = {"timeout": True}
                emit(f"{key} {basis}: subprocess wall timeout after {timeout:.1f}s")
            result = read_result()
            result["commands"][-1].update(status, seconds=round(time.monotonic() - step_started, 3))
            if status.get("timeout"):
                record = result["codes"][str(key)]["distance"].get(basis, {})
                record["status"] = "subprocess_wall_timeout"
                if record.get("attempts"):
                    record["attempts"][-1]["status"] = "subprocess_wall_timeout"
            result["last_invocation_seconds"] = round(time.monotonic() - started, 3)
            result["runner_seconds"] = round(previous_seconds + result["last_invocation_seconds"], 3)
            save(result)
    result = read_result()
    result["runner_status"] = "finished_pass"
    result["last_invocation_seconds"] = round(time.monotonic() - started, 3)
    if launched:
        result["runner_seconds"] = round(previous_seconds + result["last_invocation_seconds"], 3)
    save(result)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        worker(key_arg(sys.argv[2]), sys.argv[3], float(sys.argv[4]))
    else:
        args = sys.argv[2:] if len(sys.argv) > 1 and sys.argv[1] == "code" else sys.argv[1:]
        main(*args)
