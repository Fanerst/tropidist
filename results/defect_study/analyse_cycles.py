"""How the distance of a perfect circuit depends on the number of cycles: the records of make_cycle_jobs.py (one and two cycles, one problem per
orbit of the schedule symmetries) against the six-round tables results/papers3/bb6/KEY_all.json.  Each orbit counts by the number of (schedule,
basis) problems it stands for.

Usage: analyse_cycles.py REC.jsonl [OUT.json]"""
import collections
import json
import sys

R = "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance"
sys.path[:0] = [R + "/results/bb288_scan/screen", R + "/papers", R]
import bb6_depth7 as B
import symmetry_classes as SC


def table(key):
    d = json.load(open(f"{R}/results/papers3/bb6/{key}_all.json"))
    val = {}
    for r in d["rows"]:
        s = (tuple(r["px"]), tuple(r["pz"]))
        val[(s, "Z")], val[(s, "X")] = r["Z"][1], r["X"][1]
    return val, d["not_exact"]


def main():
    rec = {}
    for line in open(sys.argv[1]):
        r = json.loads(line)
        s = (tuple(r["px"]), tuple(r["pz"]))
        assert r["status"] == "exact" and r["lb"] == r["ub"] and r["replay_ok"], r
        rec[(r["key"], s, r["cycles"])] = r["lb"]
    out = {}
    sch = B.all_valid()
    for key in ("bb72", "bb90", "bb108", "gross"):
        rep, reps = SC.z_problems(key, sch)
        val, not_exact = table(key)
        assert not not_exact
        weight = collections.Counter(rep.values())
        cross = collections.Counter()
        mism = []
        for x in reps:
            s, b = x
            six = {val[y] for y in rep if rep[y] == x}
            assert len(six) == 1, (x, six)
            six = six.pop()
            c1, c2 = rec[(key, s, 1)], rec[(key, s, 2)]
            cross[(c1, c2, six)] += weight[x]
            if c1 != six or c2 != six:
                mism.append((s, c1, c2, six, weight[x]))
        n = sum(cross.values())
        same1 = sum(v for (a, b, c), v in cross.items() if a == c)
        same2 = sum(v for (a, b, c), v in cross.items() if b == c)
        best = max(c for _, _, c in cross)
        schedule = {}
        for s in sch:
            schedule[s] = (min(rec[(key, rep[(s, "Z")][0], 1)], rec[(key, rep[(s, "X")][0], 1)]),
                           min(rec[(key, rep[(s, "Z")][0], 2)], rec[(key, rep[(s, "X")][0], 2)]),
                           min(val[(s, "Z")], val[(s, "X")]))
        sc = collections.Counter(schedule.values())
        out[key] = dict(problems=n, orbits=len(reps), same_c1=same1, same_c2=same2, best=best,
                        above=[(a, b, c, v) for (a, b, c), v in sorted(cross.items()) if a < b or b < c or a < c],
                        cross=[(a, b, c, v) for (a, b, c), v in sorted(cross.items())],
                        schedule=[(a, b, c, v) for (a, b, c), v in sorted(sc.items())])
        print(key, "problems", n, "orbits", len(reps), "C=1 equals six rounds", same1, "C=2 equals six rounds", same2)
        print("   (C=1, C=2, six rounds): problems")
        for (a, b, c), v in sorted(cross.items()):
            print("    ", (a, b, c), v, "" if a == b == c else "<-- differs")
        print("   per schedule (min of both bases): same at C=1", sum(v for (a, b, c), v in sc.items() if a == c),
              "same at C=2", sum(v for (a, b, c), v in sc.items() if b == c), "of", sum(sc.values()))
        print("   best of the six-round values", best, "; problems with C=1 at best", sum(v for (a, b, c), v in cross.items() if a == best),
              "of those with six rounds at best", sum(v for (a, b, c), v in cross.items() if c == best))
    if len(sys.argv) > 2:
        json.dump(out, open(sys.argv[2], "w"), indent=0)


if __name__ == "__main__":
    main()
