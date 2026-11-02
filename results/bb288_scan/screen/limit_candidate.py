"""The decoder-independent limit of papers/ibm_bicycle_code_logicals.py on another schedule of the two-gross code: every circuit
built without a named schedule uses this one, so the same enumeration, checks and replays run on its own circuit.

Usage: limit_candidate.py PX PZ BASIS CYCLES WEIGHT OUT.json [p ...]     (PX, PZ like 046135 531620)"""
import json
import os
import sys

ROOT = os.environ.get("CD_ROOT", "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance")
sys.path[:0] = [ROOT + "/papers", ROOT, ROOT + "/bench"]
import bb6_depth7 as B
import ibm_bicycle as IB
import ibm_bicycle_matched as M
import ibm_bicycle_matched_bound as MB
import ibm_bicycle_code_logicals as L

px, pz, basis, cycles, weight, out = sys.argv[1:7]
ps = tuple(float(x) for x in sys.argv[7:]) or MB.PS
S = (tuple(map(int, px)), tuple(map(int, pz)))
assert S in set(B.all_valid())
D = B.to_dicts(*S)
_inst, _matched = IB.build_instruction, M.build_matched
IB.build_instruction = lambda key, b, c, p=1e-3, schedule=None: _inst(key, b, c, p, D if schedule is None else schedule)
M.build_matched = lambda key, b, c, p=1e-3, schedule=None, noise="linear": _matched(key, b, c, p, D if schedule is None else schedule, noise)
L.main("bb288", basis, cycles, weight, out, "code", ps)
r = json.load(open(out))
r["schedule"] = f"{px}_{pz}"
json.dump(r, open(out, "w"), indent=1)
