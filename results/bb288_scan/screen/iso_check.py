"""Direct test of the schedule symmetries on two-gross circuits: for random schedules and every generator, build the
sector problem of both circuits (one cycle, IBM's setting) and look for a detector map (check -> phi(check) + c, round kept
or reversed) that carries one list of (syndrome, logical) columns exactly to the other, up to an invertible change of the
logical basis.  Such a map means equal distance, and equal weight distribution of all logical fault sets."""
import os
import random
import sys
import tempfile

ROOT = os.environ.get("CD_ROOT", "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance")
sys.path[:0] = [ROOT + "/papers", ROOT, ROOT + "/bench", os.path.dirname(os.path.abspath(__file__))]
import bb6_depth7 as B
import ibm_bicycle as IB
from cdist import problem
import symmetry_classes as SC


def sector(key, s, basis, cycles):
    c = IB.build_instruction(key, basis, cycles, 1e-3, B.to_dicts(*s))
    with tempfile.TemporaryDirectory() as d:
        path = d + "/c.stim"
        c.to_file(path)
        full = problem.load_dem_problem(path, "c")
        sec = problem.sector_problem(full)
        assert problem.sector_is_exact(full, sec)
    return sec


def bits(x):
    while x:
        b = x & -x
        yield b.bit_length() - 1
        x ^= b


def solve_map(pairs, nrows, nobs):
    """Linear map f with f(a) = b for all (a, b), where a = (logical bits << nrows) | syndrome bits: the observables of
    the second circuit may be those of the first times stabilizers, which adds detector values.  Returns f if it exists and
    is invertible on the logical part (faults without a syndrome flip a logical in one circuit iff they do in the other)."""
    basis = {}
    for a, b in pairs:
        while a:
            h = a.bit_length() - 1
            if h not in basis:
                basis[h] = (a, b)
                break
            a ^= basis[h][0]
            b ^= basis[h][1]
        if a == 0 and b != 0:
            return None

    def f(a):
        out = 0
        while a:
            h = a.bit_length() - 1
            if h not in basis:
                return None
            a ^= basis[h][0]
            out ^= basis[h][1]
        return out
    img, r = {}, 0
    for k in range(nobs):
        v = f(1 << (nrows + k))
        if v is None:
            return None
        while v:
            t = v.bit_length() - 1
            if t in img:
                v ^= img[t]
            else:
                img[t] = v
                r += 1
                break
    return f if r == nobs else None


def isomorphic(p, q, checkmaps, roundmaps):
    """Search the given check maps and round maps (lists of dicts) for an isomorphism from p to q."""
    idx_q = {tuple(m): i for i, m in enumerate(q.row_meta)}
    from collections import Counter
    target = Counter(q.h)
    if p.nrows != q.nrows or p.ncols != q.ncols or p.nobs != q.nobs:
        return None
    for cm in checkmaps:
        for rm in roundmaps:
            rows, ok = [0] * p.nrows, True
            for i, m in enumerate(p.row_meta):
                t = idx_q.get((float(cm[int(m[0])]), m[1], float(rm(m[2])), q.row_meta[0][3]))
                if t is None:
                    ok = False
                    break
                rows[i] = t
            if not ok:
                continue
            mapped = []
            for h in p.h:
                v = 0
                for b in bits(h):
                    v |= 1 << rows[b]
                mapped.append(v)
            if Counter(mapped) != target:
                continue
            by = {}
            for v, l in zip(mapped, p.l):
                by.setdefault(v, [[], []])[0].append(l)
            for v, l in zip(q.h, q.l):
                by[v][1].append(l)
            nr = p.nrows
            pairs = [((x[0] << nr) | v, y[0]) for v, (x, y) in by.items() if len(x) == 1]
            f = solve_map(pairs, nr, p.nobs)
            if f is None:
                continue
            if all(Counter(f((l << nr) | v) for l in x) == Counter(y) for v, (x, y) in by.items()):
                return dict(checkmap=cm, ok=True)
    return None


def check_map_candidates(key, phi, flip):
    """check v -> phi(v) + c, for every translation c; the check index is i*m + j."""
    (l, m), _, _ = B.CODES[key][0]
    a, b, c, d = phi

    def img(i, j):
        return (a * i + c * j) % l, (b * i + d * j) % m
    out = []
    for u in range(l):
        for v in range(m):
            cm = {}
            for i in range(l):
                for j in range(m):
                    x, y = img(i, j)
                    cm[i * m + j] = ((x + u) % l) * m + (y + v) % m
            out.append(cm)
    return out


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "bb288"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    cycles = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    rng = random.Random(20261101)
    sch = B.all_valid()
    std = (tuple(B.STANDARD["X"][x] for x in [(s, a) for s in "LR" for a in range(3)]),
           tuple(B.STANDARD["Z"][x] for x in [(s, a) for s in "LR" for a in range(3)]))
    sample = [std] + rng.sample(sch, n)
    (l, m), _, _ = B.CODES[key][0]
    identity = [{i: i for i in range(l * m)}]
    au = [x for x in SC.automorphisms(key) if not (x[0] == "plain" and x[2] == (0, 1, 2) and x[3] == (0, 1, 2))]
    nfail = 0
    for s in sample:
        for basis in "ZX":
            p = sector(key, s, basis, cycles)
            rounds = sorted({mm[2] for mm in p.row_meta})
            top = rounds[0] + rounds[-1]
            q = sector(key, SC.T(s), basis, cycles)
            r = isomorphic(p, q, identity + check_map_candidates(key, (1, 0, 0, 1), False), [lambda t: top - t])
            print(s, basis, "T", "iso" if r else "NOT FOUND", "rows", p.nrows, "cols", p.ncols, "rounds", rounds, flush=True)
            nfail += r is None
            for kind, phi, pi, rho in au:
                flip = kind in ("inv", "swapinv")
                q = sector(key, SC.act(kind, pi, rho, *s), ("X" if basis == "Z" else "Z") if flip else basis, cycles)
                r = isomorphic(p, q, check_map_candidates(key, phi, flip), [lambda t: t, lambda t: top - t])
                print(s, basis, kind, phi, pi, rho, "iso" if r else "NOT FOUND", flush=True)
                nfail += r is None
    print("failures", nfail)
