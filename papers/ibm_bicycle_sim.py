"""Monte Carlo logical error rates of the memory instruction of papers/ibm_bicycle.py (IBM's setting) with a BP-OSD
decoder on the full detector error model (ldpc's BpOsdDecoder: min-sum BP, then combination-sweep OSD), for
comparing schedules at physical error rates where failures can be sampled.  A shot fails when the decoder's
correction leaves any logical observable of the memory basis flipped.

Usage: python papers/ibm_bicycle_sim.py KEY CYCLES OUT.jsonl SCHEDULES BASES PS [processes] [failures] [max shots]
       SCHEDULES: comma-free list separated by ";" of "standard" or "px0,...,px5/pz0,...,pz5"
       BASES: e.g. ZX;  PS: comma-separated physical error rates
JSON-lines output (one line per schedule, basis and p), resumable.
With IBM_SIM_MATCHED=1 the circuit is that of papers/ibm_bicycle_matched.py, Tour de gross's own simulation setting.
With IBM_SIM_SECTOR=1 the decoder sees only the detectors of the memory basis, with mechanisms merged by their effect
on them, which is much faster on many cycles.
"""
import json
import os
import sys
import time

import numpy as np
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bb6_depth7 as B
import ibm_bicycle as IB

DECODER = dict(max_iter=int(os.environ.get("IBM_SIM_ITERS", "100")), bp_method="minimum_sum", ms_scaling_factor=0.625,
               osd_method="osd_cs",
               osd_order=int(os.environ.get("IBM_SIM_OSD_ORDER", "7")))
BATCH = int(os.environ.get("IBM_SIM_BATCH", "2000"))
MATCHED = os.environ.get("IBM_SIM_MATCHED") == "1"
SECTOR = os.environ.get("IBM_SIM_SECTOR") == "1"
_CACHE = {}


def build(key, basis, cycles, p, sched):
    if MATCHED:
        import ibm_bicycle_matched as M
        return M.build_matched(key, basis, cycles, p, sched)
    return IB.build_instruction(key, basis, cycles, p, sched)


def parse_schedule(s):
    if s == "standard":
        return None, "standard"
    px, pz = (tuple(int(x) for x in part.split(",")) for part in s.split("/"))
    return B.to_dicts(px, pz), "s" + "".join(map(str, px)) + "_" + "".join(map(str, pz))


def dem_matrices(dem, keep=None):
    """Detector and observable matrices of the undecomposed model, equal mechanisms merged, with priors; keep: the
    detectors to use (default all)."""
    index = None if keep is None else {int(j): i for i, j in enumerate(keep)}
    cols = {}
    for inst in dem.flattened():
        if inst.type != "error":
            continue
        d, o = [], []
        for t in inst.targets_copy():
            if t.is_relative_detector_id():
                if index is None:
                    d.append(t.val)
                elif t.val in index:
                    d.append(index[t.val])
            elif t.is_logical_observable_id():
                o.append(t.val)
        key = (tuple(sorted(d)), tuple(sorted(o)))
        q = inst.args_copy()[0]
        r = cols.get(key, 0.0)
        cols[key] = r + q - 2 * r * q
    keys = list(cols)

    def mat(nrows, part):
        rows = [i for k in keys for i in k[part]]
        cs = [j for j, k in enumerate(keys) for _ in k[part]]
        return sp.csc_matrix((np.ones(len(rows), dtype=np.uint8), (rows, cs)), shape=(nrows, len(keys)))
    return (mat(dem.num_detectors if keep is None else len(keep), 0), mat(dem.num_observables, 1),
            np.array([cols[k] for k in keys]))


def memory_detectors(circ, basis):
    """Indices of the detectors of the memory basis (coordinate k: 3 for Z checks, 0 for X checks)."""
    k = 3 if basis == "Z" else 0
    return np.array(sorted(i for i, v in circ.get_detector_coordinates().items() if v[3] == k))


def setup(key, cycles, sched, basis, p):
    from ldpc import BpOsdDecoder
    ck = (key, cycles, sched, basis, p)
    if ck not in _CACHE:
        _CACHE.clear()
        circ = build(key, basis, cycles, p, parse_schedule(sched)[0])
        keep = memory_detectors(circ, basis) if SECTOR else None
        H, L, pri = dem_matrices(circ.detector_error_model(decompose_errors=False), keep)
        dec = BpOsdDecoder(H, error_channel=list(pri), **DECODER)
        _CACHE[ck] = (circ.compile_detector_sampler, L.toarray().astype(np.uint8), dec, keep)
    return _CACHE[ck]


def batch(args):
    key, cycles, sched, basis, p, seed, shots = args
    os.environ["OMP_NUM_THREADS"] = "1"
    sampler, L, dec, keep = setup(key, cycles, sched, basis, p)
    det, obs = sampler(seed=seed).sample(shots, separate_observables=True)
    if keep is not None:
        det = det[:, keep]
    fails = 0
    for s in range(shots):
        if det[s].any():
            pred = (L @ dec.decode(det[s].astype(np.uint8))) % 2
        else:
            pred = np.zeros(L.shape[0], dtype=np.uint8)
        fails += bool((pred != obs[s]).any())
    return shots, fails


def main(key, cycles, out, schedules, bases, ps, procs=32, target=100, max_shots=10 ** 8):
    import multiprocessing as mp
    cycles, procs, target, max_shots = int(cycles), int(procs), int(target), int(float(max_shots))
    done = set()
    if os.path.exists(out):
        for line in open(out):
            r = json.loads(line)
            done.add((r["schedule_spec"], r["basis"], r["p"]))
    configs = [(s, b, float(p)) for s in schedules.split(";") for b in bases for p in ps.split(",")]
    with mp.get_context("spawn").Pool(procs) as pool:
        for sched, basis, p in configs:
            if (sched, basis, p) in done:
                continue
            t0 = time.time()
            shots = fails = 0
            seed = 1
            while fails < target and shots < max_shots:
                # the next round aims at the target from the rate seen so far (one small batch per process first)
                need = procs * 50 if shots == 0 else (shots * (target - fails) // max(fails, 1) if fails else 4 * shots)
                need = max(procs * 50, min(need + need // 4, max_shots - shots))
                size = max(50, min(BATCH, need // procs))
                n = max(1, need // size)
                jobs = [(key, cycles, sched, basis, p, seed + i, size) for i in range(n)]
                seed += n
                for s, f in pool.imap_unordered(batch, jobs):
                    shots += s
                    fails += f
            circ = build(key, basis, cycles, p, parse_schedule(sched)[0])
            H, _, _ = dem_matrices(circ.detector_error_model(decompose_errors=False),
                                   memory_detectors(circ, basis) if SECTOR else None)
            rec = {"code": key, "cycles": cycles, "schedule": parse_schedule(sched)[1], "schedule_spec": sched,
                   "setting": "matched" if MATCHED else "instruction", "decoded": "sector" if SECTOR else "full", "basis": basis, "p": p, "shots": shots, "failures": fails, "rate": fails / shots,
                   "detectors": H.shape[0], "mechanisms": H.shape[1], "decoder": dict(DECODER, name="BpOsdDecoder"),
                   "seconds": round(time.time() - t0, 1)}
            with open(out, "a") as f:
                f.write(json.dumps(rec) + "\n")
            print(json.dumps({k: rec[k] for k in ("schedule", "basis", "p", "shots", "failures", "rate", "seconds")}),
                  flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
