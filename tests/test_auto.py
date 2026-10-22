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
