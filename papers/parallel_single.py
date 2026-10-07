"""Exact circuit distance of one mirror order of one code, with a long time limit.

Usage: python papers/parallel_single.py module key "L1 R1 L3 R3 R2 L2 R0 L0" basis out.json [seconds per threshold] [rounds]
"""
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import run_parallel

module, key, order, basis, out = sys.argv[1], int(sys.argv[2]), sys.argv[3].split(), sys.argv[4], sys.argv[5]
tl = float(sys.argv[6]) if len(sys.argv) > 6 else 14400
rounds = int(sys.argv[7]) if len(sys.argv) > 7 else 6
M = __import__(module)
order_t = tuple((s[0], int(s[1:])) for s in order)
d = M.CODES[key][2][2]
name = f"single_{module}"
mod = types.ModuleType(name)
mod.CODES = M.CODES
mod.build = lambda size, b, r, p=0.001: M.build(size, b, r, p, order=order_t)
mod.translations = M.translations
mod.tag = lambda size: f"{size}_{''.join(order)}"
sys.modules[name] = mod
run_parallel.main(name, key, basis, out, rounds, 3, d, tl, 1)
r = json.load(open(out))
r["order"] = order
json.dump(r, open(out, "w"), indent=1)
