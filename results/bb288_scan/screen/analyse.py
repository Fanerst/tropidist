"""State of the screen: schedule classes (pairs of problems), which are rejected by a fault set of weight <= 16, which remain."""
import collections as C
import json
import sys

R = "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance"
sys.path[:0] = [R + "/results/bb288_scan/screen", R + "/papers", R]
import bb6_depth7 as B
import symmetry_classes as SC

path = sys.argv[1]
rows = {}
for line in open(path):
    r = json.loads(line)
    rows[(tuple(r["px"]), tuple(r["pz"]))] = r
sch = B.all_valid()
rep, reps = SC.z_problems("bb288", sch)
vals = {}
for k in ("bb72", "bb90", "bb108", "gross"):
    d = json.load(open(f"{R}/results/papers3/bb6/{k}_all.json"))
    vals[k] = {(tuple(r["px"]), tuple(r["pz"])): min(r["Z"][1], r["X"][1]) for r in d["rows"]}
classes = {}
for s in sch:
    a, b = rep[(s, "Z")][0], rep[(s, "X")][0]
    key = tuple(sorted((a, b)))
    c = classes.setdefault(key, dict(n=0, score=(0, 0, 0, 0), s=s))
    c["n"] += 1
    sc = tuple(vals[k][s] for k in ("gross", "bb108", "bb90", "bb72"))
    if sc > c["score"]:
        c["score"], c["s"] = sc, s
state = lambda x: "none" if x not in rows else ("W%d" % rows[x]["witness"]["weight"] if rows[x].get("witness") else
                                                ("open" if any(rows[x].get(t, {}).get("status") == "timeout" for t in ("t1", "t2")) else "empty"))
print("problems done", len(rows), "of", len(reps))
print("problem states", sorted(C.Counter(state(r[0]) for r in reps).items()))
print("window columns", sorted(C.Counter(tuple(sorted(rows[x][t]["columns"] for t in ("t1", "t2") if t in rows[x])) for x in rows).items(), key=str))
print("weights by window size:", sorted(C.Counter((rows[x]["witness"]["weight"], rows[x]["witness"]["window"], rows[x][f"t{rows[x]['witness']['window']}"]["columns"]) for x in rows if rows[x].get("witness")).items()))
print("unverified witnesses", sum(1 for x in rows if rows[x].get("witness") and not rows[x]["witness"]["verified"]), "errors", sum("error" in rows[x] for x in rows))
cc = C.Counter()
remain = []
for key, c in classes.items():
    st = [state(k) for k in key]
    rej = any(x.startswith("W") and int(x[1:]) <= 16 for x in st)
    cc["rejected" if rej else ("both windows empty" if all(x == "empty" for x in st) else "not settled")] += 1
    if not rej:
        remain.append((c["score"], c["n"], st, key, c["s"]))
print("schedule classes", len(classes), dict(cc))
sec = [rows[x]["seconds"] for x in rows]
if sec:
    print("seconds per problem: mean %.0f, max %.0f" % (sum(sec) / len(sec), max(sec)))
remain.sort(key=lambda t: t[0], reverse=True)
for sc, n, st, key, s in remain[:int(sys.argv[2]) if len(sys.argv) > 2 else 15]:
    print(sc, n, st, s, "problems", ["".join(map(str, k[0])) + "_" + "".join(map(str, k[1])) for k in key])
