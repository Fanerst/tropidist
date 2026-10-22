"""Table of the DP-versus-search test (scripts/dp_vs_search_local.py) from results/dpvs/*.json.

usage: python scripts/summarize_dpvs.py [files ...]
"""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def secs(x):
    return "–" if x is None else (f"{x:.2g} s" if x < 10 else f"{x:.0f} s")


def main(files):
    rows = {}
    for f in files or sorted(glob.glob(str(ROOT / "results/dpvs/*.json"))):
        d = json.load(open(f))
        for name, rec in d["codes"].items():
            key = name if not name.isdigit() else f"surface:{name}"
            row = rows.setdefault(key, {"n": rec["n"]})
            dp = rec.get("dp", {})
            if "cut_rank" in dp:
                row["width"] = dp["cut_rank"]
                if dp.get("status") == "exact":
                    row.setdefault("dp", (dp["seconds"], dp.get("threads"), dp["distance"]))
            s = rec.get("search")
            if s:
                val = s.get("distance") if s["status"] == "exact" else f"≥ {s['lower_bound']} (timeout)"
                row["search"] = (s["seconds"], s.get("threads"), val)

    def order(k):
        fam, _, d = k.partition(":")
        return (fam, int(d) if d.isdigit() else 0, k)

    print("| code | n | DP width | DP time (threads) | DP value | search time (threads) | search value |")
    print("|---|---:|---:|---|---:|---|---|")
    for k in sorted(rows, key=order):
        r = rows[k]
        dp = r.get("dp")
        se = r.get("search")
        print(f"| {k} | {r['n']} | {r.get('width', '–')} | "
              f"{secs(dp[0]) + f' ({dp[1]})' if dp else 'too wide'} | {dp[2] if dp else '–'} | "
              f"{secs(se[0]) + f' ({se[1]})' if se else 'not run'} | {se[2] if se else '–'} |")


if __name__ == "__main__":
    main(sys.argv[1:])
