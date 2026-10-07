"""Randomised information-set search (isd.c): upper bounds only."""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time

import numpy as np

from .problem import Problem
from .search import verify

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = None


def lib():
    global _LIB
    if _LIB is None:
        src = os.path.join(_HERE, "isd.c")
        out = os.path.join(_HERE, "libisd.so")
        if not (os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src)):
            base = ["cc", "-O3", "-shared", "-fPIC", src, "-o", out]
            if sys.platform == "darwin":
                attempts = [base + ["-isysroot", "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk"], base]
            else:
                attempts = [base + ["-march=native", "-fopenmp"], base + ["-fopenmp"]]
            err = None
            for cmd in attempts:
                r = subprocess.run(cmd, capture_output=True, text=True)
                if r.returncode == 0:
                    break
                err = r.stderr
            else:
                raise RuntimeError(f"could not build isd: {err}")
        L = ctypes.CDLL(out)
        L.isd_search.restype = ctypes.c_int
        L.isd_num_threads.restype = ctypes.c_int
        _LIB = L
    return _LIB


def search(p: Problem, start_best=None, stop_at=1, time_limit=60.0, swaps_per_step=4, seed=1, log=None):
    """Look for a zero-syndrome, nonzero-logical column set lighter than
    start_best.  Runs until the time limit, or until something of weight
    <= stop_at is found.  Returns (weight, columns) or (None, None)."""
    L = lib()
    m, n = p.nrows, p.ncols
    wc = (n + 63) // 64
    wl = max(1, (p.nobs + 63) // 64)
    rows = np.zeros((m, wc), dtype=np.uint64)
    for j, a in enumerate(p.h):
        w, b = j >> 6, np.uint64(1 << (j & 63))
        x = a
        while x:
            low = x & -x
            rows[low.bit_length() - 1, w] |= b
            x ^= low
    lg = np.zeros((n, wl), dtype=np.uint64)
    for j, a in enumerate(p.l):
        for q in range(wl):
            lg[j, q] = (a >> (64 * q)) & 0xFFFFFFFFFFFFFFFF
    best = start_best if start_best is not None else m + 2
    cols = np.zeros(m + 2, dtype=np.int32)
    steps = ctypes.c_int64(0)
    t = time.time()
    w = L.isd_search(ctypes.c_int(m), ctypes.c_int(n), ctypes.c_int(wc), ctypes.c_int(wl),
                     rows.ctypes.data_as(ctypes.c_void_p), lg.ctypes.data_as(ctypes.c_void_p),
                     ctypes.c_int(best), ctypes.c_int(stop_at), ctypes.c_int(swaps_per_step),
                     ctypes.c_double(time_limit), ctypes.c_uint64(seed),
                     cols.ctypes.data_as(ctypes.c_void_p), ctypes.byref(steps))
    dt = time.time() - t
    if log:
        log(f"  isd: best={w if w > 0 else None} steps={steps.value} {dt:.1f}s threads={L.isd_num_threads()}")
    if w < 0:
        return None, None
    sol = tuple(sorted(int(x) for x in cols[:w]))
    assert verify(p, sol), "ISD returned an invalid solution"
    return w, sol
