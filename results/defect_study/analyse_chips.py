"""Random chips of make_jobs.py part c: the certified lower bound min(d_Z(none, dead_z), d_X(dead_x, none)) per chip, by number of dead checks."""
import collections as C
import json
import sys

sys.path[:0] = ["results/defect_study"]
import make_jobs as MJ


def load(n):
    return [json.loads(l) for l in open(f"results/defect_study/rec/rec_{n}.jsonl")]


rec = {}
for n in ("a", "b2", "c2"):
    for r in load(n):
        rec[(tuple(r["dead_x"]), tuple(r["dead_z"]), r["basis"], r["cycles"])] = r
print("records", len(rec), "not exact:", [k for k, r in rec.items() if r.get("status") != "exact"][:5])
print("replay not ok:", sum(1 for k, r in rec.items() if r.get("replay_ok") is not True))
PERFECT = {"Z": 10, "X": 10}
ms = [3, 4, 5, 6, 8, 10]
rows = C.defaultdict(C.Counter)
rank_rows = C.defaultdict(C.Counter)
missing = 0
detail = []
for m, dx, dz in MJ.chips(ms, 200):
    z = rec.get(((), tuple(dz), "Z", 3)) if dz else None
    x = rec.get((tuple(dx), (), "X", 3)) if dx else None
    if (dz and z is None) or (dx and x is None):
        missing += 1
        continue
    dzv = z["lb"] if z else PERFECT["Z"]
    dxv = x["lb"] if x else PERFECT["X"]
    d = min(dzv, dxv)
    ok = (not z or z["rank"]["hz_live"] == 66) and (not x or x["rank"]["hx_live"] == 66)
    rows[m][d] += 1
    rank_rows[(m, "rank kept" if ok else "rank lost")][d] += 1
    detail.append((m, dx, dz, dzv, dxv, ok))
print("missing", missing)
for m in ms:
    print("m", m, "chips", sum(rows[m].values()), sorted(rows[m].items(), reverse=True))
for k in sorted(rank_rows):
    print(k, sum(rank_rows[k].values()), sorted(rank_rows[k].items(), reverse=True))
print("rank kept with d < 9:", [x for x in detail if x[5] and min(x[3], x[4]) < 9][:12])
print("rank lost with d >= 9:", len([x for x in detail if not x[5] and min(x[3], x[4]) >= 9]), [x for x in detail if not x[5] and min(x[3], x[4]) >= 9][:6])
