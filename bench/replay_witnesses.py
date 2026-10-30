"""Replay the circuit witnesses of the pipeline's benchmark records in Stim.

The Methods say that every reported circuit error is inserted into the noiseless Stim circuit and simulated: no
detector fires and an observable flips.  bench/adapters/ours_pipeline.py checks its witnesses only against the exported
matrices (common.check_witness).  This script replays every witness of the pipeline's circuit records physically,
which also checks how the circuits were turned into matrices.

Column -> physical fault.  A column of a circuit variant is one merged mechanism of the undecomposed detector error
model (cdist.problem.load_dem_problem).
  full     row i is detector i of circuit.stim (checked against the detector coordinates), so the column's detectors
           are its rows and its observables the rows of L where it has a one;
  sector   the rows are matched to detectors through the row metadata, in order (sector.rowmeta.json against
           full.rowmeta.json), and the column becomes the full column with exactly that embedded syndrome: the
           full-model mechanism that fires no detector outside the sector.  It exists because the reduction is exact,
           and it is the column the adapter reports for the variant full (Pipeline.prepare).
A filter detector error model with one error per column goes to Circuit.explain_detector_error_model_errors(
dem_filter=..., reduce_to_one_representative_error=True), which returns one representative circuit fault per column.
The set is replayed with cdist.replay.replay: the faults become explicit Pauli gates (or measurement-record flips) in
the noiseless circuit, which is simulated.

A witness passes if
  - the regenerated variant has the record's dimensions, and the witness passes common.check_witness at its weight;
  - every column has a circuit fault with exactly its detectors and observables, and that fault replayed alone fires
    exactly those (skipped with --no-single);
  - the whole set replayed fires no detector and flips a nonempty set of observables, the set the matrix predicts.
Witnesses of records that did not finish (status timeout: upper bounds) are replayed too and counted apart.

Instance files are regenerated with bench/export_all.py, bench/export_wjh.py and bench/make_fixtures.py (only meta.json
is tracked).  --reference (default results/bench_replay/server_inputs.json: sha256 and modification time of the
instance files on the machine where the records ran) ties the regenerated files to the records: a witness has
same_inputs_as_records if the files it needs are byte-identical to those and were last modified before every run.

Writes results/bench_replay/<instance>.json, one per instance: its files' sha256, every distinct witness with the
records that report it, each column's fault and the replays.  results/bench_replay/summary.json and README.md count
pass, fail and skipped per record, with the reason of each skip; they are rebuilt from the instance files, so instances
may be replayed in several runs (--only) and the summary alone with --summary.

usage: python bench/replay_witnesses.py [--records GLOB ...] [--only a,b] [--jobs N] [--no-single] [--summary]
                                        [--reference FILE]
"""
import argparse
import glob
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common

ROOT = common.ROOT
RECORDS = ("results/bench/ours_pipeline__dp-2", "results/bench_tierB/ours_pipeline__dp-2",
           "results/bench_wjh*/ours_pipeline*", "results/bench_extended/ours_pipeline*")
OUT = os.path.join(ROOT, "results", "bench_replay")
REFERENCE = os.path.join(OUT, "server_inputs.json")
FULL_FILES = ("circuit.stim", "full.H.mtx", "full.L.mtx", "full.rowmeta.json")
SECTOR_FILES = ("sector.H.mtx", "sector.L.mtx", "sector.rowmeta.json")
FILES = FULL_FILES + SECTOR_FILES
RESULTS = ("pass", "fail", "skipped")


def shown(path):
    """A path from its repository root (records may come from another checkout)."""
    path = os.path.abspath(path)
    if path.startswith(ROOT + os.sep):
        return os.path.relpath(path, ROOT)
    i = path.rfind(os.sep + "results" + os.sep)
    return path[i + 1:] if i >= 0 else path


def find_records(patterns):
    out = []
    for pattern in patterns:
        for d in sorted(glob.glob(pattern if os.path.isabs(pattern) else os.path.join(ROOT, pattern))):
            for path in sorted(glob.glob(os.path.join(d, "*.json"))):
                with open(path) as f:
                    rec = json.load(f)
                if isinstance(rec, dict) and rec.get("method") == "ours_pipeline":
                    out.append((path, rec))
    return out


def instance_dir(rec):
    """bench/<instances folder>/<name>: the harness records the server's path of the instance."""
    d = ((rec.get("harness") or {}).get("instance_dir") or "").rstrip("/")
    cands = [os.path.join(HERE, os.path.basename(os.path.dirname(d)), os.path.basename(d))] if d else []
    cands += sorted(glob.glob(os.path.join(HERE, "instances*", rec["instance"])))
    return next((c for c in cands if os.path.basename(c) == rec["instance"]
                 and os.path.isfile(os.path.join(c, "meta.json"))), None)


def scope(path, rec):
    """(instance directory, None) for a record whose witness is replayed, else (directory, (result, reason))."""
    d = instance_dir(rec)
    if d is None:
        return None, ("skipped", "no instance directory with a meta.json")
    with open(os.path.join(d, "meta.json")) as f:
        meta = json.load(f)
    if meta["track"] != "circuit":
        return d, ("not circuit", "code-capacity instance")
    if rec["variant"] not in ("full", "sector"):
        return d, ("not circuit", "variant %s is a relaxation: its solutions are not fault sets" % rec["variant"])
    if not rec.get("witness"):
        if rec["status"] == "exact":
            return d, ("skipped", "exact record without a witness")
        return d, ("no witness", "status %s, no fault set found" % rec["status"])
    return d, None


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def unsupported(circuit):
    """Noisy instructions that cdist.replay would not strip from the noiseless circuit."""
    import stim
    from cdist import replay
    out = set()

    def walk(c):
        for inst in c:
            if isinstance(inst, stim.CircuitRepeatBlock):
                walk(inst.body_copy())
            elif (inst.gate_args_copy() and stim.gate_data(inst.name).is_noisy_gate
                  and inst.name not in replay.NOISE and inst.name not in replay.MEASURE):
                out.add(inst.name)
    walk(circuit)
    return sorted(out)


def fault(e):
    """The representative circuit fault of an explained DEM error, as cdist.replay.physical_faults writes it."""
    loc = e.circuit_error_locations[0]
    return {"tick": loc.tick_offset,
            "instruction": loc.instruction_targets.gate,
            "paulis": [(t.gate_target.pauli_type, t.gate_target.value) for t in loc.flipped_pauli_product],
            "stack": [(f.instruction_offset, f.iteration_index, f.instruction_repetitions_arg)
                      for f in loc.stack_frames],
            "flipped_measurement": (None if loc.flipped_measurement is None
                                    else loc.flipped_measurement.record_index),
            "dem_terms": [str(t) for t in e.dem_error_terms]}


def symptoms(e):
    dets = sorted(t.dem_target.val for t in e.dem_error_terms if t.dem_target.is_relative_detector_id())
    obs = sorted(t.dem_target.val for t in e.dem_error_terms if t.dem_target.is_logical_observable_id())
    return tuple(dets), tuple(obs)


def replay_instance(directory, items, single=True):
    """items: [(variant, witness, records)], records = [{record, status, lower_bound, upper_bound, rows, cols, obs}].
    Returns the instance record (results/bench_replay/<instance>.json)."""
    import stim
    from cdist import problem, replay
    t0 = time.time()
    with open(os.path.join(directory, "meta.json")) as f:
        meta = json.load(f)
    out = {"instance": meta["name"], "instance_dir": shown(directory), "stim": stim.__version__,
           "files": {name: sha256(os.path.join(directory, name)) for name in FILES
                     if os.path.isfile(os.path.join(directory, name))},
           "witnesses": []}
    entries = [{"variant": v, "witness": list(w), "weight": len(w), "records": recs} for v, w, recs in items]
    out["witnesses"] = entries

    def skip_all(reason):
        for e in entries:
            e.update(result="skipped", reasons=[reason])
        out["seconds"] = round(time.time() - t0, 3)
        return out

    needed = set(FULL_FILES)
    if any(e["variant"] == "sector" for e in entries):
        needed |= set(SECTOR_FILES)
    missing = sorted(needed - set(out["files"]))
    if missing:
        return skip_all("instance files not exported: " + ", ".join(missing))
    circuit = stim.Circuit.from_file(os.path.join(directory, "circuit.stim"))
    bad = unsupported(circuit)
    if bad:
        return skip_all("noisy instructions that cdist.replay does not handle: " + ", ".join(bad))
    full = common.load(directory, "full")
    coords = circuit.get_detector_coordinates()
    if (full.nrows != circuit.num_detectors or full.nobs != circuit.num_observables
            or any(list(coords.get(i, ())) != list(m) for i, m in enumerate(full.rowmeta))):
        return skip_all("rows of the full variant are not the detectors of circuit.stim in index order")
    probs = {"full": full}
    rows = None
    if "sector.H.mtx" in needed:
        sector = probs["sector"] = common.load(directory, "sector")
        # The sector keeps the detectors of one type in index order, chosen by their metadata (cdist.problem.
        # sector_rows), so matching the metadata in order finds them even where coordinates repeat (the final
        # detectors of the superdense colour-code circuits share the coordinates of the last round's).
        rows, i = [], 0
        for m in sector.rowmeta:
            while i < full.nrows and full.rowmeta[i] != m:
                i += 1
            if i == full.nrows:
                return skip_all("sector rows do not match detectors in order through the row metadata")
            rows.append(i)
            i += 1
        source = meta.get("source")
        try:
            high = source.get("sector_high") if isinstance(source, dict) else None
            out["sector_rows_as_exported"] = rows == problem.sector_rows(common.to_cdist(full), high)
        except AssertionError:
            out["sector_rows_as_exported"] = None
        if out["sector_rows_as_exported"] is False:
            return skip_all("rows matched through the metadata differ from cdist.problem.sector_rows")
        full_column = {(a, b): j for j, (a, b) in enumerate(zip(full.h, full.l))}

    # every witness column as (full column, detectors, observables)
    columns = {}
    for e in entries:
        p = probs[e["variant"]]
        reasons = []
        dims = [(r["rows"], r["cols"], r["obs"]) for r in e["records"]]
        if any(x != (p.nrows, p.ncols, p.nobs) for x in dims):
            reasons.append("regenerated %s is %dx%d with %d observables, the record's %s"
                           % (e["variant"], p.nrows, p.ncols, p.nobs, sorted(set(dims))))
        elif max(e["witness"]) >= p.ncols:
            reasons.append("witness column beyond the regenerated matrix")
        else:
            chk = common.check_witness(p, e["witness"])
            e["check_witness"] = chk
            if not chk["ok"] or any(r["upper_bound"] != chk["weight"] for r in e["records"]):
                reasons.append("witness fails common.check_witness on the regenerated matrices: %s" % chk)
        if reasons:
            e.update(result="skipped", reasons=reasons)
            continue
        cols = []
        for j in e["witness"]:
            if e["variant"] == "full":
                fj, a, b = j, full.h[j], full.l[j]
            else:
                a = sum(1 << rows[r] for r in common.bits(sector.h[j]))
                b = sector.l[j]
                fj = full_column.get((a, b))
            key = (tuple(common.bits(a)), tuple(common.bits(b)))
            cols.append({"column": j, "full_column": fj, "detectors": list(key[0]), "observables": list(key[1])})
            columns.setdefault(key, None)
        e["columns"] = cols

    # one representative fault per distinct column, from one pass of Stim over the circuit
    t = time.time()
    flt = stim.DetectorErrorModel()
    for dets, obs in columns:
        flt.append("error", 0.5, [stim.target_relative_detector_id(d) for d in dets]
                   + [stim.target_logical_observable_id(o) for o in obs])
    found = {}
    explained = circuit.explain_detector_error_model_errors(dem_filter=flt, reduce_to_one_representative_error=True) \
        if columns else []
    for ex in explained:
        found.setdefault(symptoms(ex), []).append(fault(ex))
    out["explain_seconds"] = round(time.time() - t, 3)

    t = time.time()
    alone = {}
    for e in entries:
        if e.get("result") == "skipped":
            continue
        reasons, faults, lg = [], [], 0
        for c in e["columns"]:
            key = (tuple(c["detectors"]), tuple(c["observables"]))
            for o in c["observables"]:
                lg ^= 1 << o
            if c["full_column"] is None:
                reasons.append("sector column %d: no full column fires exactly its detectors" % c["column"])
            hits = found.get(key, [])
            if len(hits) != 1:
                reasons.append("column %d: %d circuit faults with exactly its detectors and observables"
                               % (c["column"], len(hits)))
                continue
            c["fault"] = hits[0]
            faults.append(hits[0])
            if single:
                if key not in alone:
                    d, o = replay.replay(circuit, [hits[0]])
                    alone[key] = (tuple(d), tuple(o))
                c["alone"] = {"detectors": list(alone[key][0]), "observables": list(alone[key][1])}
                if alone[key] != key:
                    reasons.append("column %d: its fault replayed alone fires detectors %s and flips %s"
                                   % (c["column"], list(alone[key][0]), list(alone[key][1])))
        e["predicted_observables"] = common.bits(lg)
        if len(faults) == len(e["columns"]):
            d, o = replay.replay(circuit, faults)
            e["replay"] = {"fired_detectors": d, "flipped_observables": o}
            if d:
                reasons.append("replay fires %d detectors" % len(d))
            if not o:
                reasons.append("replay flips no observable")
            elif o != e["predicted_observables"]:
                reasons.append("replay flips observables %s, the matrix predicts %s" % (o, e["predicted_observables"]))
        e.update(result="fail" if reasons else "pass", reasons=reasons)
    out["replay_seconds"] = round(time.time() - t, 3)
    out["seconds"] = round(time.time() - t0, 3)
    return out


def instance_file(name):
    return os.path.join(OUT, name + ".json")


def compare(res, reference):
    """Are the regenerated files byte for byte those the records ran on (reference: sha256 and modification time of
    the files on the machine of the runs, results/bench_replay/server_inputs.json), and are those older than each
    run?  Then the witness was replayed on the record's own matrices."""
    from datetime import datetime
    folder = res["instance_dir"].split("/", 1)[1]           # instances/<name> or instances_wjh/<name>
    ref = {name: reference["files"].get(folder + "/" + name) for name in res["files"]}
    files = {name: "absent" if r is None else "identical" if r["sha256"] == res["files"][name] else "different"
             for name, r in ref.items()}
    res["reference"] = {"host": reference["host"], "directory": reference["directory"], "files": files,
                        "mtime": {name: r["mtime"] for name, r in ref.items() if r is not None}}
    for e in res["witnesses"]:
        # a run on the variant full reads no sector file (the adapter derives the sector itself)
        names = FULL_FILES + (SECTOR_FILES if e["variant"] == "sector" else ())
        if not all(files.get(n) == "identical" for n in names):
            e["same_inputs_as_records"] = False
            continue
        latest = max(datetime.fromisoformat(ref[n]["mtime"]) for n in names)
        e["same_inputs_as_records"] = all(r.get("started_at") and datetime.fromisoformat(r["started_at"]) > latest
                                          for r in e["records"])


def summarize(scoped, patterns):
    """Per-record outcomes from the instance files; writes summary.json and README.md."""
    rows = []
    cache = {}
    witnesses = {}            # distinct (instance directory, variant, witness) -> its line of the witness table
    for path, rec, d, verdict in scoped:
        row = {"record": shown(path), "directory": shown(os.path.dirname(os.path.abspath(path))),
               "instance": rec["instance"], "variant": rec["variant"], "status": rec["status"],
               "lower_bound": rec.get("lower_bound"), "upper_bound": rec.get("upper_bound"),
               "weight": len(rec.get("witness") or ())}
        if verdict is not None:
            row["result"], row["reason"] = verdict
        else:
            name = os.path.basename(d)
            if name not in cache:
                f = instance_file(name)
                cache[name] = json.load(open(f)) if os.path.isfile(f) else None
            inst = cache[name]
            entry = None if inst is None else next(
                (e for e in inst["witnesses"] if e["variant"] == rec["variant"] and e["witness"] == rec["witness"]), None)
            if entry is None:
                row["result"], row["reason"] = "skipped", "not replayed yet (no entry in results/bench_replay/%s.json)" % name
            else:
                row["result"] = entry["result"]
                row["reason"] = "; ".join(entry.get("reasons", ()))
                row["same_inputs_as_records"] = entry.get("same_inputs_as_records")
                if "replay" in entry:
                    row["fired_detectors"] = len(entry["replay"]["fired_detectors"])
                    row["flipped_observables"] = entry["replay"]["flipped_observables"]
            w = witnesses.setdefault((d, rec["variant"], tuple(rec["witness"])), {
                "instance": rec["instance"], "variant": rec["variant"], "weight": row["weight"],
                "result": row["result"], "fired_detectors": row.get("fired_detectors"),
                "flipped_observables": row.get("flipped_observables"),
                "same_inputs_as_records": row.get("same_inputs_as_records"), "records": []})
            w["records"].append(row["record"])
        rows.append(row)

    def count(results):
        c = {k: 0 for k in RESULTS}
        for x in results:
            c[x] += 1
        return c
    exact = [r for r in rows if r["status"] == "exact" and r["result"] in RESULTS]
    other = [r for r in rows if r["status"] != "exact" and r["result"] in RESULTS]
    summary = {
        "generated_by": "bench/replay_witnesses.py",
        "record_patterns": list(patterns),
        "record_directories": sorted({r["directory"] for r in rows}),
        "records": len(rows),
        "exact_circuit_records": count(r["result"] for r in exact),
        "unfinished_circuit_records_with_witness": count(r["result"] for r in other),
        "circuit_records_without_witness": sum(r["result"] == "no witness" for r in rows),
        "not_circuit_records": sum(r["result"] == "not circuit" for r in rows),
        "distinct_witnesses": count(w["result"] for w in witnesses.values()),
        "passed_on_the_records_own_inputs": sum(r["result"] == "pass" and bool(r.get("same_inputs_as_records"))
                                                for r in exact + other),
        "skipped": [{k: r[k] for k in ("record", "status", "reason")} for r in rows if r["result"] == "skipped"],
        "failed": [{k: r[k] for k in ("record", "status", "reason")} for r in rows if r["result"] == "fail"],
        "witnesses": sorted(witnesses.values(), key=lambda w: (w["instance"], w["variant"], w["weight"])),
        "per_record": rows,
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    with open(os.path.join(OUT, "README.md"), "w") as f:
        f.write(readme(summary))
    return summary


def readme(s):
    lines = ["# Replay of the pipeline's circuit witnesses", "",
             "Generated by `bench/replay_witnesses.py` (see its docstring for the method); do not edit.", "",
             "Every witness column of the exported variant is mapped to one physical circuit fault (a representative "
             "from Stim's `explain_detector_error_model_errors`), and the fault set is simulated in the noiseless "
             "circuit with `cdist.replay.replay`.  A witness passes when no detector fires and the observables the "
             "matrix predicts flip (a nonempty set), and each fault replayed alone fires exactly its column.", "",
             "| records | pass | fail | skipped |", "|---|---|---|---|"]
    for label, key in (("exact circuit records", "exact_circuit_records"),
                       ("unfinished circuit records with a witness (upper bounds)", "unfinished_circuit_records_with_witness"),
                       ("distinct witnesses (instance, variant, fault set)", "distinct_witnesses")):
        c = s[key]
        lines.append("| %s | %d | %d | %d |" % (label, c["pass"], c["fail"], c["skipped"]))
    lines += ["", "Not replayed: %d circuit records without a witness (timeouts, errors), %d records of code-capacity "
              "instances or relaxed variants." % (s["circuit_records_without_witness"], s["not_circuit_records"]), "",
              "Inputs: the instance files are regenerated by the exporters.  %d of the passing records were replayed on "
              "files byte-identical to those on the machine of their run, last modified before the run started "
              "(`server_inputs.json`; per witness `same_inputs_as_records`)." % s["passed_on_the_records_own_inputs"], ""]
    by_dir = {}
    for r in s["per_record"]:
        by_dir.setdefault(shown(r["directory"]), []).append(r)
    lines += ["## Per record directory", "", "| directory | exact: pass / fail / skipped | unfinished: pass / fail / skipped |"
              " no witness | not circuit |", "|---|---|---|---|---|"]
    for d, rs in sorted(by_dir.items()):
        cell = []
        for sel in ([r for r in rs if r["status"] == "exact"], [r for r in rs if r["status"] != "exact"]):
            cell.append(" / ".join(str(sum(r["result"] == k for r in sel)) for k in RESULTS))
        lines.append("| %s | %s | %s | %d | %d |" % (d, cell[0], cell[1], sum(r["result"] == "no witness" for r in rs),
                                                  sum(r["result"] == "not circuit" for r in rs)))
    for title, key in (("Failures", "failed"), ("Skipped", "skipped")):
        lines += ["", "## " + title, ""]
        if not s[key]:
            lines.append("None.")
        for r in s[key]:
            lines.append("- `%s` (%s): %s" % (r["record"], r["status"], r["reason"]))
    lines += ["", "## Witnesses", "",
              "Each distinct fault set once; records: how many records report it; same inputs: replayed on the files of "
              "the records' runs (see above).", "",
              "| instance | variant | weight | fired detectors | flipped observables | records | same inputs | result |",
              "|---|---|---|---|---|---|---|---|"]
    for w in s["witnesses"]:
        obs = w["flipped_observables"]
        lines.append("| %s | %s | %d | %s | %s | %d | %s | %s |" % (
            w["instance"], w["variant"], w["weight"], "–" if w["fired_detectors"] is None else w["fired_detectors"],
            "–" if obs is None else ", ".join(map(str, obs)) if len(obs) <= 6 else "%d observables" % len(obs),
            len(w["records"]), {True: "yes", False: "no"}.get(w["same_inputs_as_records"], "–"), w["result"]))
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--records", nargs="+", default=list(RECORDS),
                    help="record directories (globs, relative to the repository root unless absolute)")
    ap.add_argument("--only", help="comma-separated instance names to replay (the summary covers all records)")
    ap.add_argument("--jobs", type=int, default=1, help="instances replayed in parallel")
    ap.add_argument("--no-single", action="store_true", help="do not replay each fault alone")
    ap.add_argument("--summary", action="store_true", help="only rebuild summary.json and README.md")
    ap.add_argument("--reference", default=REFERENCE,
                    help="sha256 and modification times of the instance files the records ran on (see compare)")
    a = ap.parse_args()
    scoped = [(path, rec) + scope(path, rec) for path, rec in find_records(a.records)]
    groups = {}
    for path, rec, d, verdict in scoped:
        if verdict is None:
            items = groups.setdefault(d, {})
            key = (rec["variant"], tuple(rec["witness"]))
            items.setdefault(key, []).append({k: rec.get(k) for k in ("status", "lower_bound", "upper_bound",
                                                                       "rows", "cols", "obs")})
            items[key][-1].update(record=shown(path), started_at=(rec.get("harness") or {}).get("started_at"))
    only = set(a.only.split(",")) if a.only else None
    todo = [(d, [(v, w, recs) for (v, w), recs in sorted(items.items())]) for d, items in groups.items()
            if only is None or os.path.basename(d) in only]
    # small instances first: their results are available early
    todo.sort(key=lambda x: sum(os.path.getsize(os.path.join(x[0], f)) for f in FILES
                                if os.path.isfile(os.path.join(x[0], f))))
    reference = None
    if a.reference and os.path.isfile(a.reference):
        with open(a.reference) as f:
            reference = json.load(f)
    if not a.summary:
        os.makedirs(OUT, exist_ok=True)
        with ProcessPoolExecutor(max(1, a.jobs)) as pool:
            futures = [(d, pool.submit(replay_instance, d, items, not a.no_single)) for d, items in todo]
            for d, fut in futures:
                res = fut.result()
                if reference is not None:
                    compare(res, reference)
                with open(instance_file(res["instance"]) + ".tmp", "w") as f:
                    json.dump(res, f, indent=1)
                os.replace(instance_file(res["instance"]) + ".tmp", instance_file(res["instance"]))
                print("%-26s %6.1fs  %s" % (res["instance"], res["seconds"], "  ".join(
                    "%s w%d %s" % (e["variant"], e["weight"], e["result"]) for e in res["witnesses"])), flush=True)
    s = summarize(scoped, a.records)
    print(json.dumps({k: s[k] for k in ("exact_circuit_records", "unfinished_circuit_records_with_witness",
                                        "distinct_witnesses", "circuit_records_without_witness",
                                        "not_circuit_records")}))
    for r in s["failed"] + s["skipped"]:
        print("%s: %s (%s)" % (r["record"], r["reason"], r["status"]))
    return 1 if s["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
