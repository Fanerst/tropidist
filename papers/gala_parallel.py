"""Parallel 12-layer circuit for GALA [[132,30,12]] designed here: the X checks
use a label order whose F/G pattern is a palindrome and the Z checks use the
same labels in reverse (gala.supports with mirror=True).  The order is read
from results/papers2/design/gala<n>_parallel_order.json.  Interface as
papers/cornucopia.py, for papers/run_parallel.py.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gala

CODES = gala.CODES
translations = gala.translations


def order_file(n):
    return os.path.join(os.path.dirname(HERE), "results", "papers2", "design", f"gala{n}_parallel_order.json")


def is_palindromic(order):
    return all(order[t][0] == order[len(order) - 1 - t][0] for t in range(len(order) // 2))


def build(size, basis, rounds, p=0.001, order=None):
    if order is None:
        order = json.load(open(order_file(size)))["order"]
    assert is_palindromic(order)
    return gala.build(size, basis, rounds, p, order=order, mirror=True)


if __name__ == "__main__":
    import random
    rng = random.Random(1)
    ok = 0
    for trial in range(12):
        pairs = rng.sample(range(6), 3)                     # mirror pairs carrying F labels
        fpos = sorted(pairs + [11 - t for t in pairs])
        gpos = [t for t in range(12) if t not in fpos]
        fl, gl = [f"F{u}" for u in range(6)], [f"G{u}" for u in range(6)]
        rng.shuffle(fl)
        rng.shuffle(gl)
        order = [None] * 12
        for t, lab in zip(fpos, fl):
            order[t] = lab
        for t, lab in zip(gpos, gl):
            order[t] = lab
        for b in "ZX":
            build(132, b, 3, order=order)
        ok += 1
    print("valid deterministic parallel circuits for", ok, "random palindromic orders (both bases)")
    try:
        gala.build(132, "Z", 3, order=gala.CODES[132][6], mirror=True)
        print("paper's order with mirrored Z order: valid")
    except Exception as e:
        print("paper's order with mirrored Z order:", type(e).__name__, str(e).split("\n")[0][:80])
