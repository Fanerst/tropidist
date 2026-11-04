"""Ordered, source-backed benchmark suite. No search is performed while exporting.

Ground truth is read from the project's result files or a graph-like shortest
path computation for Stim surface memories. The two explicit paper
claims are taken from builder definitions and remain distinguishable from local
certificates. Unresolved sources/builders stay visible with status needs_lead.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import tempfile

try:
    from . import common
except ImportError:
    import common

ROOT = Path(common.ROOT)
INSTANCES = OrderedDict()
WJH = OrderedDict()          # the instances of arXiv:2603.22532, kept apart from the main suite


class NeedsLead(ValueError):
    pass


class TooLarge(ValueError):
    pass


def _json(path):
    with (ROOT / path).open() as f:
        return json.load(f)


def _truth(record, source, lower="certified_lower_bound", upper="certified_upper_bound"):
    lb, ub = record.get(lower), record.get(upper)
    if lb is not None and ub is not None and lb > ub:
        raise NeedsLead("inconsistent certified bounds in " + source)
    if lb is not None and lb == ub:
        return (lb, "exact", source)
    if lb is not None:
        return (lb, "lower_bound", source)
    raise NeedsLead("no certified lower bound in " + source)


def _collapsed(record, source):
    stage = record.get("stages", {}).get("collapsed", record.get("collapsed", {}))
    field = "stages.collapsed" if "collapsed" in record.get("stages", {}) else "collapsed"
    if stage.get("distance") is not None:
        # These producers write distance only after an exhaustive search found it.
        return (stage["distance"], "exact", source + "#" + field + ".distance")
    if stage.get("lower_bound") is not None:
        return (stage["lower_bound"], "lower_bound", source + "#" + field + ".lower_bound")
    return (None, "unknown", None)


def _add(name, track, family, builder, key=None, truth_file=None, registry=INSTANCES, **extra):
    registry[name] = dict(track=track, family=family, builder=builder, key=key,
                           basis="Z", rounds=6 if track == "circuit" else None,
                           truth_file=truth_file, status="ready", **extra)


for name in ("bb72_r6", "bb90_r10", "bb108_r10", "bb144_r12", "bb288_r18"):
    _add(name, "circuit", "bb6_si1000", "stored_bb", truth_file="results/" + name + "_Z.json",
         circuit_file="circuits/" + name + "_Z.stim", n=int(name.split("_")[0][2:]))
for name, key in (("gross_best_r6", "gross"), ("bb108_best_r6", "bb108")):
    _add(name, "circuit", "bb6_depth7", "best_bb6", key,
         "results/papers3/bb6/" + key + "_ibm.json")
for n, q in ((252, 7), (576, 16), (900, 25), (1044, 29)):
    _add("cornucopia_" + str(n), "circuit", "cornucopia", "module", q,
         "results/papers2/cornucopia_q%d_r6_Z.json" % q, module="cornucopia")
for key in (54, 90, 110, "140_13", "200_24"):
    path = "results/papers3/routing/server_%s_Z.json" % key
    if key == "200_24":
        path = "results/papers3/routing/server_full_200_24_Z.json"
    _add("routing_" + str(key), "circuit", "routing", "module", key, path, module="routing")
for n, k, d in ((150, 30, 10), (200, 40, 12), (300, 60, 14)):
    _add("mitten_" + str(n), "circuit", "mitten", "mitten", n,
         "results/papers/mitten%d_Z.json" % n, n=n, k=k,
         code_dir="papers/mitten/mitten/[[%d,%d,%d]]" % (n, k, d))
for n in (64, 120):
    path = "results/papers2/design/sdbb%d_parallel_%s.json" % (n, "family" if n == 64 else "Z")
    order = "results/papers2/design/sdbb%d_parallel_%s.json" % (n, "family" if n == 64 else "order")
    _add("sdbb_" + str(n), "circuit", "sdbb_parallel", "ordered", n, path,
         module="sdbb_parallel", order_file=order)
for name, key in (("w8bb_72", 1), ("w8bb_144_16", 2)):
    path = "results/papers2/design/bb8_%d_parallel_family.json" % key
    _add(name, "circuit", "bb8_parallel", "ordered", key, path, module="bb8_parallel", order_file=path)
for name, module, key, filename in (
        ("walkingcat_54", "walkingcat", 54, "server_54_Z.json"),
        ("star_42", "star", 42, "server_42_Z.json"),
        ("lrgross", "lrgross", "lr11", "server_lr11_Z.json"),
        ("shift_120d", "shift", "120d", "server_120d_Z.json")):
    _add(name, "circuit", module, "module", key, "results/papers3/%s/%s" % (module, filename), module=module)
_add("amplified_90", "circuit", "amplified", "amplified", 1, "results/papers/amp1_r8_Z.json")

for d in range(3, 26, 2):
    _add("surface_d%d" % d, "circuit", "surface", "stim_surface", d,
         variants=("full", "sector", "collapsed"),
         extra_sources=["bench/stim_families.py", "bench/instances.py"])
for d in range(3, 12, 2):
    name = "color_d%d" % d
    _add(name, "circuit", "stim_color", "stim_color", d,
         "results/bench_truth/%s.json" % name, variants=("full",),
         extra_sources=["bench/stim_families.py", "bench/instances.py"])

for n, key in ((72, "bb72"), (90, "bb90"), (108, "bb108"), (144, "gross"), (288, "bb288")):
    _add("code_bb" + str(n), "code", "bb6", "code_bb", key, n=n)
for n, filename, source in (
        (372, "qc_372_130_16.cpm", "results/papers2/kasai_code_distance_server.json"),
        (444, "qc_444_154_ge18.cpm", "results/papers2/kasai_code_distance_server.json"),
        (492, "qc_492_170_20.cpm", "results/papers2/kasai_492.json")):
    _add("code_kasai_" + str(n), "code", "kasai", "kasai", filename, source)
for name, key, source in (
        ("code_balanced_390", "balanced_390_78_16", "server.json"),
        ("code_balanced_625", "balanced_625_125_20", "server_balanced_625_125_20.json"),
        ("code_llmbb_360", "llmbb_360_12_24_V", "server_llmbb_360_12_24_V.json"),
        ("code_mm_324", "mm_t3_r6_324_12_20", "server.json"),
        ("code_w8bb_144_6", "w8bb_144_6_ge15", "server.json")):
    _add(name, "code", "estimated_codes", "estimated", key, "results/papers3/estdist/" + source)
_add("code_gala_132", "code", "gala", "gala", 132, "results/papers2/gala_code_distance.json")
_add("code_cornucopia_1044", "code", "cornucopia", "code_cornucopia", 29)
_add("code_sdbb_200", "code", "selfdual_bb", "selfdual", 200, "results/papers2/selfdual_bb_code_distance.json")

# The benchmark of arXiv:2603.22532 (Webster, Jacob, Higgott): their circuit files and their CSS codes, from
# their codeDistance package (github.com/m-webster/codeDistancePYPI, commit a4afe9c, MIT licence) checked out
# in WJH_REPO.  The codes are exported by papers/codedistance_export.py into WJH_CODES.  Circuit problems:
# the memory-basis sector, which equals their basis-filtered DEM column for column (checked when building).
# Codes: their quantity, the Z distance (H = HX, L = LX), which is basis "X" of stabcode.css_distance_problem.
# The long-range-noise BB directories (06_, 07_) are not separate problems: same mechanisms as 05_.
WJH_REPO = "papers/downloads/codedistance"
WJH_CODES = "papers/downloads/codedistance_codes.json"
WJH_CIRCUITS = (("surface", "01_surfacecodes"), ("midout", "03_colorcodes_midout"),
                ("superdense", "04_colorcodes_superdense"), ("bb", "05_bivariatebicyclecodes"))
WJH_CODE_FAMILIES = (("bb", 20), ("lp", 19), ("qt", 22), ("hsc", 21), ("hcc", 21))
# Distances of WJH circuits established outside the benchmark runs: result files with certified bounds of the
# sector problem (read by _truth like every truth file).  wjh_superdense_d11: the weight-truncated sparse Rank DP,
# results/sparse_dp/README.md.
WJH_TRUTH = {"wjh_superdense_d11": "results/sparse_dp/wjh_superdense_d11.json"}


def _wjh_fields(filename):
    import re
    return dict(re.findall(r"(\w+)=(\[\[[^\]]*\]\]|[^,]*)", filename[3:-len(".stim")]))


def _wjh_register():
    base = ROOT / WJH_REPO / "examples" / "stim_circuits"
    for family, folder in WJH_CIRCUITS:
        for path in sorted((base / folder).glob("*.stim")) if (base / folder).is_dir() else []:
            f = _wjh_fields(path.name)
            if family == "bb":
                name = "wjh_bb%s_circuit" % f["nkd"].strip("[]").split(",")[0]
            elif f["c"] == "color_code_mpp":
                name = "wjh_superdense_mpp_d%s" % f["d"]
            else:
                name = "wjh_%s_d%s" % (family, f["d"])
            _add(name, "circuit", "wjh_" + family + "_circuit", "wjh_circuit", path.name,
                 truth_file=WJH_TRUTH.get(name), circuit_file=str(path.relative_to(ROOT)), sector_high=True,
                 registry=WJH)
    codes = []
    if (ROOT / WJH_CODES).is_file():
        codes = _json(WJH_CODES)["codes"]
    for c in codes:
        tag = {"bb": "n%d" % c["n"], "lp": c["name"].lower().replace("_", ""), "qt": c["name"],
               "hsc": "%02d_n%d" % (c["index"], c["n"]), "hcc": "%02d_n%d" % (c["index"], c["n"])}[c["family"]]
        _add("wjh_%s_%s" % (c["family"], tag), "code", "wjh_" + c["family"], "wjh_code", (c["family"], c["index"]),
             truth_file=WJH_CODES, registry=WJH)
        WJH["wjh_%s_%s" % (c["family"], tag)].update(basis="X", n=c["n"], k=c["k"])


_wjh_register()

# Problems where the Rank DP evaluators decide (added 23 October 2026, docs/BENCHMARK.md):
#   - narrow codes of large distance, for the dense DP: color codes and concatenated Steane codes
#     (bench/export_lowwidth.py, as in the low-width trial);
#   - the long thin directional tile codes of arXiv:2606.19482 Table III, whose X distance the paper gives as upper
#     bounds only (papers/planar_nngrid.py, in the qubit order of the planar study, scripts/planar_dp.py);
#   - a many-hypercube code that no method solves, as a contrast;
#   - the superdense color-code circuits of arXiv:2603.22532, where the sparse DP decides.
# Ground truth: DP_TRUTH, written by scripts/dp_friendly_truth.py from the records that certify it.
DP_TRUTH = "results/dp_friendly_truth.json"
for _kind, _size, _name, _family in ([("color", d, "color_cc_d%d" % d, "color_cc") for d in (19, 23, 27, 31)]
                                     + [("steane", L, "concat_steane_L%d" % L, "concat_steane") for L in (3, 4)]
                                     + [("hypercube", 4, "hypercube_L4", "hypercube")]):
    _add(_name, "code", _family, "lowwidth", (_kind, _size), DP_TRUTH, truth_key=_name)
for _name in ("dtc_w5_259_2_4", "dtc_w7_269_4_5", "dtc_w9_365_10_4", "dtc_w11_537_14_12"):
    _add(_name, "code", "dtc_strip", "dtc", _name, DP_TRUTH, truth_key=_name)
for _d in (7, 9, 11):
    _w = WJH.get("wjh_superdense_d%d" % _d)
    if _w is not None:
        _add("superdense_d%d" % _d, "circuit", "superdense", "wjh_circuit", _w["key"], DP_TRUTH,
             circuit_file=_w["circuit_file"], sector_high=True, truth_key="superdense_d%d" % _d)


def _truth_record(path, spec):
    """The record of a truth file; a file with an "instances" map holds one record per instance (DP_TRUTH)."""
    data = _json(path)
    if "instances" in data:
        return data["instances"][spec["truth_key"]], path + "#instances." + spec["truth_key"]
    return data, path


def _prepare(spec):
    """Resolve file-backed metadata without building circuits or running a solver."""
    typ, key, path = spec["builder"], spec["key"], spec["truth_file"]
    if typ == "wjh_circuit":
        f = _wjh_fields(key)
        d = int(f["d"])
        if "nkd" in f:
            n, k, _ = (int(x) for x in f["nkd"].strip("[]").split(","))
        elif f["c"].startswith("surface"):
            n, k = d * d, 1
        else:
            n, k = (3 * d * d + 1) // 4, 1
        spec.update(n=n, k=k, basis="Z", rounds=int(f["r"]), description="arXiv:2603.22532 circuit " + key,
                    truth={"sector": (None, "unknown", None), "collapsed": (None, "unknown", None)})
        if path:
            spec["truth"]["sector"] = _truth(*_truth_record(path, spec))
        return
    if typ == "wjh_code":
        spec.update(description="arXiv:2603.22532 code %s %d (Z distance)" % key,
                    truth={"full": (None, "unknown", None)})
        return
    if typ in ("lowwidth", "dtc"):
        record, source = _truth_record(path, spec)
        spec.update(n=record["n"], k=record["k"], description=record["description"],
                    truth={"full": _truth(record, source)})
        return
    if typ in ("stim_surface", "stim_color"):
        try:
            from . import stim_families
        except ImportError:
            import stim_families
        spec.update(stim_families.instance_metadata(spec["family"], key))
        if typ == "stim_surface":
            # Distances are computed from the exported graphs, never assumed d.
            spec["truth"] = {v: (None, "unknown", None) for v in ("sector", "collapsed")}
            spec["notes"] = stim_families.SURFACE_NOTE
        else:
            spec["truth"] = {"full": (_truth(_json(path), path) if (ROOT / path).is_file()
                                      else (None, "unknown", None))}
        return
    data = _json(path) if path else None
    if spec["track"] == "circuit":
        if typ == "best_bb6":
            rows = [(i, r) for i, r in enumerate(data["rows"]) if "error" not in r
                    and r["Z"][0] is not None and r["Z"][0] == r["Z"][1]
                    and r["X"][0] is not None and r["X"][0] == r["X"][1]]
            # The schedule study defines its distance as min(d_Z, d_X),
            # as documented in docs/notes/PAPERS.md and design_bb6_depth7.py.
            top = max(min(r["Z"][0], r["X"][0]) for _, r in rows)
            i, row = next((i, r) for i, r in rows if min(r["Z"][0], r["X"][0]) == top)
            spec.update(n=data["code"][0], k=data["code"][1], schedule=[row["px"], row["pz"]], schedule_row=i)
            truth = {"sector": (row["Z"][0], "exact", path + "#rows[%d].Z" % i),
                     "collapsed": (row["Z"][2], "exact", path + "#rows[%d].Z[2]" % i)}
        elif typ == "ordered" and "best_circuit_distance" in data:
            if data.get("n_not_exact") != 0:
                raise NeedsLead("order-family result does not certify every order: " + path)
            mod = importlib.import_module(spec["module"])
            spec.update(n=mod.CODES[key][2][0], k=mod.CODES[key][2][1])
            truth = {"sector": (data["best_circuit_distance"], "exact", path + "#best_circuit_distance"),
                     "collapsed": (None, "unknown", None)}
        else:
            truth = {"sector": _truth(data, path), "collapsed": _collapsed(data, path)}
            code = data.get("code")
            if isinstance(code, list):
                spec.update(n=code[0], k=code[1])
            spec["basis"] = data.get("basis", "Z")
            spec["rounds"] = data.get("rounds", 6)
            if typ == "stored_bb":
                if not (ROOT / spec["circuit_file"]).is_file():
                    raise NeedsLead("missing circuit " + spec["circuit_file"])
                spec["rounds"] = int(Path(spec["circuit_file"]).stem.split("_r")[1].split("_")[0])
                spec["k"] = data["model"]["observables"]
            if typ == "mitten":
                if not (ROOT / spec["code_dir"]).is_dir():
                    raise NeedsLead("missing code directory " + spec["code_dir"])
                spec["rounds"] = data.get("witness", {}).get("rounds", 6)
                truth["collapsed"] = truth["sector"]  # effective matrix is the time-collapsed problem
                if key == 300:
                    bound_path = "results/papers/mitten300_Z_K11.json"
                    truth["sector"] = _truth(_json(bound_path), bound_path)
                    truth["collapsed"] = truth["sector"]
                    spec["extra_sources"] = [bound_path, "docs/notes/PAPERS.md"]
                    spec["truth_note"] = "Named result files certify only a lower bound; docs/notes/PAPERS.md describes an additional weight-12 witness."
            if typ == "amplified":
                mod = importlib.import_module("amplified_circuit")
                description = mod.theirs.description(key)
                spec.update(n=description["n"], k=description["k"], rounds=8)
                if description["xf"] and description["zf"]:
                    spec["sector_selector_issue"] = (
                        "amplified flags have both detector types at round 0; "
                        "common.export_circuit_instance needs an explicit memory-sector selector "
                        "(its implicit problem.sector_rows selection asserts one type at round 0)")
        spec["truth"] = truth
        model = data.get("model", {})
        spec["raw_mechanisms"] = model.get("dem_mechanisms")
        if typ == "ordered":
            order = _json(spec["order_file"])
            encoded = order["best_orders"][0] if "best_orders" in order else order["order"]
            spec["order"] = [(s[0], int(s[1:])) for s in encoded]
        if "n" not in spec:
            mod = importlib.import_module(spec.get("module", "amplified_circuit"))
            if hasattr(mod, "CODES"):
                spec.update(n=mod.CODES[key][2][0], k=mod.CODES[key][2][1])
    elif typ == "code_bb":
        if key != "bb288":
            row = importlib.import_module("bb6_depth7").DEFS[key][2]
            t = (row[2], "exact", "arXiv:2308.07915 Table 3")
        else:
            # The t=0 data-error window independently certifies this Table-3
            # code. Read its value rather than duplicating it as a literal.
            path = "results/bb288_r18_Z.json"
            certificate = _json(path)
            t = _truth(certificate["window_t0"], path + "#window_t0 (arXiv:2308.07915 Table 3)",
                       lower="lower_bound_of_window", upper="distance")
            if t[1] != "exact":
                raise NeedsLead("BB288 data-error window is not certified exact")
            row = (spec["n"], certificate["model"]["observables"], t[0])
            spec["truth_file"] = path
        spec.update(n=row[0], k=row[1], truth={"full": t})
    elif typ == "code_cornucopia":
        row = importlib.import_module("cornucopia").CODES[key][2]
        spec.update(n=row[0], k=row[1], truth={"full": (row[2], "unknown", "papers/new/2608.02773.md#Table-1")})
        certificate_path = "results/bench_dev/suite/code_cornucopia_1044__certified.json"
        if (ROOT / certificate_path).is_file():
            certificate = _json(certificate_path)
            if (certificate.get("instance") != "code_cornucopia_1044" or certificate.get("variant") != "full"
                    or certificate.get("status") != "exact" or certificate.get("witness_ok") is not True
                    or not certificate.get("input_sha256")):
                raise NeedsLead("invalid local code-capacity certificate: " + certificate_path)
            t = _truth(certificate, certificate_path, lower="lower_bound", upper="upper_bound")
            if t[1] != "exact":
                raise NeedsLead("local certificate lacks equal certified bounds: " + certificate_path)
            spec.update(truth={"full": t}, truth_file=certificate_path,
                        certified_inputs=certificate["input_sha256"], extra_sources=["papers/new/2608.02773.md"])
    else:
        selector = "file" if typ == "kasai" else "name" if typ == "estimated" else "n"
        record = next(r for r in data["codes"] if r.get(selector) == key)
        spec.update(n=record["n"], k=record["k"])
        if typ == "selfdual":
            if record.get("d") is None or not record.get("witness"):
                raise NeedsLead("selfdual result has no exact search distance/witness")
            truth = (record["d"], "exact", path + "#codes[n=%s].d" % key)
        else:
            basis_truth = {}
            for basis in ("Z", "X"):
                r = record["distance"][basis]
                # These producers' d is the certified exhaustive-search distance.
                upper = "upper_bound" if "upper_bound" in r else "d"
                basis_truth[basis] = _truth(r, path + "#codes[%s=%s].distance.%s" % (selector, key, basis),
                                           lower="lower_bound", upper=upper)
            truth = basis_truth["Z"]
            spec["other_basis_truth"] = basis_truth["X"]
        spec["truth"] = {"full": truth}
    if spec["track"] == "circuit" and "n" not in spec:
        raise NeedsLead("builder/result has no identifiable data-qubit count")
    if spec.get("sector_selector_issue"):
        raise NeedsLead(spec["sector_selector_issue"])


for _name, _spec in list(INSTANCES.items()) + list(WJH.items()):
    try:
        _prepare(_spec)
    except (OSError, ValueError, KeyError, IndexError, TypeError, StopIteration, ImportError) as exc:
        _spec.update(status="needs_lead", reason=str(exc) if isinstance(exc, NeedsLead)
                     else "%s: %s" % (type(exc).__name__, exc))
    else:
        other = _spec.get("other_basis_truth")
        full = _spec.get("truth", {}).get("full")
        if other and other[:2] != full[:2]:
            del INSTANCES[_name]
            for _basis, _t in (("Z", full), ("X", other)):
                _split = deepcopy(_spec)
                _split.update(basis=_basis, truth={"full": _t})
                INSTANCES[_name + "_" + _basis] = _split


def _circuit(spec):
    typ, key = spec["builder"], spec["key"]
    b, r = spec["basis"], spec["rounds"]
    if typ in ("stored_bb", "wjh_circuit"):
        import stim
        return stim.Circuit.from_file(str(ROOT / spec["circuit_file"])), []
    if typ in ("stim_surface", "stim_color"):
        try:
            from . import stim_families
        except ImportError:
            import stim_families
        if typ == "stim_surface":
            return stim_families.surface_circuit(key)
        return stim_families.generated_circuit("stim_color", key), []
    if typ == "best_bb6":
        mod = importlib.import_module("bb6_depth7")
        return mod.build(key, b, r, schedule=mod.to_dicts(*spec["schedule"])), mod.translations(key)
    if typ == "mitten":
        mod = importlib.import_module("mitten_circuit")
        directory = str(ROOT / spec["code_dir"])
        eff = importlib.import_module("mitten_effective").effective_problem(directory, b)
        cp = common.symmetric_subset(eff, importlib.import_module("mitten_symmetry").candidates(directory, eff.nrows))
        return mod.build(str(ROOT / spec["code_dir"]), b, r), cp
    if typ == "amplified":
        circ, info = importlib.import_module("amplified_circuit").build(key, b, r)
        spec.update(n=info["n"], k=info["k"])
        return circ, []
    mod = importlib.import_module(spec["module"])
    kwargs = {"order": spec["order"]} if typ == "ordered" else {}
    return mod.build(key, b, r, **kwargs), mod.translations(key) if hasattr(mod, "translations") else []


def _wjh_code_perms(family, hx, n):
    """Candidate check permutations for the structured families (the exporter keeps only true symmetries):
    lattice translations of a bivariate bicycle code (rows i*m + j of the l x m torus, every factorisation
    tried) and the cyclic shift of a quasi-cyclic lifted-product code (blocks of l consecutive or
    interleaved rows, every l tried).  Quantum Tanner and hyperbolic codes: none."""
    r = len(hx)
    out = []
    if family == "bb":
        for l in range(2, r):
            if r % l:
                continue
            m = r // l
            for di, dj in ((1, 0), (0, 1)):
                out.append([((i + di) % l) * m + (j + dj) % m for i in range(l) for j in range(m)])
    elif family == "lp":
        for l in range(2, r + 1):
            if r % l:
                continue
            b = r // l
            out.append([q * l + (i + 1) % l for q in range(b) for i in range(l)])
            out.append([((i + 1) % l) * b + q for i in range(l) for q in range(b)])
    return out


def _code(spec):
    typ, key = spec["builder"], spec["key"]
    if typ == "lowwidth":
        try:
            from . import export_lowwidth
        except ImportError:
            import export_lowwidth
        return (*export_lowwidth.code(*key), [])
    if typ == "dtc":
        import sys
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import planar_dp
        hx, hz, n, _ = planar_dp.family_code("nngrid", key, spec["basis"])
        return hx, hz, n, []
    if typ == "wjh_code":
        family, index = key
        c = next(c for c in _json(WJH_CODES)["codes"] if c["family"] == family and c["index"] == index)
        hx = [sum(1 << j for j in row) for row in c["hx"]]
        hz = [sum(1 << j for j in row) for row in c["hz"]]
        return hx, hz, c["n"], _wjh_code_perms(family, hx, c["n"])
    if typ == "code_bb":
        if key == "bb288":
            import stabcode
            hx, hz, n = stabcode.bb_matrices(12, 12, [(3, 0), (0, 2), (0, 7)], [(0, 3), (1, 0), (2, 0)])
            cp = [[((i + di) % 12) * 12 + (j + dj) % 12 for i in range(12) for j in range(12)]
                  for di, dj in ((1, 0), (0, 1))]
            return hx, hz, n, cp
        mod = importlib.import_module("bb6_depth7")
        return (*mod.matrices(key), mod.translations(key))
    if typ == "kasai":
        mod = importlib.import_module("kasai_codes")
        _, hx, hz, n, period, _ = mod.load(str(ROOT / "papers/downloads/kasai" / key), mod.shift_convention())
        return hx, hz, n, mod.candidate_perms(len(hz) if spec["basis"] == "Z" else len(hx), period)
    if typ == "estimated":
        mod = importlib.import_module("estimated_codes")
        return (*mod.matrices(key), mod.symmetries(key))
    if typ == "gala":
        mod = importlib.import_module("gala_codes")
        row = next(row for row in mod.CODES if row[0][0] == key)
        return mod.build(*row[1:])
    if typ == "selfdual":
        mod = importlib.import_module("selfdual_bb")
        row = next(row for row in mod.CODES if row[0] == key)
        hx, hz, n, torus, _ = mod.build(*row[3:])
        return hx, hz, n, torus.translations()
    mod = importlib.import_module("cornucopia")
    return (*mod.matrices(key), mod.translations(key))


def build(name, root=None, max_cols=None):
    """Export one named instance; max_cols bounds raw DEM mechanisms (code: n).

    A staging directory prevents failed builds from appearing as finished exports.
    No existing destination is changed until all variants were successfully written.
    """
    spec = deepcopy(INSTANCES[name] if name in INSTANCES else WJH[name])
    if spec["status"] == "needs_lead":
        raise NeedsLead(spec["reason"])
    size = spec.get("raw_mechanisms") if spec["track"] == "circuit" else spec.get("n")
    if max_cols is not None and size is not None and size > max_cols:
        raise TooLarge("%d %s exceeds --max-cols %d" % (size, "raw DEM mechanisms" if spec["track"] == "circuit" else "code columns", max_cols))
    root = Path(root or common.INSTANCES)
    root.mkdir(parents=True, exist_ok=True)
    (ROOT / "results/bench_dev/suite").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="suite-", dir=str(ROOT / "results/bench_dev/suite")) as tmp:
        meta = {k: spec[k] for k in ("family", "n", "k", "basis", "rounds", "truth") if k in spec}
        meta.update(description=spec.get("description", name.replace("_", " ")), source={k: v for k, v in spec.items()
                    if k not in ("truth", "status", "reason", "other_basis_truth")})
        sources = [spec.get("truth_file"), spec.get("order_file"), spec.get("circuit_file")] + spec.get("extra_sources", [])
        meta["source_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources if p and (ROOT / p).is_file()}
        if spec["track"] == "circuit":
            circ, cp = _circuit(spec)
            raw = circ.detector_error_model(decompose_errors=False, flatten_loops=True).num_errors
            if max_cols is not None and raw > max_cols:
                raise TooLarge("%d raw DEM mechanisms exceeds --max-cols %d" % (raw, max_cols))
            meta.update(n=spec["n"], k=spec["k"])
            # The shared exporter still constructs and checks every variant.
            # Reuse a single H/L row basis when verifying its many symmetries.
            if spec["builder"] in ("stim_surface", "stim_color"):
                meta["used_qubits"] = len(circ.get_final_qubit_coordinates())
                if spec.get("notes"):
                    meta["notes"] = spec["notes"]
                if spec["builder"] == "stim_surface":
                    try:
                        from . import stim_families
                    except ImportError:
                        import stim_families
                    out = common.export_circuit_instance(name, circ, cp, meta, root=tmp)
                    stim_families.record_surface_truth(Path(tmp) / name, out)
                else:
                    out = common.export_dem_instance(name, circ, meta, root=tmp)
            else:
                out = common.export_circuit_instance(name, circ, [], meta, root=tmp, high=spec.get("sector_high"))
            if spec["builder"] == "mitten":
                eff = importlib.import_module("mitten_effective").effective_problem(str(ROOT / spec["code_dir"]), spec["basis"])
                coll = common.load(os.path.join(tmp, name), "collapsed")
                if set(zip(eff.h, eff.l)) != set(zip(coll.h, coll.l)):
                    raise NeedsLead("exported collapse differs from the effective matrix certified by the mitten result")
            if spec["builder"] not in ("stim_surface", "stim_color"):
                import run_parallel
                for variant in out["variants"]:
                    prob = common.to_cdist(common.load(os.path.join(tmp, name), variant))
                    if spec["builder"] == "wjh_circuit" and variant == "full" and prob.ncols > 400000:
                        perms = []      # the check over all columns is too slow; our searches use sector/collapsed
                    else:
                        perms = (common.lattice_perms(prob) if spec["builder"] in ("stored_bb", "wjh_circuit")
                                 else common.fast_symmetries(prob, run_parallel.row_perms(prob, cp)))
                    counts = common.export_problem(os.path.join(tmp, name), variant, prob, perms)
                    out["variants"][variant].update(counts)
                common.write_meta(os.path.join(tmp, name), out)
        else:
            import stabcode
            hx, hz, n, cp = _code(spec)
            _, k = stabcode.css_parameters(hx, hz, n)
            if (n, k) != (spec["n"], spec["k"]):
                raise NeedsLead("builder parameters (%d,%d) differ from source (%d,%d)" % (n, k, spec["n"], spec["k"]))
            out = common.export_code_instance(name, hx, hz, n, spec["basis"], cp, meta, root=tmp)
            if spec.get("certified_inputs"):
                for filename, expected in spec["certified_inputs"].items():
                    if filename not in ("full.H.mtx", "full.L.mtx"):
                        raise NeedsLead("certificate names an unsupported input file")
                    actual = hashlib.sha256((Path(tmp) / name / filename).read_bytes()).hexdigest()
                    if actual != expected:
                        raise NeedsLead("certified input hash differs from the rebuilt " + filename)
        target = root / name
        backup = None
        if target.exists():
            backup = Path(tmp) / "previous"
            target.rename(backup)
        try:
            shutil.move(os.path.join(tmp, name), str(target))
        except Exception:
            if backup is not None:
                backup.rename(target)
            raise
        return out
