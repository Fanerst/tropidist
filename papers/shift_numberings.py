"""Audit all 36 monomial numberings of the shift-paper Tables II and III.

Usage: .venv/bin/python papers/shift_numberings.py key_base [processes] [rounds] [seconds_per_threshold]

The default is two fresh worker processes at a time, six cycles, and 30 seconds
per search threshold. Each numbering has its own module, process, log, circuit,
and pipeline results. Exact existing basis results are resumed. Searches use
the full fault set, k_coll=2, kmax=12, and OMP_NUM_THREADS=1.

Local safeguards terminate a numbering after 570 seconds and the entire sweep
after 3500 seconds. Server runs can disable these guards with environment
variables SHIFT_NUMBERINGS_WORKER_SECONDS=0 and SHIFT_NUMBERINGS_TOTAL_SECONDS=0.
Partial bounds, errors, and unfinished numberings are reported as such.
"""
import contextlib
import itertools
import json
import multiprocessing as mp
import os
import resource
import sys
import time
import traceback
import types

# Set these before importing the search kernel in either parent or spawn child.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import run_parallel
import shift
import stabcode


def _save(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w") as f:
        json.dump(value, f, indent=2)
    os.replace(temporary, path)


def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _reduce(v, span, pivots):
    for row, pivot in zip(span, pivots):
        if (v >> pivot) & 1:
            v ^= row
    return v


def _conjugate(v, gates, basis):
    for targets in gates:
        for control, target in zip(targets[::2], targets[1::2]):
            source, destination = ((control, target) if basis == "X"
                                   else (target, control))
            if (v >> source) & 1:
                v ^= 1 << destination
    return v


def _permute(v, images):
    return sum(1 << images[j] for j in stabcode.bits(v))


def monomial(dx, dy):
    terms = []
    for symbol, exponent in (("x", dx), ("y", dy)):
        if exponent == 1:
            terms.append(symbol)
        elif exponent:
            terms.append(symbol + "^" + str(exponent))
    return " ".join(terms) if terms else "1"


def logical_shift(key, numbering):
    """Independently compare every logical generator with every translation.

    The CNOT unitary is tested modulo the original code and prepared ancillary
    stabilizers. All input stabilizers must be preserved. This is the same
    Pauli calculation as tests/test_shift.py, and does not infer the action
    merely from the builder's chosen final readout permutation.
    """
    key = shift.base_key(key)
    variant = key + "d"
    hx, hz, n = shift.matrices(key)
    count = n // 2
    ell, m = shift.DEFINITIONS[key][:2]
    gates = [layer for cycle in range(2)
             for layer in shift.layers(variant, cycle, rounds=2,
                                       numbering=numbering)]
    lx, lz = stabcode.css_logicals(hx, hz, n)
    sectors = []
    preserved = {}
    for basis, checks, logs, block in (("X", hx, lx, "X"),
                                      ("Z", hz, lz, "Z")):
        stabs = checks + [1 << shift.qubit(key, block, u) for u in range(count)]
        span, pivots = stabcode.rref(stabs)
        preserved[basis] = all(_reduce(_conjugate(v, gates, basis), span, pivots) == 0
                               for v in stabs)
        transformed = [_reduce(_conjugate(v, gates, basis), span, pivots)
                       for v in logs]
        sectors.append((logs, transformed, span, pivots))
    matches = []
    if all(preserved.values()):
        for dx in range(ell):
            for dy in range(m):
                images = ([shift.qubit(key, "R", u, dx, dy) for u in range(count)] +
                          [shift.qubit(key, "L", u, dx, dy) for u in range(count)])
                if all(all(_reduce(_permute(v, images), span, pivots) == out
                           for v, out in zip(logs, transformed))
                       for logs, transformed, span, pivots in sectors):
                    matches.append([dx, dy])
    predicted = tuple(shift.pair_shift(key, numbering))
    predicted_cell = shift.shift_cell(key, 0, *predicted)
    matches_predicted = any(shift.shift_cell(key, 0, *candidate) == predicted_cell
                            for candidate in matches)
    chosen = predicted if matches_predicted else tuple(matches[0]) if matches else None
    return {
        "shift": monomial(*chosen) if chosen is not None else "none",
        "exponents": list(chosen) if chosen is not None else None,
        "predicted_exponents": list(predicted),
        "predicted_matches": matches_predicted,
        "stabilizers_preserved": preserved,
        "logical_generators": {"X": len(lx), "Z": len(lz)},
        "matching_translation_representatives": matches,
        "method": "exact Pauli conjugation, all X/Z logical generators modulo code and prepared-ancilla stabilizers",
    }


def _validate(key, numbering, rounds):
    out = {"valid": False, "layers_disjoint": False, "deterministic": {}}
    try:
        layers = [layer for cycle in range(rounds)
                  for layer in shift.layers(key, cycle, rounds=rounds,
                                            numbering=numbering)]
        assert all(len(layer) == len(set(layer)) for layer in layers), "repeated qubit in CNOT layer"
        out["layers_disjoint"] = True
        for basis in "ZX":
            circuit = shift.build(key, basis, rounds, p=0, numbering=numbering)
            dem = circuit.detector_error_model(decompose_errors=False)
            assert dem.num_errors == 0, "ideal experiment contains error mechanisms"
            out["deterministic"][basis] = True
        out["valid"] = True
    except (ValueError, AssertionError) as exc:
        out["error"] = str(exc).splitlines()[0]
        out["error_type"] = type(exc).__name__
    return out


def variant(numbering, name):
    """A uniquely named module forwarding the chosen schedule numbering."""
    mod = types.ModuleType(name)
    mod.CODES = dict(shift.CODES)
    mod.tag = shift.tag
    mod.matrices = shift.matrices
    mod.translations = shift.translations

    def build(key, basis, rounds, p=0.001, noise="full"):
        return shift.build(key, basis, rounds, p=p, noise=noise,
                           numbering=numbering)

    mod.build = build
    return mod


def _basis_summary(result, path, error=None, resumed=False):
    out = {"result": os.path.relpath(path, ROOT), "resumed": resumed}
    if result is not None:
        lower = result.get("certified_lower_bound")
        upper = result.get("certified_upper_bound")
        verified = bool(result.get("witness", {}).get("verified"))
        out.update(lower_bound=lower, upper_bound=upper,
                   distance=lower if isinstance(lower, int) and lower == upper and verified else None,
                   witness_verified=verified, seconds=result.get("seconds"),
                   model=result.get("model"),
                   sector_symmetries_kept=result.get("sector_symmetries_kept"),
                   symmetries_expected=result.get("symmetries_expected"))
    else:
        out.update(lower_bound=None, upper_bound=None, distance=None,
                   witness_verified=False)
    if error:
        out["error"] = error
    return out


def _row_template(pa, pb):
    return {"A": list(pa), "B": list(pb), "valid_s": None, "d_s": None,
            "valid_d": None, "shift_d": "none", "d_d": None,
            "bounds_s": {}, "bounds_d": {}, "results_s": {}, "results_d": {},
            "status": "pending"}


def _peak_rss_mib():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024.0 * 1024.0) if sys.platform == "darwin" else rss / 1024.0


def _job_directory(cfg, pa, pb):
    return os.path.join(cfg["directory"], "A" + "".join(map(str, pa)) +
                        "_B" + "".join(map(str, pb)))


def _work(job, cfg, connection):
    key, pa, pb = job
    numbering = (pa, pb)
    started = time.monotonic()
    directory = _job_directory(cfg, pa, pb)
    checkpoint = os.path.join(directory, "worker.json")
    row = _row_template(pa, pb)
    row["status"] = "running"
    row["pid"] = os.getpid()
    name = "shift_num" + key + "_a" + "".join(map(str, pa)) + "_b" + "".join(map(str, pb)) + "_w" + str(os.getpid())
    mod = variant(numbering, name)
    sys.modules[name] = mod
    try:
        for suffix in "sd":
            validation = _validate(key + suffix, numbering, cfg["rounds"])
            row["validation_" + suffix] = validation
            row["valid_" + suffix] = validation["valid"]
        try:
            row["logical_d"] = logical_shift(key, numbering)
            row["shift_d"] = row["logical_d"]["shift"]
        except (ValueError, AssertionError) as exc:
            row["logical_d"] = {"shift": "none", "error": str(exc).splitlines()[0]}
        _save(checkpoint, row)
        for suffix in "sd":
            if not row["valid_" + suffix]:
                continue
            row["d_" + suffix] = {}
            for basis in "ZX":
                path = os.path.join(directory, suffix + "_" + basis + ".json")
                old = _load(path)
                resumed = bool(old and old.get("rounds") == cfg["rounds"] and
                               old.get("basis") == basis and old.get("noise") == "full" and
                               old.get("code") == list(shift.CODES[key][2]) and
                               old.get("certified_lower_bound") == old.get("certified_upper_bound") and
                               isinstance(old.get("certified_lower_bound"), int) and
                               old.get("witness", {}).get("verified"))
                error = None
                if not resumed:
                    log_path = os.path.join(directory, suffix + "_" + basis + ".log")
                    try:
                        with open(log_path, "w", buffering=1) as log:
                            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                                run_parallel.main(name, key + suffix, basis, path,
                                                  cfg["rounds"], 2, 12,
                                                  cfg["time_limit"], 1)
                    except Exception as exc:
                        error = type(exc).__name__ + ": " + str(exc).splitlines()[0]
                result = old if resumed else _load(path)
                summary = _basis_summary(result, path, error, resumed)
                row["results_" + suffix][basis] = summary
                row["d_" + suffix][basis] = summary["distance"]
                row["bounds_" + suffix][basis] = [summary["lower_bound"], summary["upper_bound"]]
                row["seconds"] = round(time.monotonic() - started, 2)
                row["peak_rss_mib"] = round(_peak_rss_mib(), 2)
                _save(checkpoint, row)
        row["status"] = "complete" if all(
            not row["valid_" + suffix] or all(row["d_" + suffix].get(basis) is not None for basis in "ZX")
            for suffix in "sd") else "partial"
    except BaseException as exc:
        row["status"] = "error"
        row["error"] = type(exc).__name__ + ": " + str(exc)
        row["traceback"] = traceback.format_exc()
    finally:
        row["seconds"] = round(time.monotonic() - started, 2)
        row["peak_rss_mib"] = round(_peak_rss_mib(), 2)
        _save(checkpoint, row)
        connection.send(row)
        connection.close()


def _aggregate(key, cfg, rows, started, status):
    sorted_rows = sorted(rows, key=lambda row: (row["A"], row["B"]))
    counts = {suffix: sum(row["valid_" + suffix] is True for row in rows)
              for suffix in "sd"}
    histograms = {}
    for suffix in "sd":
        histogram = {}
        for row in rows:
            if row["valid_" + suffix]:
                value = row["d_" + suffix]
                label = "/".join(str(value.get(basis)) for basis in "ZX") if value else "open"
                histogram[label] = histogram.get(label, 0) + 1
        histograms[suffix] = dict(sorted(histogram.items()))
    return {"source": "arXiv:2601.09911v1", "key": key,
            "code": list(shift.CODES[key][2]), "paper_circuit_distance_upper_bound": shift.CODES[key][3],
            "rounds": cfg["rounds"], "seconds_per_threshold": cfg["time_limit"],
            "k_coll": 2, "kmax": 12, "noise": "full", "processes": cfg["processes"],
            "threads_per_process": 1, "numberings": 36, "reported_numberings": len(rows),
            "completed_numberings": sum(row["status"] == "complete" for row in rows),
            "valid_s": counts["s"], "valid_d": counts["d"],
            "invalid_s": sum(row["valid_s"] is False for row in rows),
            "invalid_d": sum(row["valid_d"] is False for row in rows),
            "distance_histograms_Z_X": histograms, "rows": sorted_rows,
            "printed_order": next((row for row in sorted_rows if row["A"] == [1, 2, 3] and row["B"] == [1, 2, 3]), None),
            "status": status, "seconds": round(time.monotonic() - started, 1),
            "limits": {"worker_seconds": cfg["worker_seconds"], "total_seconds": cfg["total_seconds"]}}


def main(key_base, processes=2, rounds=6, time_limit=30):
    key = shift.base_key(str(key_base))
    if key not in shift.PARAMETERS:
        raise ValueError("key_base must name one of 72, 120, 144, 170")
    processes, rounds, time_limit = int(processes), int(rounds), float(time_limit)
    if processes < 1 or rounds < 2 or rounds % 2 or time_limit <= 0:
        raise ValueError("processes and time limit must be positive; rounds must be even and at least two")
    directory = os.path.join(ROOT, "results", "papers3", "shift", "numberings_" + key)
    output = os.path.join(ROOT, "results", "papers3", "shift", "numberings_" + key + ".json")
    cfg = {"processes": processes, "rounds": rounds, "time_limit": time_limit,
           "directory": directory,
           "worker_seconds": float(os.environ.get("SHIFT_NUMBERINGS_WORKER_SECONDS", "570")),
           "total_seconds": float(os.environ.get("SHIFT_NUMBERINGS_TOTAL_SECONDS", "3500"))}
    if cfg["worker_seconds"] < 0 or cfg["total_seconds"] < 0:
        raise ValueError("wall limits must be nonnegative; zero disables a limit")
    jobs = [(key, pa, pb) for pa in itertools.permutations((1, 2, 3))
            for pb in itertools.permutations((1, 2, 3))]
    context = mp.get_context("spawn")
    started = time.monotonic()
    active, rows = {}, []
    pending = iter(jobs)
    exhausted = False
    total_timeout = False
    _save(output, _aggregate(key, cfg, rows, started, "running"))
    try:
        while active or not exhausted:
            if cfg["total_seconds"] and time.monotonic() - started >= cfg["total_seconds"]:
                total_timeout = True
                exhausted = True
                break
            while not exhausted and len(active) < processes:
                try:
                    job = next(pending)
                except StopIteration:
                    exhausted = True
                    break
                receiver, sender = context.Pipe(duplex=False)
                proc = context.Process(target=_work, args=(job, cfg, sender))
                proc.start()
                sender.close()
                active[proc.pid] = (proc, receiver, job, time.monotonic())
            for pid, (proc, receiver, job, job_started) in list(active.items()):
                row = None
                if receiver.poll():
                    try:
                        row = receiver.recv()
                    except EOFError:
                        pass
                timed_out = bool(cfg["worker_seconds"] and
                                 time.monotonic() - job_started >= cfg["worker_seconds"])
                if row is None and not timed_out and proc.is_alive():
                    continue
                if row is None:
                    row = _load(os.path.join(_job_directory(cfg, job[1], job[2]), "worker.json")) or _row_template(job[1], job[2])
                    row["status"] = "worker_timeout" if timed_out else "worker_failed"
                    row["error"] = str(cfg["worker_seconds"]) + "-second worker wall limit reached" if timed_out else "worker exited without a final report"
                    row["seconds"] = round(time.monotonic() - job_started, 2)
                    if proc.is_alive():
                        proc.terminate()
                proc.join(timeout=5)
                if proc.is_alive():
                    proc.kill()
                    proc.join(timeout=5)
                row["worker_exitcode"] = proc.exitcode
                receiver.close()
                active.pop(pid)
                rows.append(row)
                result = _aggregate(key, cfg, rows, started, "running")
                _save(output, result)
                print(time.strftime("%H:%M:%S"), "shift", key,
                      "A=" + "".join(map(str, row["A"])), "B=" + "".join(map(str, row["B"])),
                      "(" + str(row["valid_s"]) + ", " + str(row["d_s"]) + ", " +
                      str(row["valid_d"]) + ", " + row["shift_d"] + ", " + str(row["d_d"]) + ")",
                      row["status"], "%.1fs" % (time.monotonic() - started), flush=True)
            if active:
                time.sleep(0.1)
    finally:
        for proc, receiver, job, job_started in active.values():
            if proc.is_alive():
                proc.terminate()
            proc.join(timeout=5)
            if proc.is_alive():
                proc.kill()
                proc.join(timeout=5)
            receiver.close()
            row = _load(os.path.join(_job_directory(cfg, job[1], job[2]), "worker.json")) or _row_template(job[1], job[2])
            row.update(status="total_timeout" if total_timeout else "interrupted",
                       worker_exitcode=proc.exitcode,
                       seconds=round(time.monotonic() - job_started, 2))
            rows.append(row)
        if total_timeout:
            reported = {(tuple(row["A"]), tuple(row["B"])) for row in rows}
            for _, pa, pb in jobs:
                if (pa, pb) not in reported:
                    row = _row_template(pa, pb)
                    row["status"] = "not_started_total_timeout"
                    rows.append(row)
        status = "complete" if len(rows) == 36 and all(row["status"] == "complete" for row in rows) else "partial"
        result = _aggregate(key, cfg, rows, started, status)
        _save(output, result)
        print(time.strftime("%H:%M:%S"), "shift", key, str(len(rows)) + "/36 numberings;",
              "valid_s=" + str(result["valid_s"]), "valid_d=" + str(result["valid_d"]),
              "distances (Z,X)=" + str(result["distance_histograms_Z_X"]),
              status, str(result["seconds"]) + "s", flush=True)
    return result


if __name__ == "__main__":
    main(*sys.argv[1:])
