"""Marks in the instance metadata the distances closed by the runs outside the benchmark (results/bench_extended/certificates.json).  Only the ground
truth of an instance changes, never a solver's record or count: an instance closed this way is still uncertified in the tier it did not finish.
The metadata of an instance is rewritten when it is exported again, so run this after bench/export_all.py and whenever more runs close.
Usage: python bench/mark_extended_truth.py [--check]"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERT = "results/bench_extended/certificates.json"
# certificate -> (metadata file, variants whose distance it fixes); the collapsed variant of a circuit is another problem and keeps its own value
MARKS = {
    "mitten [[300,60,14]] circuit": ("bench/instances/mitten_300/meta.json", ("full", "sector")),
    "many-hypercube L = 4": ("bench/instances/hypercube_L4/meta.json", ("full",)),
    "Tanner [[288,2]] Z": ("bench/instances_wjh/wjh_qt_288_2_24/meta.json", ("full",)),
    "Tanner [[324,4]] Z": ("bench/instances_wjh/wjh_qt_324_4_25/meta.json", ("full",)),
    "Tanner [[360,4]] Z": ("bench/instances_wjh/wjh_qt_360_4_24/meta.json", ("full",)),
    "Tanner [[396,4]] Z": ("bench/instances_wjh/wjh_qt_396_4_26/meta.json", ("full",)),
    "BB [[648,4]]": ("bench/instances_wjh/wjh_bb_n648/meta.json", ("full",)),
    "BB [[756,16]]": ("bench/instances_wjh/wjh_bb_n756/meta.json", ("full",)),
}
cert = json.load(open(os.path.join(ROOT, CERT)))
check = "--check" in sys.argv
for name, (path, variants) in MARKS.items():
    c = cert[name]
    if not c["closed"]:
        print("open  ", name, c["lower_bound"], c["upper_bound"])
        continue
    full = os.path.join(ROOT, path)
    m = json.load(open(full))
    changed = []
    for v in variants:
        rec = m["variants"][v]
        old = rec.get("distance"), rec.get("distance_kind")
        if old[1] == "exact":
            assert old[0] == c["upper_bound"], (name, v, old)       # never overwrite an exact value with another
            continue
        rec.update(distance=c["upper_bound"], distance_kind="exact", distance_source="%s#%s" % (CERT, name))
        changed.append((v, old))
    print("closed", name, c["upper_bound"], "changed" if changed else "already exact", changed if changed else "")
    if changed and not check:
        json.dump(m, open(full, "w"), indent=1)
        open(full, "a").write("\n")
