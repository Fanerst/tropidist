"""BP-OSD on chips with dead checks: the decoder and settings of papers/ibm_bicycle_sim.py (min-sum BP, 100 iterations, combination
sweep of order 7, sector decoding) on the matched circuit of chip.py, C = 10.  A shot fails when any logical observable of the memory
basis is left flipped.  JSON lines, resumable.

Usage: python sim_chip.py OUT.jsonl CHIPS.json PS PROCESSES FAILURES MAX_SHOTS    CHIPS.json: [{"name", "dead_x", "dead_z", "px", "pz"}, ...]
"""
import json
import multiprocessing as mp
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["IBM_SIM_SECTOR"] = "1"
import chip
import ibm_bicycle_sim as SIM

CYCLES = 10
_CACHE = {}


def setup(ch, basis, p):
    from ldpc import BpOsdDecoder
    key = (json.dumps(ch), basis, p)
    if key not in _CACHE:
        _CACHE.clear()
        s = None if ch.get("px") is None else chip.B.to_dicts(tuple(ch["px"]), tuple(ch["pz"]))
        c = chip.build_chip("gross", basis, CYCLES, p, s, tuple(ch["dead_x"]), tuple(ch["dead_z"]))
        keep = SIM.memory_detectors(c, basis)
        H, L, pri = SIM.dem_matrices(c.detector_error_model(decompose_errors=False), keep)
        dec = BpOsdDecoder(H, error_channel=list(pri), **SIM.DECODER)
        _CACHE[key] = (c.compile_detector_sampler, L.toarray().astype(np.uint8), dec, keep, H.shape)
    return _CACHE[key]


def batch(args):
    ch, basis, p, seed, shots = args
    os.environ["OMP_NUM_THREADS"] = "1"
    sampler, L, dec, keep, _ = setup(ch, basis, p)
    det, obs = sampler(seed=seed).sample(shots, separate_observables=True)
    det = det[:, keep]
    fails = 0
    for s in range(shots):
        pred = (L @ dec.decode(det[s].astype(np.uint8))) % 2 if det[s].any() else np.zeros(L.shape[0], dtype=np.uint8)
        fails += bool((pred != obs[s]).any())
    return shots, fails


def main():
    out, chips, ps, procs, target, max_shots = sys.argv[1], json.load(open(sys.argv[2])), [float(x) for x in sys.argv[3].split(",")], int(sys.argv[4]), \
        int(sys.argv[5]), int(float(sys.argv[6]))
    done = set()
    if os.path.exists(out):
        for line in open(out):
            r = json.loads(line)
            done.add((r["name"], r["basis"], r["p"]))
    with mp.get_context("spawn").Pool(procs) as pool:
        for p in sorted(ps, reverse=True):
            for ch in chips:
                for basis in "ZX":
                    if (ch["name"], basis, p) in done:
                        continue
                    t0 = time.time()
                    shots = fails = 0
                    seed = 1
                    while fails < target and shots < max_shots:
                        need = procs * 50 if shots == 0 else (shots * (target - fails) // max(fails, 1) if fails else 4 * shots)
                        need = max(procs * 50, min(need + need // 4, max_shots - shots))
                        size = max(50, min(SIM.BATCH, need // procs))
                        n = max(1, need // size)
                        for s, f in pool.imap_unordered(batch, [(ch, basis, p, seed + i, size) for i in range(n)]):
                            shots += s
                            fails += f
                        seed += n
                    rec = dict(ch, basis=basis, p=p, cycles=CYCLES, shots=shots, failures=fails, rate=fails / shots, decoder=dict(SIM.DECODER, name="BpOsdDecoder"),
                               seconds=round(time.time() - t0, 1))
                    with open(out, "a") as f:
                        f.write(json.dumps(rec) + "\n")
                    print(time.strftime("%F %T"), ch["name"], basis, p, shots, fails, "%.3e" % rec["rate"], "%.0f s" % rec["seconds"], flush=True)


if __name__ == "__main__":
    main()
