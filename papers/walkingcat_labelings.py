"""Walking Cat circuits (arXiv:2604.19481): does the result depend on how the
indexed terms A_i, B_i of the paper's Table 10 are matched to the monomials of
Table 30?

papers/walkingcat.py numbers the monomials in their printed order and gets
circuit distance 8 for all three codes, where the paper states 9.  The paper
does not print the numbering, so this script runs every numbering: for each
pair of permutations (of the A monomials, of the B monomials) the Table 10
schedule is rebuilt; numberings whose circuit is not a valid syndrome
measurement (non-deterministic detectors) are counted and skipped; for the
valid ones the exact circuit distance is computed with papers/run_parallel.py.

Usage: python papers/walkingcat_labelings.py key [processes] [bases: Z | ZX] [rounds] [seconds per threshold]
"""
import contextlib
import io
import itertools
import json
import multiprocessing as mp
import os
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import run_parallel
import walkingcat

_CFG = None


def _init(cfg):
    global _CFG
    os.environ["OMP_NUM_THREADS"] = "1"
    _CFG = cfg


def variant(key, pa, pb, name):
    """A module like walkingcat whose code `key` has its A and B monomials renumbered."""
    ell, m, a, b = walkingcat.CODES[key][0]
    mod = types.ModuleType(name)
    mod.__dict__.update({k: v for k, v in walkingcat.__dict__.items() if not k.startswith("__")})
    mod.__dict__["__builtins__"] = walkingcat.__dict__["__builtins__"]
    mod.CODES = dict(walkingcat.CODES)
    mod.CODES[key] = ((ell, m, tuple(a[i] for i in pa), tuple(b[i] for i in pb)),) + walkingcat.CODES[key][1:]
    # the functions of walkingcat read the module globals CODES / SCHEDULES: rebind them to the variant
    for fn in ("matrices", "supports", "translations", "build", "tag"):
        f = getattr(walkingcat, fn)
        g = types.FunctionType(f.__code__, mod.__dict__, f.__name__, f.__defaults__, f.__closure__)
        g.__kwdefaults__ = f.__kwdefaults__
        setattr(mod, fn, g)
    return mod


def _work(job):
    key, pa, pb = job
    rounds, time_limit, bases = _CFG
    name = f"wcl_w{os.getpid()}"
    mod = variant(key, pa, pb, name)
    try:
        mod.build(key, "Z", 2).detector_error_model(decompose_errors=False)
        mod.build(key, "X", 2).detector_error_model(decompose_errors=False)
    except (ValueError, AssertionError):       # Stim: non-deterministic detector; builder: a qubit used twice in a layer
        return pa, pb, "invalid", None
    sys.modules[name] = mod
    d = walkingcat.CODES[key][2][2]
    out = {}
    for basis in bases:
        path = os.path.join(ROOT, "results", "papers3", "walkingcat", "labelings_tmp", f"{name}_{key}_{basis}.json")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                run_parallel.main(name, key, basis, path, rounds, 3, d, time_limit, 1)
            r = json.load(open(path))
            out[basis] = (r.get("certified_lower_bound"), r.get("certified_upper_bound"), r["collapsed"].get("distance"))
        except Exception as e:
            out[basis] = ("error", repr(e)[:200], None)
        for f in (path, os.path.join(ROOT, "circuits", "papers", f"{name}{key}_r{rounds}_{basis}.stim")):
            if os.path.exists(f):
                os.remove(f)
    return pa, pb, "valid", out


def main(key, procs=8, bases="Z", rounds=6, time_limit=900):
    key, procs, rounds, time_limit = int(key), int(procs), int(rounds), float(time_limit)
    ell, m, a, b = walkingcat.CODES[key][0]
    jobs = [(key, pa, pb) for pa in itertools.permutations(range(len(a))) for pb in itertools.permutations(range(len(b)))]
    os.makedirs(os.path.join(ROOT, "results", "papers3", "walkingcat", "labelings_tmp"), exist_ok=True)
    out = os.path.join(ROOT, "results", "papers3", "walkingcat", f"labelings_{key}.json")
    t0 = time.time()
    rows, invalid = [], 0
    with mp.Pool(procs, maxtasksperchild=8, initializer=_init, initargs=((rounds, time_limit, bases),)) as pool:
        for i, (pa, pb, status, res) in enumerate(pool.imap_unordered(_work, jobs, chunksize=1)):
            if status == "invalid":
                invalid += 1
            else:
                rows.append({"A": [x + 1 for x in pa], "B": [x + 1 for x in pb], **{bs: list(v) for bs, v in res.items()}})
            if (i + 1) % 50 == 0:
                print(time.strftime("%H:%M:%S"), f"{i + 1}/{len(jobs)} numberings, {len(rows)} valid, {time.time() - t0:.0f}s",
                      flush=True)
    hist = {}
    for r in rows:
        vals = [r[bs] for bs in bases]
        if all(isinstance(v[0], int) and v[0] == v[1] for v in vals):
            k = str(min(v[0] for v in vals))
        else:
            k = "open:" + "/".join(f"{v[0]}-{v[1]}" for v in vals)
        hist[k] = hist.get(k, 0) + 1
    res = {"code": list(walkingcat.CODES[key][2]), "paper_circuit_distance": walkingcat.CODES[key][3], "bases": bases,
           "rounds": rounds, "numberings": len(jobs), "invalid_circuits": invalid, "valid": len(rows),
           "circuit_distance_histogram": dict(sorted(hist.items())),
           "printed_order": next((r for r in rows if r["A"] == sorted(r["A"]) and r["B"] == sorted(r["B"])), None),
           "rows": rows, "seconds": round(time.time() - t0, 1)}
    json.dump(res, open(out, "w"), indent=1)
    print(time.strftime("%H:%M:%S"), f"walkingcat {key}: {len(jobs)} numberings, {invalid} invalid, {len(rows)} valid; "
          f"circuit distance ({bases}): {res['circuit_distance_histogram']}; printed order: {res['printed_order']}; "
          f"{res['seconds']}s", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
