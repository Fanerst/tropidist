"""Weight-8 self-dual bivariate bicycle codes of Liang and Chen
(arXiv:2510.05211, Tables 1 and 2): rebuild every code from the printed
polynomial and twisted torus, and compute its parameters and exact distance.

Each row gives f = 1 + x + x^a y^b + x^c y^d and basis vectors a1 = (0, alpha),
a2 = (beta, gamma), i.e. the relations y^alpha = 1 and x^beta y^gamma = 1.
With g the antipode of f, the X check at cell s acts on the v1 qubits at
s + (exponents of f) and the v2 qubits at s + (exponents of g); the Z checks
have the same supports (H_X = H_Z = [A | A^T]).

The paper gives no syndrome-extraction circuit, so only the code distance is
tested here.

Usage: python papers/selfdual_bb.py [out.json] [max_n]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stabcode
from cdist import search, symmetry

# (n, k, d, [the two non-trivial exponent pairs of f], a1, a2), transcribed from Tables 1 and 2
CODES = [
    (16, 4, 4, [(0, 1), (0, -1)], (0, 4), (2, 2)),
    (24, 8, 4, [(-1, 1), (1, 1)], (0, 6), (2, 2)),
    (30, 6, 5, [(2, 1), (-1, 1)], (0, 3), (5, 0)),
    (32, 12, 4, [(2, 1), (-1, 1)], (0, 4), (4, 2)),
    (36, 10, 4, [(-1, -1), (-1, 1)], (0, 3), (6, 0)),
    (40, 6, 6, [(1, -1), (-1, 0)], (0, 4), (5, 1)),
    (42, 6, 6, [(2, 1), (-1, 1)], (0, 3), (7, 0)),
    (48, 16, 4, [(0, 2), (-2, 0)], (0, 4), (6, 0)),
    (50, 10, 5, [(2, 1), (-1, 1)], (0, 5), (5, 0)),
    (54, 10, 6, [(-1, -1), (-1, 1)], (0, 9), (3, 3)),
    (56, 6, 8, [(2, 1), (-1, 1)], (0, 7), (4, 3)),
    (60, 12, 5, [(2, 1), (-1, 1)], (0, 6), (5, 0)),
    (64, 8, 8, [(0, 1), (0, -1)], (0, 8), (4, 4)),
    (66, 6, 8, [(0, 2), (-2, 0)], (0, 11), (3, -3)),
    (70, 10, 6, [(2, 1), (-1, 1)], (0, 5), (7, 0)),
    (72, 12, 6, [(2, 1), (-1, 1)], (0, 6), (6, 3)),
    (78, 6, 10, [(0, 2), (-2, 0)], (0, 13), (3, -3)),
    (80, 10, 8, [(2, 1), (-1, 1)], (0, 8), (5, 4)),
    (84, 6, 10, [(-1, -1), (-1, 1)], (0, 21), (2, 5)),
    (90, 18, 6, [(3, 1), (-1, 1)], (0, 15), (3, 6)),
    (96, 12, 8, [(-1, -1), (-1, 1)], (0, 12), (4, 4)),
    (98, 14, 6, [(2, 1), (-1, 1)], (0, 7), (7, 0)),
    (100, 12, 8, [(2, 1), (-1, 1)], (0, 5), (10, 0)),
    (102, 6, 10, [(0, 2), (-2, 0)], (0, 17), (3, 7)),
    (104, 6, 12, [(0, 1), (-1, -1)], (0, 26), (2, 8)),
    (108, 20, 6, [(1, 2), (-1, 2)], (0, 18), (3, 6)),
    (110, 10, 8, [(2, 1), (-1, 1)], (0, 5), (11, 0)),
    (112, 6, 12, [(2, 1), (-1, 2)], (0, 7), (8, 0)),
    (114, 6, 10, [(0, 2), (-2, 0)], (0, 19), (3, 5)),
    (120, 8, 12, [(0, 1), (-2, -2)], (0, 6), (10, 0)),
    (126, 22, 6, [(-2, 1), (-1, -2)], (0, 21), (3, 6)),
    (128, 16, 8, [(2, 1), (-1, 1)], (0, 8), (8, 4)),
    (130, 10, 10, [(3, 1), (-1, 1)], (0, 5), (13, 1)),
    (132, 8, 12, [(0, 2), (-1, -1)], (0, 33), (2, 11)),
    (136, 6, 14, [(2, 1), (-1, 2)], (0, 17), (4, 4)),
    (138, 6, 12, [(0, 2), (-2, 0)], (0, 23), (3, 5)),
    (140, 16, 8, [(2, 1), (-1, 1)], (0, 7), (10, 0)),
    (144, 6, 14, [(0, 1), (0, -2)], (0, 24), (3, 11)),
    (150, 6, 14, [(-1, -1), (-1, 1)], (0, 15), (5, 7)),
    (152, 6, 16, [(2, 1), (-1, 2)], (0, 19), (4, 6)),
    (154, 14, 8, [(2, 1), (-1, 1)], (0, 7), (11, 0)),
    (156, 12, 10, [(0, 2), (-2, 0)], (0, 26), (3, 10)),
    (160, 8, 16, [(2, 2), (-1, 1)], (0, 10), (8, 0)),
    (162, 6, 14, [(0, 1), (0, -2)], (0, 27), (3, 12)),
    (168, 6, 16, [(0, 1), (-1, -1)], (0, 42), (2, 10)),
    (170, 10, 10, [(3, 1), (-1, 1)], (0, 5), (17, 0)),
    (174, 6, 14, [(0, 2), (-2, 0)], (0, 29), (3, 5)),
    (176, 8, 16, [(0, 1), (0, -2)], (0, 44), (2, 30)),
    (180, 10, 12, [(-1, -1), (-1, 1)], (0, 15), (6, 6)),
    (182, 14, 10, [(3, 1), (-2, 1)], (0, 7), (13, 0)),
    (184, 6, 16, [(2, 1), (-1, 2)], (0, 23), (4, 4)),
    (186, 6, 14, [(0, 2), (-2, 0)], (0, 31), (3, 5)),
    (190, 10, 10, [(3, 1), (-1, 1)], (0, 5), (19, 0)),
    (192, 12, 12, [(0, 2), (-1, -1)], (0, 48), (2, 21)),
    (196, 14, 10, [(3, 1), (-1, 1)], (0, 7), (14, 0)),
    (198, 10, 12, [(-1, -1), (-1, 1)], (0, 33), (3, 9)),
    (200, 12, 12, [(-1, 1), (1, 2)], (0, 50), (2, 14)),
]


def build(extra, a1, a2):
    """Returns (hx, hz, n, torus, f)."""
    T = stabcode.Torus(a1, a2)
    f = [(0, 0), (1, 0)] + list(extra)
    g = [(-a, -b) for a, b in f]
    A = stabcode.shift_matrix(T, f)
    B = stabcode.shift_matrix(T, g)
    N = T.n
    h = [A[r] | (B[r] << N) for r in range(N)]
    for r in h:
        assert bin(r).count("1") == 8, "the monomials of f are not distinct on this torus"
    return h, list(h), 2 * N, T, f


def translation_symmetry(p, T):
    return symmetry.from_row_perms(p, T.translations())


def main(out=None, max_n=10 ** 9):
    max_n = int(max_n)
    res = []
    for n, k, d, extra, a1, a2 in CODES:
        if n > max_n:
            continue
        t = time.time()
        hx, hz, nn, T, f = build(extra, a1, a2)
        _, kk = stabcode.css_parameters(hx, hz, nn)
        p = stabcode.css_distance_problem(hx, hz, nn, "Z", name=f"sdbb{n}")
        sym = translation_symmetry(p, T)
        kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {}
        ktab = 2 if d <= 6 else 3
        r = search.distance(p, k_table=ktab, kmax=d + 2, cover=True, **kw)
        rec = {"claimed": [n, k, d], "f_exponents": f, "a1": a1, "a2": a2, "n": nn, "k": kk, "d": r["distance"],
               "symmetry_orbits": len(sym["anchors"]) if sym.get("ok") else None,
               "witness": list(r["solutions"][0]) if r["solutions"] else None,
               "nodes": sum(sum(x["nodes"]) for x in r["runs"]), "seconds": round(time.time() - t, 2),
               "agrees": (nn, kk, r["distance"]) == (n, k, d)}
        res.append(rec)
        print(f"[[{n},{k},{d}]] rebuilt [[{nn},{kk},{r['distance']}]] {'ok' if rec['agrees'] else 'DIFFERS'} "
              f"orbits={rec['symmetry_orbits']} nodes={rec['nodes']:.3g} {rec['seconds']}s", flush=True)
        if out:
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
            json.dump({"paper": "arXiv:2510.05211", "threads": search.lib().gm_num_threads(), "codes": res},
                      open(out, "w"), indent=1)
    bad = [x["claimed"] for x in res if not x["agrees"]]
    print(f"{len(res)} codes, {len(res) - len(bad)} agree with the paper; differing: {bad}")


if __name__ == "__main__":
    main(*sys.argv[1:])
