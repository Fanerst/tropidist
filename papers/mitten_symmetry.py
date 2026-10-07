"""Symmetries of a mitten-code distance problem.

Rows of the collapsed/window problems are checks, indexed (block, group
element).  Candidates: e -> u*e*v applied to every block, for all u, v in G,
and e -> alpha(e) for inner automorphisms; each candidate is verified on the
problem itself by cdist.symmetry.from_row_perms, so a wrong guess is simply
discarded.
"""
import json
import os

from cdist import symmetry


def candidates(code_dir, nrows):
    sched = json.load(open(os.path.join(code_dir, "hook_free_SE_cycle_schedule.json")))
    mul = sched["group"]["multiplication_table"]
    g = len(mul)
    assert nrows % g == 0
    blocks = nrows // g
    if g <= 60:
        pairs = [(u, v) for u in range(g) for v in range(g)]
    else:
        # for the small codes the full scan finds exactly the central
        # translations; for the large ones only those are tried
        center = [z for z in range(g) if all(mul[z][x] == mul[x][z] for x in range(g))]
        ident = next(e for e in range(g) if all(mul[e][x] == x for x in range(g)))
        pairs = [(z, ident) for z in center]
    for u, v in pairs:
        yield [b * g + mul[mul[u][e]][v] for b in range(blocks) for e in range(g)]


def find(p, code_dir):
    """p: problem whose row_meta[r][0] is the check index (block * |G| + element)."""
    idx = [int(m[0]) for m in p.row_meta]
    nchecks = max(idx) + 1
    pos = {c: r for r, c in enumerate(idx)}
    assert len(pos) == p.nrows == nchecks, "expected one row per check"
    perms = []
    for cand in candidates(code_dir, nchecks):
        perms.append([pos[cand[idx[r]]] for r in range(p.nrows)])
    return symmetry.from_row_perms(p, perms)
