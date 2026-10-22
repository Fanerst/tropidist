"""Shared interface of the builders of planar, 2D-local codes (papers/planar_<family>.py).

Every builder module has a function instances() returning a list of dicts with the keys

  name        short unique identifier, e.g. "tile_288_8_12"
  family      e.g. "tile codes"
  arxiv       arXiv id of the paper the instance is taken from
  locator     where in the paper the instance is defined (table, equation, figure)
  n, k        computed here from hx, hz (check() fills them in)
  n_paper, k_paper
              the paper's values
  dx, dz      the paper's X and Z distances (weight of the lightest X / Z logical), or None
  d           the paper's distance, min(dx, dz) when both are given
  d_kind      "exact" (paper says it is proven or computed exactly), "upper" (a bound from a heuristic
              search), "conjectured", or "unknown"
  d_method    how the paper obtained d, with a locator
  hx, hz      checks as Python int bitmasks over the n qubits (bit j = qubit j)
  xy          list of n (x, y) float positions on the planar lattice, for geometric column orders
  notes       free text

Distances use the convention of stabcode.css_distance_problem: the problem of basis "Z" (X errors,
detected by the Z checks) has distance dx, the problem of basis "X" has distance dz.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import stabcode  # noqa: E402


def from_cells(cells, n):
    """Rows as int bitmasks from lists of qubit indices; duplicates cancel (GF(2))."""
    out = []
    for c in cells:
        v = 0
        for q in c:
            v ^= 1 << q
        if v:
            out.append(v)
    return out


def check(inst):
    """Commutation, n and k; fills inst['n'], inst['k'] and returns the instance."""
    hx, hz = inst["hx"], inst["hz"]
    n = len(inst["xy"])
    for a in hx:
        assert a >> n == 0, "X check outside the n qubits"
    for b in hz:
        assert b >> n == 0, "Z check outside the n qubits"
    _, k = stabcode.css_parameters(hx, hz, n)
    inst["n"], inst["k"] = n, k
    return inst


def summary(insts):
    rows = []
    for inst in insts:
        check(inst)
        ok = (inst["n"] == inst.get("n_paper")) and (inst["k"] == inst.get("k_paper"))
        wx = max(bin(r).count("1") for r in inst["hx"]) if inst["hx"] else 0
        wz = max(bin(r).count("1") for r in inst["hz"]) if inst["hz"] else 0
        rows.append("%-28s n=%4d (paper %s)  k=%3d (paper %s)  %s  max weights X %d Z %d  dx=%s dz=%s [%s]"
                    % (inst["name"], inst["n"], inst.get("n_paper"), inst["k"], inst.get("k_paper"),
                       "OK " if ok else "MISMATCH", wx, wz, inst.get("dx"), inst.get("dz"), inst.get("d_kind")))
    return "\n".join(rows)
