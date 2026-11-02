"""How the distance of a perfect circuit depends on the number of cycles: every problem (schedule, basis) of the four smaller weight-6 codes, one
representative per orbit of the schedule symmetries (results/bb288_scan/screen/symmetry_classes.py), in the matched circuit of chip.py at the given
cycle counts, to compare with the six-round table results/papers3/bb6/KEY_all.json.  Prints the jobs for run_chips.py.

Usage: make_cycle_jobs.py CYCLES...   (e.g. 2 1)"""
import json
import sys

R = "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance"
sys.path[:0] = [R + "/results/bb288_scan/screen", R + "/papers", R, R + "/results/defect_study"]
import bb6_depth7 as B
import make_jobs as MJ
import symmetry_classes as SC

for c in map(int, sys.argv[1:]):
    for key in ("bb72", "bb90", "bb108", "gross"):
        rep, reps = SC.z_problems(key, B.all_valid())
        for s, b in sorted(set(reps)):
            assert b == "Z"
            print(json.dumps(MJ.job((), (), b, c, key=key, s=s)))
