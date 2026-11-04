"""Dead checks on the gross code: several cycles, and several dead checks.  Each case: (cycles, dead X checks, dead Z checks)."""
import json, os, random, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import defect as DF
import common
import stabcode
R = DF.R
here = os.path.dirname(os.path.abspath(__file__))
root, out = here + "/inst", here + "/rec"
os.makedirs(out, exist_ok=True)
T = sys.argv[1] if len(sys.argv) > 1 else "4"
which = sys.argv[2]
xs, zs, N = DF.B.supports("gross", None)
supp_z = [set(q for _, q in g) for g in zs]
overlap = [j for j in range(1, 72) if supp_z[0] & supp_z[j]]
far = [j for j in range(1, 72) if not supp_z[0] & supp_z[j]]
rng = random.Random(7)
if which == "cycles":
    cases = [(c, dx, dz, b) for c in (2, 3) for dx, dz, b in (((), (0,), "Z"), ((0,), (), "X"), ((), (0,), "X"), ((0,), (), "Z"))]
elif which == "many":
    cases = []
    for j in overlap[:4] + rng.sample(far, 2):
        cases += [(1, (), (0, j), "Z"), (1, (), (0, j), "X")]
    for j in overlap[:2]:
        cases += [(1, (0, j), (), "X"), (1, (0, j), (), "Z")]
    for m in (3, 4, 6):
        for _ in range(2):
            dead_z = tuple(sorted(rng.sample(range(72), m)))
            cases += [(1, (), dead_z, "Z"), (1, (), dead_z, "X")]
for cyc, dx, dz, basis in cases:
    c, info = DF.build("gross", basis, cyc, 1e-3, None, dx, dz)
    name = "gross_c%d_x%s_z%s_%s" % (cyc, "-".join(map(str, dx)), "-".join(map(str, dz)), basis)
    n, k = stabcode.css_parameters(*DF.B.matrices("gross"))
    common.export_circuit_instance(name, c, [], {"track": "circuit", "family": "defect", "n": n, "k": k, "basis": basis, "rounds": cyc,
        "description": name, "source": {"dead_x": dx, "dead_z": dz, "cycles": cyc}}, root=root)
    t0 = time.time()
    rec = "%s/%s.json" % (out, name)
    subprocess.run([sys.executable, R + "/bench/adapters/ours_pipeline.py", "--instance", root + "/" + name, "--variant", "sector",
                    "--config", "dp=2", "--threads", T, "--time-limit", "1500", "--out", rec], capture_output=True, text=True)
    rr = json.load(open(rec))
    print(name, "rank z %d->%d x %d->%d" % (info["rank_hz"], info["rank_hz_live"], info["rank_hx"], info["rank_hx_live"]), rr["status"], rr["lower_bound"], rr["upper_bound"], rr["witness_ok"], "cols", rr["cols"], "%.0f s" % (time.time() - t0), flush=True)
