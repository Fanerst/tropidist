"""Adapter for Qubitserf (Quantinuum; https://github.com/Quantinuum/Qubitserf, v0.1.0): exact
code distance of a CSS code by connected-cluster enumeration (cc), Brouwer-Zimmermann (bz) or
meet in the middle (mitm).  Code-capacity instances only: the tool takes the CSS check matrices
(`css.Hx.mtx`, `css.Hz.mtx`), not a general (H, L) problem.

The public API returns a single integer and no codeword, so the record has lower_bound =
upper_bound = that value with witness null ("exact" as claimed by the tool; the harness compares it
with the ground truth).  A run that is cut off by the time limit yields no bound at all.

config: method = cc (default) | bz | mitm
"""
import queue
import signal
import multiprocessing as mp
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common


def _dense(path):
    import numpy as np
    nrows, ncols, cols = common.read_mtx(path)
    m = np.zeros((nrows, ncols), dtype=np.uint8)
    for j, c in enumerate(cols):
        for r in common.bits(c):
            m[r, j] = 1
    return m


def _convention(df):
    """Which value of `which` gives the minimum weight of an X-type logical operator?
    Test code: three qubits, Z checks Z1Z2 and Z2Z3, no X checks: X-type logical XXX (weight 3),
    Z-type logical Z1 (weight 1)."""
    import numpy as np
    hx = np.zeros((0, 3), dtype=np.uint8)
    hz = np.array([[1, 1, 0], [0, 1, 1]], dtype=np.uint8)
    vals = {w: df.css_distance(hx, hz, method="bz", which=w, threads=1) for w in ("x", "z")}
    if sorted(vals.values()) != [1, 3]:
        raise RuntimeError(f"convention test failed: {vals}")
    return {"X": next(w for w, v in vals.items() if v == 3), "Z": next(w for w, v in vals.items() if v == 1)}


def _child(q, inst, basis, method, threads):
    try:
        from qubitserf import distfind as df
        conv = _convention(df)
        hx, hz = _dense(os.path.join(inst, "css.Hx.mtx")), _dense(os.path.join(inst, "css.Hz.mtx"))
        # meta basis "Z": X-type errors -> minimum weight of an X-type logical operator
        which = conv["X"] if basis == "Z" else conv["Z"]
        d = df.css_distance(hx, hz, method=method, which=which, threads=threads)
        q.put(("ok", int(d), f"which={which}"))
    except Exception as e:                          # reported in the record
        q.put(("error", None, repr(e)[:300]))


def main():
    a = common.adapter_args(__doc__)
    prob = common.load(a.instance, a.variant)
    tr = common.Trace()
    method = a.cfg.get("method", "cc")
    name = f"qubitserf_{method}"
    try:
        import qubitserf  # noqa: F401
    except ImportError:
        common.save_result(a.out, prob, name, tr, "unavailable", a.threads, a.time_limit, config=a.cfg,
                           notes="qubitserf is not installed")
        print("unavailable")
        return
    if prob.meta.get("track") != "code" or not os.path.exists(os.path.join(a.instance, "css.Hx.mtx")):
        common.save_result(a.out, prob, name, tr, "unavailable", a.threads, a.time_limit, config=a.cfg,
                           notes="Qubitserf takes CSS check matrices; this instance is not a code-capacity instance")
        print("unavailable")
        return
    q = mp.Queue()
    p = mp.Process(target=_child, args=(q, a.instance.rstrip("/"), prob.meta.get("basis", "Z"), method, a.threads))
    p.start()
    p.join(max(0.0, a.time_limit - tr.seconds()))
    if p.is_alive():
        p.kill()
        p.join()
        common.save_result(a.out, prob, name, tr, "timeout", a.threads, a.time_limit, config=a.cfg,
                           notes="killed at the time limit; the tool reports no partial bounds")
        print("timeout")
        return
    try:
        kind, d, note = q.get(timeout=5)
    except queue.Empty:
        code = p.exitcode
        why = ("terminated by " + signal.Signals(-code).name if code is not None and code < 0 else f"exit code {code}")
        kind, d, note = "error", None, f"child ended without a result ({why}); the memory limit of the run is the usual cause"
    if kind != "ok" or d is None or d < 1:
        common.save_result(a.out, prob, name, tr, "error", a.threads, a.time_limit, config=a.cfg, notes=f"{note}; d={d}")
        print("error", note)
        return
    tr.lb(d)
    tr.ub(d)
    common.save_result(a.out, prob, name, tr, "exact", a.threads, a.time_limit, config=a.cfg, version="0.1.0",
                       notes=f"value returned by the tool, no codeword available ({note})", value_only=True)
    print("exact", d, d, tr.seconds())


if __name__ == "__main__":
    main()
