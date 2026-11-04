"""Compares the detector error model of papers/bravyi_repo_circuit.py with the decoding matrices that decoder_setup.py of
github.com/sbravyi/BivariateBicycleCodes (commit fa77e33) computes by its own fault simulation.

decoder_setup.py is run as published, with three changes: the code and the number of cycles are set, its imports of
the ldpc and bposd packages are replaced by a stand-in whose css_code returns the logical operators of
stabcode.css_logicals (so that both sides read the same observables), and it stops before saving its matrices.
Every distinct column of its HX (X-type faults, Z-check detectors) and HZ (Z-type faults, X-check detectors), with
its logical rows, must be a mechanism of the Z-basis and X-basis circuits, and the other way round.

Usage: python papers/bravyi_repo_check.py PATH/TO/decoder_setup.py KEY CYCLES [OUT.json]
"""
import json
import os
import sys
import types

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bb6_depth7 as B
import bravyi_repo_circuit as BR
import stabcode

PARAMS = {"bb72": ((6, 6), (3, 1, 2), (3, 1, 2)), "bb108": ((9, 6), (3, 1, 2), (3, 1, 2)),
          "gross": ((12, 6), (3, 1, 2), (3, 1, 2)), "bb288": ((12, 12), (3, 2, 7), (3, 1, 2))}


def repo_columns(path, key, cycles):
    src = open(path).read()
    (ell, m), (a1, a2, a3), (b1, b2, b3) = PARAMS[key]
    for old, new in (("from ldpc import bposd_decoder\n", ""), ("from bposd.css import css_code\n", ""),
                     ("ell,m = 12,6\na1,a2,a3 = 3,1,2\nb1,b2,b3 = 3,1,2\n",
                      f"ell,m = {ell},{m}\na1,a2,a3 = {a1},{a2},{a3}\nb1,b2,b3 = {b1},{b2},{b3}\n"),
                     ("num_cycles = 12\n", f"num_cycles = {cycles}\n")):
        assert src.count(old) == 1, old
        src = src.replace(old, new)
    src = src[:src.index("# save decoding matrices")]
    hx_ours, hz_ours, nq = B.matrices(key)
    lx, lz = stabcode.css_logicals(hx_ours, hz_ours, nq)
    rows = lambda vs: np.array([[(v >> j) & 1 for j in range(nq)] for v in vs], dtype=int)

    class css_code:
        def __init__(self, hx, hz):
            assert [int("".join(map(str, r[::-1])), 2) for r in hx] == hx_ours
            assert [int("".join(map(str, r[::-1])), 2) for r in hz] == hz_ours
            self.lx, self.lz = rows(lx), rows(lz)

        def test(self):
            pass
    ns = {"css_code": css_code, "__name__": "decoder_setup"}
    exec(compile(src, path, "exec"), ns)
    out = {}
    for basis, table, first in (("Z", ns["HXdict"], ns["first_logical_rowX"]), ("X", ns["HZdict"], ns["first_logical_rowZ"])):
        cols = set()
        for supp in table:
            if supp:
                det = tuple(s for s in supp if s < first)
                obs = tuple(s - first for s in supp if s >= first)
                cols.add((det, obs))
        out[basis] = cols
    return out


def circuit_columns(key, basis, cycles):
    dem = BR.build_memory(key, basis, cycles).detector_error_model(decompose_errors=False)
    cols = set()
    for inst in dem.flattened():
        if inst.type != "error":
            continue
        det = tuple(sorted(t.val for t in inst.targets_copy() if t.is_relative_detector_id()))
        obs = tuple(sorted(t.val for t in inst.targets_copy() if t.is_logical_observable_id()))
        if det or obs:
            cols.add((det, obs))
    return cols


if __name__ == "__main__":
    path, key, cycles = sys.argv[1], sys.argv[2], int(sys.argv[3])
    repo = repo_columns(path, key, cycles)
    result = {"decoder_setup": path, "key": key, "cycles": cycles}
    for basis in "ZX":
        ours = circuit_columns(key, basis, cycles)
        result[basis] = {"repo_columns": len(repo[basis]), "circuit_columns": len(ours), "equal": repo[basis] == ours,
                         "only_repo": len(repo[basis] - ours), "only_circuit": len(ours - repo[basis])}
        print(basis, result[basis], flush=True)
    if len(sys.argv) > 4:
        json.dump(result, open(sys.argv[4], "w"), indent=1)
