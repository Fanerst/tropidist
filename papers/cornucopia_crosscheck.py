"""Compare the Cornucopia codes and schedules rebuilt from the paper's text
(papers/cornucopia.py) with the files in the authors' repository
(github.com/ZhideLu/Cornucopia_code, read as data only).

  1. H_X and H_Z: equal as sets of rows after relabelling the data qubits
     (their site index u in Z_P  ->  (u mod 3, u mod q)).
  2. Schedule: for every check, the order in which it meets its data qubits in
     the first cycle of their Stim circuit equals the order used here.

Usage: python papers/cornucopia_crosscheck.py [repo dir] [out.json]
"""
import json
import os
import subprocess
import sys

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cornucopia

NAMES = {7: "p21_d6", 16: "p48_d8", 25: "p75_d10", 29: "p87_d12", 49: "p147_d14", 64: "p192_d16", 79: "p237_d18"}


def read_mtx(path):
    rows = {}
    with open(path) as f:
        header = None
        for line in f:
            if line.startswith("%"):
                continue
            a = line.split()
            if header is None:
                header = (int(a[0]), int(a[1]), int(a[2]))
                continue
            rows.setdefault(int(a[0]) - 1, []).append(int(a[1]) - 1)
    return header, rows


def main(repo=os.path.join(HERE, "downloads", "cornucopia_repo"), out=None):
    commit = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%H %ad"], capture_output=True, text=True).stdout.strip()
    res = {"repository": "https://github.com/ZhideLu/Cornucopia_code", "commit": commit, "codes": {}}
    for q, name in NAMES.items():
        P = 3 * q
        n = 12 * P

        def relabel(j):                     # their data index -> ours
            block, u = divmod(j, P)
            return block * P + (u % 3) * q + (u % q)

        hx, hz, _ = cornucopia.matrices(q)
        rec = {}
        for typ, mine in (("HX", hx), ("HZ", hz)):
            (nr, nc, nnz), rows = read_mtx(os.path.join(repo, "code_construction", "results", "matrices",
                                                         f"cornucopia_{name}_{typ}.mtx"))
            theirs = {sum(1 << relabel(j) for j in cols) for cols in rows.values()}
            rec[typ] = {"shape": [nr, nc], "equal_as_row_sets": theirs == set(mine)}
        # schedule
        circ = stim.Circuit.from_file(os.path.join(repo, "syndrome_extraction", "results", "stim_circuits",
                                                   f"cornucopia_{name}_r2.stim"))
        layers = [inst for inst in circ.flattened() if inst.name == "CX"]
        seq_x, seq_z = {}, {}
        for inst in layers[:12]:
            t = [x.value for x in inst.targets_copy()]
            for a, b in zip(t[::2], t[1::2]):
                if a >= n:                  # ancilla is the control: X check
                    seq_x.setdefault(a, []).append(relabel(b))
                else:                       # ancilla is the target: Z check
                    seq_z.setdefault(b, []).append(relabel(a))
        xs, zs = cornucopia.supports(q)
        mine_x = {tuple(d for _, d in g) for g in xs}
        mine_z = {tuple(d for _, d in g) for g in zs}
        rec["cx_layers_in_file"] = len(layers)
        rec["x_check_orders_equal"] = {tuple(v) for v in seq_x.values()} == mine_x
        rec["z_check_orders_equal"] = {tuple(v) for v in seq_z.values()} == mine_z
        res["codes"][f"[[{n},{cornucopia.CODES[q][2][1]},{cornucopia.CODES[q][2][2]}]]"] = rec
        print(n, rec)
    if out:
        json.dump(res, open(out, "w"), indent=1)
    ok = all(r["HX"]["equal_as_row_sets"] and r["HZ"]["equal_as_row_sets"] and r["x_check_orders_equal"]
             and r["z_check_orders_equal"] for r in res["codes"].values())
    print("all equal:", ok, "| commit", commit)


if __name__ == "__main__":
    main(*sys.argv[1:])
