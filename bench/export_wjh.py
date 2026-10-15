"""Export the instances of the benchmark of arXiv:2603.22532 (Webster, Jacob, Higgott) into bench/instances_wjh.

Needs their codeDistance package checked out in papers/downloads/codedistance (github.com/m-webster/
codeDistancePYPI) and, for the codes, papers/downloads/codedistance_codes.json written by
papers/codedistance_export.py.  The registry entries are instances.WJH.  For every circuit the exported
sector problem is compared with their basis-filtered DEM (papers/downloads/codedistance/codedistance/
dem_detector_filtering.py); an instance whose column sets differ is not exported.

usage: python bench/export_wjh.py [--only a,b] [--jobs N] [--force]
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common
import instances

ROOT = Path(common.ROOT)
OUT = HERE / "instances_wjh"


def their_columns(circuit_file):
    """Distinct (detector set, observable set) columns of their filtered DEM, detectors renumbered."""
    sys.path.insert(0, str(ROOT / instances.WJH_REPO / "codedistance"))
    import stim
    from dem_detector_filtering import filter_by_det_basis_using_chromobius_coords
    dem = filter_by_det_basis_using_chromobius_coords(
        stim.Circuit.from_file(str(ROOT / circuit_file)).detector_error_model().flattened())
    cols = set()
    for inst in dem:
        if inst.type == "error":
            dets = frozenset(t.val for t in inst.targets_copy() if t.is_relative_detector_id())
            obs = frozenset(t.val for t in inst.targets_copy() if t.is_logical_observable_id())
            if dets or obs:
                cols.add((dets, obs))
    return cols


def ours_columns(directory):
    """Columns of the exported sector problem, its rows mapped back to detector indices: the sector keeps the
    detectors whose 4th coordinate is >= 3 (Z type), in index order (cdist.problem.sector_rows)."""
    import stim
    p = common.load(str(directory), "sector")
    coords = stim.Circuit.from_file(str(directory / "circuit.stim")).get_detector_coordinates()
    rows = [i for i in sorted(coords) if coords[i][3] >= 3]
    meta = json.loads((directory / "sector.rowmeta.json").read_text())
    if len(rows) != p.nrows or any(list(coords[i]) != list(m) for i, m in zip(rows, meta)):
        raise ValueError("sector rows are not the Z-type detectors in index order")
    return {(frozenset(rows[r] for r in common.bits(h)), frozenset(common.bits(l))) for h, l in zip(p.h, p.l)}


def done(name):
    path = OUT / name / "meta.json"
    if not path.is_file():
        return False
    meta = json.loads(path.read_text())
    return all((OUT / name / (v + ".H.mtx")).is_file() for v in meta["variants"])


def export(name):
    t = time.time()
    try:
        meta = instances.build(name, root=str(OUT))
        if meta["track"] == "circuit":
            same = their_columns(instances.WJH[name]["circuit_file"]) == ours_columns(OUT / name)
            meta["same_as_their_filtered_dem"] = same
            common.write_meta(str(OUT / name), meta)
            if not same:
                raise ValueError("sector problem differs from their filtered DEM")
        return name, "exported", {v: (x["rows"], x["cols"], x.get("symmetries", 0)) for v, x in meta["variants"].items()}, time.time() - t
    except Exception as exc:
        return name, "failed", "%s: %s" % (type(exc).__name__, exc), time.time() - t


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    names = a.only.split(",") if a.only else list(instances.WJH)
    todo = [n for n in names if a.force or not done(n)]
    bad = [n for n in todo if instances.WJH[n]["status"] != "ready"]
    for n in bad:
        print(n, "not ready:", instances.WJH[n].get("reason"), flush=True)
    todo = [n for n in todo if n not in bad]
    # largest last, so that the small ones are available early
    todo.sort(key=lambda n: (instances.WJH[n]["track"] == "circuit", instances.WJH[n].get("n") or 0))
    OUT.mkdir(exist_ok=True)
    with ProcessPoolExecutor(a.jobs) as pool:
        for name, status, info, seconds in pool.map(export, todo):
            print("%s %s %s %.1fs" % (name, status, info, seconds), flush=True)


if __name__ == "__main__":
    main()
