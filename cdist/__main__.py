"""Certified distance of a Stim circuit or of a pair of matrices, with the pipeline used in the paper.

    python -m cdist CIRCUIT.stim [--out RECORD.json] [--threads N] [--time-limit SECONDS] [--config KEY=VALUE,...]
    python -m cdist --matrices H.mtx L.mtx [same options]

Run from the repository root.  A circuit gives its undecomposed detector error model with equal mechanisms merged.
If it is a CSS memory experiment whose detectors carry coordinates (check, 0, round, type), as the circuits in
circuits/ and those built in papers/ do, the run also uses the sector of the memory basis, its time collapse and the
translations of the detector coordinates; otherwise it searches the full detector error model.  --matrices takes
the problem min |e| subject to He = 0 and Le != 0 as two MatrixMarket coordinate files with the same columns; for a
CSS code, H = H_X and L = L_X give the distance d_Z.

The run is bench/adapters/ours_pipeline.py with dp=2, the configuration of every reported benchmark run, on an
instance exported as the benchmark exports its own.  The record holds the certified lower and upper bounds, the log
of every threshold, and the fault set that attains the upper bound.  The default time limit 0 means none.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))


def export_circuit(path, directory):
    """Export as bench/instances.py exports the stored circuits; returns a note if only the full problem is used."""
    import stim
    import common
    import instances
    circ = stim.Circuit.from_file(path)
    root, name = os.path.split(directory)
    meta = {"family": "cli", "description": "python -m cdist", "source": os.path.abspath(path)}
    try:
        out = common.export_circuit_instance(name, circ, [], dict(meta), root=root)
    except Exception as exc:            # no coordinates of that form, or the sector is only a relaxation
        common.export_dem_instance(name, circ, dict(meta), root=root)
        return ("searching the full detector error model: no exact memory sector from detector coordinates "
                "(check, 0, round, type) [%s: %s]" % (type(exc).__name__, exc))
    for variant in out["variants"]:
        prob = common.to_cdist(common.load(directory, variant))
        out["variants"][variant].update(common.export_problem(directory, variant, prob, instances._lattice_perms(prob)))
    common.write_meta(directory, out)
    return None


def export_matrices(h_path, l_path, directory):
    import common
    nrows, ncols, h = common.read_mtx(h_path)
    nobs, ncols_l, l = common.read_mtx(l_path)
    if ncols != ncols_l:
        raise SystemExit("H has %d columns and L has %d" % (ncols, ncols_l))
    os.makedirs(directory)
    common.write_mtx(os.path.join(directory, "full.H.mtx"), h, nrows)
    common.write_mtx(os.path.join(directory, "full.L.mtx"), l, nobs)
    variant = {"rows": nrows, "cols": ncols, "obs": nobs, "symmetries": 0,
               "distance": None, "distance_kind": "unknown", "distance_source": None}
    common.write_meta(directory, {"name": os.path.basename(directory), "track": "code", "family": "cli",
                                  "description": "python -m cdist", "source": [os.path.abspath(h_path), os.path.abspath(l_path)],
                                  "variants": {"full": variant}})


def main():
    ap = argparse.ArgumentParser(prog="python -m cdist", description=__doc__.split("\n\n")[0])
    ap.add_argument("circuit", nargs="?", help="Stim circuit file")
    ap.add_argument("--matrices", nargs=2, metavar=("H.mtx", "L.mtx"), help="constraint and logical matrices instead of a circuit")
    ap.add_argument("--out", help="record file (default: NAME.distance.json in the current directory)")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--time-limit", type=float, default=0.0, help="seconds; 0 means no limit")
    ap.add_argument("--config", default="", help="settings of bench/adapters/ours_pipeline.py, e.g. kmax=20 (dp=2 unless given)")
    a = ap.parse_args()
    if (a.circuit is None) == (a.matrices is None):
        ap.error("give either a circuit file or --matrices H.mtx L.mtx")
    source = a.circuit or a.matrices[0]
    name = os.path.splitext(os.path.basename(source))[0]
    out = os.path.abspath(a.out or name + ".distance.json")
    config = a.config if "dp=" in a.config else ",".join(x for x in ("dp=2", a.config) if x)
    with tempfile.TemporaryDirectory(prefix="cdist_") as tmp:
        directory = os.path.join(tmp, name)
        if a.circuit:
            note = export_circuit(a.circuit, directory)
        else:
            note = None
            export_matrices(*a.matrices, directory)
        if note:
            print(note, flush=True)
        cmd = [sys.executable, os.path.join(ROOT, "bench", "adapters", "ours_pipeline.py"), "--instance", directory,
               "--variant", "full", "--threads", str(a.threads), "--time-limit", str(a.time_limit), "--config", config,
               "--out", out]
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL)
        if not os.path.exists(out):
            raise SystemExit("no record was written; run bench/adapters/ours_pipeline.py directly to see why")
        rec = json.load(open(out))
        if a.circuit and rec.get("witness"):
            # the fault set as physical faults in the noiseless circuit, as bench/replay_witnesses.py does for the records
            import replay_witnesses
            item = {k: rec.get(k) for k in ("status", "lower_bound", "upper_bound", "rows", "cols", "obs")}
            res = replay_witnesses.replay_instance(directory, [("full", rec["witness"], [dict(item, record=out)])], single=False)
            w = res["witnesses"][0]
            rec["replay"] = dict(w.get("replay", {}), result=w["result"], reasons=w.get("reasons", []))
            json.dump(rec, open(out, "w"), indent=1)
            print("fault set replayed in Stim: %s%s" % (w["result"], "".join("; " + r for r in w.get("reasons", []))))
    lower, upper = rec.get("lower_bound"), rec.get("upper_bound")
    if lower is not None and lower == upper:
        print("distance %d, certified (%s, %.1f s); record in %s" % (lower, rec.get("status"), rec.get("seconds", 0), out))
    else:
        print("distance between %s and %s (%s, %.1f s); record in %s" % (lower, upper, rec.get("status"), rec.get("seconds", 0), out))


if __name__ == "__main__":
    main()
