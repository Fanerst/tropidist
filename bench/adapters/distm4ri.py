"""dist-m4ri CLI adapter (0.9.0 and 0.14.x): connected clusters, random windows, or bracketing.

Config: binary=<path> or build=<version> (bench/external/dist-m4ri-<version>/src/dist_m4ri;
default: the 0.9.0 build in bench/external/dist-m4ri), mode=cc|rw|bracket, input=mtx|dem,
cutoff=1|0 (0: a native timeout far beyond the budget, so the program runs until the wall
deadline kills it, which avoids 0.9.0's predictive skipping of a CC round), bound=none|model,
followed by documented dist-m4ri key=value options. DEM is restricted to circuit/full and pmin=0.

bound=model (0.14.5 and later, circuits, mode cc or bracket) is the model lower bound of
dist-m4ri's --model-lb: compute_model_lower_bound() of the build's dist_m4ri.py, with its cache
off, on the instance's circuit.stim, within half of the remaining budget; then the binary runs
as usual with dmin set to that certified bound, so CC starts there, as compute_dem_distance()
does with the cached bound.
Input paths/method are owned by the adapter; classical=1 changes the problem and
is rejected. Assumed dmin/dmax, noscan, and restricted columns disable all lower
bound claims. --threads is authoritative and nothrottle=1 is mandatory.

One subprocess supplies live completed-weight proofs (debug bit 1), with no
repeated search/startup overhead. outC supplies independently checked NZLIST
witnesses at shutdown; a hard kill may therefore retain only lower bounds.
For CC, maxC defaults to 1 when dW=0: stop on the first minimum-weight witness
instead of paying outC's exhaustive codeword-collection overhead. RW/bracket
retain the program's unlimited collection default. Native timeout is clamped
to the remaining budget, reserving at most 0.1s for export; an independent wall
deadline kills the entire process group, including during DEM preparation.

Source-specific details: dist_m4ri.c coordinators print completion messages only
after a round completes; util_io.c discards DEM probabilities after its pmin
filter and stores one raw column per error. Exported benchmark columns merge
equal (H,L) signatures and discard zero columns, so DEM witnesses are remapped
with GF(2) cancellation. The final triple is dmin,dmax,rw_steps: method 1's
dmin is an assumption, not a proof; method 3 can be exact with nonzero rw_steps.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common

DEFAULT_BINARY = Path(common.ROOT) / "bench/external/dist-m4ri/src/dist_m4ri"
METHODS = {"cc": 2, "rw": 1, "bracket": 3}
# The CLI uses signed C ints, except maxC (long long) and timeout/pmin (double).
INT_OPTIONS = {
    "wmax": (0, 99), "wmin": (0, 2147483647), "steps": (0, 2147483647),
    "dmin": (0, 2147483647), "dmax": (0, 2147483647),
    "dest": (0, 2147483647), "dexp": (0, 2147483647),
    "seed": (0, 2147483647), "smax": (0, 2147483647),
    "noscan": (0, 1), "start": (-1, 2147483647),
    "cbeg": (-1, 2147483647), "cend": (-1, 2147483647),
    "maxC": (0, 9223372036854775807), "dW": (-2147483648, 2147483647),
    "classical": (0, 1), "css": (1, 1), "debug": (0, 4095),
    "nothrottle": (1, 1), "threads": (1, 2147483647),
    "chunk_size": (0, 2147483647), "batch": (0, 2147483647),
}
TRIPLE = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s*$")
COMPLETION = re.compile(
    r"^# CC (?:w=(\d+) completed|round w=(\d+) finished) .*"
    r": no codewords(?: found)? -> dmin=(\d+)\s*$")
FOUND = re.compile(r"^# CC found min-weight codeword: d=(\d+)\b")
CODEWORD = re.compile(r"codeword of weight (\d+) \(1-based columns\): ([\d ]+?)\s*$")   # debug bit 32
COINCIDE = re.compile(r"^# bracketing bounds coincide: dmin = dmax = (\d+)\b")


def parse_triple(text):
    """Last standard-output result, ignoring banners/confinement comments."""
    triples = [tuple(map(int, m.groups())) for line in text.splitlines()
               for m in [TRIPLE.fullmatch(line)] if m]
    if not triples:
        raise ValueError("no dist-m4ri dmin dmax rw_steps triple")
    lower, upper, steps = triples[-1]
    if lower < 1:
        raise ValueError("invalid dmin in dist-m4ri result")
    return lower, upper, steps


def parse_progress(line):
    """Only completed, unsuccessful CC rounds; confinement is not a proof."""
    match = COMPLETION.fullmatch(line.strip())
    if not match:
        return None
    first, second, lower = match.groups()
    weight, lower = int(first or second), int(lower)
    if weight < 1 or lower != weight + 1:
        raise ValueError("inconsistent CC completion message")
    return weight, lower


def _codewords(path, ncols, partial=False):
    with open(path) as stream:
        header = stream.readline()
        if partial and not header.endswith("\n"):
            return  # SIGKILL before the buffered header was completely exported.
        if header.strip() != "%% NZLIST":
            raise ValueError("codeword file is not NZLIST")
        for number, line in enumerate(stream, 2):
            if not line.strip() or line.lstrip().startswith("%"):
                continue
            # A hard kill during export can leave an incomplete final row.
            if partial and not line.endswith("\n"):
                break
            try:
                values = list(map(int, line.split()))
            except ValueError:
                raise ValueError("noninteger NZLIST row %d" % number)
            weight, indices = values[0], values[1:]
            if (weight < 1 or len(indices) != weight or
                    indices != sorted(set(indices)) or
                    any(j < 1 or j > ncols for j in indices)):
                raise ValueError("invalid NZLIST support on row %d" % number)
            yield [j - 1 for j in indices]


def read_codewords(path, ncols):
    """Read the real 1-based NZLIST format as zero-based column supports."""
    return list(_codewords(path, ncols))


def settings(cfg, threads):
    cfg = dict(cfg)
    default = DEFAULT_BINARY
    build = cfg.pop("build", None)
    if build is not None:
        if "binary" in cfg:
            raise ValueError("specify binary or build, not both")
        if not re.fullmatch(r"\d+(\.\d+)*", build):
            raise ValueError("build must be a version such as 0.14.7")
        default = Path(common.ROOT) / ("bench/external/dist-m4ri-%s/src/dist_m4ri" % build)
    binary = str(Path(cfg.pop("binary", str(default))).expanduser().absolute())
    cutoff = cfg.pop("cutoff", "1")
    if cutoff not in ("0", "1"):
        raise ValueError("cutoff must be 0 or 1")
    mode = cfg.pop("mode", "cc")
    input_kind = cfg.pop("input", "mtx")
    if mode not in METHODS or input_kind not in ("mtx", "dem"):
        raise ValueError("mode must be cc/rw/bracket and input must be mtx/dem")
    bound = cfg.pop("bound", "none")
    if bound not in ("none", "model"):
        raise ValueError("bound must be none or model")
    if bound == "model" and (mode == "rw" or "dmin" in cfg):
        raise ValueError("bound=model needs mode cc or bracket and supplies dmin itself")
    options = {}
    for key, value in cfg.items():
        if key in INT_OPTIONS:
            if not re.fullmatch(r"[+-]?\d+", value):
                raise ValueError("%s must be an integer" % key)
            lo, hi = INT_OPTIONS[key]
            integer = int(value)
            if not lo <= integer <= hi:
                raise ValueError("%s must be in [%d,%d]" % (key, lo, hi))
            if key == "debug" and integer & ~2303:
                raise ValueError("debug contains undocumented bits")
            options[key] = str(integer)
        elif key in ("timeout", "pmin"):
            number = float(value)
            if not math.isfinite(number) or number < 0:
                raise ValueError("%s must be finite and nonnegative" % key)
            if key == "pmin" and (number != 0 or input_kind != "dem"):
                raise ValueError("pmin is allowed only for DEM input and must be 0")
            options[key] = str(number)
        elif key in ("outC", "finC"):
            if not value or "\x00" in value or "\n" in value:
                raise ValueError("%s must be a nonempty file path" % key)
            options[key] = str(Path(value).expanduser().absolute())
        else:
            raise ValueError("unknown or adapter-owned dist-m4ri parameter: %s" % key)
    if int(options.get("threads", threads)) != threads:
        raise ValueError("config threads must equal --threads")
    if int(options.get("classical", 0)) != 0:
        raise ValueError("classical=1 changes the benchmark's H/L problem")
    for first, second in (("dest", "dexp"), ("batch", "chunk_size")):
        if first in options and second in options:
            raise ValueError("specify only one of %s/%s" % (first, second))
    if int(options.get("noscan", 0)) and mode != "cc":
        raise ValueError("noscan=1 is valid only in cc mode")
    if int(options.get("noscan", 0)) and int(options.get("wmax", 0)) == 0:
        raise ValueError("noscan=1 requires wmax>0")
    start = int(options.get("start", -1))
    beg, end = int(options.get("cbeg", -1)), int(options.get("cend", -1))
    if start >= 0 and (beg >= 0 or end >= 0):
        raise ValueError("start cannot be combined with cbeg/cend")
    if beg >= 0 and end >= 0 and beg > end:
        raise ValueError("cbeg cannot exceed cend")
    if mode == "rw" and max(start, beg, end) >= 0:
        raise ValueError("column restrictions require cc/bracket")
    wmax = int(options.get("wmax", 0))
    if wmax and max(int(options.get("wmin", 1)), int(options.get("dmin", 1))) > wmax:
        raise ValueError("wmin/dmin cannot exceed a positive wmax")
    if (int(options.get("dmax", 0)) > 0 and
            int(options.get("dmin", 1)) > int(options["dmax"])):
        raise ValueError("dmin cannot exceed a positive dmax")
    if mode == "rw" and int(options.get("steps", 1000)) == 0:
        raise ValueError("rw requires positive steps (bracket permits steps=0)")
    options.update(threads=str(threads), nothrottle="1", classical="0", css="1")
    # Pass exactly one debug argument: the source rejects conflicting duplicates.  Bracket with bound=model takes
    # its witnesses from stderr (bit 32: each new lightest codeword; 2048: no cutoff of its support), see main().
    options["debug"] = str(int(options.get("debug", 0)) | 1 | (2080 if stderr_witness(mode, bound) else 0))
    if (mode == "cc" and "maxC" not in options and "finC" not in options and
            int(options.get("dW", 0)) == 0):
        options["maxC"] = "1"
    if cutoff == "0" and "timeout" in options:
        raise ValueError("cutoff=0 and an explicit timeout contradict each other")
    return binary, mode, input_kind, options, cutoff == "1", bound


def stderr_witness(mode, bound):
    """Bracket mode with the model bound runs without outC, as dist-m4ri's own flow does: with outC the program
    goes on enumerating every codeword of the minimum weight once the bounds meet (its first CC round is at the
    bound itself), and a cap (maxC) also counts the heavier RW codewords and ends the run early."""
    return mode == "bracket" and bound == "model"


def proof_eligible(options, ncols, certified=1):
    """certified: a lower bound already proved (the model bound), from which CC may start."""
    return (int(options.get("dmin", 1)) <= max(1, certified) and
            int(options.get("dmax", 0)) == 0 and
            int(options.get("noscan", 0)) == 0 and
            int(options.get("start", -1)) == -1 and
            int(options.get("cbeg", -1)) in (-1, 0) and
            int(options.get("cend", -1)) in (-1, ncols - 1))


def prepare_dem(instance, dem_path, map_path):
    """Runs in a child so native Stim preparation is covered by the wall limit."""
    import stim
    prob = common.load(instance, "full")
    circuit = stim.Circuit.from_file(str(Path(instance) / "circuit.stim"))
    dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=True).flattened()
    if (circuit.num_detectors, circuit.num_observables) != (prob.nrows, prob.nobs):
        raise ValueError("circuit and full-variant dimensions disagree")
    index = {pair: j for j, pair in enumerate(zip(prob.h, prob.l))}
    if len(index) != prob.ncols or (0, 0) in index:
        raise ValueError("full variant must have unique nonzero (H,L) columns")
    mapping, covered = [], set()
    for instruction in dem:
        if instruction.type != "error":
            continue
        probability = instruction.args_copy()[0]
        if not 0 < probability < 1:
            raise ValueError("dist-m4ri requires DEM error probabilities strictly in (0,1)")
        h = logical = 0
        for target in instruction.targets_copy():
            if target.is_relative_detector_id():
                h ^= 1 << target.val
            elif target.is_logical_observable_id():
                logical ^= 1 << target.val
            else:
                raise ValueError("undecomposed DEM unexpectedly contains a separator")
        pair = (h, logical)
        if pair == (0, 0):
            mapping.append(None)
        else:
            if pair not in index:
                raise ValueError("DEM mechanism missing from full-variant columns")
            mapping.append(index[pair])
            covered.add(index[pair])
    if len(covered) != prob.ncols:
        raise ValueError("DEM does not cover every full-variant column")
    dem.to_file(dem_path)
    with open(map_path, "w") as stream:
        json.dump(mapping, stream)


def wrapper_path(binary):
    """The build's dist_m4ri.py: next to the binary, or one level up (the source tree's src/dist_m4ri)."""
    for directory in (Path(binary).parent, Path(binary).parent.parent):
        if (directory / "dist_m4ri.py").is_file():
            return directory / "dist_m4ri.py"
    return None


def model_bound(circuit, wrapper, binary, *args):
    """Runs in a child: dist-m4ri's model bound of a Stim circuit, as JSON in the last argument.
    args: method=, threads=, timeout= (the threads= token also sets OMP_NUM_THREADS in run_process)."""
    import importlib.util
    *settings_, out_path = args
    kw = dict(arg.split("=", 1) for arg in settings_)
    spec = importlib.util.spec_from_file_location("dist_m4ri", wrapper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.disable_distance_cache()          # nothing carried over between runs
    bound, info = module.compute_model_lower_bound(
        circuit=circuit, dist_m4ri=binary, method=int(kw["method"]), threads=int(kw["threads"]),
        timeout=float(kw["timeout"]), nothrottle=True, return_info=True)
    keep = ("model_d_info", "measured_d_info", "rows", "cols", "rows_measured", "cols_measured", "dem_cols", "trivial")
    with open(out_path, "w") as stream:
        json.dump(dict({k: info.get(k) for k in keep}, bound=int(bound)), stream, default=int)


def map_witness(support, mapping):
    if mapping is None:
        return support
    parity = set()
    for raw in support:
        col = mapping[raw]
        if col is not None:
            if col in parity:
                parity.remove(col)
            else:
                parity.add(col)
    return sorted(parity)


def run_process(command, deadline, on_line):
    """Drain both pipes, processing proof lines live; hard-kill the process group."""
    env = dict(os.environ, OMP_NUM_THREADS=command_threads(command),
               PYTHONDONTWRITEBYTECODE="1")
    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             start_new_session=True, env=env)

    def kill_group():
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # The process group can exit just before the deadline.

    buffers = {"stdout": b"", "stderr": b""}
    selector = selectors.DefaultSelector()
    killed = False
    for label, pipe in (("stdout", child.stdout), ("stderr", child.stderr)):
        os.set_blocking(pipe.fileno(), False)
        selector.register(pipe, selectors.EVENT_READ, label)
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                killed = True
                kill_group()
                break
            for key, _ in selector.select(min(remaining, 0.05)):
                data = os.read(key.fileobj.fileno(), 65536)
                label = key.data
                if not data:
                    selector.unregister(key.fileobj)
                    if buffers[label]:
                        on_line(label, buffers[label].decode("utf-8", "replace"))
                    buffers[label] = b""
                    continue
                pieces = (buffers[label] + data).split(b"\n")
                buffers[label] = pieces.pop()
                for line in pieces:
                    on_line(label, line.decode("utf-8", "replace"))
                if len(buffers[label]) > 1048576:
                    raise ValueError("dist-m4ri diagnostic line exceeds 1 MiB")
        # A child can close its pipes while still running: wait only to deadline.
        if not killed:
            try:
                child.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                killed = True
                kill_group()
        child.wait(timeout=2)
        # Read final bytes already in the pipes after killing (without waiting).
        for label, pipe in (("stdout", child.stdout), ("stderr", child.stderr)):
            tail = buffers[label]
            while True:
                try:
                    data = os.read(pipe.fileno(), 65536)
                except BlockingIOError:
                    break
                if not data:
                    break
                tail += data
            for line in tail.splitlines():
                on_line(label, line.decode("utf-8", "replace"))
        return child.returncode, killed
    finally:
        if child.poll() is None:
            kill_group()
            child.wait(timeout=2)
        selector.close()
        child.stdout.close()
        child.stderr.close()


def command_threads(command):
    return next((arg.split("=", 1)[1] for arg in command if arg.startswith("threads=")),
                os.environ.get("OMP_NUM_THREADS", "1"))


def load_instance(instance, variant, deadline):
    """Bound matrix loading too; an expired load can only yield a timeout record.

    The fallback contains metadata dimensions, not matrix entries. range avoids
    allocating a second large matrix merely to serialize a no-witness result.
    """
    class ReadTimeout(Exception):
        pass

    def expired(signum, frame):
        raise ReadTimeout()

    old_handler = signal.signal(signal.SIGALRM, expired)
    old_timer = signal.setitimer(signal.ITIMER_REAL,
                                min(2147483647, max(0.001, deadline - time.monotonic())))
    try:
        try:
            return common.load(instance, variant), False
        except ReadTimeout:
            signal.setitimer(signal.ITIMER_REAL, 0)
            with open(Path(instance) / "meta.json") as stream:
                meta = json.load(stream)
            shape = meta["variants"][variant]
            prob = common.Prob(meta["name"], variant, shape["rows"], shape["obs"],
                               range(shape["cols"]), range(shape["cols"]), meta)
            return prob, True
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        if old_timer[0] or old_timer[1]:
            signal.setitimer(signal.ITIMER_REAL, *old_timer)


def main():
    a = common.adapter_args(__doc__)
    tr = common.Trace()  # Includes reading matrices and preparing the DEM.
    valid_limit = math.isfinite(a.time_limit) and a.time_limit >= 0
    deadline = time.monotonic() + (a.time_limit if valid_limit else 0)
    prob, read_timed_out = load_instance(a.instance, a.variant, deadline)
    notes = ["Single-process completed-weight trace via debug bit 1; no repeated enumeration. "
             "Includes startup, progress logging and NZLIST export overhead. "
             "nothrottle=1; threads=%d." % a.threads]
    status, witness, version = "error", None, None
    effective = dict(a.cfg)
    try:
        if not 1 <= a.threads <= 2147483647 or not math.isfinite(a.time_limit) or a.time_limit < 0:
            raise ValueError("threads must be positive and time-limit finite/nonnegative")
        binary, mode, input_kind, options, native_limit, bound_kind = settings(a.cfg, a.threads)
        effective.update(binary=binary, mode=mode, input=input_kind)
        if bound_kind == "model" and (prob.meta.get("track") != "circuit" or a.variant not in ("sector", "full")):
            raise ValueError("bound=model requires a circuit instance and variant sector or full")
        if not Path(binary).is_file() or not os.access(binary, os.X_OK):
            status = "unavailable"
            notes.append("dist-m4ri binary is missing or not executable: %s" % binary)
        elif input_kind == "dem" and (a.variant != "full" or prob.meta.get("track") != "circuit"):
            raise ValueError("input=dem requires a circuit instance and variant=full")
        elif read_timed_out or time.monotonic() >= deadline:
            status = "timeout"
            if read_timed_out:
                notes.append("Wall deadline reached while reading instance matrices.")
        else:
            with tempfile.TemporaryDirectory(prefix="bench-distm4ri-") as temp:
                version_lines = []
                version_rc, version_killed = run_process(
                    [binary, "--version"], min(deadline, time.monotonic() + 1),
                    lambda stream, line: version_lines.append(line) if len(version_lines) < 10 else None)
                if version_rc == 0:
                    for line in version_lines:
                        match = re.fullmatch(r"dist_m4ri version (\S+)", line.strip())
                        if match:
                            version = match.group(1)
                if version is None:
                    notes.append("Executable version could not be read; parser targets bundled 0.9.0.")
                elif tuple(int(x) for x in re.findall(r"\d+", version)[:2]) >= (0, 10):
                    # from 0.10 the finished CC rounds are printed under debug bit 2, not 1
                    options["debug"] = str(int(options["debug"]) | 2)
                    notes.append("dist-m4ri %s: completed-weight trace via debug bits 1|2." % version)
                if version_killed and time.monotonic() >= deadline:
                    status = "timeout"
                certified = 1
                if bound_kind == "model" and status != "timeout":
                    wrapper = wrapper_path(binary)
                    circuit = Path(a.instance).resolve() / "circuit.stim"
                    if wrapper is None or not circuit.is_file():
                        raise ValueError("bound=model needs the build's dist_m4ri.py and the instance's circuit.stim")
                    model_path, model_lines = str(Path(temp) / "model.json"), []
                    started = time.monotonic()
                    rc, killed = run_process(
                        [sys.executable, str(Path(__file__).resolve()), "--_model-bound", str(circuit), str(wrapper),
                         binary, "method=%d" % METHODS[mode], "threads=%d" % a.threads,
                         "timeout=%.3f" % max(0.001, (deadline - started) / 2), model_path], deadline,
                        lambda stream, line: model_lines.append(line) if len(model_lines) < 30 else None)
                    if killed:
                        status = "timeout"
                    elif rc != 0:
                        raise ValueError("model bound failed: " + " | ".join(model_lines[-10:]))
                    else:
                        with open(model_path) as stream:
                            model = json.load(stream)
                        certified = int(model["bound"])
                        if certified < 1:
                            raise ValueError("model bound returned no bound")
                        tr.lb(certified)
                        if certified > 1:
                            options["dmin"] = str(certified)
                        seconds = time.monotonic() - started
                        effective.update(model_bound=certified, model_seconds=round(seconds, 3))
                        notes.append("Model bound (compute_model_lower_bound of %s, method %d, cache off): d >= %d "
                                     "from a %s x %s model of %s DEM mechanisms, model bounds %s, in %.1f s; "
                                     "passed to the binary as dmin." % (wrapper, METHODS[mode], certified,
                                     model.get("rows"), model.get("cols"), model.get("dem_cols"),
                                     model.get("model_d_info"), seconds))
                mapping = None
                if input_kind == "dem" and status != "timeout":
                    dem_path, map_path = str(Path(temp) / "input.dem"), str(Path(temp) / "map.json")
                    prep_lines = []
                    rc, killed = run_process(
                        [sys.executable, str(Path(__file__).resolve()), "--_prepare-dem",
                         str(Path(a.instance).resolve()), dem_path, map_path], deadline,
                        lambda stream, line: prep_lines.append(line) if len(prep_lines) < 30 else None)
                    if killed:
                        status = "timeout"
                    elif rc != 0:
                        raise ValueError("DEM preparation failed: " + " | ".join(prep_lines))
                    else:
                        with open(map_path) as stream:
                            mapping = json.load(stream)
                    notes.append("Undecomposed loop-flattened DEM; pmin=0 retains every mechanism. "
                                 "dist-m4ri ignores probabilities after filtering, using unit weights. "
                                 "Raw supports map to full columns with GF(2) cancellation.")
                    inputs = {"fdem": dem_path, "pmin": "0"}
                else:
                    base = Path(a.instance).resolve() / a.variant
                    inputs = {"finH": str(base) + ".H.mtx", "finL": str(base) + ".L.mtx"}
                if status != "timeout":
                    ncols = len(mapping) if mapping is not None else prob.ncols
                    if any(int(options.get(k, -1)) >= ncols for k in ("start", "cbeg", "cend")):
                        raise ValueError("CC column restriction exceeds input column count")
                    max_distance = max(ncols, int(options.get("dmax", 0)))
                    if int(options.get("dW", 0)) > 2147483647 - max_distance - 1:
                        raise ValueError("dW would overflow dist-m4ri's C weight arithmetic")
                    safe = mode != "rw" and proof_eligible(options, ncols, certified)
                    if mode == "rw":
                        notes.append("RW is heuristic; printed dmin is not a certified lower bound.")
                    elif not safe:
                        notes.append("Lower bounds suppressed: assumed bounds, skipped weights or "
                                     "restricted CC columns do not prove this run's full distance.")
                    if "finC" in options:
                        notes.append("finC explicitly seeds codewords; this is a warm-start run.")
                    if mode == "cc" and options.get("maxC") == "1":
                        notes.append("maxC=1 stops at the first CC witness after exhausting lighter weights.")
                    codeword_path = options.get("outC", str(Path(temp) / "codewords.nz"))
                    if Path(codeword_path).exists():
                        # Never mistake an old output file for a witness from this run.
                        if options.get("finC") == codeword_path:
                            raise ValueError("finC=outC is not supported; use separate files")
                        raise ValueError("outC must name a new file, not an existing codeword file")
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        status = "timeout"
                    else:
                        native_timeout = max(0.000001, remaining - min(0.1, remaining / 10))
                        configured = float(options.get("timeout", 0))
                        if configured > 0:
                            native_timeout = min(native_timeout, configured)
                        if native_limit:
                            options.update(inputs, outC=codeword_path, timeout="%.9f" % native_timeout)
                        else:
                            # 0.9.0 rejects timeout=0 for CC; a timeout far beyond the budget keeps its
                            # predictive round skipping from ever triggering
                            options.update(inputs, outC=codeword_path, timeout="1000000000")
                            notes.append("cutoff=0: native timeout 1e9 s, far beyond the budget, so the program runs "
                                         "until the wall deadline kills it (completed rounds give the lower bound; a "
                                         "codeword found by CC is exported by the program before it exits).")
                        from_stderr = stderr_witness(mode, bound_kind)
                        if from_stderr:
                            del options["outC"]
                            notes.append("Bracket mode with the model bound: no outC, so the program stops when the "
                                         "bounds meet; witnesses are the supports it prints (debug bit 32), checked here.")
                        effective.update(options)
                        command = [binary, "method=%d" % METHODS[mode]] + [
                            "%s=%s" % (key, value) for key, value in options.items()]
                        triple, diagnostics, reported_upper = None, [], []
                        native_cutoff = False

                        def on_line(stream, line):
                            nonlocal triple, native_cutoff, witness
                            if stream == "stdout" and TRIPLE.fullmatch(line):
                                triple = parse_triple(line)
                            if stream == "stderr":
                                if len(diagnostics) >= 20:
                                    diagnostics.pop(0)
                                diagnostics.append(line)
                                printed = CODEWORD.search(line) if from_stderr else None
                                if printed:
                                    support = [int(j) - 1 for j in printed.group(2).split()]
                                    if (len(support) != int(printed.group(1)) or support != sorted(set(support))
                                            or any(j < 0 or j >= ncols for j in support)):
                                        raise ValueError("invalid codeword support on stderr")
                                    candidate = map_witness(support, mapping)
                                    if not common.check_witness(prob, candidate)["ok"]:
                                        raise ValueError("printed codeword fails H/L witness verification")
                                    if tr.upper is None or len(candidate) < tr.upper:
                                        witness = candidate
                                        tr.ub(len(candidate))
                                if safe:
                                    progress = parse_progress(line)
                                    if progress:
                                        tr.lb(progress[1])
                                    found = FOUND.match(line) or COINCIDE.match(line)
                                    if found:
                                        tr.lb(int(found.group(1)))
                                match = re.search(r"RW found new upper bound cw of weight (\d+)", line)
                                if match:
                                    reported_upper.append(int(match.group(1)))
                                if "terminating early (dmin=" in line:
                                    native_cutoff = True

                        started = time.monotonic()
                        rc, killed = run_process(command, deadline, on_line)
                        duration = time.monotonic() - started
                        if triple is not None and (rc == 0 or killed):
                            lower, upper, steps = triple
                            notes.append("Native triple: %d %d %d (dmin dmax rw_steps)." % triple)
                            if safe:
                                tr.lb(lower)
                            if upper:
                                reported_upper.append(upper)
                        elif not killed:
                            raise ValueError("dist-m4ri exited %d without a result: %s" %
                                             (rc, " | ".join(diagnostics)))
                        if rc != 0 and not killed:
                            raise ValueError("dist-m4ri exited %d: %s" % (rc, " | ".join(diagnostics)))
                        if Path(codeword_path).exists():
                            for support in _codewords(codeword_path, ncols, partial=killed):
                                candidate = map_witness(support, mapping)
                                checked = common.check_witness(prob, candidate)
                                if not checked["ok"]:
                                    raise ValueError("exported codeword fails H/L witness verification")
                                if tr.upper is None or len(candidate) < tr.upper:
                                    witness = candidate
                                    tr.ub(len(candidate))
                                if time.monotonic() >= deadline + 0.2:
                                    notes.append("Codeword scan stopped after the export grace period.")
                                    break
                        if reported_upper and (tr.upper is None or min(reported_upper) < tr.upper):
                            notes.append("Native upper estimate %d has no exported verified witness; "
                                         "it is not reported as upper_bound." % min(reported_upper))
                        if tr.lower is not None and tr.upper is not None and tr.lower > tr.upper:
                            raise ValueError("native lower bound contradicts verified witness")
                        budget_finished = (triple is not None and (
                            mode == "rw" and triple[2] >= int(options.get("steps", 1000)) or
                            mode == "cc" and int(options.get("wmax", 0)) > 0 and
                            triple[0] > int(options["wmax"])))
                        if killed:
                            status = "timeout"
                            notes.append("Wall deadline reached; process group killed. "
                                         "Only completed proofs and available checked witnesses retained.")
                        elif tr.lower is not None and tr.lower == tr.upper:
                            status = "exact"
                        elif native_cutoff or duration >= native_timeout and not budget_finished:
                            status = "timeout"
                            notes.append("Native timeout or predictive timeout cutoff reached.")
                        else:
                            status = "bounds"
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        status = "error"
        notes.append(str(exc))
    common.save_result(a.out, prob, "distm4ri", tr, status, a.threads, a.time_limit,
                       witness=witness, config=effective, notes=" ".join(notes), version=version)
    print(status, tr.lower, tr.upper, tr.seconds())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--_prepare-dem":
        prepare_dem(*sys.argv[2:])
    elif len(sys.argv) > 1 and sys.argv[1] == "--_model-bound":
        model_bound(*sys.argv[2:])
    else:
        main()
