"""Memory instruction of papers/ibm_bicycle.py on a chip with dead check qubits (or a dead coupler, which disables its check):
the check's gates, preparation, measurement and detectors are dropped; its data qubits idle in those slots.  Same
setting otherwise: C noisy cycles between an error-free code state and a noise-free final round, observables from the
noise-free data measurement.  The final-readout comparison of a dead check is not used: it exists only because the
readout of this benchmark is noise-free, and a running memory has no such detector."""
import os
import sys

import stim

R = "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance"
for p in (os.environ.get("CD_ROOT", R),):
    sys.path[:0] = [p + "/papers", p, p + "/bench"]
import bb6_depth7 as B
import stabcode


def gf2_rank(rows):
    rows, r = list(rows), 0
    basis = {}
    for v in rows:
        while v:
            h = v.bit_length() - 1
            if h in basis:
                v ^= basis[h]
            else:
                basis[h] = v
                r += 1
                break
    return r


def build(key, basis, cycles, p=1e-3, schedule=None, dead_x=(), dead_z=()):
    xs, zs, N = B.supports(key, schedule)
    nq = 2 * N
    hx = [sum(1 << q for _, q in g) for g in xs]
    hz = [sum(1 << q for _, q in g) for g in zs]
    lx, lz = stabcode.css_logicals(hx, hz, nq)
    live_x = [i for i in range(len(xs)) if i not in set(dead_x)]
    live_z = [i for i in range(len(zs)) if i not in set(dead_z)]
    nx, nz = len(live_x), len(live_z)
    data = list(range(nq))
    za = {i: nq + k for k, i in enumerate(live_z)}
    xa = {i: nq + nz + k for k, i in enumerate(live_x)}
    za_list, xa_list = [za[i] for i in live_z], [xa[i] for i in live_x]
    everything = data + za_list + xa_list
    layers = []
    for t in range(7):
        tg = []
        for i in live_x:
            tg += [v for tt, q in xs[i] if tt == t for v in (xa[i], q)]
        for i in live_z:
            tg += [v for tt, q in zs[i] if tt == t for v in (q, za[i])]
        assert len(set(tg)) == len(tg)
        layers.append(tg)
    per = nz + nx
    c = stim.Circuit()
    c.append("R" if basis == "Z" else "RX", data)
    c.append("TICK")

    def round_(t, noisy, prep_noise):
        c.append("R", za_list)
        c.append("RX", xa_list)
        if prep_noise:
            c.append("X_ERROR", za_list, p)
            c.append("Z_ERROR", xa_list, p)
        c.append("TICK")
        for tg in layers:
            c.append("CX", tg)
            if noisy:
                c.append("DEPOLARIZE2", tg, p)
                idle = sorted(set(everything) - set(tg))
                if idle:
                    c.append("DEPOLARIZE1", idle, p)
            c.append("TICK")
        if noisy:
            c.append("X_ERROR", za_list, p)
            c.append("Z_ERROR", xa_list, p)
        c.append("M", za_list)
        c.append("MX", xa_list)
        if noisy:
            c.append("DEPOLARIZE1", data, p)
        for k, i in enumerate(live_z):
            cur = stim.target_rec(-per + k)
            if t == 0:
                if basis == "Z":
                    c.append("DETECTOR", [cur], (i, 0, 0, 3))
            else:
                c.append("DETECTOR", [cur, stim.target_rec(-2 * per + k)], (i, 0, t, 3))
        for k, i in enumerate(live_x):
            cur = stim.target_rec(-nx + k)
            if t == 0:
                if basis == "X":
                    c.append("DETECTOR", [cur], (i, 0, 0, 0))
            else:
                c.append("DETECTOR", [cur, stim.target_rec(-nx - per + k)], (i, 0, t, 0))
        c.append("TICK")

    round_(0, False, False)
    for t in range(1, cycles + 1):
        if t == 1:
            c.append("DEPOLARIZE1", data, p)
        round_(t, True, True)
    round_(cycles + 1, False, False)
    if basis == "Z":
        c.append("M", data)
        for k, i in enumerate(live_z):
            c.append("DETECTOR", [stim.target_rec(-nq + q) for _, q in zs[i]] + [stim.target_rec(-nq - nx - nz + k)],
                     (i, 0, cycles + 2, 3))
        logs = lz
    else:
        c.append("MX", data)
        for k, i in enumerate(live_x):
            c.append("DETECTOR", [stim.target_rec(-nq + q) for _, q in xs[i]] + [stim.target_rec(-nq - nx + k)],
                     (i, 0, cycles + 2, 0))
        logs = lx
    for a, v in enumerate(logs):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-nq + j) for j in stabcode.bits(v)], a)
    c.detector_error_model(decompose_errors=False)
    return c, dict(rank_hx=gf2_rank(hx), rank_hz=gf2_rank(hz), rank_hx_live=gf2_rank([hx[i] for i in live_x]),
                   rank_hz_live=gf2_rank([hz[i] for i in live_z]))
