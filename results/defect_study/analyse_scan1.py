"""One dead check, all schedules (make_scan_m1.py): the chip's distance per schedule, min(distance in the basis of the dead check, perfect-chip distance
in the other basis).  Orbit values spread to all schedules through the symmetries."""
import collections as C
import json
import sys

R = "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance"
sys.path[:0] = [R + "/results/bb288_scan/screen", R + "/papers", R]
import bb6_depth7 as B
import symmetry_classes as SC

val = {}
for l in open(R + "/results/defect_study/rec/rec_scan1.jsonl"):
    r = json.loads(l)
    assert r.get("status") == "exact", r
    val[(tuple(r["px"]), tuple(r["pz"]))] = r["lb"]
print("orbits done", len(val), "values", sorted(C.Counter(val.values()).items()))
sch = B.all_valid()
rep, reps = SC.z_problems("gross", sch)
d = json.load(open(R + "/results/papers3/bb6/gross_all.json"))
perf = {(tuple(r["px"]), tuple(r["pz"])): (r["Z"][1], r["X"][1]) for r in d["rows"]}
T = C.Counter()
best = []
for s in sch:
    pz, px = perf[s]
    if min(pz, px) < 10:
        continue
    a, b = val.get(rep[(s, "Z")][0]), val.get(rep[(s, "X")][0])
    if a is None or b is None:
        T["not yet"] += 1
        continue
    dead_z = min(a, px)          # dead Z check: Z basis loses detectors, X basis at least the perfect value
    dead_x = min(b, pz)
    T[(min(pz, px), dead_z, dead_x)] += 1
    best.append((min(dead_z, dead_x), dead_z, dead_x, pz, px, s))
for k, v in sorted(T.items(), key=str):
    print(k, v)
labs = [(s_, a_) for s_ in "LR" for a_ in range(3)]
std = (tuple(B.STANDARD["X"][l] for l in labs), tuple(B.STANDARD["Z"][l] for l in labs))
print("standard", next((x for x in best if x[5] == std), None))
best.sort(reverse=True)
print("top", best[:8])
print("worst-case distance histogram", sorted(C.Counter(x[0] for x in best).items()))
