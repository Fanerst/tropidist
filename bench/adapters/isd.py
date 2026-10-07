"""Upper bounds from this project's randomised information-set search.

config: seed=1, swaps_per_step=4, chunk_seconds=0.25, chunks=0 (unlimited),
stop_at=1. Each native search stops after its first improving iteration, so upper-bound
events are reported promptly. A finite chunks limit or stop_at ends with bounds;
the wall-time limit ends with timeout. Neither outcome proves a lower bound.
"""
from __future__ import annotations

import ctypes
import math
import multiprocessing
import os
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
_STARTED = time.time()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common


class _Unavailable(Exception):
    pass


def _load_library(isd, deadline):
    """Load a current library, or build outside cdist to preserve the checkout."""
    src = os.path.join(common.ROOT, "cdist", "isd.c")
    existing = os.path.join(common.ROOT, "cdist", "libisd.so")

    def load(path):
        lib = ctypes.CDLL(path)
        lib.isd_search.restype = ctypes.c_int
        lib.isd_num_threads.restype = ctypes.c_int
        isd._LIB = lib
        return lib

    if os.path.exists(existing) and os.path.getmtime(existing) >= os.path.getmtime(src):
        try:
            return load(existing), None
        except (OSError, AttributeError):
            pass                     # for example, an incompatible shared-library architecture
    build_root = os.path.join(common.ROOT, "results", "bench_dev", "heuristics")
    os.makedirs(build_root, exist_ok=True)
    build_dir = tempfile.TemporaryDirectory(prefix="isd-build-", dir=build_root)
    out = os.path.join(build_dir.name, "libisd.so")
    base = ["cc", "-O3", "-shared", "-fPIC", src, "-o", out]
    if sys.platform == "darwin":
        attempts = [base + ["-isysroot", "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk"], base]
    else:
        attempts = [base + ["-march=native", "-fopenmp"], base + ["-fopenmp"]]
    errors = []
    try:
        for cmd in attempts:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("deadline reached while building ISD")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=remaining)
            except FileNotFoundError as exc:
                raise _Unavailable(str(exc))
            except subprocess.TimeoutExpired:
                raise TimeoutError("deadline reached while building ISD")
            if result.returncode == 0:
                try:
                    return load(out), build_dir
                except (OSError, AttributeError) as exc:
                    raise _Unavailable("could not load ISD library: " + str(exc))
            errors.append(result.stderr.strip()[-1500:])
        raise _Unavailable("could not build ISD library: " + "; ".join(errors))
    except BaseException:
        build_dir.cleanup()
        raise


def _worker(conn, prob, cfg, deadline, threads, started):
    # A separate process lets the parent stop native code, model construction,
    # imports, or the compiler when the whole-run deadline is reached.
    if hasattr(os, "setsid"):
        os.setsid()
    os.environ["OMP_NUM_THREADS"] = str(threads)
    os.environ["OMP_DYNAMIC"] = "FALSE"
    calls = valid = 0
    build_dir = None
    try:
        from cdist import isd

        lib, build_dir = _load_library(isd, deadline)
        actual_threads = int(lib.isd_num_threads())
        conn.send({"type": "ready", "kernel_threads": actual_threads})
        p = common.to_cdist(prob)
        # The native pivot-swap loop requires positive rank. At rank zero its
        # information-set vectors are the single columns themselves.
        if not any(prob.h):
            for j, logical in enumerate(prob.l):
                if logical:
                    conn.send({"type": "result", "weight": 1, "witness": [j], "calls": 0,
                               "valid": 1, "seconds": time.time() - started})
                    break
            conn.send({"type": "done", "status": "bounds", "calls": 0,
                       "valid": int(any(prob.l)), "note": "zero-rank information set"})
            return
        if not any(prob.l):
            conn.send({"type": "done", "status": "bounds", "calls": 0, "valid": 0,
                       "note": "all logical columns are zero"})
            return
        best = None
        while not cfg["chunks"] or calls < cfg["chunks"]:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                conn.send({"type": "done", "status": "timeout", "calls": calls, "valid": valid})
                return
            # Returning after each improvement preserves its discovery time.
            # The initial fundamental information-set vector has weight <= m+1.
            stop = p.nrows + 1 if best is None else best - 1
            w, sol = isd.search(p, start_best=best, stop_at=stop,
                                time_limit=min(cfg["chunk_seconds"], remaining),
                                swaps_per_step=cfg["swaps_per_step"],
                                seed=(cfg["seed"] + calls) % (1 << 64))
            found_seconds = time.time() - started
            calls += 1
            conn.send({"type": "progress", "calls": calls, "valid": valid})
            if w is not None:
                if not common.check_witness(prob, sol)["ok"] or w != len(sol):
                    raise RuntimeError("ISD returned an invalid witness")
                valid += 1
                best = w
                conn.send({"type": "result", "weight": w, "witness": list(sol),
                           "calls": calls, "valid": valid, "seconds": found_seconds})
                if best <= cfg["stop_at"]:
                    status = "timeout" if time.monotonic() >= deadline else "bounds"
                    conn.send({"type": "done", "status": status, "calls": calls, "valid": valid})
                    return
        status = "timeout" if time.monotonic() >= deadline else "bounds"
        conn.send({"type": "done", "status": status, "calls": calls, "valid": valid})
    except _Unavailable as exc:
        conn.send({"type": "done", "status": "unavailable", "calls": calls, "valid": valid,
                   "note": str(exc)})
    except TimeoutError as exc:
        conn.send({"type": "done", "status": "timeout", "calls": calls, "valid": valid,
                   "note": str(exc)})
    except BaseException as exc:
        conn.send({"type": "done", "status": "error", "calls": calls, "valid": valid,
                   "note": type(exc).__name__ + ": " + str(exc)})
    finally:
        if build_dir is not None:
            build_dir.cleanup()
        conn.close()


def _stop_worker(proc):
    if proc.pid is None:
        return
    proc.join(timeout=0.05)
    if proc.is_alive():
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except (AttributeError, ProcessLookupError, PermissionError):
            proc.terminate()
    proc.join(timeout=0.3)
    if proc.is_alive():
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (AttributeError, ProcessLookupError, PermissionError):
            proc.kill()
        proc.join(timeout=0.3)


def _config(raw):
    cfg = {"seed": int(raw.get("seed", 1)),
           "swaps_per_step": int(raw.get("swaps_per_step", 4)),
           "chunk_seconds": float(raw.get("chunk_seconds", 0.25)),
           "chunks": int(raw.get("chunks", 0)), "stop_at": int(raw.get("stop_at", 1))}
    unknown = set(raw) - set(cfg)
    if unknown:
        raise ValueError("unknown config keys: " + ", ".join(sorted(unknown)))
    if (cfg["seed"] < 0 or cfg["swaps_per_step"] < 0 or not math.isfinite(cfg["chunk_seconds"])
            or cfg["chunk_seconds"] <= 0 or cfg["chunks"] < 0):
        raise ValueError("seed, swaps_per_step and chunks must be nonnegative; chunk_seconds must be positive")
    if cfg["stop_at"] < 1:
        raise ValueError("stop_at must be positive")
    return cfg


def main():
    a = common.adapter_args(__doc__)
    tr = common.Trace()
    tr.t0 = _STARTED
    deadline = time.monotonic() + max(0.0, a.time_limit - (time.time() - _STARTED))
    prob = common.load(a.instance, a.variant)
    status, witness = "timeout", None
    cfg = a.cfg
    calls = valid = 0
    kernel_threads = None
    note = ""
    proc = None
    conn = None
    try:
        cfg = _config(a.cfg)
        if a.threads < 1:
            raise ValueError("threads must be positive")
        if deadline > time.monotonic():
            ctx = multiprocessing.get_context("spawn")
            conn, child_conn = ctx.Pipe(duplex=False)
            proc = ctx.Process(target=_worker, args=(child_conn, prob, cfg, deadline, a.threads, _STARTED))
            proc.start()
            child_conn.close()
            while True:
                # Drain queued witnesses before enforcing the deadline, so a
                # completed call's best result survives a subsequent timeout.
                if conn.poll(max(0.0, min(0.05, deadline - time.monotonic()))):
                    try:
                        msg = conn.recv()
                    except EOFError:
                        status, note = "error", "ISD worker closed without a terminal record"
                        break
                    calls, valid = msg.get("calls", calls), msg.get("valid", valid)
                    if msg["type"] == "ready":
                        kernel_threads = msg["kernel_threads"]
                    elif msg["type"] == "result":
                        chk = common.check_witness(prob, msg["witness"])
                        if not chk["ok"] or chk["weight"] != msg["weight"]:
                            raise RuntimeError("ISD worker returned an invalid witness")
                        if tr.upper is None or msg["weight"] < tr.upper:
                            tr.ub(msg["weight"])
                            tr.events[-1]["t"] = round(max(0.0, msg["seconds"]), 3)
                            witness = msg["witness"]
                    elif msg["type"] == "done":
                        status, note = msg["status"], msg.get("note", "")
                        break
                elif time.monotonic() >= deadline:
                    status = "timeout"
                    break
                elif not proc.is_alive():
                    status, note = "error", "ISD worker exited with code " + str(proc.exitcode)
                    break
    except Exception as exc:
        status, note = "error", type(exc).__name__ + ": " + str(exc)
    finally:
        if proc is not None:
            _stop_worker(proc)
        if conn is not None:
            conn.close()
    notes = "search calls: %d; valid outputs: %d; kernel maximum threads: %s" % (calls, valid, kernel_threads)
    if kernel_threads is not None and kernel_threads != a.threads:
        notes += "; native library ignores requested threads=%d" % a.threads
    if note:
        notes += "; " + note
    common.save_result(a.out, prob, "isd", tr, status, a.threads, a.time_limit,
                       witness=witness, config=cfg, notes=notes, version="cdist/isd.c")
    print(status, tr.lower, tr.upper, tr.seconds())


if __name__ == "__main__":
    main()
