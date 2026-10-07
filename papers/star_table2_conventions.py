"""STAR Table 2 schedule on the three codes under the index conventions B_i = A_sigma(i)^T that
matter: the natural one and the two that reproduce the paper's 192 / 20 histogram
(papers/star_dictionary.py).  Usage: python papers/star_table2_conventions.py"""
import contextlib
import io
import json
import os
import sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import run_parallel
import star
import star_dictionary as D

out = {}
for key in (42, 66, 78):
    for sigma in ((1, 2, 3, 4), (1, 2, 4, 3), (2, 1, 3, 4)):
        sched = D.relabel(star.PAPER_SCHEDULE, sigma)
        assert star.schedule_is_valid(key, sched)
        s = "".join(map(str, sigma))
        codes = dict(star.CODES)
        d0 = codes[key]
        codes[key] = (d0[0], d0[1], d0[2], None)
        sys.modules["starconv"] = SimpleNamespace(
            CODES=codes, translations=star.translations, tag=lambda size, s=s: f"{size}_s{s}",
            build=lambda size, basis, rounds, p=0.001, sched=sched: star.build(size, basis, rounds, p=p, schedule=sched))
        rec = {}
        for basis in "ZX":
            path = os.path.join(ROOT, "results", "papers3", "star", f"conv_{key}_{s}_{basis}.json")
            with contextlib.redirect_stdout(io.StringIO()):
                run_parallel.main("starconv", key, basis, path, 6, 3, 12, 3600, 1)
            r = json.load(open(path))
            rec[basis] = [r.get("certified_lower_bound"), r.get("certified_upper_bound"), (r.get("witness") or {}).get("verified")]
        out[f"{key}:{s}"] = rec
        print(key, sigma, rec, flush=True)
json.dump(out, open(os.path.join(ROOT, "results", "papers3", "star", "table2_conventions.json"), "w"), indent=1)
