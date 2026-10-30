"""Executors for a trellis Plan: a numpy reference and the C kernel."""
from __future__ import annotations

import ctypes
import glob
import os
import subprocess
import sys
import time

import numpy as np

INF = 255               # 8-bit table entries; additions saturate here (final_value)
_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = None


def final_value(entry):
    """Minimum cost from the last table entry of a feasible plan (a fault set with the target value exists).
    Additions saturate at INF, so every entry equals min(true cost, INF): below INF it is exact, and INF means a
    cost of at least 255, which the 8-bit entries cannot hold.  Never None: that would claim no logical."""
    v = int(entry)
    if v == INF:
        raise OverflowError("the distance is at least %d, beyond the 8-bit entries of the dense DP" % INF)
    return v


def build(force=False):
    """Compile viterbi.c next to this file and return the library path."""
    src = os.path.join(_HERE, "viterbi.c")
    out = os.path.join(_HERE, "libviterbi.so")
    if not force and os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
        return out
    base = ["cc", "-O3", "-shared", "-fPIC", src, "-o", out]
    attempts = []
    if sys.platform == "darwin":
        for sdk in sorted(glob.glob("/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk")):
            attempts.append(base + ["-isysroot", sdk])
        attempts.append(base)
    else:
        attempts.append(base + ["-march=native", "-fopenmp"])
        attempts.append(base + ["-fopenmp"])
    err = None
    for cmd in attempts:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return out
        err = r.stderr
    raise RuntimeError(f"could not build viterbi kernel: {err}")


def lib():
    global _LIB
    if _LIB is None:
        L = ctypes.CDLL(build())
        u8p = ctypes.POINTER(ctypes.c_uint8)
        L.dp_update.argtypes = [u8p, ctypes.c_uint64, ctypes.c_uint64]
        L.dp_update.restype = None
        L.dp_expand_update.argtypes = [u8p, ctypes.c_uint64, ctypes.c_uint64]
        L.dp_expand_update.restype = None
        L.dp_select.argtypes = [u8p, ctypes.c_uint64, ctypes.c_int, ctypes.c_int]
        L.dp_select.restype = ctypes.c_uint64
        L.dp_fill.argtypes = [u8p, ctypes.c_uint64, ctypes.c_uint8]
        L.dp_fill.restype = None
        L.dp_hist.argtypes = [u8p, ctypes.c_uint64, ctypes.POINTER(ctypes.c_uint64)]
        L.dp_hist.restype = None
        L.dp_num_threads.restype = ctypes.c_int
        _LIB = L
    return _LIB


def run_plan_numpy(plan):
    """Reference executor.  Returns the minimum cost, or None if infeasible; OverflowError if it is >= 255."""
    if not plan.feasible:
        return None
    T = np.zeros(1, dtype=np.uint8)
    for op in plan.ops:
        if op[0] == "expand":
            T = np.concatenate([T, np.full(T.size, INF, dtype=np.uint8)])
        elif op[0] == "update":
            h = op[1]
            idx = np.arange(T.size, dtype=np.int64) ^ h
            other = T[idx]
            other = np.where(other == INF, INF, other + 1).astype(np.uint8)
            T = np.minimum(T, other)
        else:
            _, pos, target = op
            idx = np.arange(T.size, dtype=np.int64)
            T = T[((idx >> pos) & 1) == target]
    assert T.size == 1
    return final_value(T[0])


def run_plan(plan, log=None, progress_every=0.0):
    """Run the plan with the C kernel.  Returns (min cost or None if infeasible, stats); OverflowError if the
    cost is >= 255."""
    if not plan.feasible:
        return None, {"feasible": False}
    L = lib()
    u8p = ctypes.POINTER(ctypes.c_uint8)
    size = 1 << plan.peak_bits
    buf = np.empty(size, dtype=np.uint8)
    ptr = buf.ctypes.data_as(u8p)
    buf[0] = 0
    n = 1
    t0 = time.time()
    last = t0
    ops = plan.ops
    i = 0
    nops = len(ops)
    ncol = 0
    while i < nops:
        op = ops[i]
        if op[0] == "expand":
            # an expand is always followed by the update of the starting column
            nxt = ops[i + 1]
            if nxt[0] == "update" and (nxt[1] >> n.bit_length() - 1) == 1:
                L.dp_expand_update(ptr, n, nxt[1] ^ n)
                n <<= 1
                i += 2
                ncol += 1
            else:
                L.dp_fill(ctypes.cast(ctypes.addressof(ptr.contents) + n, u8p), n, INF)
                n <<= 1
                i += 1
        elif op[0] == "update":
            L.dp_update(ptr, n, op[1])
            i += 1
            ncol += 1
        else:
            n = L.dp_select(ptr, n, op[1], op[2])
            i += 1
        if log and progress_every and time.time() - last > progress_every:
            last = time.time()
            log(f"  op {i}/{nops}  col~{ncol}  bits={n.bit_length() - 1}  t={last - t0:.1f}s")
    assert n == 1
    return final_value(buf[0]), {"seconds": time.time() - t0, "peak_bits": plan.peak_bits,
                                 "threads": L.dp_num_threads()}
