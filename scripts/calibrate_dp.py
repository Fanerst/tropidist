"""Rate of the dense Rank DP kernel (table entries touched per second, trellis.Plan.work) for the time predictions
of cdist/auto.py.  Runs the DP on surface and color codes of growing width with the current OMP_NUM_THREADS.

usage: OMP_NUM_THREADS=1 python scripts/calibrate_dp.py out.json
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "papers"), os.path.join(ROOT, "scripts")]
import stabcode
import dp_vs_search_local as dvs
from cdist import auto, kernel


def main(out):
    res = {"threads": kernel.lib().dp_num_threads(), "runs": []}
    cases = [("surface", d, dvs.rotated_surface) for d in (25, 31, 37, 43)] + \
            [("color", d, dvs.color_code) for d in (21, 23, 25, 27)]
    for fam, d, build in cases:
        hx, hz, n = build(d)
        p = stabcode.css_distance_problem(hx, hz, n, "X")
        est = auto.estimate(p, threads=1)
        t = time.time()
        v, _ = auto.dp_distance(p, est["order"])
        dt = time.time() - t
        rec = {"code": f"{fam}_d{d}", "distance": v, "peak_bits": est["peak_bits"], "work": est["work"],
               "seconds": round(dt, 3), "rate": est["work"] / max(dt, 1e-9)}
        res["runs"].append(rec)
        print(rec, flush=True)
    big = [r for r in res["runs"] if r["seconds"] >= 0.5]
    res["rate_median_of_runs_over_half_a_second"] = sorted(r["rate"] for r in big)[len(big) // 2] if big else None
    json.dump(res, open(out, "w"), indent=1)
    print("median rate", res["rate_median_of_runs_over_half_a_second"])


if __name__ == "__main__":
    main(sys.argv[1])
