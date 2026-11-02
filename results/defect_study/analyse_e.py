"""The same chips on the standard schedule and on the two distance-11 schedules: chip value = min(d_Z(none, dead_z), d_X(dead_x, none)), perfect-chip value in a basis without dead checks of its type."""
import collections as C
import json
import sys

sys.path[:0] = ["results/defect_study"]
import make_jobs as MJ


def load(n):
    return [json.loads(l) for l in open(f"results/defect_study/rec/rec_{n}.jsonl")]


def key(r):
    return (None if r.get("px") is None else ("".join(map(str, r["px"])), "".join(map(str, r["pz"]))), tuple(r["dead_x"]), tuple(r["dead_z"]), r["basis"], r["cycles"])


rec = {}
for n in ("a", "b2", "c2", "e"):
    for r in load(n):
        rec[key(r)] = r
e = load("e")
print(len(e), C.Counter((r.get("status"), r.get("replay_ok")) for r in e), "errors", sum("error" in r for r in e), "seconds mean %.0f max %.0f" % (sum(r["seconds"] for r in e) / len(e), max(r["seconds"] for r in e)))
S = {"standard": (None, 10), "best8": (("561234", "324015"), 11), "best9": (("106432", "342560"), 11)}
chips = MJ.chips([3, 4, 5, 6, 8, 10], 200)
sets = {3: [c for c in chips if c[0] == 3][:100], 5: [c for c in chips if c[0] == 5][:100]}
for name, (s, perfect) in S.items():
    print("==", name, "perfect", perfect)
    # pairs of one type, all up to translation
    for typ in "ZX":
        c = C.Counter()
        for j in range(1, 72):
            k = (s, (), (0, j), "Z", 3) if typ == "Z" else (s, (0, j), (), "X", 3)
            r = rec[k]
            live = r["rank"]["hz_live"] if typ == "Z" else r["rank"]["hx_live"]
            c[(r["lb"], "kept" if live == 66 else "lost")] += 1
        print("  pairs", typ, sorted(c.items(), reverse=True))
    for m, cs in sets.items():
        hist, kept = C.Counter(), C.Counter()
        for _, dx, dz in cs:
            a = rec[(s, (), tuple(dz), "Z", 3)]["lb"] if dz else perfect
            b = rec[(s, tuple(dx), (), "X", 3)]["lb"] if dx else perfect
            ok = (not dz or rec[(s, (), tuple(dz), "Z", 3)]["rank"]["hz_live"] == 66) and (not dx or rec[(s, tuple(dx), (), "X", 3)]["rank"]["hx_live"] == 66)
            hist[min(a, b)] += 1
            if ok:
                kept[min(a, b)] += 1
        print("  m", m, "all", sorted(hist.items(), reverse=True), "| rank kept", sorted(kept.items(), reverse=True))
