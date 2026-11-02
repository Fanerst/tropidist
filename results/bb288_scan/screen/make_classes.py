"""The 390 schedule classes of the two-gross code in priority order (high distance on the smaller codes first), each with its one
or two problems (schedule, Z basis).  Output: JSON list of {"score", "n" (schedules in the class), "s" (a member), "problems"}."""
import json
import sys

R = "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance"
sys.path[:0] = [R + "/results/bb288_scan/screen", R + "/papers", R]
import bb6_depth7 as B
import symmetry_classes as SC

sch = B.all_valid()
rep, reps = SC.z_problems("bb288", sch)
vals = {}
for k in ("bb72", "bb90", "bb108", "gross"):
    d = json.load(open(f"{R}/results/papers3/bb6/{k}_all.json"))
    vals[k] = {(tuple(r["px"]), tuple(r["pz"])): min(r["Z"][1], r["X"][1]) for r in d["rows"]}
classes = {}
for s in sch:
    key = tuple(sorted({rep[(s, "Z")][0], rep[(s, "X")][0]}))
    c = classes.setdefault(key, dict(n=0, score=(0, 0, 0, 0), s=s))
    c["n"] += 1
    sc = tuple(vals[k][s] for k in ("gross", "bb108", "bb90", "bb72"))
    if sc > c["score"]:
        c["score"], c["s"] = sc, s
out = []
for key, c in sorted(classes.items(), key=lambda kv: tuple(-x for x in kv[1]["score"])):
    out.append(dict(score=c["score"], n=c["n"], s=c["s"], problems=[["".join(map(str, p[0])), "".join(map(str, p[1]))] for p in key]))
assert sum(c["n"] for c in out) == 8496
assert sum(len(c["problems"]) for c in out) == 708
json.dump(out, open(sys.argv[1], "w"))
print(len(out), "classes")
