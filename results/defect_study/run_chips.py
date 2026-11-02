"""Certified circuit distance of chips with dead checks (chip.py), many at a time, one thread per run: the benchmark pipeline
(bench/adapters/ours_pipeline.py, dp=2) on the exported sector problem, then a replay of its fault set in Stim.

A job is a JSON line {"key", "px", "pz" (null: standard), "dead_x", "dead_z", "basis", "cycles"}; results are appended to a
JSON-lines file, and jobs already there are skipped.

Usage: python run_chips.py JOBS.jsonl OUT.jsonl PROCESSES SECONDS_PER_RUN
"""
import json
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TMP = os.environ.get("CHIP_TMP", tempfile.gettempdir())
CFG = None


def job_id(j):
    return json.dumps([j["key"], j.get("px"), j.get("pz"), sorted(j["dead_x"]), sorted(j["dead_z"]), j["basis"], j["cycles"]])


def init(cfg):
    global CFG
    os.environ["OMP_NUM_THREADS"] = "1"
    CFG = cfg


def work(j):
    import chip
    import common
    import stabcode
    from cdist import problem, replay
    t0 = time.time()
    out = dict(j)
    tmp = tempfile.mkdtemp(dir=TMP, prefix="chip_")
    try:
        sched = None if j.get("px") is None else chip.B.to_dicts(tuple(j["px"]), tuple(j["pz"]))
        c = chip.build_chip(j["key"], j["basis"], j["cycles"], 1e-3, sched, tuple(j["dead_x"]), tuple(j["dead_z"]))
        rk = chip.ranks(j["key"], tuple(j["dead_x"]), tuple(j["dead_z"]))
        out["rank"] = dict(hx=rk[0], hx_live=rk[1], hz=rk[2], hz_live=rk[3])
        n, k = stabcode.css_parameters(*chip.B.matrices(j["key"]))[:2]
        common.export_circuit_instance("chip", c, [], {"track": "circuit", "family": "defect", "n": n, "k": k,
                                                       "basis": j["basis"], "rounds": j["cycles"], "description": "chip",
                                                       "source": {"job": job_id(j)}}, root=tmp)
        rec = tmp + "/rec.json"
        p = subprocess.run([sys.executable, chip.ROOT + "/bench/adapters/ours_pipeline.py", "--instance", tmp + "/chip",
                            "--variant", "sector", "--config", "dp=2", "--threads", "1", "--time-limit", str(CFG),
                            "--out", rec], capture_output=True, text=True, timeout=CFG + 300)
        r = json.load(open(rec))
        out.update(status=r["status"], lb=r["lower_bound"], ub=r["upper_bound"], witness_ok=r["witness_ok"],
                   rows=r["rows"], cols=r["cols"], run_seconds=r["seconds"], witness=r["witness"])
        if r["witness"] is not None:
            full = problem.load_dem_problem(tmp + "/chip/circuit.stim", "chip")
            sector = problem.sector_problem(full)
            raw = replay.lift_to_dem(full, sector, r["witness"])
            dets, obs, _ = replay.check_in_dem(c, raw)
            faults = replay.physical_faults(c, raw)
            d2, o2 = replay.replay(c, faults)
            out["replay_ok"] = (not dets) and bool(obs) and (not d2) and o2 == obs and len(set(raw)) == len(raw)
            out["faults"] = [{k: f[k] for k in ("tick", "paulis", "flipped_measurement")} for f in faults]
    except Exception as e:
        out["error"] = repr(e)[:400]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main():
    jobs_path, out_path, procs, limit = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
    jobs = [json.loads(x) for x in open(jobs_path) if x.strip()]
    done = set()
    if os.path.exists(out_path):
        done = {job_id(json.loads(x)) for x in open(out_path)}
    todo = [j for j in jobs if job_id(j) not in done]
    print(time.strftime("%F %T"), "jobs", len(jobs), "to do", len(todo), flush=True)
    ctx = mp.get_context("spawn")
    with ctx.Pool(procs, initializer=init, initargs=(limit,), maxtasksperchild=20) as pool, open(out_path, "a") as f:
        for i, r in enumerate(pool.imap_unordered(work, todo), 1):
            f.write(json.dumps(r) + "\n")
            f.flush()
            if i % 50 == 0 or i == len(todo):
                print(time.strftime("%F %T"), i, "of", len(todo), flush=True)
    print(time.strftime("%F %T"), "end", flush=True)


if __name__ == "__main__":
    main()
