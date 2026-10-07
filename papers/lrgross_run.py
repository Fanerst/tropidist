"""Bounded local runners for lrgross; existing run_parallel is unchanged.

Usage:
  python papers/lrgross_run.py parallel Z [wall_seconds=590]
  python papers/lrgross_run.py effective Z [wall_seconds=590]

The parallel mode runs the requested run_parallel arguments 6 3 12 600.
Each child is stopped before ten minutes, or at RSS >= 2 GiB.  Execution
metadata records whether the existing driver returned or was interrupted;
its threshold-by-threshold JSON remains intact.  Effective mode separately
checks the paper's residual problem, and replays every upper-bound witness.
"""
import json
import math
import os
import ctypes
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
OUTDIR = os.path.join(ROOT, "results", "papers3", "lrgross")
LOGDIR = os.path.join(ROOT, "logs", "papers3", "lrgross")


def save(path, result):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(result, f, indent=2)
    os.replace(path + ".tmp", path)


def log(*items):
    print(time.strftime("%H:%M:%S"), *items, flush=True)


def rss_reader():
    """Read the child directly; spawning `ps` is disallowed by this sandbox."""
    if sys.platform == "darwin":
        lib = ctypes.CDLL("/usr/lib/libproc.dylib")
        lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                                     ctypes.c_void_p, ctypes.c_int]
        lib.proc_pidinfo.restype = ctypes.c_int

        def read(pid):
            task_info = ctypes.create_string_buffer(96)
            got = lib.proc_pidinfo(pid, 4, 0, task_info, 96)  # PROC_PIDTASKINFO
            return ctypes.c_uint64.from_buffer(task_info, 8).value if got == 96 else None
        return read

    def read(pid):
        try:
            with open(f"/proc/{pid}/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) * 1024
        except FileNotFoundError:
            pass
        return None
    return read


def verify(circ, full, sector, columns):
    from cdist import replay
    raw = replay.lift_to_dem(full, sector, columns)
    dets, obs, terms = replay.check_in_dem(circ, raw)
    faults = replay.physical_faults(circ, raw)
    d2, o2 = replay.replay(circ, faults)
    ok = not dets and bool(obs) and not d2 and o2 == obs and len(set(raw)) == len(raw)
    return {"weight": len(raw), "verified": ok, "dem_error_indices": raw,
            "dem_errors": terms, "dem_check": {"detectors": dets, "observables": obs},
            "physical_faults": [{k: f[k] for k in ("tick", "instruction", "paulis", "flipped_measurement", "stack")}
                                for f in faults],
            "replay": {"fired_detectors": d2, "flipped_observables": o2}}


def effective_worker(basis, out):
    import design
    import lrgross
    import stabcode
    from cdist import isd, problem, search
    started = time.monotonic()
    key = "lr11"
    eff = lrgross.effective(key, basis)
    circ = lrgross.build(key, basis, 6)
    path = os.path.join(ROOT, "circuits", "papers", f"lrgrosslr11_r6_{basis}_effective.stim")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    circ.to_file(path)
    full = problem.load_dem_problem(path)
    sector = problem.sector_problem(full)
    assert problem.sector_is_exact(full, sector)
    window = problem.window_problem(sector, 1, 1)
    index = {}
    for j, (h, l) in enumerate(zip(window.h, window.l)):
        mask = sum(1 << int(window.row_meta[i][0]) for i in stabcode.bits(h))
        index[mask, l] = window.col_meta[j]
    assert set(index) == set(zip(eff.h, eff.l))
    coll = problem.collapse_time(sector)
    collapsed_columns = {(sum(1 << int(coll.row_meta[i][0]) for i in stabcode.bits(h)), l)
                         for h, l in zip(coll.h, coll.l)}
    assert collapsed_columns == set(index)
    sym, kw = design.problem_symmetry(eff, lrgross.make_code(key))
    assert sym["n_symmetries_kept"] == len(lrgross.translations(key))
    slots = 2 ** max(10, math.ceil(math.log2(2 * sum(math.comb(eff.ncols, i) for i in range(4)) + 1)))
    result = {"paper": "arXiv:2603.05481v2", "key": key, "basis": basis,
              "paper_circuit_distance": 11, "paper_claim_status": "conjecture",
              "method": "design.effective_problem; exact search with cover and per-check cyclic orders",
              "rounds": 6, "noise": "full", "circuit": os.path.relpath(path, ROOT),
              "model": {"rows": eff.nrows, "columns": eff.ncols, "observables": eff.nobs,
                        "qubits": circ.num_qubits, "detectors": circ.num_detectors,
                        "dem_mechanisms": full.notes["raw_mechanisms"],
                        "sector_reduction_exact": True, "symmetries_kept": sym["n_symmetries_kept"],
                        "symmetries_expected": len(lrgross.translations(key)),
                        "effective_equals_collapsed": True, "effective_equals_window_t1": True,
                        "k3_table_bytes": 9 * slots},
              "certified_lower_bound": 1, "runs": []}
    save(out, result)

    def accept(sol, source):
        assert eff.check(sol)[0] == 0 and eff.check(sol)[1]
        columns = [index[eff.h[j], eff.l[j]] for j in sol]
        witness = verify(circ, full, sector, columns)
        assert witness["verified"], witness
        if witness["weight"] < result.get("certified_upper_bound", 10 ** 9):
            result.update(certified_upper_bound=witness["weight"], witness=witness, upper_bound_source=source)
            save(out, result)
            log("effective", basis, "upper bound", witness["weight"], "verified by DEM and physical replay")

    # The test's exact distance-12 data logical is an unconditional starting
    # witness, independent of the conjectured circuit distance.
    with open(os.path.join(OUTDIR, "builder_checks.json")) as f:
        checks = json.load(f)
    codep = stabcode.css_distance_problem(*lrgross.matrices(key), basis)
    by_signature = {(h, l): j for j, (h, l) in enumerate(zip(eff.h, eff.l))}
    sol12 = checks["code_distance"][basis]["witness"]
    assert checks["code_distance"][basis]["distance"] == 12
    accept([by_signature[codep.h[j], codep.l[j]] for j in sol12], "exact code-distance witness")
    # Random search can provide a tighter upper bound; never a lower bound.
    upper_started = time.monotonic()
    weight, sol = isd.search(eff, start_best=13, stop_at=11, time_limit=45, seed=260305481, log=log)
    result["isd"] = {"seconds": time.monotonic() - upper_started, "weight": weight, "upper_bounds_only": True}
    if sol is not None:
        accept(sol, "ISD on the effective problem, mapped to the real window")
    save(out, result)

    def on_run(rec):
        result["runs"].append({"K": rec["K"], "status": rec["status"], "best": rec["best"],
                               "nodes": sum(rec["nodes"]), "seconds": rec["seconds"]})
        if rec["status"] == "exhausted" and rec["best"] is None:
            result["certified_lower_bound"] = rec["K"] + 1
        result["seconds"] = time.monotonic() - started
        save(out, result)

    distance = search.distance(eff, k_table=3, kmax=12, cover=True, time_limit=120,
                               log=log, on_run=on_run, **kw)
    result["certified_lower_bound"] = distance["lower_bound"]
    result["effective_distance"] = distance["distance"]
    if distance["solutions"]:
        accept(distance["solutions"][0], "exact effective search, mapped to the real window")
    result["seconds"] = time.monotonic() - started
    result["status"] = "exact" if result.get("certified_upper_bound") == result["certified_lower_bound"] else "bounded"
    save(out, result)
    log("effective done", basis, "bounds", result["certified_lower_bound"], result.get("certified_upper_bound"),
        "seconds", round(result["seconds"], 2))


def monitored(mode, basis, wall_seconds=590):
    if basis not in ("Z", "X") or mode not in ("parallel", "effective"):
        raise ValueError("mode parallel/effective, basis Z/X")
    wall_seconds = min(float(wall_seconds), 590)
    os.makedirs(OUTDIR, exist_ok=True)
    os.makedirs(LOGDIR, exist_ok=True)
    stem = f"lr11_{basis}" if mode == "parallel" else f"effective_{basis}"
    out = os.path.join(OUTDIR, stem + ".json")
    logfile = os.path.join(LOGDIR, stem + ".log")
    python = os.path.join(ROOT, ".venv", "bin", "python")
    if mode == "parallel":
        command = [python, os.path.join(HERE, "run_parallel.py"), "lrgross", "lr11", basis, out, "6", "3", "12", "600"]
    else:
        command = [python, __file__, "effective-worker", basis, out]
    env = dict(os.environ, OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2", PYTHONDONTWRITEBYTECODE="1")
    started = time.monotonic()
    max_rss, stop_reason = 0, None
    read_rss = rss_reader()
    rss_samples = 0
    with open(logfile, "w") as handle:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                elapsed = time.monotonic() - started
                value = read_rss(child.pid)
                if value is not None:
                    max_rss = max(max_rss, value)
                    rss_samples += 1
                if elapsed >= wall_seconds or max_rss >= 2 * 1024 ** 3:
                    stop_reason = "wall_time_limit" if elapsed >= wall_seconds else "RSS_limit"
                    child.terminate()
                    try:
                        child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        child.kill()
                    break
                time.sleep(1)
        finally:
            if child.poll() is None:
                child.kill()
        exit_code = child.wait()
    execution = {"mode": mode, "basis": basis, "command": command,
                 "OMP_NUM_THREADS": 2, "wall_limit_seconds": wall_seconds,
                 "RSS_limit_bytes": 2 * 1024 ** 3, "max_RSS_bytes": max_rss,
                 "RSS_samples": rss_samples,
                 "seconds": time.monotonic() - started, "exit_code": exit_code,
                 "stop_reason": stop_reason, "log": os.path.relpath(logfile, ROOT)}
    save(os.path.join(OUTDIR, stem + "_execution.json"), execution)
    log("execution", stem, "exit", exit_code, "reason", stop_reason,
        "seconds", round(execution["seconds"], 2), "peak RSS MiB", round(max_rss / 1024 ** 2, 1))
    if os.path.exists(out):
        with open(out) as handle:
            result = json.load(handle)
        log("saved bounds", result.get("certified_lower_bound"), result.get("certified_upper_bound"))
    return exit_code


if __name__ == "__main__":
    mode, basis = sys.argv[1:3]
    if mode == "effective-worker":
        effective_worker(basis, sys.argv[3])
    else:
        sys.exit(monitored(mode, basis, *sys.argv[3:]))
