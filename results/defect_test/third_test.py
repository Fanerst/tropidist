"""Dead Z checks, Z-basis memory, the basis that loses detectors: how the circuit distance depends on the number of cycles
and on which checks are dead.  Up to translation the pairs are (0, j)."""
import json, os, random, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import defect as DF
import common
import stabcode
R = DF.R
here = os.path.dirname(os.path.abspath(__file__))
root, out = here + "/inst", here + "/rec"
T, which = sys.argv[1], sys.argv[2]
rng = random.Random(11)
if which == "cycles":
    cases = [(c, (), (0,), "Z") for c in (4, 6, 10)] + [(2, (), (), "Z"), (3, (), (), "Z"), (2, (), (), "X"), (3, (), (), "X")]
elif which == "pairs":
    cases = [(3, (), (0, j), "Z") for j in range(1, 72)]
elif which == "more":
    cases = []
    for m in (3, 4, 5):
        seen = 0
        while seen < 25:
            dz = tuple(sorted(rng.sample(range(72), m)))
            cases.append((3, (), dz, "Z"))
            seen += 1
hist = {}
for cyc, dx, dz, basis in cases:
    c, info = DF.build("gross", basis, cyc, 1e-3, None, dx, dz)
    name = "gross_c%d_x%s_z%s_%s" % (cyc, "-".join(map(str, dx)), "-".join(map(str, dz)), basis)
    n, k = stabcode.css_parameters(*DF.B.matrices("gross"))
    common.export_circuit_instance(name, c, [], {"track": "circuit", "family": "defect", "n": n, "k": k, "basis": basis, "rounds": cyc,
        "description": name, "source": {"dead_x": dx, "dead_z": dz, "cycles": cyc}}, root=root)
    t0 = time.time()
    rec = "%s/%s.json" % (out, name)
    subprocess.run([sys.executable, R + "/bench/adapters/ours_pipeline.py", "--instance", root + "/" + name, "--variant", "sector",
                    "--config", "dp=2", "--threads", T, "--time-limit", "1200", "--out", rec], capture_output=True, text=True)
    rr = json.load(open(rec))
    print(name, "rank z %d->%d" % (info["rank_hz"], info["rank_hz_live"]), rr["status"], rr["lower_bound"], rr["upper_bound"], rr["witness_ok"], "%.0f s" % (time.time() - t0), flush=True)
    os.system("rm -rf '%s/%s'" % (root, name))
