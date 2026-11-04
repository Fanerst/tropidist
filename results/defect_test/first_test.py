import json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import defect as DF
import common
import stabcode
R = DF.R
root = os.path.dirname(os.path.abspath(__file__)) + "/inst"
out = os.path.dirname(os.path.abspath(__file__)) + "/rec"
os.makedirs(out, exist_ok=True)
T = sys.argv[1] if len(sys.argv) > 1 else "3"
cases = [("none", (), ()), ("x0", (0,), ()), ("z0", (), (0,))]
for tag, dx, dz in cases:
    for basis in "ZX":
        c, info = DF.build("gross", basis, 1, 1e-3, None, dx, dz)
        name = "gross_dead_%s_%s" % (tag, basis)
        n, k = stabcode.css_parameters(*DF.B.matrices("gross"))
        common.export_circuit_instance(name, c, [], {"track": "circuit", "family": "defect", "n": n, "k": k, "basis": basis, "rounds": 1,
            "description": name, "source": {"dead_x": dx, "dead_z": dz}}, root=root)
        t0 = time.time()
        rec = "%s/%s.json" % (out, name)
        r = subprocess.run([sys.executable, R + "/bench/adapters/ours_pipeline.py", "--instance", root + "/" + name, "--variant", "sector",
                            "--config", "dp=2", "--threads", T, "--time-limit", "900", "--out", rec], capture_output=True, text=True)
        rr = json.load(open(rec))
        print(tag, basis, info, rr["status"], rr["lower_bound"], rr["upper_bound"], rr["witness_ok"], "cols", rr["cols"], "%.0f s" % (time.time() - t0), flush=True)
