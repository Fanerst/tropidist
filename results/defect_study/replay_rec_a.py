"""Stim replay of the fault sets in rec/rec_a.jsonl that were stored without one (replay_ok null): rebuilds each chip's
circuit as run_chips.py does, lifts the stored sector witness to the detector error model, and replays it as Pauli
faults.  Writes rec/rec_a_replay.jsonl, one line per replayed record.

Usage: python results/defect_study/replay_rec_a.py
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chip
import common
import stabcode
from cdist import problem, replay

out = []
for line in open(os.path.join(HERE, "rec", "rec_a.jsonl")):
    j = json.loads(line)
    if j.get("replay_ok") is not None or j.get("witness") is None:
        continue
    tmp = tempfile.mkdtemp(prefix="chip_")
    try:
        sched = None if j.get("px") is None else chip.B.to_dicts(tuple(j["px"]), tuple(j["pz"]))
        c = chip.build_chip(j["key"], j["basis"], j["cycles"], 1e-3, sched, tuple(j["dead_x"]), tuple(j["dead_z"]))
        n, k = stabcode.css_parameters(*chip.B.matrices(j["key"]))[:2]
        common.export_circuit_instance("chip", c, [], {"track": "circuit", "family": "defect", "n": n, "k": k,
                                                       "basis": j["basis"], "rounds": j["cycles"], "description": "chip",
                                                       "source": {}}, root=tmp)
        full = problem.load_dem_problem(tmp + "/chip/circuit.stim", "chip")
        sector = problem.sector_problem(full)
        raw = replay.lift_to_dem(full, sector, j["witness"])
        dets, obs, _ = replay.check_in_dem(c, raw)
        faults = replay.physical_faults(c, raw)
        d2, o2 = replay.replay(c, faults)
        ok = (not dets) and bool(obs) and (not d2) and o2 == obs and len(set(raw)) == len(raw)
        out.append({k: j[k] for k in ("key", "px", "pz", "dead_x", "dead_z", "basis", "cycles", "lb", "ub")} |
                   {"weight": len(raw), "replay_ok": ok})
        print(j["dead_x"], j["dead_z"], j["basis"], j["cycles"], "weight", len(raw), "replay", ok, flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
with open(os.path.join(HERE, "rec", "rec_a_replay.jsonl"), "w") as f:
    for r in out:
        f.write(json.dumps(r) + "\n")
print(len(out), "replayed;", sum(r["replay_ok"] for r in out), "ok")
