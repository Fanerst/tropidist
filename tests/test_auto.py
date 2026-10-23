"""cdist.auto: the dense Rank DP front end agrees with the weight-bounded search, and its cost estimate stops early
when no table can fit."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "papers"), os.path.join(ROOT, "scripts")]

import stabcode
import dp_vs_search_local as dvs
from cdist import auto, problem, search


def search_distance(p):
    return search.distance(p, k_table=2, kmax=40, labelfree=True, cover=True)["distance"]


def test_surface_and_color_codes():
    for build, d in ((dvs.rotated_surface, 5), (dvs.rotated_surface, 9), (dvs.color_code, 7)):
        hx, hz, n = build(d)
        for sector in ("X", "Z"):
            p = stabcode.css_distance_problem(hx, hz, n, sector)
            est = auto.estimate(p)
            value, per = auto.dp_distance(p, est["order"])
            assert value == d == search_distance(p), (build.__name__, d, sector, value)
            assert est["fits"] and est["work"] > 0 and len(per) == p.nobs


def test_many_observables_and_collapsed_circuit():
    # [[72,12,6]]: twelve logical observables, one DP query each
    sys.path.insert(0, os.path.join(ROOT, "bench"))
    import instances
    spec = instances.INSTANCES["code_bb72"]
    hx, hz, n, _ = instances._code(spec)
    p = stabcode.css_distance_problem(hx, hz, n, spec["basis"])
    est = auto.estimate(p)
    assert p.nobs == 12 and est["fits"] and est["work"] < 1e10
    assert auto.dp_distance(p, est["order"])[0] == 6 == search_distance(p)
    # the time-collapsed problem of a surface-code memory circuit (a code-capacity problem with hook columns)
    import stim_families                                    # the benchmark's Stim surface circuits ([check,0,round,type])
    circ = stim_families.surface_circuit(5)[0]           # (circuit, candidate symmetries)
    path = os.path.join(ROOT, "circuits", "papers", "test_auto_surface5_r5.stim")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    circ.to_file(path)
    try:
        coll = problem.collapse_time(problem.sector_problem(problem.load_dem_problem(path, "t")))
    finally:
        os.remove(path)
    est = auto.estimate(coll, max_table_bytes=1 << 30)
    assert est["fits"] and est["work"] < 1e10
    assert auto.dp_distance(coll, est["order"])[0] == search_distance(coll)


def test_estimate_stops_when_no_table_fits():
    hx, hz, n = dvs.rotated_surface(15)                       # cut rank 8: any table needs at least 2^8 bytes
    p = stabcode.css_distance_problem(hx, hz, n, "X")
    est = auto.estimate(p, max_table_bytes=1 << 4)
    assert est["fits"] is False and est["work"] is None and est["predicted_seconds"] == float("inf")


def test_witness_by_traceback():
    for build, d in ((dvs.rotated_surface, 11), (dvs.color_code, 13)):
        hx, hz, n = build(d)
        p = stabcode.css_distance_problem(hx, hz, n, "X")
        est = auto.estimate(p)
        value, per = auto.dp_distance(p, est["order"])
        cols = auto.dp_witness(p, est["order"], per.index(value))
        assert value == d and len(cols) == d and search.verify(p, tuple(cols))
    assert auto.dp_witness(p, est["order"], 0, max_bytes=1) is None       # tables over the cap: no traceback


def test_sparse_front_end():
    # the sparse DP's sweep at K returns the distance when it is <= K (with a witness), else None, and agrees with
    # the dense DP; its estimate predicts the work from probe sweeps, and a trellis wider than the C tables does
    # not fit
    for build, d in ((dvs.rotated_surface, 7), (dvs.color_code, 9)):
        hx, hz, n = build(d)
        for sector in ("X", "Z"):
            p = stabcode.css_distance_problem(hx, hz, n, sector)
            order = auto.best_order(p)[0]
            assert auto.dp_distance(p, order)[0] == d
            trs = auto.sparse_trellises(p, order)
            est = auto.sparse_estimate(p, d - 1, order, trellises=trs)
            assert est["fits"] and est["predicted_work"] > 0 and est["predicted_seconds"] > 0
            assert len(est["schedule"]) == trs[0].N + 1 and set(est["probe_weights"]) <= {2, 3}
            # far beyond the caller's limits at weight 2: no probe at weight 3
            assert auto.sparse_estimate(p, d - 1, order, trellises=trs, max_seconds=1e-9)["probe_weights"] == [2, 2]
            assert auto.sparse_distance(p, d - 1, order, trellises=trs, schedule=est["schedule"]) is None
            for lower in (0, d):
                value, cols, obs = auto.sparse_distance(p, d + 1, order, trellises=trs, lower=lower)
                assert value == d and len(cols) == d and search.verify(p, tuple(cols))
    import random
    rng = random.Random(1)
    wide = problem.Problem("wide", 80, 1, [rng.getrandbits(80) | 1 for _ in range(160)],
                           [rng.getrandbits(1) for _ in range(160)], [(i, 0) for i in range(80)])
    est = auto.sparse_estimate(wide, 5, list(range(160)))
    assert est["fits"] is False and (est["slots"] is None or est["slots"] > auto.SPARSE_MAX_SLOTS)


def test_pipeline_option_dp2(tmp_path):
    # the pipeline with dp=2 on an exported surface-code circuit: the sparse DP closes the sector's gap with an
    # upper bound (window stage on: one sweep at u - 1) and without one (every stage off: deepening from 1)
    import json
    import subprocess
    sys.path.insert(0, os.path.join(ROOT, "bench"))
    import common
    import stim_families
    circ, _ = stim_families.surface_circuit(5)
    meta = {"family": "surface", "description": "test", "n": 25, "k": 1, "basis": "Z", "rounds": 5,
            "source": "stim_families.surface_circuit(5)", "truth": {"sector": (5, "exact", "graph-like distance")}}
    common.export_circuit_instance("surf5", circ, [], meta, root=str(tmp_path))
    adapter = os.path.join(ROOT, "bench", "adapters", "ours_pipeline.py")
    for config, sweeps in (("dp=2", None), ("dp=2,dp_head=0,collapse=0,lift=0,window=1", [4]),
                           ("dp=2,dp_head=0,collapse=0,lift=0,window=0", [1, 2, 3, 4, 5])):
        out = tmp_path / ("%s.json" % config.replace(",", "_").replace("=", "-"))
        subprocess.run([sys.executable, adapter, "--instance", str(tmp_path / "surf5"), "--variant", "sector",
                        "--time-limit", "120", "--threads", "1", "--out", str(out), "--config", config],
                       check=True, capture_output=True)
        r = json.loads(out.read_text())
        notes = json.loads(r["notes"])
        assert r["status"] == "exact" and r["lower_bound"] == r["upper_bound"] == 5 and r["witness_ok"], r
        if sweeps is not None:
            assert notes["sparse"]["decision"].startswith("sparse DP"), notes["sparse"]
            assert [x["K"] for x in notes["sparse"]["sweeps"]] == sweeps
    sys.path.insert(0, os.path.join(ROOT, "bench", "adapters"))
    import ours_pipeline
    for bad in ({"dp": 3}, {"dp_head": -2}):
        try:
            ours_pipeline.configuration(bad)
        except ValueError:
            continue
        raise AssertionError("accepted %s" % bad)
