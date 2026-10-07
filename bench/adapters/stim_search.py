"""Stim's circuit searches as an upper-bound heuristic.

config: ladder=2:2:1;3:3:1;4:4:1;4:6:1;4:10:1;4:10:0,
graphlike=1. Each ladder entry is the maximum intermediate detector-set size,
maximum error degree, and whether to forbid increases in symptom degree.
The undecomposed DEM must be graphlike for the optional graphlike shortcut.
Searches run in killable subprocesses; Stim itself does not expose a thread
setting, so --threads is recorded but ignored.
"""
from __future__ import annotations

import multiprocessing
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common


DEFAULT_LADDER = "2:2:1;3:3:1;4:4:1;4:6:1;4:10:1;4:10:0"


def dem_error_signature(error_or_targets, row_map=None):
    """Return the XOR (detectors, observables) signature of a DEM error.

    Accepts a DemInstruction, an ExplainedError, or a sequence of DemTargets
    (including DemTargetWithCoords). An optional detector-id -> variant-row
    mapping projects detectors; omitted detector ids are dropped.
    """
    if hasattr(error_or_targets, "dem_error_terms"):
        targets = error_or_targets.dem_error_terms
    elif hasattr(error_or_targets, "targets_copy"):
        targets = error_or_targets.targets_copy()
    else:
        targets = error_or_targets
    h = l = 0
    for target in targets:
        target = getattr(target, "dem_target", target)
        if target.is_relative_detector_id():
            row = target.val if row_map is None else row_map.get(target.val)
            if row is not None:
                h ^= 1 << row
        elif target.is_logical_observable_id():
            l ^= 1 << target.val
    return h, l


def build_signature_index(prob):
    """Index the variant's distinct nonzero (H-column, L-column) signatures."""
    index = {}
    for j, signature in enumerate(zip(prob.h, prob.l)):
        if signature in index:
            raise ValueError("variant contains duplicate column signatures")
        if signature == (0, 0):
            raise ValueError("variant contains an all-zero column")
        index[signature] = j
    return index


def _detector_row_map(prob, coordinates, num_detectors):
    if prob.variant == "full":
        if prob.nrows != num_detectors:
            raise ValueError("full variant rows differ from circuit detectors")
        return {i: i for i in range(num_detectors)}
    if not prob.rowmeta:
        raise ValueError("projected circuit variant needs row metadata")
    target_rows = {tuple(coords): i for i, coords in enumerate(prob.rowmeta)}
    if len(target_rows) != prob.nrows:
        raise ValueError("variant row metadata is ambiguous")
    if prob.variant == "sector":
        row_map = {i: target_rows[tuple(coords)] for i, coords in coordinates.items()
                   if tuple(coords) in target_rows}
        if len(row_map) != prob.nrows:
            raise ValueError("sector row metadata does not match circuit coordinates")
        return row_map
    if prob.variant == "collapsed":
        # Matches common.export_circuit_instance / cdist.problem.collapse_time:
        # retain the first-round memory sector, then XOR each check over time.
        first_types = {coords[3] >= 3 for coords in coordinates.values()
                       if len(coords) >= 4 and coords[2] == 0}
        if len(first_types) != 1:
            raise ValueError("cannot infer collapsed variant's memory sector")
        high = first_types.pop()
        row_map = {}
        for i, coords in coordinates.items():
            if len(coords) >= 4 and (coords[3] >= 3) == high:
                key = tuple(coords[:2])
                if key not in target_rows:
                    raise ValueError("collapsed check is absent from row metadata")
                row_map[i] = target_rows[key]
        if set(row_map.values()) != set(range(prob.nrows)):
            raise ValueError("collapsed row metadata does not match circuit coordinates")
        return row_map
    raise ValueError("unsupported circuit variant: " + prob.variant)


def detector_row_map(prob, circuit):
    """Map circuit detector ids to requested rows, including sector projection."""
    return _detector_row_map(prob, circuit.get_detector_coordinates(), circuit.num_detectors)


def map_errors_to_witness(errors, prob, row_map=None, index=None):
    """Map returned errors to columns and cancel repeated columns over GF(2)."""
    if index is None:
        index = build_signature_index(prob)
    support = set()
    for error in errors:
        signature = dem_error_signature(error, row_map)
        if signature == (0, 0):
            continue                 # this variant drops projected zero columns
        if signature not in index:
            raise ValueError("returned DEM signature is absent from variant: %r" % (signature,))
        col = index[signature]
        if col in support:
            support.remove(col)
        else:
            support.add(col)
    return sorted(support)


def _worker(send, circuit_path, operation, settings):
    """Only the worker constructs the DEM or runs Stim's uninterruptible C++ calls."""
    try:
        # A runaway high-degree search must not consume the shared laptop's RAM.
        # RLIMIT_AS is enforced on Linux; supported platforms also get the cap.
        try:
            import resource
            cap = 2 * 1024 ** 3
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            resource.setrlimit(resource.RLIMIT_AS, (cap if soft < 0 else min(cap, soft), hard))
        except (ImportError, ValueError, OSError, AttributeError):
            pass
        import stim
        circuit = stim.Circuit.from_file(circuit_path)
        if operation == "prepare":
            dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=True)
            graphlike = all(bin(dem_error_signature(inst)[0]).count("1") <= 2
                            for inst in dem if inst.type == "error")
            payload = {"coordinates": circuit.get_detector_coordinates(),
                       "num_detectors": circuit.num_detectors, "graphlike": graphlike}
        else:
            if operation == "graphlike":
                errors = circuit.shortest_graphlike_error(ignore_ungraphlike_errors=True,
                                                          canonicalize_circuit_errors=True)
            else:
                symptoms, degree, monotone = settings
                errors = circuit.search_for_undetectable_logical_errors(
                    dont_explore_detection_event_sets_with_size_above=symptoms,
                    dont_explore_edges_with_degree_above=degree,
                    dont_explore_edges_increasing_symptom_degree=monotone,
                    canonicalize_circuit_errors=True)
            # Send only integer signatures, keeping even very verbose explained
            # errors out of the parent process and away from multiprocessing pickles.
            payload = [dem_error_signature(error) for error in errors]
        send.send(("ok", payload))
    except BaseException as exc:
        send.send(("error", "%s: %s" % (type(exc).__name__, exc)))
    finally:
        send.close()


def _run_call(circuit_path, operation, settings, deadline):
    """Return (state, payload), terminating the entire child at the deadline."""
    if time.monotonic() >= deadline:
        return "timeout", None
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(send, circuit_path, operation, settings))
    process.start()
    send.close()
    state, payload = "error", "worker exited without a result"
    try:
        while time.monotonic() < deadline:
            if receive.poll(min(0.05, max(0.0, deadline - time.monotonic()))):
                try:
                    state, payload = receive.recv()
                except EOFError:
                    payload = "worker exited without a result (exitcode %s)" % process.exitcode
                break
            if not process.is_alive():
                payload = "worker exited without a result (exitcode %s)" % process.exitcode
                break
        else:
            state, payload = "timeout", None
    finally:
        receive.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=0.2)
        if process.is_alive():
            process.kill()
            process.join(timeout=0.2)
        process.close()
    return state, payload


def _parse_ladder(value):
    out = []
    for item in value.split(";"):
        symptoms, degree, monotone = map(int, item.split(":"))
        if symptoms < 0 or degree < 1 or monotone not in (0, 1):
            raise ValueError("invalid ladder entry: " + item)
        out.append((symptoms, degree, bool(monotone)))
    return out


def _project_signature(signature, row_map):
    h, l = signature
    projected = 0
    for row in common.bits(h):
        target = row_map.get(row)
        if target is not None:
            projected ^= 1 << target
    return projected, l


def main():
    trace = common.Trace()
    start = time.monotonic()
    a = common.adapter_args(__doc__)
    deadline = start + max(0.0, a.time_limit)
    prob = common.load(a.instance, a.variant)
    config = dict(a.cfg)
    config.setdefault("ladder", DEFAULT_LADDER)
    config.setdefault("graphlike", "1")
    notes = ["Stim searches are serial; --threads is ignored",
             "all reported bounds are heuristic upper bounds"]
    witness = None
    version = None
    status = "bounds"
    calls = 0
    valid = 0
    try:
        if a.threads < 1:
            raise ValueError("threads must be positive")
        unknown = set(a.cfg) - {"ladder", "graphlike"}
        if unknown:
            raise ValueError("unknown config keys: " + ", ".join(sorted(unknown)))
        if int(config["graphlike"]) not in (0, 1):
            raise ValueError("graphlike must be 0 or 1")
        if prob.meta.get("track") != "circuit":
            status = "unavailable"
            notes.append("Stim circuit search does not support code-capacity instances")
        else:
            import importlib.util
            import importlib.metadata
            if importlib.util.find_spec("stim") is None:
                status = "unavailable"
                notes.append("stim is not installed")
            else:
                try:
                    version = importlib.metadata.version("stim")
                except importlib.metadata.PackageNotFoundError:
                    pass
            if status != "unavailable":
                ladder = _parse_ladder(config["ladder"])
                index = build_signature_index(prob)
                circuit_path = os.path.join(a.instance, "circuit.stim")
                state, prepared = _run_call(circuit_path, "prepare", None, deadline)
                if state == "timeout":
                    status = "timeout"
                elif state != "ok":
                    status = "error"
                    notes.append("DEM preparation: " + str(prepared))
                else:
                    row_map = _detector_row_map(prob, prepared["coordinates"], prepared["num_detectors"])
                    operations = [("search", entry) for entry in ladder]
                    if int(config["graphlike"]) and prepared["graphlike"]:
                        operations.insert(0, ("graphlike", None))
                    notes.append("undecomposed DEM graphlike: %s" % prepared["graphlike"])
                    if prob.variant == "collapsed":
                        notes.append("searches the original circuit, then projects into the collapsed relaxation")
                    for operation, settings in operations:
                        state, payload = _run_call(circuit_path, operation, settings, deadline)
                        calls += 1
                        if state == "timeout":
                            status = "timeout"
                            notes.append("deadline stopped %s %s" % (operation, settings))
                            break
                        if state != "ok":
                            # Stim raises ValueError when a truncated search has
                            # no logical error; this is a normal heuristic miss.
                            notes.append("%s %s: %s" % (operation, settings, payload))
                            if not str(payload).startswith("ValueError: Failed to find any"):
                                status = "error"
                            continue
                        support = set()
                        try:
                            for signature in payload:
                                signature = _project_signature(signature, row_map)
                                if signature == (0, 0):
                                    continue
                                col = index[signature]
                                if col in support:
                                    support.remove(col)
                                else:
                                    support.add(col)
                        except KeyError as exc:
                            notes.append("returned signature absent from variant: %s" % (exc,))
                            continue
                        candidate = sorted(support)
                        if not common.check_witness(prob, candidate)["ok"]:
                            notes.append("discarded a returned error list that failed H/L witness verification")
                            continue
                        valid += 1
                        if trace.upper is None or len(candidate) < trace.upper:
                            witness = candidate
                            trace.ub(len(candidate))
                    if time.monotonic() >= deadline:
                        status = "timeout"
    except Exception as exc:
        status = "error"
        notes.append("%s: %s" % (type(exc).__name__, exc))
    notes.append("search calls: %s; valid outputs: %s" % (calls, valid))
    record = common.save_result(a.out, prob, "stim_search", trace, status, a.threads,
                                a.time_limit, witness=witness, config=config,
                                notes="; ".join(notes), version=version)
    import json
    print(json.dumps(record))


if __name__ == "__main__":
    main()
