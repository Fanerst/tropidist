"""Search one representative of each distinct one-round window (window_types.py) up to weight KMAX, with the translation symmetry, and replay a
fault set found in Stim.  What this finds or excludes holds for every problem with that window.

Usage: python window_search.py OUT.jsonl TYPES.json KMAX SECONDS ID...   (threads: OMP_NUM_THREADS)
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import time

ROOT = os.environ.get("CD_ROOT", os.path.expanduser("~/claude_runs/bb288_scan"))
sys.path[:0] = [ROOT + "/papers", ROOT, ROOT + "/bench"]
import bb6_depth7 as B
import ibm_bicycle as IB
import run_parallel as RP
from cdist import problem, replay

KEY = "bb288"


def main():
    out, tpath, kmax, tl = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
    rows = json.load(open(tpath))
    for wid in sys.argv[5:]:
        rep = next((r["problem"], w["t"]) for r in rows for w in r["windows"] if w["id"].startswith(wid))
        (p, t), t0 = rep, time.time()
        s = (tuple(map(int, p[0])), tuple(map(int, p[1])))
        circ = IB.build_instruction(KEY, "Z", 1, 1e-3, B.to_dicts(*s))
        with tempfile.TemporaryDirectory() as d:
            circ.to_file(d + "/c.stim")
            full = problem.load_dem_problem(d + "/c.stim", "c")
        sector = problem.sector_problem(full)
        assert problem.sector_is_exact(full, sector)
        win = problem.window_problem(sector, t, t)
        _, kw = RP.sym_of(win, B.translations(KEY))
        print(time.strftime("%F %T"), wid, "problem", p, "window", t, "columns", win.ncols, "symmetry", bool(kw), flush=True)
        r = RP.dist(win, k_table=2, kmax=kmax, time_limit=tl, start=1, **kw)
        runs = r["runs"]
        res = dict(id=wid, problem=p, t=t, columns=win.ncols, kmax=kmax, distance=r["distance"], lower=r["lower_bound"],
                   status=runs[-1]["status"] if runs else None, seconds=round(time.time() - t0, 1),
                   runs=[{k: x[k] for k in ("K", "status", "best", "seconds") if k in x} for x in runs])
        if r["distance"] is not None:
            raw = replay.lift_to_dem(full, sector, [win.col_meta[j] for j in r["solutions"][0]])
            dets, obs, _ = replay.check_in_dem(circ, raw)
            faults = replay.physical_faults(circ, raw)
            d2, o2 = replay.replay(circ, faults)
            res["witness"] = dict(weight=len(raw), verified=(not dets) and bool(obs) and (not d2) and o2 == obs and len(set(raw)) == len(raw),
                                  dem_error_indices=raw, faults=[{k: f[k] for k in ("tick", "instruction", "paulis", "flipped_measurement")} for f in faults])
        with open(out, "a") as f:
            f.write(json.dumps(res) + "\n")
        print(time.strftime("%F %T"), wid, "distance", r["distance"], "lower", r["lower_bound"], runs[-1]["status"] if runs else None,
              "verified", res.get("witness", {}).get("verified"), "%.0f s" % res["seconds"], flush=True)
    print(time.strftime("%F %T"), "end", flush=True)


if __name__ == "__main__":
    main()
