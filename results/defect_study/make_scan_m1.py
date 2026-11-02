"""Schedule scan on chips with one dead check (gross code, 3 cycles).  Only the check type of the memory basis can lower the
distance (make_jobs.py), so the problem of a schedule is (schedule, basis) with one dead check of that basis.  The schedule
symmetries (results/bb288_scan/screen/symmetry_classes.py) act on these problems, a single dead check being translatable
anywhere: all orbits have a representative with basis Z.  One job per orbit that contains a schedule of perfect-chip
distance >= DMIN (results/papers3/bb6/gross_all.json).  Prints the jobs."""
import json
import sys

R = "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance"
sys.path[:0] = [R + "/results/bb288_scan/screen", R + "/papers", R]
import bb6_depth7 as B
import symmetry_classes as SC

dmin = int(sys.argv[1]) if len(sys.argv) > 1 else 10
sch = B.all_valid()
d = json.load(open(R + "/results/papers3/bb6/gross_all.json"))
perfect = {(tuple(r["px"]), tuple(r["pz"])): min(r["Z"][1], r["X"][1]) for r in d["rows"]}
rep, reps = SC.z_problems("gross", sch)
keep = {r for (s, b), r in rep.items() if perfect[s] >= dmin}
print(len(reps), "orbits,", len(keep), "kept", file=sys.stderr)
for s, b in sorted(keep):
    assert b == "Z"
    print(json.dumps(dict(key="gross", px=list(s[0]), pz=list(s[1]), dead_x=[], dead_z=[0], basis="Z", cycles=3)))
