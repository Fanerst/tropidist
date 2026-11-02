"""The memory instruction of papers/ibm_bicycle_matched.py (Tour de gross's own setting) on a chip with dead check qubits.

A dead check qubit, or a dead coupler (which leaves its check unmeasurable, since a check missing one data qubit would not
commute with the others), removes that check: its gates, preparation, measurement and detectors are dropped in every round,
including the noise-free first and last ones, and its data qubits idle in those slots.  Timing, noise, logical operators and
everything else stay as in the perfect circuit.  The final data readout gives no detector for a dead check: such a detector
has no earlier measurement to compare with, and a running memory has no noise-free readout.

CD_ROOT selects the checkout (default: this file's repository).
"""
import os
import sys

import stim

ROOT = os.environ.get("CD_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path[:0] = [ROOT + "/papers", ROOT, ROOT + "/bench"]
import bb6_depth7 as B
import stabcode

STD = (tuple(B.STANDARD["X"][x] for x in [(s, a) for s in "LR" for a in range(3)]),
       tuple(B.STANDARD["Z"][x] for x in [(s, a) for s in "LR" for a in range(3)]))


def timing(schedule=None):
    """As papers/ibm_bicycle_matched.timing (that module cannot be imported without its Stim-free dependencies here)."""
    tx, tz = (B.STANDARD["X"], B.STANDARD["Z"]) if schedule is None else schedule
    pm = {typ: (min(t.values()), max(t.values()) + 2) for typ, t in (("X", tx), ("Z", tz))}
    return pm, max(m - a + 1 for a, m in pm.values())


def flip(m, q):
    return (1 - (1 - 2 * q) ** m) / 2


def gf2_rank(rows):
    basis, r = {}, 0
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


def ranks(key, dead_x=(), dead_z=()):
    """(rank H_X, rank of the live X checks, rank H_Z, rank of the live Z checks)."""
    hx, hz, _ = B.matrices(key)
    return (gf2_rank(hx), gf2_rank([v for i, v in enumerate(hx) if i not in set(dead_x)]),
            gf2_rank(hz), gf2_rank([v for i, v in enumerate(hz) if i not in set(dead_z)]))


def build_chip(key, basis, cycles, p=1e-3, schedule=None, dead_x=(), dead_z=(), noise="linear"):
    xs, zs, N = B.supports(key, schedule)
    nq = 2 * N
    hx = [sum(1 << q for _, q in g) for g in xs]
    hz = [sum(1 << q for _, q in g) for g in zs]
    assert (hx, hz, nq) == tuple(B.matrices(key))
    lx, lz = stabcode.css_logicals(hx, hz, nq)
    live = {"Z": [i for i in range(len(zs)) if i not in set(dead_z)],
            "X": [i for i in range(len(xs)) if i not in set(dead_x)]}
    data = list(range(nq))
    pos = {"Z": {i: nq + i for i in live["Z"]}, "X": {i: nq + len(zs) + i for i in live["X"]}}
    anc = {typ: [pos[typ][i] for i in live[typ]] for typ in "ZX"}
    layers = []
    for t in range(7):
        tg = []
        for i in live["X"]:
            tg += [v for tt, q in xs[i] if tt == t for v in (pos["X"][i], q)]
        for i in live["Z"]:
            tg += [v for tt, q in zs[i] if tt == t for v in (q, pos["Z"][i])]
        assert len(set(tg)) == len(tg)
        layers.append(tg)
    pm, period = timing(schedule)
    q = p / 15
    if noise == "linear":
        cx_p, idle_ps, flip_p = 15 / 16 * (1 - (1 - 2 * q) ** 8), flip(5, q), flip(15, q)
    else:
        assert noise == "stim"
        cx_p, idle_ps, flip_p = p, None, p
    c = stim.Circuit()
    c.append("R" if basis == "Z" else "RX", data)
    c.append("TICK")
    first = {}
    count = [0]

    def measure(r, typ):
        first[(r, typ)] = count[0]
        c.append("M" if typ == "Z" else "MX", anc[typ])
        count[0] += len(anc[typ])

    def detectors(r):
        for typ, k in (("Z", 3), ("X", 0)):
            for a, i in enumerate(live[typ]):
                cur = stim.target_rec(first[(r, typ)] + a - count[0])
                if r == 0:
                    if typ == basis:
                        c.append("DETECTOR", [cur], (i, 0, 0, k))
                else:
                    c.append("DETECTOR", [cur, stim.target_rec(first[(r - 1, typ)] + a - count[0])], (i, 0, r, k))

    def clean_round(r):
        c.append("R", anc["Z"])
        c.append("RX", anc["X"])
        c.append("TICK")
        for tg in layers:
            c.append("CX", tg)
            c.append("TICK")
        measure(r, "Z")
        measure(r, "X")
        detectors(r)
        c.append("TICK")

    def idle(qs):
        if not qs:
            return
        if idle_ps is None:
            c.append("DEPOLARIZE1", qs, p)
        else:
            for e in ("X_ERROR", "Y_ERROR", "Z_ERROR"):
                c.append(e, qs, idle_ps)

    clean_round(0)
    last = max(m for _, m in pm.values())
    for T in range(period * (cycles - 1) + last + 1):
        busy = set()
        for typ in "ZX":
            a, m = pm[typ]
            r = (T - m) // period + 1
            if (T - m) % period == 0 and 1 <= r <= cycles:
                c.append("X_ERROR" if typ == "Z" else "Z_ERROR", anc[typ], flip_p)
                measure(r, typ)
                busy.update(anc[typ])
        for typ in "ZX":
            a, m = pm[typ]
            r = (T - a) // period + 1
            if (T - a) % period == 0 and 1 <= r <= cycles:
                c.append("R" if typ == "Z" else "RX", anc[typ])
                c.append("X_ERROR" if typ == "Z" else "Z_ERROR", anc[typ], flip_p)
                busy.update(anc[typ])
        r, s = (T - 1) // period + 1, (T - 1) % period
        if T >= 1 and s < 7 and r <= cycles:
            tg = layers[s]
            c.append("CX", tg)
            c.append("DEPOLARIZE2", tg, cx_p)
            assert not busy & set(tg)
            busy.update(tg)
        alive = list(data)
        for typ in "ZX":
            a, m = pm[typ]
            if any(a <= T - period * (r - 1) <= m for r in range(1, cycles + 1)):
                alive += anc[typ]
        idle(sorted(set(alive) - busy))
        r = (T - last) // period + 1
        if (T - last) % period == 0 and 1 <= r <= cycles:
            detectors(r)
        c.append("TICK")
    clean_round(cycles + 1)
    typ = basis
    gens = zs if basis == "Z" else xs
    c.append("M" if basis == "Z" else "MX", data)
    count[0] += nq
    for a, i in enumerate(live[typ]):
        c.append("DETECTOR", [stim.target_rec(-nq + qq) for _, qq in gens[i]]
                 + [stim.target_rec(first[(cycles + 1, typ)] + a - count[0])], (i, 0, cycles + 2, 3 if typ == "Z" else 0))
    for a, v in enumerate(lz if basis == "Z" else lx):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-nq + j) for j in stabcode.bits(v)], a)
    c.detector_error_model(decompose_errors=False)
    return c
