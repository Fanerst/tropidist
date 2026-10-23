"""Ground truth of the main-suite instances added for the Rank DP evaluators (bench/instances.py, DP_TRUTH), read
from the records that certify them.  Every exact value needs a finished record with a checked witness; where a
value rests on a theorem (the concatenation bound of the many-hypercube code) the record supplies the witness.

  color_cc_d19..31, concat_steane_L3/L4   dense DP records of the low-width trial (results/bench_lowwidth)
  hypercube_L4                            d >= 2^L by concatenation ([[6,4,2]] has distance 2 on every level), and a
                                          weight-16 logical found by BP+OSD in the trial
  dtc_w*_*  (arXiv:2606.19482 Table III)  dense DP and, independently, the search alone (results/planar_dp); the
                                          [[537,14]] strip only has bounds: the search's lower bound, ISD's witness
  superdense_d7/d9/d11                    the pipeline's records on arXiv:2603.22532 and the sparse-DP certificate

usage: python scripts/dp_friendly_truth.py      -> results/dp_friendly_truth.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "dp_friendly_truth.json"


def load(path):
    return json.loads((ROOT / path).read_text())


def exact(path):
    r = load(path)
    assert r["status"] == "exact" and r["witness_ok"] is True and r["lower_bound"] == r["upper_bound"], path
    return r["lower_bound"]


def bound(path, key):
    r = load(path)
    if key == "upper_bound":
        assert r.get("witness_ok") is True, path
    return r[key]


def entry(n, k, description, lower, upper, sources):
    return dict(n=n, k=k, description=description, certified_lower_bound=lower, certified_upper_bound=upper,
                sources=sources)


def main():
    out = {}
    lw = "results/bench_lowwidth/ours_pipeline__dp-1/%s__full__t1.json"
    for d in (19, 23, 27, 31):
        name = "color_cc_d%d" % d
        meta = load("bench/instances_lowwidth/%s/meta.json" % name)
        v = exact(lw % name)
        assert v == d
        out[name] = entry(meta["n"], meta["k"], meta["description"], v, v, [lw % name])
    for L in (3, 4):
        name = "concat_steane_L%d" % L
        meta = load("bench/instances_lowwidth/%s/meta.json" % name)
        v = exact(lw % name)
        assert v == 3 ** L
        out[name] = entry(meta["n"], meta["k"], meta["description"], v, v, [lw % name])
    meta = load("bench/instances_lowwidth/hypercube_L4/meta.json")
    witness = "results/bench_lowwidth/bposd/hypercube_L4__full__t1.json"
    assert bound(witness, "upper_bound") == 16
    out["hypercube_L4"] = entry(meta["n"], meta["k"], meta["description"], 16, 16,
                                ["concatenation bound: a logical of level L is a logical of some level-L [[6,4,2]] "
                                 "code, so it acts on at least two level-(L-1) blocks, each with weight >= 2^(L-1)",
                                 witness])
    dp, srch = "results/planar_dp/code_dp1/%s_Z__t32.json", "results/planar_dp/code_dp0/%s_Z__t32.json"
    for name, paper in (("dtc_w5_259_2_4", 37), ("dtc_w7_269_4_5", 28), ("dtc_w9_365_10_4", 31)):
        meta = load("results/planar_dp/instances/%s_Z/meta.json" % name)
        v = exact(dp % name)
        assert v == exact(srch % name)                          # the search alone reaches the same value
        out[name] = entry(meta["n"], meta["k"], "directional tile code of arXiv:2606.19482 Table III, X distance "
                          "(paper: <= %d, a QDistRnd upper bound)" % paper, v, v, [dp % name, srch % name])
    name = "dtc_w11_537_14_12"
    meta = load("results/planar_dp/instances/%s_Z/meta.json" % name)
    isd = "results/planar_dp/isd/%s_Z__t4.json" % name
    out[name] = entry(meta["n"], meta["k"], "directional tile code of arXiv:2606.19482 Table III, X distance "
                      "(paper: <= 35, a QDistRnd upper bound)", bound(srch % name, "lower_bound"),
                      bound(isd, "upper_bound"), [srch % name, isd])
    for d in (7, 9):
        rec = "results/bench_wjh/ours_pipeline/wjh_superdense_d%d__sector__t1.json" % d
        v = exact(rec)
        assert v == d
        out["superdense_d%d" % d] = entry(None, 1, "superdense color-code memory circuit of arXiv:2603.22532, "
                                          "memory-basis sector", v, v, [rec])
    cert = "results/sparse_dp/wjh_superdense_d11.json"
    c = load(cert)
    assert c["certified_lower_bound"] == c["certified_upper_bound"] == 11
    out["superdense_d11"] = entry(None, 1, "superdense color-code memory circuit of arXiv:2603.22532, memory-basis "
                                  "sector", 11, 11, [cert])
    OUT.write_text(json.dumps({"note": __doc__.split("\n\n")[0].replace("\n", " "), "instances": out}, indent=1)
                   + "\n")
    for name, e in out.items():
        print("%-20s %s..%s" % (name, e["certified_lower_bound"], e["certified_upper_bound"]))
    print(OUT)


if __name__ == "__main__":
    main()
