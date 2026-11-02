"""Combined certificates of the runs outside the benchmark.  A run started at a threshold (option kmin) proves its lower bound only together with
the run that excluded the lighter thresholds, on the same problem; the upper bound is an explicit error in another record.  This script checks that the
records of each instance chain without a gap and writes certificates.json.  Records that are not here yet are skipped, so an instance can stay open.
Usage: python combine_certificates.py"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
D = "ours_pipeline__dp-2"
INSTANCES = {
    "Tanner [[288,2]] Z": [D + "/wjh_qt_288_2_24__full__t32.json"],
    "Tanner [[324,4]] Z": [D + "/wjh_qt_324_4_25__full__t32.json"],
    "Tanner [[360,4]] Z": [D + "/wjh_qt_360_4_24__full__t32.json"],
    "Tanner [[396,4]] Z": [D + "/wjh_qt_396_4_26__full__t32.json", D + "__kmin-26__kmax-26/wjh_qt_396_4_26__full__t89.json", "isd__stop%5Fat-27/wjh_qt_396_4_26__full__t16.json"],
    "Tanner [[288,2]] X": ["tanner_x/wjh_qt_288_2_24_Xdist__full__t12.json", "tanner_x/wjh_qt_288_2_24_Xdist_isd.json"],
    "Tanner [[324,4]] X": ["tanner_x/wjh_qt_324_4_25_Xdist__full__t12.json", "tanner_x/wjh_qt_324_4_25_Xdist_kmin24.json", "tanner_x/wjh_qt_324_4_25_Xdist_isd.json"],
    "Tanner [[360,4]] X": ["tanner_x/wjh_qt_360_4_24_Xdist_kmax23.json", "tanner_x/wjh_qt_360_4_24_Xdist_isd.json"],
    "Tanner [[396,4]] X": ["tanner_x/wjh_qt_396_4_26_Xdist_kmax25.json", "tanner_x/wjh_qt_396_4_26_Xdist_isd.json"],
    "BB [[648,4]]": [D + "/wjh_bb_n648__full__t32.json", D + "__kmin-31__kmax-31/wjh_bb_n648__full__t57.json", "isd__stop%5Fat-32/wjh_bb_n648__full__t16.json"],
    "BB [[756,16]]": [D + "__kmax-32/wjh_bb_n756__full__t57.json", D + "__kmin-33__kmax-33/wjh_bb_n756__full__t134.json", "isd/wjh_bb_n756__full__t16.json"],
    "many-hypercube L = 4": [D + "/hypercube_L4__full__t32.json"],
}


def combine(paths):
    recs = [(p, json.load(open(os.path.join(HERE, p)))) for p in paths if os.path.exists(os.path.join(HERE, p))]
    searches = [(p, r) for p, r in recs if r["lower_bound"] is not None]
    shape = {(r["instance"].replace("_Xdist", ""), r["rows"], r["cols"], r["obs"]) for _, r in searches}
    assert len(shape) <= 1, shape
    covered, used = 1, []
    for p, r in sorted(searches, key=lambda x: x[1]["config"].get("kmin", 1)):
        kmin = r["config"].get("kmin", 1)
        assert kmin <= covered, ("gap", p, kmin, covered)      # every threshold below kmin is excluded by an earlier record
        covered = max(covered, r["lower_bound"])
        used.append({"record": p, "kmin": kmin, "lower_bound": r["lower_bound"], "status": r["status"], "threads": r["threads"], "seconds": r["seconds"]})
    witness = [(r["upper_bound"], p) for p, r in recs if r["upper_bound"] is not None and r["witness_ok"]]
    ub, wp = min(witness) if witness else (None, None)
    return {"lower_bound": covered, "upper_bound": ub, "closed": covered == ub, "lower_bound_records": used, "witness_record": wp, "records_missing": [p for p in paths if not os.path.exists(os.path.join(HERE, p))]}


out = {k: combine(v) for k, v in INSTANCES.items()}
# mitten 300: the 3-round fault set replayed in the 6-round circuit (scripts/mitten_transfer_check.py)
m = json.load(open(HERE + "/transfer/mitten_300__sector.json"))
r = json.load(open(HERE + "/" + D + "/mitten_300__sector__t32.json"))
out["mitten [[300,60,14]] circuit"] = {"lower_bound": r["lower_bound"], "upper_bound": m.get("weight", m.get("upper_bound")), "closed": r["lower_bound"] == m.get("weight", m.get("upper_bound")),
                                       "lower_bound_records": [{"record": D + "/mitten_300__sector__t32.json", "kmin": 1, "lower_bound": r["lower_bound"], "status": r["status"], "threads": r["threads"], "seconds": r["seconds"]}],
                                       "witness_record": "transfer/mitten_300__sector.json", "records_missing": []}
json.dump(out, open(HERE + "/certificates.json", "w"), indent=1)
for k, v in out.items():
    print(k.ljust(30), v["lower_bound"], v["upper_bound"], "closed" if v["closed"] else "open", "; missing " + ", ".join(os.path.basename(x) for x in v["records_missing"]) if v["records_missing"] else "")
