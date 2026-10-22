"""Exported-instance adapter for the collapsed/lift/window/sector pipeline.

config: symmetry=1, cover=1, collapse=1, lift=1, window=1,
        k_coll=3, k_table=2, kmax=40.

collapse controls the standalone collapsed lower bound and the pruning table.
With collapse=0 and lift=1, collapsed solutions are still generated for lifting
and the exhaustive orbit argument.  With collapse=lift=window=0 this is the
plain weight-bounded search on the sector.  Code instances use plain search.
"""
import json
import math
import multiprocessing
import os
import signal
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common


DEFAULTS = dict(symmetry=1, cover=1, collapse=1, lift=1, window=1,
                k_coll=3, k_table=2, kmax=40, table_gb=0)
SWITCHES = ("symmetry", "cover", "collapse", "lift", "window")
TABLE_BUDGET = 1 << 30          # leave space below 2 GiB for search/Python arrays
SOL_CAP = 100000


class Deadline(Exception):
    pass


class ResourceLimit(Exception):
    pass


def configuration(values):
    unknown = set(values) - set(DEFAULTS)
    if unknown:
        raise ValueError("unknown config keys: " + ", ".join(sorted(unknown)))
    cfg = dict(DEFAULTS)
    cfg.update({k: int(v) for k, v in values.items()})
    for k in SWITCHES:
        if cfg[k] not in (0, 1):
            raise ValueError(k + " must be 0 or 1")
    for k in ("k_coll", "k_table", "kmax"):
        if not 1 <= cfg[k] <= 40:
            raise ValueError(k + " must be between 1 and 40")
    global TABLE_BUDGET
    TABLE_BUDGET = table_budget(cfg["table_gb"])
    return cfg


def table_budget(table_gb):
    """Bytes allowed for live lookup tables: `table_gb` if given, else half of the address-space
    limit the harness imposes, else 1 GiB (a laptop default)."""
    if table_gb > 0:
        return table_gb << 30
    try:
        import resource
        soft, _ = resource.getrlimit(resource.RLIMIT_AS)
        if soft not in (resource.RLIM_INFINITY, -1) and soft > 0:
            return max(1 << 30, soft // 2)
    except (ImportError, ValueError, OSError):
        pass
    return 1 << 30


def induced_perms(source, target, perms, collapsed=False):
    """Restrict row permutations, or induce them on whole time-collapse groups.

    A collapsed generator is used only when it is induced by a real-sector
    symmetry.  This makes lifting one representative of its orbit sound.
    """
    key = (lambda m: tuple(m[:2])) if collapsed else tuple
    index = {key(m): i for i, m in enumerate(target.row_meta)}
    out = []
    for perm in perms:
        image = [None] * target.nrows
        ok = len(perm) == source.nrows and sorted(perm) == list(range(source.nrows))
        if not ok:
            continue
        for r, m in enumerate(source.row_meta):
            old = index.get(key(m))
            new = index.get(key(source.row_meta[perm[r]]))
            if old is None:
                if new is not None:
                    ok = False
                    break
            elif new is None or (image[old] is not None and image[old] != new):
                ok = False
                break
            else:
                image[old] = new
        if ok and sorted(x for x in image if x is not None) == list(range(target.nrows)):
            out.append(image)
    return out


class Pipeline:
    def __init__(self, prob, cfg, trace, deadline, progress):
        from cdist import lift, problem, search, symmetry
        self.lift, self.problem, self.search, self.symmetry = lift, problem, search, symmetry
        self.prob, self.cfg, self.tr = prob, cfg, trace
        self.deadline, self.progress = deadline, progress
        self.tables = []
        self.table_bytes = 0
        self.witness = None
        self.notes = {"stages": {}, "kernel_threads": search.lib().gm_num_threads()}
        self.p = common.to_cdist(prob)
        self.sector = self.p
        self.output_cols = list(range(self.p.ncols))
        self.perms = []

    def checkpoint(self):
        self.progress(self.tr, self.witness, self.notes)

    def remaining(self):
        if self.deadline is None:
            return 0.0
        value = self.deadline - time.monotonic()
        if value <= 0:
            raise Deadline("whole-run wall-time limit reached")
        return value

    def table(self, p, k, seed=12345):
        self.remaining()
        def nbytes(kk):
            total = sum(math.comb(p.ncols, i) for i in range(min(kk, p.ncols) + 1))
            return 9 * (1 << max(10, math.ceil(math.log2(total / 0.5 + 1))))   # label-free: nine bytes per slot
        k0 = k
        while k > 1 and nbytes(k) + self.table_bytes > TABLE_BUDGET:
            k -= 1                    # a smaller table is always valid: it only moves work into the search
        if k != k0:
            self.notes.setdefault("table_k_reduced", []).append([p.ncols, k0, k])
        size = nbytes(k)
        if size + self.table_bytes > TABLE_BUDGET:
            raise ResourceLimit("live lookup tables would exceed the table budget of %.1f GiB" % (TABLE_BUDGET / 2 ** 30))
        # Register before __init__: an interruption during native construction
        # must still free a handle that has already been allocated.
        tab = self.search.Table.__new__(self.search.Table)
        self.tables.append(tab)
        tab._pipeline_bytes = size
        self.table_bytes += size
        tab.__init__(p, k, seed=seed, labelfree=True)
        self.remaining()
        return tab

    def free(self, tab):
        if getattr(tab, "handle", None):
            tab.free()
        if tab in self.tables:
            self.tables.remove(tab)
            self.table_bytes -= tab._pipeline_bytes

    def close(self):
        for tab in list(self.tables):
            self.free(tab)

    def valid_perms(self, p, candidates):
        if not self.cfg["symmetry"]:
            return []
        out, seen = [], set()
        for perm in candidates:
            self.remaining()
            key = tuple(perm)
            if (key in seen or len(perm) != p.nrows or
                    sorted(perm) != list(range(p.nrows)) or
                    all(i == x for i, x in enumerate(perm))):
                continue
            seen.add(key)
            sym = self.symmetry.from_row_perms(p, [perm])
            if sym.get("ok") and sym.get("n_symmetries_kept") == 1:
                out.append(perm)
        return out

    def sym(self, p, perms):
        self.remaining()
        if not self.cfg["symmetry"] or not perms:
            return {"ok": False}, {}
        sym = self.symmetry.from_row_perms(p, perms)
        kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {}
        return sym, kw

    def found(self, cols):
        cols = tuple(cols)
        if not self.search.verify(self.sector, cols):
            raise ValueError("pipeline produced an invalid sector witness")
        if self.tr.upper is None or len(cols) < self.tr.upper:
            self.witness = [self.output_cols[j] for j in cols]
            self.tr.ub(len(cols))
            self.checkpoint()

    def distance(self, p, stage, k, start=1, kmax=None, perms=(),
                 certify=False, witness_map=None, enum_all=False, relaxed=()):
        """Iterative deepening with one global deadline and explicit table ownership.

        certify is true only for the sector or a lower-bounding relaxation.
        Exhausted lift/window restrictions never raise the sector lower bound.
        """
        kmax = self.cfg["kmax"] if kmax is None else min(kmax, self.cfg["kmax"])
        info = self.notes["stages"].setdefault(stage, {"runs": [], "rows": p.nrows, "cols": p.ncols})
        result = {"distance": None, "solutions": [], "complete": False}
        if start > kmax:
            return result
        self.remaining()
        _, kw = self.sym(p, perms)
        S = self.search.Searcher(p, labelfree=True, **kw)
        S.build_exclusions()
        self.remaining()
        for tab, img in relaxed:
            zh, zl = tab.hashes_for(img)
            S.add_table(tab, zh, zl)
        tab = self.table(p, k)
        try:
            S.add_table(tab, exact=True)
            for K in range(start, kmax + 1):
                # Supply task_depth explicitly to avoid retries that each get
                # a fresh native time budget.  Retry with updated remaining time.
                depth = max(1, min(4 if self.cfg["cover"] else 3, K - k - 1))
                while True:
                    r = S.search(K, enum_all=enum_all, task_depth=depth,
                                 time_limit=self.remaining(), sol_cap=SOL_CAP,
                                 cover=bool(self.cfg["cover"]))
                    if r["status"] != "too_many_tasks" or depth == 1:
                        break
                    depth -= 1
                sols = sorted(set(r["solutions"]))
                for sol in sols:
                    if not self.search.verify(p, sol):
                        raise ValueError("search witness failed verification")
                info["runs"].append({key: r[key] for key in
                                     ("K", "status", "best", "seconds", "nsol_recorded")})
                if r["best"] is not None and sols:
                    sols = [s for s in sols if len(s) == r["best"]]
                    result.update(distance=r["best"], solutions=sols,
                                  complete=r["status"] == "exhausted" and r["nsol_recorded"] < SOL_CAP)
                    if witness_map is not None:
                        self.found(witness_map(sols[0]))
                    if certify:
                        # start is certified, and all previous thresholds were
                        # exhausted; a witness at this threshold closes the gap.
                        self.tr.lb(r["best"])
                elif r["status"] == "exhausted" and certify:
                    self.tr.lb(K + 1)
                self.checkpoint()
                if r["status"] == "timeout":
                    raise Deadline("search exhausted the remaining wall-time budget")
                if r["status"] == "too_many_tasks":
                    info["incomplete"] = "too_many_tasks"
                    result["complete"] = False
                    break
                if r["best"] is not None:
                    break
                result["complete"] = r["status"] == "exhausted"
            return result
        finally:
            self.free(tab)

    def prepare(self):
        # A circuit exported without a sector variant is not a CSS memory experiment (no sector
        # reduction, no time collapse): its full DEM is searched as it is, like a code instance.
        self.plain = (self.prob.meta.get("track") == "code"
                      or "sector" not in self.prob.meta.get("variants", {"sector": None}))
        if self.plain:
            self.notes["mode"] = ("code instance" if self.prob.meta.get("track") == "code" else
                                  "circuit without CSS sectors") + ": plain weight-bounded search (as ours.py)"
            self.perms = self.valid_perms(self.p, self.prob.perms or [])
            return
        if self.prob.variant not in ("full", "sector"):
            raise ValueError("circuit pipeline requires variant full or sector")
        if any(len(m) != 4 for m in self.p.row_meta):
            raise ValueError("circuit rows must carry [check, 0, round, type] metadata")
        candidates = self.prob.perms or []
        if self.prob.variant == "full":
            self.sector = self.problem.sector_problem(self.p)
            if not self.problem.sector_is_exact(self.p, self.sector):
                raise ValueError("full-to-sector reduction is not exact")
            candidates = induced_perms(self.p, self.sector, candidates)
            rows = self.sector.notes["sector_rows"]
            full_index = {(a, b): j for j, (a, b) in enumerate(zip(self.p.h, self.p.l))}
            # A projected column's first parent may have extra detectors.  Use
            # the full column with exactly the embedded sector syndrome instead.
            self.output_cols = [full_index[(sum(1 << rows[r] for r in common.bits(a)), b)]
                                for a, b in zip(self.sector.h, self.sector.l)]
            self.notes["sector_reduction_exact"] = True
        self.perms = self.valid_perms(self.sector, candidates)
        self.notes["mode"] = "circuit collapsed/lift/window/sector pipeline"
        self.notes["sector_symmetries_used"] = len(self.perms)
        if self.cfg["lift"] and not self.cfg["collapse"]:
            self.notes["collapse_off_lift_on"] = (
                "collapsed search supplies lift candidates only; no standalone collapsed LB or pruning table; "
                "the exhaustive no-lift orbit proof remains enabled")
        self.checkpoint()

    def lift_classes(self, coll, classes, slack, stage):
        cols = [i for j in classes for i in coll.col_meta[j]]
        if slack:
            cols.extend(i for i, img in enumerate(coll.image) if img == 0 and self.sector.l[i] == 0)
        cols = sorted(set(cols))
        sub = self.problem.Problem("lift", self.sector.nrows, self.sector.nobs,
                                   [self.sector.h[i] for i in cols], [self.sector.l[i] for i in cols],
                                   self.sector.row_meta)
        # every solution of the restriction is a sector solution, so its weight is at least the certified lower
        # bound: thresholds below it need no search (before 2026-10-21 this started at 1, which is valid but slow)
        return self.distance(sub, stage, self.cfg["k_table"] if not slack else 1,
                             start=self.tr.lower, kmax=len(classes) + slack,
                             witness_map=lambda sol: [cols[j] for j in sol])

    def window(self, round_, start, kmax, stage):
        self.remaining()
        win = self.problem.window_problem(self.sector, round_, round_)
        perms = induced_perms(self.sector, win, self.perms)
        return self.distance(win, stage, self.cfg["k_table"], start=start, kmax=kmax,
                             perms=perms, witness_map=lambda sol: [win.col_meta[j] for j in sol])

    def run(self):
        self.prepare()
        if self.plain:
            self.distance(self.sector, "plain", self.cfg["k_table"], perms=self.perms,
                          certify=True, witness_map=list)
            return
        coll = None
        rc = None
        cperms = []
        csym = {"ok": False}
        if self.cfg["collapse"] or self.cfg["lift"]:
            coll = self.problem.collapse_time(self.sector)
            cperms = self.valid_perms(coll, induced_perms(self.sector, coll, self.perms, collapsed=True))
            csym, _ = self.sym(coll, cperms)
            rc = self.distance(coll, "collapsed", self.cfg["k_coll"], perms=cperms,
                               certify=bool(self.cfg["collapse"]))
        d_coll = rc["distance"] if rc else None
        if d_coll is not None:
            if self.cfg["lift"]:
                for i, sol in enumerate(rc["solutions"][:20]):
                    self.lift_classes(coll, sol, 0, "quick_lift_" + str(i))
                    if self.tr.upper is not None:
                        break
            if self.cfg["window"] and self.tr.upper is None:
                for tw in (0, 1):
                    self.window(tw, d_coll, d_coll, "window_t%d_at_d_coll" % tw)
                    if self.tr.upper is not None:
                        break
            if self.cfg["lift"] and self.tr.upper is None:
                enum = self.distance(coll, "collapsed_minimum_enumeration", self.cfg["k_coll"],
                                     start=d_coll, kmax=d_coll, perms=cperms, enum_all=True)
                maps = csym.get("colmaps", []) if csym.get("ok") else []
                reps = self.lift.orbit_representatives(enum["solutions"], maps)
                complete = enum["complete"] and bool(reps)
                self.notes["minimum_orbits"] = len(reps)
                self.notes["minimum_enumeration_complete"] = complete
                for slack in (0, 1):
                    all_exhausted = complete
                    for i, (rep, _) in enumerate(reps):
                        r = self.lift_classes(coll, rep, slack, "orbit_lift_%d_%d" % (slack, i))
                        all_exhausted = all_exhausted and r["complete"] and r["distance"] is None
                        if self.tr.upper is not None:
                            break
                    if slack == 0 and all_exhausted:
                        self.tr.lb(d_coll + 1)
                        self.notes["orbit_lower_bound"] = d_coll + 1
                    self.checkpoint()
                    if self.tr.upper is not None:
                        break
        if self.tr.upper is not None and self.tr.lower == self.tr.upper:
            return
        if self.cfg["window"]:
            self.window(1, self.tr.lower, self.tr.upper - 1 if self.tr.upper else self.cfg["kmax"],
                        "window_t1")
        if self.tr.upper is not None and self.tr.lower == self.tr.upper:
            return
        ctab = None
        try:
            relaxed = []
            if self.cfg["collapse"]:
                ctab = self.table(coll, self.cfg["k_coll"], seed=777)
                relaxed = [(ctab, coll.image)]
            self.distance(self.sector, "sector", self.cfg["k_table"], start=self.tr.lower,
                          kmax=self.tr.upper - 1 if self.tr.upper else self.cfg["kmax"],
                          perms=self.perms, certify=True, witness_map=list, relaxed=relaxed)
        finally:
            if ctab is not None:
                self.free(ctab)


def worker(prob, cfg, t0, deadline, conn):
    """The parent can stop untimed native table construction at the wall limit."""
    tr = common.Trace()
    tr.t0 = t0
    pipeline = None
    witness = None
    notes = {}

    def progress(trace, wit, detail):
        conn.send(dict(events=trace.events, lower=trace.lower, upper=trace.upper,
                       witness=wit, notes=detail))

    def stop(signum, frame):
        raise Deadline("whole-run wall-time limit reached")

    signal.signal(signal.SIGTERM, stop)
    tr.lb(1)
    progress(tr, witness, notes)
    status = "bounds"
    try:
        pipeline = Pipeline(prob, cfg, tr, deadline, progress)
        pipeline.run()
        status = "exact" if tr.upper is not None and tr.lower == tr.upper else "bounds"
    except Deadline as exc:
        status = "timeout"
        notes["stop_reason"] = str(exc)
    except (ImportError, OSError) as exc:
        status = "unavailable"
        notes["error"] = str(exc)
    except (ResourceLimit, MemoryError) as exc:
        notes["stop_reason"] = str(exc) or "memory allocation failed"
    except Exception as exc:
        status = "error"
        notes["error"] = "%s: %s" % (type(exc).__name__, exc)
    finally:
        # Disable further termination exceptions while freeing native handles.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if pipeline is not None:
            pipeline.close()
            witness = pipeline.witness
            notes = dict(pipeline.notes, **notes)
        progress(tr, witness, notes)
        conn.send({"status": status})
        conn.close()


def record_header(instance, variant):
    """Metadata sufficient to report a timeout before matrix loading completes.

    No witness is reported on this path, so save_result does not need the
    matrices.  Reading only the MatrixMarket headers keeps shutdown bounded.
    """
    with open(os.path.join(instance, "meta.json")) as f:
        meta = json.load(f)

    def shape(kind):
        with open(os.path.join(instance, variant + "." + kind + ".mtx")) as f:
            for line in f:
                if line.strip() and not line.startswith("%"):
                    return tuple(map(int, line.split()[:2]))
        raise ValueError("missing MatrixMarket dimensions")

    nrows, ncols = shape("H")
    nobs, lcols = shape("L")
    if ncols != lcols:
        raise ValueError("H and L have different column counts")
    truth = meta.get("variants", {}).get(variant, {})
    return SimpleNamespace(name=meta["name"], variant=variant, nrows=nrows, ncols=ncols,
                           nobs=nobs, distance=truth.get("distance"),
                           distance_kind=truth.get("distance_kind"))


def main():
    a = common.adapter_args(__doc__)
    tr = common.Trace()                 # includes reading and full-sector reduction
    started = time.monotonic()
    deadline = started + a.time_limit if a.time_limit > 0 else None
    os.environ["OMP_NUM_THREADS"] = str(a.threads)
    # MatrixMarket reading is Python code: unlike native table construction,
    # it can be interrupted directly without a worker or partial model.
    def loading_timeout(signum, frame):
        raise Deadline("wall-time limit reached while reading the instance")

    old_handler = signal.signal(signal.SIGALRM, loading_timeout)
    try:
        if deadline is not None:
            signal.setitimer(signal.ITIMER_REAL, max(0.000001, deadline - time.monotonic()))
        prob = common.load(a.instance, a.variant)
    except Deadline as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        prob = record_header(a.instance, a.variant)
        tr.lb(1)
        common.save_result(a.out, prob, "ours_pipeline", tr, "timeout", a.threads, a.time_limit,
                           config=a.cfg, notes=str(exc))
        print("timeout", tr.lower, tr.upper, tr.seconds())
        return
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
    witness, detail = None, {}
    status = "error"
    cfg = a.cfg
    try:
        cfg = configuration(a.cfg)
        if a.threads < 1:
            raise ValueError("threads must be positive")
        # Spawn before loading numpy/the kernel, so OpenMP sees the requested
        # environment, and bound the entire worker (including model builds).
        ctx = multiprocessing.get_context("spawn")
        parent, child = ctx.Pipe(duplex=False)
        proc = ctx.Process(target=worker, args=(prob, cfg, tr.t0, deadline, child))
        proc.start()
        child.close()
        finished = False
        while True:
            if parent.poll(0.02):
                try:
                    update = parent.recv()
                except EOFError:
                    break
                if "status" in update:
                    status, finished = update["status"], True
                    break
                tr.events, tr.lower, tr.upper = update["events"], update["lower"], update["upper"]
                witness, detail = update["witness"], update["notes"]
            if deadline is not None and time.monotonic() >= deadline:
                status = "timeout"
                detail["stop_reason"] = "whole-run wall-time limit reached"
                break
            if not proc.is_alive() and not parent.poll():
                break
        if not finished and proc.is_alive():
            proc.terminate()
        proc.join(timeout=1.0)
        if proc.is_alive():
            proc.kill()
            proc.join(timeout=1.0)
        # Preserve the last bounds/witness even when native code returned as
        # termination was requested.  Final worker status cannot undo timeout.
        while parent.poll():
            try:
                update = parent.recv()
            except EOFError:
                break
            if "events" in update:
                tr.events, tr.lower, tr.upper = update["events"], update["lower"], update["upper"]
                witness = update["witness"]
                stop_reason = detail.get("stop_reason") if status == "timeout" else None
                detail = update["notes"]
                if stop_reason:
                    detail["stop_reason"] = stop_reason
        if not finished and status != "timeout":
            detail["error"] = "pipeline worker exited without a final record (exit code %s)" % proc.exitcode
        parent.close()
    except Exception as exc:
        detail["error"] = "%s: %s" % (type(exc).__name__, exc)
    actual = detail.get("kernel_threads")
    if actual is not None and actual != a.threads:
        detail["threads_note"] = "kernel uses %d threads; requested %d (build ignores the request)" % (actual, a.threads)
    common.save_result(a.out, prob, "ours_pipeline", tr, status, a.threads, a.time_limit,
                       witness=witness, config=cfg, notes=json.dumps(detail, sort_keys=True))
    print(status, tr.lower, tr.upper, tr.seconds())


if __name__ == "__main__":
    main()
