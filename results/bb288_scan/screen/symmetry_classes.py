"""Schedule symmetries of a bivariate bicycle code with weight-six checks (papers/bb6_depth7.py).

A group automorphism phi of Z_l x Z_m with phi(A) = a translate of A (or of B, or of -A, -B) relabels the terms of A and B.
Together with the block and translation maps it follows from, it carries the circuit of a schedule to the circuit of the
relabeled schedule, so both have the same distance:
  plain   (A->A, B->B): basis kept;  swap (A->B, B->A): basis kept, blocks exchanged;
  inv     (A->-A, B->-B): X and Z exchanged, blocks exchanged (D of the earlier notes when phi = -1);
  swapinv (A->-B, B->-A): X and Z exchanged, blocks kept.
T reverses the slots and keeps the basis.  These are claims about circuits; `check` compares them with the exact records.
"""
import itertools
import json
import os
import sys

ROOT = os.environ.get("CD_ROOT", "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance")
sys.path[:0] = [ROOT + "/papers", ROOT]
import bb6_depth7 as B


def automorphisms(key):
    """All (kind, phi, pi, rho, alpha, beta): pi, rho give the image index of each A term and B term."""
    (l, m), A, Bt = B.CODES[key][0]
    out = []
    A = [(a % l, b % m) for a, b in A]
    Bt = [(a % l, b % m) for a, b in Bt]
    for a, b, c, d in itertools.product(range(l), range(m), range(l), range(m)):
        if (l * a) % l or (l * b) % m or (m * c) % l or (m * d) % m:
            continue
        phi = lambda t: ((a * t[0] + c * t[1]) % l, (b * t[0] + d * t[1]) % m)
        if len({phi((i, j)) for i in range(l) for j in range(m)}) != l * m:
            continue
        for swap, inv in itertools.product((0, 1), (0, 1)):
            tA, tB = (Bt, A) if swap else (A, Bt)      # the terms that phi(A), phi(B) must be translates of
            sign = -1 if inv else 1
            def match(src, dst):
                sols = []
                for u in range(l):
                    for v in range(m):
                        img = [((u + sign * dst_[0]) % l, (v + sign * dst_[1]) % m) for dst_ in dst]
                        perm = []
                        for t in src:
                            p = phi(t)
                            if p not in img:
                                perm = None
                                break
                            perm.append(img.index(p))
                        if perm is not None and sorted(perm) == [0, 1, 2]:
                            sols.append(perm)
                return sols
            sa, sb = match(A, tA), match(Bt, tB)
            for pi in sa:
                for rho in sb:
                    out.append((("swapinv" if inv else "swap") if swap else ("inv" if inv else "plain"), (a, b, c, d), tuple(pi), tuple(rho)))
    return sorted(set(out))


def act(kind, pi, rho, px, pz):
    """Schedule image; px = (tx L0 L1 L2, R0 R1 R2) slots of A0 A1 A2 B0 B1 B2, pz = (tz L0 L1 L2, R0 R1 R2) of B^T, A^T."""
    a, b = [None] * 6, [None] * 6
    for i in range(3):
        if kind == "plain":
            a[pi[i]] = px[i]; a[3 + rho[i]] = px[3 + i]
            b[rho[i]] = pz[i]; b[3 + pi[i]] = pz[3 + i]
        elif kind == "swap":        # tx'(R, pi a) = tx(L, a); tx'(L, rho b) = tx(R, b); tz'(R, rho b) = tz(L, b); tz'(L, pi a) = tz(R, a)
            a[3 + pi[i]] = px[i]; a[rho[i]] = px[3 + i]
            b[3 + rho[i]] = pz[i]; b[pi[i]] = pz[3 + i]
        elif kind == "inv":         # tz'(R, pi a) = tx(L, a); tz'(L, rho b) = tx(R, b); tx'(R, rho b) = tz(L, b); tx'(L, pi a) = tz(R, a)
            b[3 + pi[i]] = px[i]; b[rho[i]] = px[3 + i]
            a[3 + rho[i]] = pz[i]; a[pi[i]] = pz[3 + i]
        elif kind == "swapinv":     # tz'(L, pi a) = tx(L, a); tz'(R, rho b) = tx(R, b); tx'(L, rho b) = tz(L, b); tx'(R, pi a) = tz(R, a)
            b[pi[i]] = px[i]; b[3 + rho[i]] = px[3 + i]
            a[rho[i]] = pz[i]; a[3 + pi[i]] = pz[3 + i]
    return tuple(a), tuple(b)


def T(s):
    return tuple(6 - x for x in s[0]), tuple(6 - x for x in s[1])


def group(key, schedules):
    """Generators acting on schedules: list of (name, basis_flip, function)."""
    gens = [("T", False, T)]
    for kind, phi, pi, rho in automorphisms(key):
        if kind == "plain" and pi == (0, 1, 2) and rho == (0, 1, 2):
            continue
        flip = kind in ("inv", "swapinv")
        gens.append((f"{kind}{phi}{pi}{rho}", flip, lambda s, kind=kind, pi=pi, rho=rho: act(kind, pi, rho, *s)))
    return gens


def z_problems(key, schedules):
    """Orbits of (schedule, basis) under the group: returns {(s, b): representative (s, 'Z')}, the list of representatives."""
    gens = group(key, schedules)
    universe = {(s, b) for s in schedules for b in "ZX"}
    rep, reps = {}, []
    for x in sorted(universe, key=lambda t: (t[1] != "Z", t[0])):
        if x in rep:
            continue
        reps.append(x)
        stack, rep[x] = [x], x
        while stack:
            s, b = stack.pop()
            for _, flip, f in gens:
                y = (f(s), ("X" if b == "Z" else "Z") if flip else b)
                assert y in universe, (y, s, b)
                if y not in rep:
                    rep[y] = x
                    stack.append(y)
    return rep, reps


if __name__ == "__main__":
    sch = B.all_valid()
    sset = set(sch)
    for key in ("bb72", "bb90", "bb108", "gross", "bb288"):
        au = automorphisms(key)
        kinds = {}
        for kind, phi, pi, rho in au:
            kinds.setdefault(kind, []).append((phi, pi, rho))
        print(key, {k: len(v) for k, v in kinds.items()})
        gens = group(key, sch)
        bad = [(n, s) for n, _, f in gens for s in sch if f(s) not in sset]
        print("   generators", len(gens), "invalid images", len(bad))
        rep, reps = z_problems(key, sch)
        print("   (schedule, basis) problems", len(rep), "orbits", len(reps), "all have a Z representative:",
              all(b == "Z" for _, b in reps))
        path = f"{ROOT}/results/papers3/bb6/{key}_all.json"
        if os.path.exists(path):
            d = json.load(open(path))
            val = {}
            for r in d["rows"]:
                s = (tuple(r["px"]), tuple(r["pz"]))
                val[(s, "Z")], val[(s, "X")] = r["Z"][1], r["X"][1]
            for n, flip, f in gens:
                ok = sum(val[(f(s), ("X" if b == "Z" else "Z") if flip else b)] == val[(s, b)] for s in sch for b in "ZX")
                print("     ", n, "match", ok, "of", 2 * len(sch))
