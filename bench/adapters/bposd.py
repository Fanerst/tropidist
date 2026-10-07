"""Random logical-constraint BP+OSD sampling; upper bounds only (ldpc >= 2).

config: logical=random|single, seed=1, shots=0 (unlimited), bp_method=minimum_sum,
max_iter=100, osd_method=OSD_CS, osd_order=2, error_rate=0.01, jitter=0.5.
The prior for each column is p * (1 + Uniform[-jitter, jitter]), clipped to
(0, 0.5). Each worker uses one decoder thread and an independent seed.
shots is the total number of decoding attempts, divided across workers.
"""
from __future__ import annotations

import importlib.util
import multiprocessing as mp
import os
import random
import sys
import time
from importlib import metadata

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common


DEFAULTS = {"logical": "random", "seed": 1, "shots": 0,
            "bp_method": "minimum_sum", "max_iter": 100, "osd_method": "OSD_CS",
            "osd_order": 2, "error_rate": 0.01, "jitter": 0.5}


def settings(raw):
    unknown = set(raw) - set(DEFAULTS)
    if unknown:
        raise ValueError("unknown config keys: " + ", ".join(sorted(unknown)))
    cfg = dict(DEFAULTS, **raw)
    for key in ("seed", "shots", "max_iter", "osd_order"):
        cfg[key] = int(cfg[key])
    for key in ("error_rate", "jitter"):
        cfg[key] = float(cfg[key])
    if cfg["logical"] not in ("single", "random"):
        raise ValueError("logical must be single or random")
    if cfg["shots"] < 0 or cfg["max_iter"] < 0 or cfg["osd_order"] < 0:
        raise ValueError("shots, max_iter, and osd_order must be nonnegative")
    if not 0 < cfg["error_rate"] < 0.5 or not 0 <= cfg["jitter"] <= 1:
        raise ValueError("require 0 < error_rate < 0.5 and 0 <= jitter <= 1")
    return cfg


def logical_constraint(prob, rng, logical):
    """Return c != 0 and the GF(2) row c L, as a list of bits.

    A nonzero coefficient vector may still give a zero row if L is dependent;
    that is an inconsistent syndrome, counted as an invalid decoding attempt.
    """
    if prob.nobs == 0:
        raise ValueError("instance has no logical rows")
    c = (1 << rng.randrange(prob.nobs)) if logical == "single" else 0
    while not c:
        c = rng.getrandbits(prob.nobs)
    return c, [(x & c).bit_count() % 2 if hasattr(int, "bit_count")
               else bin(x & c).count("1") % 2 for x in prob.l]


def perturbed_priors(ncols, rng, error_rate, jitter):
    return [min(0.5 - 1e-12, max(1e-12, error_rate * (1 + rng.uniform(-jitter, jitter))))
            for _ in range(ncols)]


def _worker(prob, cfg, worker_id, quota, deadline, conn, counts):
    # Set these before importing numpy/scipy/ldpc; workers never oversubscribe.
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[key] = "1"
    offset = 3 * worker_id
    try:
        import numpy as np
        from scipy import sparse
        from ldpc import BpOsdDecoder

        rng = random.Random(cfg["seed"] + 1000003 * worker_id)
        rr, cc = [], []
        for j, column in enumerate(prob.h):
            for r in common.bits(column):
                rr.append(r)
                cc.append(j)
        h = sparse.csr_matrix((np.ones(len(rr), dtype=np.uint8), (rr, cc)),
                              shape=(prob.nrows, prob.ncols))
        syndrome = np.zeros(prob.nrows + 1, dtype=np.uint8)
        syndrome[-1] = 1
        best = None
        while time.monotonic() < deadline and (quota is None or counts[offset] < quota):
            counts[offset] += 1  # attempts, including an interrupted decode
            _, logical_row = logical_constraint(prob, rng, cfg["logical"])
            if not any(logical_row):
                counts[offset + 1] += 1
                continue
            matrix = sparse.vstack((h, sparse.csr_matrix(np.asarray([logical_row], dtype=np.uint8))),
                                   format="csr")
            decoder = BpOsdDecoder(matrix, error_channel=perturbed_priors(
                prob.ncols, rng, cfg["error_rate"], cfg["jitter"]),
                bp_method=cfg["bp_method"], max_iter=cfg["max_iter"],
                osd_method=cfg["osd_method"], osd_order=cfg["osd_order"], omp_thread_count=1)
            output = np.asarray(decoder.decode(syndrome)).reshape(-1)
            if output.size != prob.ncols or not np.all((output == 0) | (output == 1)):
                raise ValueError("decoder returned a nonbinary vector or the wrong number of columns")
            witness = np.flatnonzero(output).tolist()
            counts[offset + 1] += 1
            # Also require the augmented logical constraint, not merely L e != 0.
            if (common.check_witness(prob, witness)["ok"] and
                    sum(logical_row[j] for j in witness) % 2 == 1):
                counts[offset + 2] += 1
                if best is None or len(witness) < best:
                    best = len(witness)
                    conn.send({"kind": "ub", "t": time.time(), "witness": witness})
        conn.send({"kind": "done", "reason": "quota" if quota is not None and
                   counts[offset] >= quota else "deadline"})
    except Exception as exc:
        conn.send({"kind": "error", "note": f"worker {worker_id}: {type(exc).__name__}: {exc}"})
    finally:
        conn.close()


def _stop(processes):
    for process in processes:
        if process.is_alive():
            process.terminate()
    for process in processes:
        process.join(0.2)
        if process.is_alive():
            process.kill()
            process.join(0.2)


def main():
    tr = common.Trace()  # include CLI, loading, imports, and worker construction
    t0 = time.monotonic()
    a = common.adapter_args(__doc__)
    deadline = t0 + max(0.0, a.time_limit)
    prob = common.load(a.instance, a.variant)
    cfg, witness, version, notes = dict(a.cfg), None, None, []
    status = "error"
    processes, connections = [], []
    counts = None
    candidates = []
    try:
        cfg = settings(a.cfg)
        if a.threads < 1:
            raise ValueError("threads must be positive")
        if importlib.util.find_spec("ldpc") is None:
            status = "unavailable"
            notes.append("requires ldpc >= 2 with ldpc.BpOsdDecoder; ldpc is not installed")
        else:
            try:
                version = metadata.version("ldpc")
            except metadata.PackageNotFoundError:
                version = "unknown"
            if version != "unknown" and int(version.split(".", 1)[0]) < 2:
                status = "unavailable"
                notes.append("requires ldpc >= 2; installed version is " + version)
            elif time.monotonic() >= deadline:
                status = "timeout"
            else:
                ctx = mp.get_context("spawn")
                workers = min(a.threads, cfg["shots"]) if cfg["shots"] else a.threads
                counts = ctx.Array("q", 3 * workers, lock=False)
                finished = set()
                deadline_workers = set()
                for i in range(workers):
                    recv, send = ctx.Pipe(duplex=False)
                    quota = (cfg["shots"] // workers + int(i < cfg["shots"] % workers)) if cfg["shots"] else None
                    process = ctx.Process(target=_worker, args=(prob, cfg, i, quota, deadline, send, counts))
                    process.start()
                    send.close()
                    processes.append(process)
                    connections.append(recv)
                status = "bounds"

                def drain():
                    for i, conn in enumerate(connections):
                        while i not in finished and conn.poll():
                            try:
                                event = conn.recv()
                            except EOFError:
                                finished.add(i)
                                # EOF without a terminal message is a failure,
                                # even before multiprocessing observes exitcode.
                                notes.append(f"worker {i} closed without a terminal message "
                                             f"(exitcode {processes[i].exitcode})")
                                break
                            if event["kind"] == "ub":
                                if not common.check_witness(prob, event["witness"])["ok"]:
                                    raise ValueError("worker returned an invalid witness")
                                candidates.append(event)
                            else:
                                finished.add(i)
                                if event["kind"] == "error":
                                    notes.append(event["note"])
                                elif event.get("reason") == "deadline":
                                    deadline_workers.add(i)

                while len(finished) < workers and time.monotonic() < deadline:
                    drain()
                    if len(finished) < workers:
                        time.sleep(min(0.01, max(0, deadline - time.monotonic())))
                drain()
                if len(finished) < workers or deadline_workers:
                    status = "timeout"
                elif notes:
                    status = "error"
                _stop(processes)
                drain()
    except Exception as exc:
        status = "error"
        notes.append(f"{type(exc).__name__}: {exc}")
    finally:
        _stop(processes)
        for conn in connections:
            conn.close()
    # Preserve verified candidates even if a later worker or cleanup failed.
    # Merge by discovery time, since independent pipes can arrive out of order.
    for event in sorted(candidates, key=lambda event: event["t"]):
        w = len(event["witness"])
        if tr.upper is None or w < tr.upper:
            tr.ub(w)
            tr.events[-1]["t"] = round(max(0, event["t"] - tr.t0), 3)
            witness = event["witness"]
    attempted = sum(counts[::3]) if counts is not None else 0
    completed = sum(counts[1::3]) if counts is not None else 0
    valid = sum(counts[2::3]) if counts is not None else 0
    notes.append(f"shots={attempted}; completed_shots={completed}; valid_outputs={valid}; "
                 f"workers={len(processes)}; one decoder thread per worker; "
                 "worker seeds=seed+1000003*worker_index")
    common.save_result(a.out, prob, "bposd", tr, status, a.threads, a.time_limit,
                       witness=witness, config=cfg, notes="; ".join(notes), version=version)
    print(status, tr.lower, tr.upper, tr.seconds())


if __name__ == "__main__":
    main()
