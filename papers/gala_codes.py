"""GALA codes over abelian groups (arXiv:2608.07431v1, Tables S3 and S5):
rebuild from the printed lifts and compute parameters and exact distances.

Definition 11: L/2 "left" and L/2 "right" data blocks of m = |C| qubits each,
J block rows of checks per type, lifts F_u, G_u (sums of group elements),
subscripts mod L/2:
  X check (i, v):  left block j at v + e, e in F_{j-i};   right block j at v + e, e in G_{j-i}
  Z check (i, v):  left block j at v - e, e in G_{i-j};   right block j at v - e, e in F_{i-j}
J is printed in Table S5; for Table S3 it is L/4 (inferred from the rate).

No extraction circuit could be rebuilt from the paper (see gala.py), so only
the code distance is tested.

Usage: python papers/gala_codes.py [out.json] [max_n]
"""
import itertools
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stabcode
from cdist import search, symmetry

# (claimed n, k, d), L, J, cyclic factors, F, G  -- each lift is a list of exponent tuples
CODES = [
    ((136, 36, 8), 8, 3, (17,), [[(7,)], [(0,), (5,)], [(6,)], [(1,), (2,)]],
     [[(10,)], [(16,), (15,)], [(11,)], [(0,), (12,)]]),
    ((132, 30, 12), 12, 5, (11,), [[(2,)], [(4,)], [(3,)], [(6,)], [(3,)], [(9,)]],
     [[(9,)], [(2,)], [(8,)], [(5,)], [(8,)], [(7,)]]),
    ((136, 34, 12), 8, 3, (17,), [[(2,)], [(1,)], [(3,), (16,)], [(13,), (12,)]],
     [[(15,)], [(4,), (5,)], [(14,), (1,)], [(16,)]]),
    ((168, 42, 12), 8, 3, (3, 7), [[(0, 1)], [(0, 3), (0, 2)], [(2, 4), (0, 4)], [(1, 3)]],
     [[(0, 6)], [(2, 4)], [(1, 3), (0, 3)], [(0, 4), (0, 5)]]),
    ((192, 40, 12), 12, 5, (16,), [[(10,)], [(3,)], [(2,)], [(15,)], [(12,)], [(6,)]],
     [[(6,)], [(10,)], [(4,)], [(1,)], [(14,)], [(13,)]]),
    ((228, 46, 12), 12, 5, (19,), [[(10,)], [(15,)], [(6,)], [(4,)], [(5,)], [(17,)]],
     [[(9,)], [(2,)], [(14,)], [(15,)], [(13,)], [(4,)]]),
    ((248, 62, 12), 8, 3, (31,), [[(15,)], [(22,), (10,)], [(7,), (27,)], [(17,)]],
     [[(25,), (1,)], [(25,)], [(3,), (12,)], [(26,)]]),
    ((280, 70, 12), 8, 3, (35,), [[(27,), (20,)], [(4,)], [(26,)], [(29,), (12,)]],
     [[(18,)], [(6,), (29,)], [(22,), (31,)], [(26,)]]),
    ((328, 82, 12), 8, 3, (41,), [[(5,)], [(6,)], [(40,), (25,)], [(13,), (38,)]],
     [[(21,), (29,)], [(18,)], [(40,), (39,)], [(35,)]]),
    ((336, 84, 12), 8, 3, (3, 14), [[(0, 5)], [(0, 3)], [(2, 12), (2, 10), (0, 11)], [(1, 11)]],
     [[(0, 8), (2, 13)], [(2, 5), (2, 6)], [(0, 4)], [(1, 5)]]),
    ((672, 336, 12), 8, 2, (2, 3, 14), [[(1, 1, 5)], [(0, 2, 7), (0, 0, 10)], [(1, 2, 5)], [(1, 0, 6), (0, 0, 8)]],
     [[(0, 1, 13)], [(1, 0, 10), (0, 2, 10)], [(0, 0, 6)], [(1, 0, 8), (0, 1, 12)]]),
]


def group(factors):
    els = list(itertools.product(*[range(f) for f in factors]))
    idx = {e: i for i, e in enumerate(els)}

    def add(i, e, sign=1):
        return idx[tuple((a + sign * b) % f for a, b, f in zip(els[i], e, factors))]
    return els, add


def build(L, J, factors, F, G):
    els, add = group(factors)
    m, h = len(els), L // 2
    n = L * m
    hx, hz = [], []
    for i in range(J):
        for v in range(m):
            x = z = 0
            for j in range(h):
                for e in F[(j - i) % h]:
                    x ^= 1 << (j * m + add(v, e))
                for e in G[(j - i) % h]:
                    x ^= 1 << ((h + j) * m + add(v, e))
                for e in G[(i - j) % h]:
                    z ^= 1 << (j * m + add(v, e, -1))
                for e in F[(i - j) % h]:
                    z ^= 1 << ((h + j) * m + add(v, e, -1))
            hx.append(x)
            hz.append(z)
    # translations of the checks: v -> v + g for every group element g
    perms = [[i * m + add(v, g) for i in range(J) for v in range(m)] for g in els[1:]]
    return hx, hz, n, perms


def main(out=None, max_n=10 ** 9):
    max_n = int(max_n)
    res = []
    for (n, k, d), L, J, factors, F, G in CODES:
        if n > max_n:
            continue
        t = time.time()
        hx, hz, nn, perms = build(L, J, factors, F, G)
        _, kk = stabcode.css_parameters(hx, hz, nn)
        roww = sorted({bin(r).count("1") for r in hx + hz})
        colw = sorted({sum((r >> j) & 1 for r in hx) for j in range(nn)} | {sum((r >> j) & 1 for r in hz) for j in range(nn)})
        rec = {"claimed": [n, k, d], "n": nn, "k": kk, "row_weights": roww, "column_weights": colw, "distance": {}}
        for basis in "ZX":
            p = stabcode.css_distance_problem(hx, hz, nn, basis, name=f"gala{n}")
            sym = symmetry.from_row_perms(p, perms)
            kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {}
            r = search.distance(p, k_table=3 if nn <= 400 else 2, kmax=d + 1, cover=True, **kw)
            rec["distance"][basis] = {"d": r["distance"], "lower_bound": r["lower_bound"],
                                      "witness": list(r["solutions"][0]) if r["solutions"] else None,
                                      "nodes": sum(sum(x["nodes"]) for x in r["runs"])}
        dd = [rec["distance"][b]["d"] for b in "ZX"]
        rec["d"] = min(x for x in dd if x is not None) if any(x is not None for x in dd) else None
        rec["agrees"] = (nn, kk, rec["d"]) == (n, k, d)
        rec["seconds"] = round(time.time() - t, 1)
        res.append(rec)
        print(f"[[{n},{k},{d}]] rebuilt [[{nn},{kk},{rec['d']}]] (d_Z, d_X = {dd}) {'ok' if rec['agrees'] else 'DIFFERS'} "
              f"row weights {roww} column weights {colw} {rec['seconds']}s", flush=True)
        if out:
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
            json.dump({"paper": "arXiv:2608.07431", "threads": search.lib().gm_num_threads(), "codes": res},
                      open(out, "w"), indent=1)
    bad = [x["claimed"] for x in res if not x["agrees"]]
    print(f"{len(res)} codes, {len(res) - len(bad)} agree with the paper; differing: {bad}")


if __name__ == "__main__":
    main(*sys.argv[1:])
