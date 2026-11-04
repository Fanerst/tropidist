"""Shared pieces of the benchmark: instance files, loading, witness check, result records.

The benchmark compares methods for one problem:

    given binary matrices H (rows = detectors or checks, columns = fault mechanisms) and
    L (rows = logical observables), find  d = min { |e| : H e = 0, L e != 0 }  over GF(2).

Layout of one instance, `bench/instances/<name>/`:

    meta.json                 see `write_meta`
    circuit.stim              circuit track only: the noisy Stim memory circuit the problem comes from
    <variant>.H.mtx           MatrixMarket "coordinate pattern general", rows x columns, 1-based
    <variant>.L.mtx           same column set; rows = observables
    <variant>.rowmeta.json    optional: one list per row of H, [check, 0, round, type] for circuit problems
                              (type >= 3: Z-type detector, < 3: X-type), [check, 0] for collapsed problems
    <variant>.perms.json      optional: row permutations (perm[r] = image of row r) that are symmetries
                              of the problem (they map the column set to itself and respect L)

Variants of a circuit instance:
    full       the undecomposed detector error model, identical columns merged, zero columns dropped
    sector     only the detectors of the memory-basis type; exact reduction (same distance as `full`,
               checked when the instance is exported)
    collapsed  detectors of each check XOR-ed over all rounds; a relaxation: its distance is a lower
               bound on the distance of `sector`, and it has its own ground truth
A code-capacity instance has the single variant `full`, plus `css.Hx.mtx` and `css.Hz.mtx` (checks x
qubits) for tools that take the CSS code itself.  meta["basis"] = "Z" means: X-type errors, detected by the
Z checks, i.e. the problem is the minimum weight of an X-type logical operator.

Every adapter (bench/adapters/<method>.py) has the command line

    python bench/adapters/<method>.py --instance bench/instances/<name> --variant sector \\
        --time-limit 600 --threads 1 --out results/bench/<method>/<name>__sector__t1.json [--config k=v,k=v]

and writes one JSON record with `save_result` (schema in its docstring).
"""
from __future__ import annotations

import json
import os
import resource
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INSTANCES = os.path.join(HERE, "instances")
for _p in (ROOT, os.path.join(ROOT, "papers")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

STATUSES = ("exact", "bounds", "timeout", "unavailable", "error")


def bits(x):
    out = []
    while x:
        low = x & -x
        out.append(low.bit_length() - 1)
        x ^= low
    return out


# ---------------------------------------------------------------------------- matrix files
def write_mtx(path, cols, nrows):
    """cols[j] = Python int bitmask of the rows in which column j has a one."""
    nnz = sum(bin(c).count("1") for c in cols)
    with open(path, "w") as f:
        f.write("%%MatrixMarket matrix coordinate pattern general\n")
        f.write(f"{nrows} {len(cols)} {nnz}\n")
        for j, c in enumerate(cols):
            for r in bits(c):
                f.write(f"{r + 1} {j + 1}\n")


def read_mtx(path):
    """Returns (nrows, ncols, cols) with cols[j] an int bitmask over rows."""
    with open(path) as f:
        line = f.readline()
        assert line.startswith("%%MatrixMarket matrix coordinate"), path
        line = f.readline()
        while line.startswith("%"):
            line = f.readline()
        nrows, ncols, nnz = map(int, line.split())
        cols = [0] * ncols
        for _ in range(nnz):
            parts = f.readline().split()
            r, c = int(parts[0]), int(parts[1])
            cols[c - 1] ^= 1 << (r - 1)
    return nrows, ncols, cols


# ---------------------------------------------------------------------------- problems
class Prob:
    """One benchmark problem: h[j], l[j] are the bitmasks of column j over the rows of H and of L."""

    def __init__(self, name, variant, nrows, nobs, h, l, meta, rowmeta=None, perms=None):
        self.name, self.variant, self.nrows, self.nobs, self.h, self.l = name, variant, nrows, nobs, h, l
        self.meta, self.rowmeta, self.perms = meta, rowmeta, perms
        v = meta.get("variants", {}).get(variant, {})
        self.distance = v.get("distance")                # ground truth of THIS variant, or None
        self.distance_kind = v.get("distance_kind")      # "exact" | "lower_bound" | "unknown"

    @property
    def ncols(self):
        return len(self.h)


def load(instance_dir, variant="full", lbasis=None):
    """lbasis: read the logical matrix from <variant>.L.<lbasis>.mtx instead of <variant>.L.mtx when that
    file exists (bench/standard_logicals.py writes L.std, a sparse basis of the same logical space; circuits
    have none, their L is fixed by the observables).  prob.lfile names the file read."""
    instance_dir = instance_dir.rstrip("/")
    meta = json.load(open(os.path.join(instance_dir, "meta.json")))
    base = os.path.join(instance_dir, variant)
    nrows, ncols, h = read_mtx(base + ".H.mtx")
    lfile = base + ".L.mtx"
    if lbasis and os.path.exists(base + ".L.%s.mtx" % lbasis):
        lfile = base + ".L.%s.mtx" % lbasis
    elif lbasis and meta.get("track") == "code":
        raise FileNotFoundError("no %s.L.%s.mtx for code instance %s" % (variant, lbasis, meta.get("name")))
    nobs, ncols2, l = read_mtx(lfile)
    assert ncols == ncols2
    rowmeta = json.load(open(base + ".rowmeta.json")) if os.path.exists(base + ".rowmeta.json") else None
    perms = json.load(open(base + ".perms.json")) if os.path.exists(base + ".perms.json") else None
    prob = Prob(meta["name"], variant, nrows, nobs, h, l, meta, rowmeta, perms)
    prob.lfile = os.path.basename(lfile)
    return prob


def to_cdist(prob):
    """The problem as a cdist.problem.Problem (row_meta as tuples, so collapse/window helpers work)."""
    from cdist.problem import Problem
    rm = [tuple(m) for m in prob.rowmeta] if prob.rowmeta else [(i, 0) for i in range(prob.nrows)]
    return Problem(f"{prob.name}:{prob.variant}", prob.nrows, prob.nobs, list(prob.h), list(prob.l), rm,
                   [[j] for j in range(prob.ncols)], {"raw_mechanisms": prob.ncols})


def check_witness(prob, cols):
    """Is `cols` (column indices of this variant) an undetected logical fault set?"""
    cols = list(cols)
    s = lg = 0
    for j in cols:
        s ^= prob.h[j]
        lg ^= prob.l[j]
    ok = s == 0 and lg != 0 and len(set(cols)) == len(cols)
    return {"ok": ok, "weight": len(cols), "syndrome_zero": s == 0, "logical_nonzero": lg != 0}


# ---------------------------------------------------------------------------- export
def write_meta(instance_dir, meta):
    """meta.json fields: name, track ("code" | "circuit"), family, description, n, k, basis, rounds (circuit),
    source (how it was built), variants: {variant: {rows, cols, obs, distance, distance_kind, distance_source}}."""
    json.dump(meta, open(os.path.join(instance_dir, "meta.json"), "w"), indent=1)


def export_problem(instance_dir, variant, p, perms=None):
    """Write one cdist Problem as a variant.  Returns the dict {rows, cols, obs} for meta['variants']."""
    os.makedirs(instance_dir, exist_ok=True)
    base = os.path.join(instance_dir, variant)
    write_mtx(base + ".H.mtx", p.h, p.nrows)
    write_mtx(base + ".L.mtx", p.l, p.nobs)
    json.dump([list(m) for m in p.row_meta], open(base + ".rowmeta.json", "w"))
    if perms:
        json.dump([list(x) for x in perms], open(base + ".perms.json", "w"))
    elif os.path.exists(base + ".perms.json"):
        os.remove(base + ".perms.json")
    return {"rows": p.nrows, "cols": p.ncols, "obs": p.nobs, "symmetries": len(perms) if perms else 0}


def strict_symmetries(p, cand):
    """The candidate row permutations that map the column set of p to itself and keep the logical label of
    every column (stricter than cdist.symmetry.from_row_perms, which allows a change of logical basis)."""
    from cdist import symmetry
    colindex = {}
    for j, a in enumerate(p.h):
        if a in colindex:
            return []
        colindex[a] = j
    seen, out = set(), []
    for perm in cand:
        key = tuple(perm)
        if key in seen or len(perm) != p.nrows or all(i == x for i, x in enumerate(perm)):
            continue
        seen.add(key)
        cache = {}
        ok = True
        for a, b in zip(p.h, p.l):
            j = colindex.get(symmetry._apply(a, perm, cache))
            if j is None or p.l[j] != b:
                ok = False
                break
        if ok:
            out.append(list(perm))
    return out


def kept_row_perms(p, check_perms):
    """Lift permutations of the check index to the rows of p and keep those that are symmetries of p
    in the sense of cdist.symmetry.from_row_perms (column set invariant, logical labels consistent)."""
    from cdist import symmetry
    import run_parallel
    if not check_perms:
        return []
    cand = [list(x) for x in run_parallel.row_perms(p, check_perms)]
    return symmetric_subset(p, cand)


def symmetric_subset(p, cand):
    from cdist import symmetry
    out, seen = [], set()
    for perm in cand:
        key = tuple(perm)
        if key in seen or len(perm) != p.nrows or all(i == x for i, x in enumerate(perm)):
            continue
        seen.add(key)
        sym = symmetry.from_row_perms(p, [perm])
        if sym.get("ok") and sym.get("n_symmetries_kept") == 1:
            out.append(list(perm))
    return out


def lattice_perms(p):
    """Use the same coordinate translation generators as scripts/run_bb.py (none if the detector coordinates
    do not identify rows by (x, y, t), as for both detector types of a colour code)."""
    from cdist import symmetry
    try:
        found = symmetry.translations(p)
    except AssertionError:
        return []
    if not found.get("ok"):
        return []
    x0, sx, nx = symmetry._axis(m[0] for m in p.row_meta)
    y0, sy, ny = symmetry._axis(m[1] for m in p.row_meta)
    index = {tuple(m[:3]): i for i, m in enumerate(p.row_meta)}
    out = []
    for dx, dy in found["generators"]:
        out.append([index[(x0 + ((m[0] - x0) / sx + dx) % nx * sx,
                           y0 + ((m[1] - y0) / sy + dy) % ny * sy) + tuple(m[2:3])]
                    for m in p.row_meta])
    return fast_symmetries(p, out)


def fast_symmetries(p, candidates):
    """Verify the same H/L condition as symmetric_subset, with one basis.

    A mapped logical row must belong to rowspace([H; L]); this is exactly
    l(g c) = M l(c) + B h(c), checked by cdist.symmetry._labels_consistent.
    Eliminating rows over column positions avoids rebuilding the identical
    column-space elimination for every candidate translation.
    """
    from cdist import symmetry
    colindex = {h: j for j, h in enumerate(p.h)}
    if len(colindex) != p.ncols:
        return []  # same duplicate-syndrome restriction as from_row_perms
    width = (p.ncols + 7) // 8
    rows = [bytearray(width) for _ in range(p.nrows + p.nobs)]
    for j, (h, l) in enumerate(zip(p.h, p.l)):
        byte, bit = j // 8, 1 << (j % 8)
        for i in bits(h):
            rows[i][byte] |= bit
        for i in bits(l):
            rows[p.nrows + i][byte] |= bit
    basis = {}
    for packed in rows:
        vector = int.from_bytes(packed, "little")
        while vector:
            pivot = vector.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = vector
                break
            vector ^= basis[pivot]
    seen, out = set(), []
    for perm in candidates:
        key = tuple(perm)
        if key in seen or len(perm) != p.nrows or all(i == x for i, x in enumerate(perm)):
            continue
        seen.add(key)
        if sorted(perm) != list(range(p.nrows)):
            continue
        cache, mapped_rows = {}, [bytearray(width) for _ in range(p.nobs)]
        valid = True
        for j, h in enumerate(p.h):
            image = colindex.get(symmetry._apply(h, perm, cache))
            if image is None:
                valid = False
                break
            byte, bit = j // 8, 1 << (j % 8)
            for i in bits(p.l[image]):
                mapped_rows[i][byte] |= bit
        if not valid:
            continue
        for packed in mapped_rows:
            vector = int.from_bytes(packed, "little")
            while vector:
                row = basis.get(vector.bit_length() - 1)
                if row is None:
                    valid = False
                    break
                vector ^= row
            if not valid:
                break
        if valid:
            out.append(list(perm))
    return out


def export_circuit_instance(name, circ, check_perms, meta, root=INSTANCES, high=None):
    """circ: stim.Circuit of a CSS memory experiment whose detectors carry coordinates
    (check, 0, round, type).  Writes circuit.stim and the variants full, sector, collapsed.
    meta: dict with track/family/description/n/k/basis/rounds/source and optionally
    'truth': {'sector': (distance, kind, source), 'collapsed': (...)}.
    Raises if the sector reduction is not exact."""
    from cdist import problem
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "circuit.stim")
    circ.to_file(path)
    full = problem.load_dem_problem(path, name)
    sector = problem.sector_problem(full, high)       # high: see cdist.problem.sector_rows (None = type present at round 0)
    assert problem.sector_is_exact(full, sector), "sector reduction is only a relaxation for this circuit"
    coll = problem.collapse_time(sector)
    truth = meta.pop("truth", {})
    variants = {}
    for v, p in (("full", full), ("sector", sector), ("collapsed", coll)):
        variants[v] = export_problem(d, v, p, kept_row_perms(p, check_perms))
        t = truth.get("sector" if v == "full" else v)
        variants[v].update({"distance": t[0] if t else None, "distance_kind": t[1] if t else "unknown",
                            "distance_source": t[2] if t else None})
    variants["collapsed"]["is_relaxation_of"] = "sector"
    out = dict(meta, name=name, track="circuit", variants=variants,
               raw_mechanisms=full.notes.get("raw_mechanisms"), qubits=circ.num_qubits,
               detectors=circ.num_detectors, observables=circ.num_observables)
    write_meta(d, out)
    return out


def export_dem_instance(name, circ, meta, root=INSTANCES):
    """Any Stim circuit, with no assumption on its detectors: only the variant `full`, the
    undecomposed detector error model.  For circuits that are not CSS memory experiments (no
    sector reduction, no time collapse).  meta may contain 'truth': {'full': (distance, kind, source)}."""
    from cdist import problem
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "circuit.stim")
    circ.to_file(path)
    full = problem.load_dem_problem(path, name)
    truth = meta.pop("truth", {})
    variants = {"full": export_problem(d, "full", full)}
    t = truth.get("full")
    variants["full"].update({"distance": t[0] if t else None, "distance_kind": t[1] if t else "unknown",
                             "distance_source": t[2] if t else None})
    out = dict(meta, name=name, track="circuit", variants=variants,
               raw_mechanisms=full.notes.get("raw_mechanisms"), qubits=circ.num_qubits,
               detectors=circ.num_detectors, observables=circ.num_observables)
    write_meta(d, out)
    return out


def export_code_instance(name, hx, hz, n, basis, check_perms, meta, root=INSTANCES):
    """Code-capacity problem of a CSS code (rows of hx / hz as int bitmasks over the n qubits).
    basis 'Z': Z-logical operators detected by the X checks... as in stabcode.css_distance_problem.
    meta may contain 'truth': {'full': (distance, kind, source)}."""
    import stabcode
    d = os.path.join(root, name)
    p = stabcode.css_distance_problem(hx, hz, n, basis, name=name)
    perms = symmetric_subset(p, [list(x) for x in (check_perms or [])])
    truth = meta.pop("truth", {})
    variants = {"full": export_problem(d, "full", p, perms)}
    for tag, rows in (("Hx", hx), ("Hz", hz)):          # rows x qubits, for tools that take the CSS code itself
        write_mtx(os.path.join(d, f"css.{tag}.mtx"),
                  [sum(1 << i for i, r in enumerate(rows) if (r >> j) & 1) for j in range(n)], len(rows))
    t = truth.get("full")
    variants["full"].update({"distance": t[0] if t else None, "distance_kind": t[1] if t else "unknown",
                             "distance_source": t[2] if t else None})
    out = dict(meta, name=name, track="code", n=n, basis=basis, variants=variants)
    write_meta(d, out)
    return out


# ---------------------------------------------------------------------------- results
def peak_rss_mb():
    scale = 1.0 / (1024 * 1024) if sys.platform == "darwin" else 1.0 / 1024
    return round((resource.getrusage(resource.RUSAGE_SELF).ru_maxrss +
                  resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) * scale, 1)


class Trace:
    """Progress of the bounds over time.  Call lb(K) when every weight below K is excluded with a
    proof, ub(w) when a fault set of weight w has been found."""

    def __init__(self):
        self.t0 = time.time()
        self.events = []
        self.lower = None
        self.upper = None

    def seconds(self):
        return round(time.time() - self.t0, 3)

    def lb(self, value):
        if self.lower is None or value > self.lower:
            self.lower = value
            self.events.append({"t": self.seconds(), "lb": value})

    def ub(self, value):
        if self.upper is None or value < self.upper:
            self.upper = value
            self.events.append({"t": self.seconds(), "ub": value})


def save_result(out, prob, method, trace, status, threads, time_limit, witness=None, config=None, notes=None,
                version=None, value_only=False):
    """One record per (method, instance, variant, threads).  Fields:

      method, version, config        which tool and settings
      instance, variant, rows, cols, obs
      threads, time_limit
      status         exact        lower_bound == upper_bound, both obtained by this method in this run
                     bounds       finished within the limit but the method does not prove optimality
                                  (heuristics: only upper_bound) or left a gap
                     timeout      stopped by the time limit (bounds reached so far are reported)
                     unavailable  the tool is not installed on this machine
                     error        anything else (notes says what)
      lower_bound    certified by this method (every lighter fault set excluded), or null
      upper_bound    weight of a fault set found, or null
      witness        column indices of that fault set in this variant, or null
      witness_ok     checked here against H and L
      seconds        wall time of the whole run
      trace          [{"t": seconds, "lb": K} | {"t": seconds, "ub": w}, ...] in time order
      peak_rss_mb    the adapter's own process and its reaped children only; the harness adds
                     harness.peak_group_rss_mb, the peak of the whole process group (workers and
                     external solvers included), which is the figure to use
      truth (the variant's ground truth if known), agrees_with_truth
      value_only     true for tools whose interface returns the distance as a number and no fault set:
                     upper_bound then has no witness, and the value is checked against the ground
                     truth only (the report labels such results)
    """
    assert status in STATUSES, status
    rec = {"method": method, "version": version, "config": config or {}, "instance": prob.name, "variant": prob.variant,
           "rows": prob.nrows, "cols": prob.ncols, "obs": prob.nobs, "threads": threads, "time_limit": time_limit,
           "status": status, "lower_bound": trace.lower, "upper_bound": trace.upper,
           "witness": list(witness) if witness is not None else None, "witness_ok": None,
           "seconds": trace.seconds(), "trace": trace.events, "peak_rss_mb": peak_rss_mb(),
           "truth": prob.distance, "truth_kind": prob.distance_kind, "notes": notes,
           "value_only": bool(value_only and witness is None)}
    if witness is not None:
        chk = check_witness(prob, witness)
        rec["witness_ok"] = chk["ok"] and chk["weight"] == trace.upper
        if not rec["witness_ok"]:
            rec["status"] = "error"
            rec["notes"] = f"witness failed the check: {chk}; " + (notes or "")
    agrees = None
    if prob.distance is not None and prob.distance_kind == "exact":
        agrees = True
        if trace.lower is not None and trace.lower > prob.distance:
            agrees = False
        if trace.upper is not None and trace.upper < prob.distance:
            agrees = False
        if rec["status"] == "exact" and trace.upper != prob.distance:
            agrees = False
    rec["agrees_with_truth"] = agrees
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        json.dump(rec, open(out + ".tmp", "w"), indent=1)
        os.replace(out + ".tmp", out)
    return rec


def adapter_args(description):
    """The command line shared by all adapters."""
    import argparse
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--instance", required=True)
    ap.add_argument("--variant", default="full")
    ap.add_argument("--time-limit", type=float, default=600.0)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--out", default=None)
    ap.add_argument("--config", default="", help="comma-separated key=value settings of the method")
    a = ap.parse_args()
    a.cfg = dict(kv.split("=", 1) for kv in a.config.split(",") if kv)
    return a
