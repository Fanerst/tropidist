"""Robustness of a designed parallel circuit's distance against the number of
cycles: rerun the exact pipeline with more cycles for the stored best order.

Usage: python papers/rounds_check.py sdbb_parallel 40 10 [basis]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import run_parallel

paper, n, rounds = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
bases = sys.argv[4] if len(sys.argv) > 4 else "Z"
mod = __import__(paper)
d = mod.CODES[n][2][2]
res = {}
for b in bases:
    out = os.path.join(ROOT, "results", "papers2", "design", f"{paper}{n}_rounds{rounds}_{b}.json")
    run_parallel.main(paper, n, b, out, rounds, 2 if d <= 8 else 3, d, 1800, 1)
    r = json.load(open(out))
    res[b] = (r.get("certified_lower_bound"), r.get("certified_upper_bound"))
print(f"{paper} n={n} with {rounds} cycles: (lower, upper) = {res}")
