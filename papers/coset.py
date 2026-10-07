"""Coset codes and the fixed schedule of arXiv:2606.17268v1.

Construction 1 / Table 2 give GAP 4.14.0 indices, not group presentations
or explicit binary matrices.  An existing GAP 4.14.0 with SmallGroups is
therefore required for the first extraction.  No software is downloaded.
Set COSET_GAP to its executable if it is not on PATH.  Extracted row-to-column
permutations are cached as data under results/papers3/coset/.

The schedule is exactly the configuration in Section VI.  Weight 6 uses
staggered preparation/measurement (Algorithm V, odd branch): 8 layers per
round plus one startup layer.  Weight 8 uses 10 layers per round.  Idle
depolarization is applied in preparation and measurement layers as well as
CNOT layers.  The memory wrapper adds noisy data preparation/readout; the
paper specifies the syndrome circuit but does not specify these endpoints.

  OMP_NUM_THREADS=2 .venv/bin/python papers/coset.py extract
  OMP_NUM_THREADS=2 .venv/bin/python papers/coset.py check-distance
  .venv/bin/python papers/coset.py build 48 Z 6 circuits/papers/coset48_r6_Z.stim
"""
from __future__ import annotations

import argparse
import ast
from collections import deque
from functools import lru_cache
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import stim

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import stabcode

SOURCE = "https://arxiv.org/html/2606.17268v1"
RESULTS = ROOT / "results" / "papers3" / "coset"
GAP_VERSION = "4.14.0"
# definition = (SmallGroup order, index, non-normal subgroup index, a, b).
# All indices are ONE-based in the precise GAP lists in the Table 2 caption.
_BOUND = "Table 5: randomized BP-OSD circuit-distance upper bound, not exact"
CODES = {
    48: ((384, 512, 53, (1, 34, 48), (1, 6, 12)), _BOUND, (48, 8, 6), 5),
    96: ((384, 512, 27, (1, 9, 87), (1, 21, 23)), _BOUND, (96, 8, 10), 9),
    224: ((224, 53, 1, (1, 81, 186), (1, 16, 47)), _BOUND, (224, 12, 16), 14),
    84: ((252, 21, 6, (1, 14, 71, 89), (1, 6, 8, 19)), _BOUND, (84, 16, 8), 7),
    112: ((224, 53, 9, (1, 11, 59, 81), (1, 15, 23, 25)), _BOUND, (112, 16, 10), 8),
    128: ((128, 10, 1, (1, 47, 75, 88), (1, 8, 12, 19)), _BOUND, (128, 16, 12), 10),
    168: ((168, 33, 1, (1, 72, 106, 109), (1, 11, 18, 26)), _BOUND, (168, 16, 15), 13),
}


class ReconstructionUnavailable(RuntimeError):
    """The paper's GAP-defined data cannot be reconstructed in this environment."""


def tag(key):
    return str(int(key))


def _gap_source(key):
    order, index, subgroup, aa, bb = CODES[key][0]
    # Membership y^-1*x in H implements equality of LEFT cosets xH=yH.
    # The output uses row->column maps: A_g(i)=index(g^-1*x_i H),
    # B_g(i)=index(x_i*g^-1 H).  This is Section V's inverse convention.
    return f'''
SizeScreen([1000000, 1000000]);;
if GAPInfo.Version <> "{GAP_VERSION}" then
    Print("COSET_VERSION_ERROR:", GAPInfo.Version, "\\n");
    QUIT_GAP(1);
fi;
if LoadPackage("smallgrp") <> true then
    Print("COSET_PACKAGE_ERROR: SmallGroups unavailable\\n");
    QUIT_GAP(1);
fi;
G := SmallGroup({order}, {index});;
subs := Filtered(AllSubgroups(G), h -> not IsNormal(G,h));;
H := subs[{subgroup}];;
N := Normalizer(G,H);;
C := Core(G,H);;
ca := LeftCosets(G,C);;
cb := LeftCosets(N,H);;
aa := List({list(aa)}, i -> Representative(ca[i]));;
bb := List({list(bb)}, i -> Representative(cb[i]));;
cs := LeftCosets(G,H);;
reps := List(cs, Representative);;
CosetIndex := x -> PositionProperty(reps, y -> y^-1*x in H);;
A := List(aa, g -> List(reps, x -> CosetIndex(g^-1*x)));;
B := List(bb, g -> List(reps, x -> CosetIndex(x*g^-1)));;
Print("COSET_BEGIN\\n");
Print([GAPInfo.Version, PackageInfo("smallgrp")[1].Version, Length(reps), Size(H), Size(N), Size(C), A, B]);
Print("\\nCOSET_END\\n");
QUIT_GAP(0);
'''


def _validate_operators(key, record):
    if record.get("source") != SOURCE or record.get("gap_version") != GAP_VERSION:
        raise ReconstructionUnavailable("coset cache source/version does not match Table 2")
    if record.get("definition") != json.loads(json.dumps(CODES[key][0])):
        raise ReconstructionUnavailable("coset cache definition does not match Table 2")
    m = CODES[key][2][0] // 2
    if record.get("cosets") != m:
        raise ReconstructionUnavailable(f"GAP rebuilt {record.get('cosets')} cosets; paper specifies {m}")
    A, B = record["A"], record["B"]
    if len(A) != len(CODES[key][0][3]) or len(B) != len(CODES[key][0][4]):
        raise ReconstructionUnavailable("incorrect number of permutation terms in cache")
    if any(sorted(p) != list(range(m)) for p in A + B):
        raise ReconstructionUnavailable("GAP output contains a non-permutation")
    if any(a[b[i]] != b[a[i]] for a in A for b in B for i in range(m)):
        raise ReconstructionUnavailable("left and right term actions do not commute")
    return A, B


def extract(key, refresh=False):
    """Rebuild Table 2 data using an existing GAP; bounded to 120 seconds."""
    path = RESULTS / f"coset{tag(key)}_operators.json"
    if path.exists() and not refresh:
        rec = json.loads(path.read_text())
        _validate_operators(key, rec)
        return rec
    executable = os.environ.get("COSET_GAP") or shutil.which("gap")
    if not executable:
        raise ReconstructionUnavailable(
            "GAP 4.14.0 with SmallGroups is required by the paper's Table 2 indices; "
            "no existing executable found. Set COSET_GAP to an existing installation. "
            "No packages, group data, or author repositories were downloaded."
        )
    try:
        result = subprocess.run([executable, "-q", "-b", "-r", "-m", "64m", "-o", "1024m", "-K", "1024m"],
                                input=_gap_source(key), text=True, capture_output=True,
                                timeout=120, env={**os.environ, "OMP_NUM_THREADS": "2"})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReconstructionUnavailable(f"GAP extraction failed: {exc}") from exc
    if result.returncode or "COSET_BEGIN\n" not in result.stdout or "\nCOSET_END" not in result.stdout:
        raise ReconstructionUnavailable(f"GAP extraction failed (exit {result.returncode}): "
                                        + (result.stderr + result.stdout)[-3000:])
    try:
        raw = ast.literal_eval(result.stdout.split("COSET_BEGIN\n", 1)[1].split("\nCOSET_END", 1)[0])
        version, package_version, m, hsize, nsize, csize, A, B = raw
        rec = {"source": SOURCE, "gap_version": version, "smallgroups_version": package_version,
               "definition": CODES[key][0],
               "cosets": m, "subgroup_order": hsize, "normalizer_order": nsize, "core_order": csize,
               "A": [[j - 1 for j in p] for p in A], "B": [[j - 1 for j in p] for p in B]}
        rec = json.loads(json.dumps(rec))
        _validate_operators(key, rec)
    except (ValueError, TypeError, SyntaxError) as exc:
        raise ReconstructionUnavailable(f"could not parse GAP extraction: {exc}") from exc
    RESULTS.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".json.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(rec, indent=2) + "\n")
    os.replace(tmp, path)
    operators.cache_clear()
    return rec


@lru_cache(None)
def operators(key):
    rec = extract(key)
    A, B = _validate_operators(key, rec)
    return tuple(tuple(p) for p in A), tuple(tuple(p) for p in B)


def _inverse(p):
    out = [0] * len(p)
    for i, j in enumerate(p):
        out[j] = i
    return out


def _matrices(A, B):
    m = len(A[0])
    Ai, Bi = list(map(_inverse, A)), list(map(_inverse, B))
    def rows(left, right):
        out = []
        for i in range(m):
            row = 0
            for p in left:
                row ^= 1 << p[i]
            for p in right:
                row ^= 1 << (m + p[i])
            out.append(row)
        return out
    # Nonregular actions can have coincident term edges. Construction 1 is
    # a GF(2) sum; retain the term schedule and cancel duplicate matrix bits.
    hx, hz = rows(A, B), rows(Bi, Ai)
    return hx, hz, 2 * m


def matrices(key):
    return _matrices(*operators(key))


def _centralizer(perms):
    """Commuting row permutations, including generators swapping equal orbits.

    A trial image of one vertex uniquely determines an equivariant bijection
    of its connected component.  No general graph-automorphism package is needed.
    """
    m = len(perms[0])
    gens = list(perms) + [_inverse(p) for p in perms]
    unseen, components = set(range(m)), []
    while unseen:
        todo, comp = [min(unseen)], set()
        while todo:
            u = todo.pop()
            if u in comp:
                continue
            comp.add(u)
            todo.extend(g[u] for g in gens if g[u] not in comp)
        unseen.difference_update(comp)
        components.append(sorted(comp))

    def equivariant(src, target):
        mapping, queue = {src[0]: target}, deque([src[0]])
        while queue:
            u = queue.popleft()
            for g in gens:
                a, b = g[u], g[mapping[u]]
                if a in mapping:
                    if mapping[a] != b:
                        return None
                else:
                    mapping[a] = b
                    queue.append(a)
        return mapping if len(set(mapping.values())) == len(src) else None

    out, seen = [], set()
    identity = list(range(m))
    for i, src in enumerate(components):
        for j in range(i, len(components)):
            dst = components[j]
            if len(src) != len(dst):
                continue
            for target in dst:
                mapping = equivariant(src, target)
                if mapping is None:
                    continue
                p = identity.copy()
                for u, v in mapping.items():
                    p[u] = v
                    if i != j:
                        p[v] = u
                key = tuple(p)
                if p != identity and key not in seen:
                    assert all(p[g[u]] == g[p[u]] for g in gens for u in range(m))
                    seen.add(key)
                    out.append(p)
    return out


def translations(key):
    """Same row permutation on both check types and both data blocks."""
    A, B = operators(key)
    return _centralizer(A + B)


def _schedule(A, B):
    """Layers of (operation name, targets), excluding noise and TICKs."""
    m, w = len(A[0]), len(A)
    if w != len(B) or w not in (3, 4):
        raise ValueError("Section VI's fixed schedule requires 3+3 or 4+4 terms")
    za, xa = list(range(2 * m, 3 * m)), list(range(3 * m, 4 * m))

    def x(block, p):
        return ("CX", [q for i in range(m) for q in (xa[i], block * m + p[i])])

    def z(block, p):
        # Paper: data[i] -> Z[M(g)(i)], with M(g) a row->column map.
        return ("CX", [q for i in range(m) for q in (block * m + i, za[p[i]])])

    if w == 3:
        return [
            [("RX", xa), z(1, A[0])],
            [x(0, A[1]), z(1, A[2])],
            [x(1, B[1]), z(0, B[0])],
            [x(1, B[0]), z(0, B[1])],
            [x(1, B[2]), z(0, B[2])],
            [x(0, A[2]), z(1, A[1])],
            [x(0, A[0]), ("M", za)],
            [("MX", xa), ("R", za)],
        ]
    return [
        [("R", za), ("RX", xa)],
        [x(0, A[1]), z(1, A[0])],
        [x(0, A[2]), z(1, A[3])],
        [x(1, B[0]), z(0, B[1])],
        [x(1, B[1]), z(0, B[0])],
        [x(1, B[2]), z(0, B[3])],
        [x(1, B[3]), z(0, B[2])],
        [x(0, A[0]), z(1, A[1])],
        [x(0, A[3]), z(1, A[2])],
        [("M", za), ("MX", xa)],
    ]


def schedule(key):
    return _schedule(*operators(key))


def _build(A, B, basis, rounds, p):
    if basis not in ("Z", "X") or rounds < 1:
        raise ValueError("basis must be Z or X, and rounds must be positive")
    if not 0 <= p <= 1:
        raise ValueError("p must lie in [0, 1]")
    hx, hz, n = _matrices(A, B)
    stabcode.css_parameters(hx, hz, n)
    lx, lz = stabcode.css_logicals(hx, hz, n)
    m, odd = n // 2, len(A) == 3
    data = list(range(n))
    za = list(range(n, n + m))
    all_qubits = set(range(2 * n))
    c = stim.Circuit()
    records = {"Z": {}, "X": {}}
    measured = 0

    def layer(ops, t=None):
        nonlocal measured
        used = set()
        for op, qs in ops:
            if len(set(qs)) != len(qs) or used.intersection(qs):
                raise AssertionError("schedule operates on a qubit twice in a layer")
            used.update(qs)
            if op in ("M", "MX"):
                c.append("X_ERROR" if op == "M" else "Z_ERROR", qs, p)
            c.append(op, qs)
            if op == "CX":
                c.append("DEPOLARIZE2", qs, p)
            elif op in ("R", "RX"):
                c.append("X_ERROR" if op == "R" else "Z_ERROR", qs, p)
            elif op in ("M", "MX"):
                kind = "Z" if op == "M" else "X"
                if t is not None:
                    for i in range(len(qs)):
                        current = measured + i
                        previous = records[kind].get(i)
                        measured_so_far = measured + len(qs)
                        recs = [stim.target_rec(current - measured_so_far)]
                        if previous is not None:
                            recs.append(stim.target_rec(previous - measured_so_far))
                        if previous is not None or kind == basis:
                            c.append("DETECTOR", recs, (i, 0, t, 3 if kind == "Z" else 0))
                        records[kind][i] = current
                measured += len(qs)
        idle = sorted(all_qubits - used)
        if idle:
            c.append("DEPOLARIZE1", idle, p)
        c.append("TICK")

    initial = [("R" if basis == "Z" else "RX", data)]
    if odd:
        initial.append(("R", za))
    layer(initial)
    for t in range(rounds):
        for ops in _schedule(A, B):
            layer(ops, t)
    # Add the memory boundary; paper Algorithm V ends at the syndrome cycle.
    layer([("M" if basis == "Z" else "MX", data)])
    checks, logs = (hz, lz) if basis == "Z" else (hx, lx)
    for i, row in enumerate(checks):
        recs = [stim.target_rec(-n + j) for j in stabcode.bits(row)]
        recs.append(stim.target_rec(records[basis][i] - measured))
        c.append("DETECTOR", recs, (i, 0, rounds, 3 if basis == "Z" else 0))
    for i, row in enumerate(logs):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-n + j) for j in stabcode.bits(row)], i)
    return c


def build(key, basis, rounds, p=0.001):
    return _build(*operators(key), basis, rounds, p)


def check_distance(keys=None, seconds=60):
    """Bounded exact code-distance check; explicit results include timeouts."""
    import time
    from cdist import search, symmetry
    results = []
    for key in (CODES if keys is None else keys):
        if CODES[key][2][2] > 12:
            continue
        rec = {"key": key, "paper_code": CODES[key][2], "method": "css_distance_problem + search.distance(cover=True)",
               "seconds_per_threshold": seconds, "distance": {}}
        start = time.monotonic()
        try:
            hx, hz, n = matrices(key)
            rec["rebuilt_parameters"] = stabcode.css_parameters(hx, hz, n)
            for basis in "ZX":
                prob = stabcode.css_distance_problem(hx, hz, n, basis, name=f"coset{key}")
                sym = symmetry.from_row_perms(prob, translations(key))
                kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {}
                r = search.distance(prob, k_table=2, kmax=CODES[key][2][2], cover=True,
                                    time_limit=seconds, **kw)
                witness = list(r["solutions"][0]) if r["solutions"] else None
                rec["distance"][basis] = {"distance": r["distance"], "lower_bound": r["lower_bound"],
                                           "symmetries_expected": len(translations(key)),
                                           "symmetries_kept": sym.get("n_symmetries_kept"),
                                           "witness": witness, "runs": r["runs"]}
        except ReconstructionUnavailable as exc:
            rec["blocked"] = str(exc)
        rec["seconds"] = round(time.monotonic() - start, 3)
        results.append(rec)
        print(json.dumps(rec), flush=True)
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / "code_distance.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    pextract = sub.add_parser("extract")
    pextract.add_argument("keys", nargs="*", type=int)
    pextract.add_argument("--refresh", action="store_true")
    pdist = sub.add_parser("check-distance")
    pdist.add_argument("keys", nargs="*", type=int)
    pdist.add_argument("--seconds", type=float, default=60)
    pbuild = sub.add_parser("build")
    pbuild.add_argument("key", type=int, choices=list(CODES))
    pbuild.add_argument("basis", choices=("Z", "X"))
    pbuild.add_argument("rounds", type=int)
    pbuild.add_argument("out", type=Path)
    args = parser.parse_args()
    if hasattr(args, "keys") and any(key not in CODES for key in args.keys):
        parser.error("unknown code key; valid keys: " + ", ".join(map(str, CODES)))
    try:
        if args.action == "extract":
            for key in args.keys or CODES:
                extract(key, refresh=args.refresh)
                hx, hz, n = matrices(key)
                print(key, "rebuilt (n,k)", stabcode.css_parameters(hx, hz, n), flush=True)
        elif args.action == "check-distance":
            results = check_distance(args.keys or None, args.seconds)
            if any("blocked" in rec for rec in results):
                return 2
        else:
            circ = build(args.key, args.basis, args.rounds)
            circ.detector_error_model(decompose_errors=False)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            circ.to_file(args.out)
            print(args.out, "qubits", circ.num_qubits, "detectors", circ.num_detectors)
    except ReconstructionUnavailable as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
