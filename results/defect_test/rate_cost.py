"""What one dead Z check costs in the low-noise logical rate of the gross code (standard schedule, Z-basis memory): all fault
sets of weight 9 on the defective circuit against the weight-10 sets of the perfect one, at order p^5 for a minimum-weight
decoder.  A set of weight 9 fails on each of its C(9,5) subsets of five faults; a set of weight 10 on the less likely side
of each of its 126 splits.  usage: rate_cost.py CYCLES"""
import itertools, math, os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import defect as DF
import numpy as np
sys.path.insert(0, DF.R + "/papers")
import run_parallel as RP
from cdist import problem

C = int(sys.argv[1])


def model(dz, p):
    c, _ = DF.build("gross", "Z", C, p, None, (), dz)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "c.stim")
        c.to_file(path)
        full = problem.load_dem_problem(path, "c.stim")
    sector = problem.sector_problem(full)
    rows = list(sector.notes["sector_rows"])
    pos = {r: i for i, r in enumerate(rows)}
    merged = {}
    for inst in c.detector_error_model(decompose_errors=False).flattened():
        if inst.type != "error":
            continue
        h, l = 0, 0
        for t in inst.targets_copy():
            if t.is_relative_detector_id() and t.val in pos:
                h ^= 1 << pos[t.val]
            elif t.is_logical_observable_id():
                l ^= 1 << t.val
        q = inst.args_copy()[0]
        r = merged.get((h, l), 0.0)
        merged[(h, l)] = r + q - 2 * r * q
    pri = np.array([merged[(sector.h[j], sector.l[j])] for j in range(sector.ncols)])
    return sector, pri


def enum(sector, K, perms=()):
    kw = {}
    if perms:
        sym, kw = RP.sym_of(sector, perms)
        assert sym.get("ok")
    t0 = time.time()
    r = RP.dist(sector, k_table=2, kmax=K, start=K, enum_all=True, time_limit=3000, **kw)
    print("K", K, "distance", r["distance"], "complete", r["solutions_complete"], "solutions", len(r["solutions"]), "%.0f s" % (time.time() - t0), flush=True)
    return r, kw


p = 1e-4
s0, pri0 = model((), p)
r10, kw = enum(s0, 10, DF.B.translations("gross"))
colmaps = RP.sym_of(s0, DF.B.translations("gross"))[0]["colmaps"]
sets10 = set()
for F in r10["solutions"]:
    sets10.add(tuple(sorted(F)))
    for cm in colmaps:
        sets10.add(tuple(sorted(int(cm[j]) for j in F)))
print("perfect chip: sets of weight 10:", len(sets10), "(%d cycles)" % C, flush=True)
base = 0.0
for F in sets10:
    for c in itertools.combinations(F, 5):
        if F[0] in c:
            rest = [x for x in F if x not in c]
            base += min(np.prod(pri0[list(c)]), np.prod(pri0[rest]))
print("perfect chip: order p^5 rate of the sets of weight 10: 10^%.2f over %d cycles, 10^%.2f per cycle" % (math.log10(base), C, math.log10(base / C)), flush=True)
for dz in ((0,), (0, 1)):
    s1, pri1 = model(dz, p)
    r9, _ = enum(s1, 9)
    sets9 = {tuple(sorted(F)) for F in r9["solutions"]}
    add = 0.0
    for F in sets9:
        for c in itertools.combinations(F, 5):
            add += np.prod(pri1[list(c)])
    print("dead", dz, "sets of weight 9:", len(sets9), "added rate 10^%.2f; total/perfect = %.2f" % (math.log10(add) if add else -99, (base + add) / base), flush=True)
