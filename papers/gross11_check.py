"""Independent checks of the depth-7 interleaved gross-code schedules with circuit distance 11
found by the numbering sweep of papers/shift_numberings.py (static Table II pattern of
arXiv:2601.09911 with the monomials renumbered).

For each numbering: (a) papers/run_parallel.py with 6 and 12 cycles, both bases;
(b) the original pipeline run_bb.py on the six-cycle circuits without symmetry.

Usage: python papers/gross11_check.py [seconds per threshold]
"""
import contextlib
import io
import json
import os
import subprocess
import sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import run_parallel
import shift

NUMBERINGS = [((2, 3, 1), (2, 3, 1)), ((3, 2, 1), (2, 1, 3)), ((3, 2, 1), (2, 3, 1)), ((1, 2, 3), (1, 2, 3))]
tl = float(sys.argv[1]) if len(sys.argv) > 1 else 7200
out_path = os.path.join(ROOT, "results", "papers3", "shift", "gross11_check.json")
res = json.load(open(out_path)) if os.path.exists(out_path) else {}
for pa, pb in NUMBERINGS:
    tagname = "A" + "".join(map(str, pa)) + "_B" + "".join(map(str, pb))
    rec = res.setdefault(tagname, {})
    codes = dict(shift.CODES)
    d0 = codes["144s"]
    codes["144s"] = (d0[0], d0[1], d0[2], None)
    sys.modules["gross11"] = SimpleNamespace(
        CODES=codes, translations=shift.translations, tag=lambda key, t=tagname: f"144s_{t}",
        build=lambda key, basis, rounds, p=0.001, pa=pa, pb=pb: shift.build(key, basis, rounds, p=p, numbering=(pa, pb)))
    for rounds in (6, 12):
        for basis in "ZX":
            k = f"run_parallel_r{rounds}_{basis}"
            if k in rec:
                continue
            path = os.path.join(ROOT, "results", "papers3", "shift", f"gross11_{tagname}_r{rounds}_{basis}.json")
            with contextlib.redirect_stdout(io.StringIO()):
                run_parallel.main("gross11", "144s", basis, path, rounds, 3, 12, tl, 1)
            r = json.load(open(path))
            rec[k] = [r.get("certified_lower_bound"), r.get("certified_upper_bound"), (r.get("witness") or {}).get("verified"),
                      r.get("sector_symmetries_kept"), r.get("seconds")]
            json.dump(res, open(out_path, "w"), indent=1)
            print(tagname, k, rec[k], flush=True)
    for basis in "ZX":
        k = f"run_bb_r6_{basis}"
        if k in rec:
            continue
        circ = os.path.join(ROOT, "circuits", "papers", f"gross11144s_{tagname}_r6_{basis}.stim")
        out = os.path.join(ROOT, "results", "papers3", "shift", f"gross11_{tagname}_run_bb_{basis}.json")
        p = subprocess.run([sys.executable, os.path.join(ROOT, "run_bb.py"), circ, out, "--no-sym", "--kmax", "12",
                            "--time-limit", str(tl)], capture_output=True, text=True)
        if os.path.exists(out):
            r = json.load(open(out))
            rec[k] = [r.get("certified_lower_bound"), r.get("certified_upper_bound"), r.get("seconds")]
        else:
            rec[k] = ["failed", p.stderr[-300:]]
        json.dump(res, open(out_path, "w"), indent=1)
        print(tagname, k, rec[k], flush=True)
