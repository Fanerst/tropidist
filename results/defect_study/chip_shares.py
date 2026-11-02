"""Chips by certified distance, per number of dead checks, on the standard schedule and on the eight-timestep distance-11 schedule, and
the share of all chips that reach a given distance at a junction yield.

One or two dead checks: all cases up to translation, weighted by how many chips they stand for.  Three or more: the random chips of
make_jobs.py, only those computed on both schedules.  A chip's value is min(d_Z(none, dead_z), d_X(dead_x, none)), a certified lower
bound (make_jobs.py).  Junction counts as in yield_calc.py.

Usage: chip_shares.py [OUT.json]"""
import collections as C
import json
import math
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE]
import make_jobs as MJ

BEST8 = ("561234", "324015")
PERFECT = {None: 10, BEST8: 11}
MS = [3, 4, 5, 6, 8, 10]
SAMPLE = 200


def records():
    rec = {}
    for n in ("a", "b2", "c2", "e", "f"):
        path = f"{HERE}/rec/rec_{n}.jsonl"
        if not os.path.exists(path):
            continue
        for line in open(path):
            r = json.loads(line)
            if r.get("status") != "exact" or r.get("cycles") != 3:
                continue
            s = None if r.get("px") is None else ("".join(map(str, r["px"])), "".join(map(str, r["pz"])))
            rec[(s, tuple(r["dead_x"]), tuple(r["dead_z"]), r["basis"])] = r
    return rec


def singles(rec, s, typ):
    """The value of one dead check of a type: every single check found, all equal by translation."""
    idx = 1 if typ == "X" else 2
    vals = {r["lb"] for k, r in rec.items() if k[0] == s and len(k[idx]) == 1 and not k[3 - idx] and k[3] == typ}
    assert len(vals) == 1, (s, typ, vals)
    return vals.pop()


def chip_value(rec, s, dx, dz):
    z = rec.get((s, (), tuple(dz), "Z")) if dz else None
    x = rec.get((s, tuple(dx), (), "X")) if dx else None
    if (dz and z is None) or (dx and x is None):
        return None
    return min(z["lb"] if z else PERFECT[s], x["lb"] if x else PERFECT[s])


def shares(rec):
    """{schedule: {m: {distance: share}}} and the number of chips behind each sampled m."""
    out = {s: {0: {PERFECT[s]: 1.0}} for s in PERFECT}
    for s in PERFECT:
        vz, vx = singles(rec, s, "Z"), singles(rec, s, "X")
        out[s][1] = {}
        for v in (vz, vx):
            out[s][1][v] = out[s][1].get(v, 0) + 0.5
        # two dead checks: the pairs (0, j) stand for all pairs, one type or one of each
        same = Fraction(math.comb(72, 2), math.comb(144, 2))
        mixed = Fraction(72 * 72, math.comb(144, 2))
        tot = C.Counter({min(vz, vx): mixed})
        for j in range(1, 72):
            tot[rec[(s, (), (0, j), "Z")]["lb"]] += same / 71
            tot[rec[(s, (0, j), (), "X")]["lb"]] += same / 71
        out[s][2] = {d: float(v) for d, v in tot.items()}
    n = {}
    for m in MS:
        cs = [c for c in MJ.chips(MS, SAMPLE) if c[0] == m]
        both = [(dx, dz) for _, dx, dz in cs if all(chip_value(rec, s, dx, dz) is not None for s in PERFECT)]
        n[m] = len(both)
        if not both:
            continue
        for s in PERFECT:
            c = C.Counter(chip_value(rec, s, dx, dz) for dx, dz in both)
            out[s][m] = {d: v / len(both) for d, v in c.items()}
    return out, n


def reach(table, m, dmin):
    """Share of chips with m dead checks at distance at least dmin; between sampled m the mean of the neighbors, and 0 beyond the sample."""
    if m in table:
        return sum(v for d, v in table[m].items() if d >= dmin), True
    lo = [x for x in table if x < m]
    hi = [x for x in table if x > m]
    if lo and hi:
        return (reach(table, max(lo), dmin)[0] + reach(table, min(hi), dmin)[0]) / 2, True
    return 0.0, False


def yields(tab, dmins=(10, 9)):
    res = {}
    for y in (0.9998, 0.9995, 0.999):
        pc = 1 - y ** 20
        data = y ** (2 * 144)
        pm = [math.comb(144, m) * pc ** m * (1 - pc) ** (144 - m) for m in range(145)]
        row = {"perfect": data * pm[0]}
        for dmin in dmins:
            for name, s in (("standard", None), ("best8", BEST8)):
                val, missing = 0.0, 0.0
                for m, q in enumerate(pm):
                    v, known = reach(tab[s], m, dmin)
                    val += q * v
                    if not known:
                        missing += q
                row[f"{name}_d{dmin}"] = data * val
                row[f"{name}_d{dmin}_not_sampled"] = data * missing
        row["share_by_m"] = [data * q for q in pm[:12]]
        res[str(y)] = row
    return res


def main(out=None):
    rec = records()
    tab, n = shares(rec)
    res = {"chips_on_both_schedules": n, "yields": yields(tab),
           "shares": {"standard" if s is None else "best8": {str(m): {str(d): v for d, v in t.items()} for m, t in sorted(tab[s].items())} for s in tab}}
    if out:
        json.dump(res, open(out, "w"), indent=1)
    return tab, n, res


if __name__ == "__main__":
    tab, n, res = main(sys.argv[1] if len(sys.argv) > 1 else None)
    print("chips on both schedules", n)
    for s in tab:
        print("schedule", s or "standard")
        for m, t in sorted(tab[s].items()):
            print("  m", m, {d: round(v, 4) for d, v in sorted(t.items(), reverse=True)})
    for y, row in res["yields"].items():
        print(y, {k: round(v, 4) for k, v in row.items() if k != "share_by_m"})
