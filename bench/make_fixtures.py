"""Two small instances that every adapter and the harness can be tested on.
Usage: python bench/make_fixtures.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import stabcode
import sdbb_parallel

# code capacity: the [[72,12,6]] bivariate bicycle code, Z errors
l, m, A, B = 6, 6, [(3, 0), (0, 1), (0, 2)], [(0, 3), (1, 0), (2, 0)]
hx, hz, n = stabcode.bb_matrices(l, m, A, B)
perms = [[((i + di) % l) * m + (j + dj) % m for i in range(l) for j in range(m)] for di in range(l) for dj in range(m)]
print(common.export_code_instance("fx_bb72_code", hx, hz, n, "Z", perms, {
    "family": "fixture", "description": "[[72,12,6]] bivariate bicycle code, code capacity", "k": 12,
    "source": "stabcode.bb_matrices(6, 6, x^3+y+y^2, y^3+x+x^2)", "truth": {"full": (6, "exact", "known; README.md")}})["variants"])

# circuit: mirror depth-8 circuit of the self-dual BB code [[16,4,4]], 3 cycles
fam = json.load(open(os.path.join(common.ROOT, "results", "papers2", "design", "sdbb16_parallel_family.json")))
order = [(s[0], int(s[1:])) for s in fam["best_orders"][0]]
circ = sdbb_parallel.build(16, "Z", 3, order=order)
print(common.export_circuit_instance("fx_sdbb16_r3", circ, sdbb_parallel.translations(16), {
    "family": "fixture", "description": "[[16,4,4]] self-dual BB code, mirror depth-8 circuit, 3 cycles, Z basis",
    "n": 16, "k": 4, "basis": "Z", "rounds": 3, "source": "sdbb_parallel.build(16, 'Z', 3, order=" + " ".join(fam["best_orders"][0]) + ")",
    "truth": {"sector": (4, "exact", "results/papers2/design/sdbb16_parallel_family.json and bench/adapters/ours.py"),
              "collapsed": (None, "unknown", None)}})["variants"])
