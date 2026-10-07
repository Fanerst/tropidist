"""Table of the exact distances of the rebuilt codes of arXiv:2610.03682 (block RESULTS4 of PAPERS.md).

Reads results/papers4/hyperbolic/server_*.json (papers/hyperbolic_run.py on the server) and caches the
paper's two graph bounds, recomputed by papers/hyperbolic_bounds.py, in
results/papers4/hyperbolic/bounds.json.

Usage: python scripts/summarize_hyperbolic.py [--bounds]     (--bounds: compute missing bounds, slow for large n)
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "papers4", "hyperbolic")

# rows of the paper: our code name -> (paper's name of the tiling, what the paper states for d)
ROWS = [
    ("bolza_L1", "(4,4,4) 32", "2"), ("bolza_L2", "(4,4,4) 32", "6"), ("bolza_L3", "(4,4,4) 32", "8"),
    ("bolza_L4", "(4,4,4) 32", "12"),
    ("lins444_40_L1", "(4,4,4) 40", "4"), ("lins444_40_L2", "(4,4,4) 40", "8"), ("lins444_40_L3", "(4,4,4) 40", "12"),
    ("lins444_58_L1", "(4,4,4) 58", "8"), ("lins444_58_L2", "(4,4,4) 58", "12"), ("lins444_58_L3", "(4,4,4) 58", "16"),
    ("lins444_58_L4", "(4,4,4) 58", "20–24"),
    ("lins444_96_L2", "(4,4,4) 96", "14"), ("lins444_96_L3", "(4,4,4) 96", "20"), ("lins444_96_L4", "(4,4,4) 96", "26–28"),
    ("lins444_109_L2", "(4,4,4) 109", "14–16"), ("lins444_109_L3", "(4,4,4) 109", "22"), ("lins444_109_L4", "(4,4,4) 109", "30"),
    ("lins444_120_L2", "(4,4,4) 120", "16"), ("lins444_120_L3", "(4,4,4) 120", "24"),
    ("lins444_271_L1", "(4,4,4) 271", "10–12"), ("lins444_271_L2", "(4,4,4) 271", "18–20"),
    ("psl25_444_c1_L2", "(4,4,4) onto PSL(2,25)", "22–24"),
    ("psl25_444_c1_x2_L1", "(4,4,4) onto PSL(2,25) × Z2", "10–14"),
    ("lins666_445_L4", "(6,6,6) 445", "20–24"), ("lins777_16_L4", "(7,7,7) 16", "22–24"),
    ("lins446_211_L4", "(4,4,6) 211", "26–28"), ("lins566_130_L4", "(5,6,6) 130", "24–28"),
    ("lins446_339_L4", "(4,4,6) 340 (our entry 339)", "30–32"),
    ("lins788_189_L1", "(7,8,8) 189", "6–8"),
    ("pgl17_466_c2_L1", "(4,6,6) onto PGL(2,17), class 1", "8–10"),
    ("psl29_555_c3_L1", "(5,5,5) onto PSL(2,29), class 1", "8–10"),
    ("pgl19_445_c1_x2_L1", "(4,4,5) onto PGL(2,19) × Z2, class 1", "8–12"),
]


def load_results():
    best = {}
    for f in sorted(glob.glob(os.path.join(RES, "server_*.json")) + glob.glob(os.path.join(RES, "bolza*.json"))
                    + glob.glob(os.path.join(RES, "lins32.json"))):
        try:
            data = json.load(open(f))
        except ValueError:
            continue
        for c in data.get("codes", []):
            r = dict(c["distance"]["Z"], n=c["n"], k=c["k"], threads=data.get("threads"), file=os.path.basename(f))
            old = best.get(c["name"])
            if old is None or (r.get("d") is not None and old.get("d") is None) or \
                    (old.get("d") is None and (r.get("lower_bound") or 0) > (old.get("lower_bound") or 0)):
                best[c["name"]] = r
    return best


def load_bounds(compute):
    path = os.path.join(RES, "bounds.json")
    cache = json.load(open(path)) if os.path.exists(path) else {}
    if compute:
        sys.path.insert(0, os.path.join(ROOT, "papers"))
        import hyperbolic_bounds as B
        for name, _, _ in ROWS:
            if name not in cache:
                r = B.bounds(name)
                cache[name] = [r["d_res"], r["d_string"]]
                json.dump(cache, open(path, "w"), indent=1)
                print(name, cache[name], flush=True)
    return cache


def table(compute=False):
    res, bounds = load_results(), load_bounds(compute)
    lines = ["| tiling in the paper | L | n | k | paper | bounds recomputed | exact distance | search time |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    closed = checked = 0
    for name, label, stated in ROWS:
        r = res.get(name)
        L = int(name.rsplit("_L", 1)[1])
        b = bounds.get(name)
        btxt = "" if b is None else ("%d" % b[0] if b[0] == b[1] else "%d–%d" % tuple(b))
        if r is None:
            lines.append("| %s | %d | | | %s | %s | not run | |" % (label, L, stated, btxt))
            continue
        is_range = "–" in stated
        if r.get("d") is not None:
            d = "**%d**" % r["d"] if is_range else "%d" % r["d"]
            closed += is_range
            checked += (not is_range) and str(r["d"]) == stated
        else:
            d = "≥ %s" % r.get("lower_bound")
        secs = r.get("seconds") or 0
        t = "%.0f s" % secs if secs >= 1 else "< 1 s"
        lines.append("| %s | %d | %d | %d | %s | %s | %s | %s |" % (label, L, r["n"], r["k"], stated, btxt, d, t))
    lines.append("")
    lines.append("%d open ranges closed; %d certified values of the paper reproduced." % (closed, checked))
    return "\n".join(lines)


def main():
    text = table("--bounds" in sys.argv)
    path = os.path.join(ROOT, "docs", "PAPERS.md")
    s = open(path).read()
    pat = re.compile(r"(<!-- RESULTS4:BEGIN -->\n).*?(<!-- RESULTS4:END -->)", re.S)
    if pat.search(s):
        open(path, "w").write(pat.sub(lambda m: m.group(1) + text + "\n" + m.group(2), s))
        print("PAPERS.md updated")
    print(text)


if __name__ == "__main__":
    main()
