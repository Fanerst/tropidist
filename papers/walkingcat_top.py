"""Both bases for the numberings of the Walking Cat terms that reach the largest circuit distance in
the Z basis (results/papers3/walkingcat/labelings_<key>.json from walkingcat_labelings.py).

Usage: python papers/walkingcat_top.py key [rounds] [seconds per threshold]
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import run_parallel
import walkingcat
import walkingcat_labelings as W


def main(key, rounds=6, time_limit=1800):
    key, rounds, time_limit = int(key), int(rounds), float(time_limit)
    path = os.path.join(ROOT, "results", "papers3", "walkingcat", f"labelings_{key}.json")
    res = json.load(open(path))
    d = walkingcat.CODES[key][2][2]
    top = max(r["Z"][0] for r in res["rows"] if isinstance(r["Z"][0], int) and r["Z"][0] == r["Z"][1])
    out = []
    for r in res["rows"]:
        if r["Z"][0] != top or r["Z"][1] != top:
            continue
        pa, pb = tuple(x - 1 for x in r["A"]), tuple(x - 1 for x in r["B"])
        name = f"wctop{key}"
        sys.modules[name] = W.variant(key, pa, pb, name)
        rec = {"A": r["A"], "B": r["B"]}
        for basis in "ZX":
            tmp = os.path.join(ROOT, "results", "papers3", "walkingcat", "labelings_tmp", f"top_{key}_{basis}.json")
            with contextlib.redirect_stdout(io.StringIO()):
                run_parallel.main(name, key, basis, tmp, rounds, 3, d, time_limit, 1)
            x = json.load(open(tmp))
            rec[basis] = [x.get("certified_lower_bound"), x.get("certified_upper_bound")]
            rec[basis + "_witness_verified"] = (x.get("witness") or {}).get("verified")
        out.append(rec)
        print(key, rec, flush=True)
    res["top_numberings_both_bases"] = out
    json.dump(res, open(path, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
