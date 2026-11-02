"""Deep run of two-gross problems: the benchmark pipeline (dp=2) up to weight KMAX on the one-cycle instruction (IBM's setting)
of one schedule and basis.  A finished run gives either a fault set of weight <= KMAX or the lower bound KMAX + 1.
Records and progress files go to deep/.

Usage: python deep_run.py THREADS KMAX SECONDS PROBLEM [PROBLEM ...]     PROBLEM: px_pz[_Z|_X], e.g. 026135_531640_Z
Environment: DEEP_CYCLES (default 1) noisy cycles; DEEP_MATCHED=1 the circuit of papers/ibm_bicycle_matched.py;
DEEP_CONFIG, DEEP_TAG: other pipeline settings, and a tag for the file names (for a cross-check with other code paths).
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.environ.get("CD_ROOT", os.path.expanduser("~/claude_runs/defect_study"))
sys.path[:0] = [ROOT + "/papers", ROOT, ROOT + "/bench"]
HERE = os.path.dirname(os.path.abspath(__file__))
import bb6_depth7 as B
import common
import ibm_bicycle as IB
import stabcode


def main():
    threads, kmax, seconds = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
    cycles = int(os.environ.get("DEEP_CYCLES", "1"))
    matched = os.environ.get("DEEP_MATCHED") == "1"
    os.makedirs(HERE + "/deep/instances", exist_ok=True)
    for prob in sys.argv[4:]:
        parts = prob.split("_")
        s = (tuple(map(int, parts[0])), tuple(map(int, parts[1])))
        basis = parts[2] if len(parts) > 2 else "Z"
        name = f"ibm_bb288_s{parts[0]}_{parts[1]}_c{cycles}_{basis}" + ("_matched" if matched else "")
        tag = os.environ.get("DEEP_TAG", "")
        rec = f"{HERE}/deep/{name}_k{kmax}{tag}.json"
        if os.path.exists(rec):
            print(name, "already done", flush=True)
            continue
        if matched:
            import ibm_bicycle_matched as M
            c = M.build_matched("bb288", basis, cycles, 1e-3, B.to_dicts(*s))
        else:
            c = IB.build_instruction("bb288", basis, cycles, 1e-3, B.to_dicts(*s))
        n, k = stabcode.css_parameters(*B.matrices("bb288"))[:2]
        root = HERE + "/deep/instances"
        common.export_circuit_instance(name, c, B.translations("bb288"),
                                       {"track": "circuit", "family": "bb288_scan", "n": n, "k": k, "basis": basis, "rounds": cycles,
                                        "description": name, "source": {"px": s[0], "pz": s[1]}}, root=root)
        env = dict(os.environ, OMP_NUM_THREADS=str(threads), PIPELINE_PROGRESS=rec + ".progress")
        print(time.strftime("%F %T"), name, "start", flush=True)
        p = subprocess.run([sys.executable, ROOT + "/bench/adapters/ours_pipeline.py", "--instance", root + "/" + name,
                            "--variant", "sector", "--config", os.environ.get("DEEP_CONFIG", f"dp=2,kmax={kmax}"), "--threads", str(threads),
                            "--time-limit", str(seconds), "--out", rec], capture_output=True, text=True, env=env)
        print(time.strftime("%F %T"), name, "end:", p.stdout.strip()[-200:], p.stderr.strip()[-300:], flush=True)
        subprocess.run(["rm", "-rf", root + "/" + name])


if __name__ == "__main__":
    main()
