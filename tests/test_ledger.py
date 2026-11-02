"""The task ledger of the search kernel (search.set_ledger): a threshold interrupted or split between machines must end with the same answer as
one uninterrupted run, nothing else may ever report a threshold as exhausted, and a ledger must never carry over to another problem or
turn on by itself.  Run directly or with pytest."""
import glob
import importlib.util
import os
import random
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bench"))

from cdist import search
from cdist.problem import Problem


def sample_problem(seed=7, rows=64, cols=100, weight=3):
    """A random sparse problem with one logical label: enough tasks, and a distance of several columns."""
    rng = random.Random(seed)
    h = [sum(1 << r for r in rng.sample(range(rows), weight)) for _ in range(cols)]
    lg = [rng.randrange(2) for _ in range(cols)]
    return Problem("sample", rows, 1, h, lg, [()] * cols)


def run(p, K, path=None, part=(0, 1), **kw):
    S = search.Searcher(p, labelfree=False)
    t = search.Table(p, 1)
    S.add_table(t, exact=True)
    search.set_ledger(path, part)
    try:
        return S.search(K, task_depth=2, **kw)
    finally:
        search.set_ledger()
        t.free()


def distance_of(p):
    d = search.distance(p, k_table=1, kmax=14)
    assert d["distance"] is not None
    return d["distance"]


def ledger_file(path):
    files = glob.glob(path + ".K*")
    assert len(files) == 1, files
    return files[0]


def lines(path):
    with open(path) as f:
        return f.read().splitlines()


def test_ledger_matches_a_plain_run_and_resumes():
    p = sample_problem()
    K = distance_of(p) - 1
    plain = run(p, K)
    assert plain["status"] == "exhausted" and plain["tasks"] > 10
    with tempfile.TemporaryDirectory() as tmp:
        path = tmp + "/ledger"
        first = run(p, K, path)
        assert first["status"] == "exhausted" and first["nodes"] == plain["nodes"] and first["tasks"] == plain["tasks"]
        body = lines(ledger_file(path))
        assert body[0].startswith("gm_ledger") and len(body) == plain["tasks"] + 1
        again = run(p, K, path)      # every task is in the ledger: nothing below the prefixes runs
        assert again["status"] == "exhausted" and sum(again["nodes"]) < sum(plain["nodes"])
        assert sum(again["nodes"][3:]) == 0


def test_a_solution_is_found_through_the_ledger():
    p = sample_problem()
    d = distance_of(p)
    with tempfile.TemporaryDirectory() as tmp:
        r = run(p, d, tmp + "/ledger")
        assert r["status"] == "found" and r["best"] == d
        assert search.verify(p, r["solutions"][0])


def test_a_lost_task_is_searched_again():
    """Remove tasks from the ledger as a crash would: the rest is skipped, the removed ones run, and the answer stands."""
    p = sample_problem()
    K = distance_of(p) - 1
    with tempfile.TemporaryDirectory() as tmp:
        path = tmp + "/ledger"
        full = run(p, K, path)
        f = ledger_file(path)
        body = lines(f)
        keep = body[:1 + len(body) // 2]
        with open(f, "w") as out:
            out.write("\n".join(keep) + "\n" + body[len(keep)][:3])     # a line cut by a crash: no newline at the end
        resumed = run(p, K, path)
        assert resumed["status"] == "exhausted"
        assert 0 < sum(resumed["nodes"][3:]) < sum(full["nodes"][3:])
        got = {x.split()[0] for x in lines(f)[1:] if len(x.split()) == 2}   # the ledger holds every task again
        assert len(got) == full["tasks"]


def test_a_line_with_a_wrong_check_does_not_mark_a_task():
    p = sample_problem()
    K = distance_of(p) - 1
    with tempfile.TemporaryDirectory() as tmp:
        path = tmp + "/ledger"
        full = run(p, K, path)
        f = ledger_file(path)
        body = lines(f)
        with open(f, "w") as out:                     # keep the header only, plus lines whose check value is wrong
            out.write(body[0] + "\n" + "".join("%d 0\n" % i for i in range(full["tasks"])))
        again = run(p, K, path)
        assert again["status"] == "exhausted" and again["nodes"] == full["nodes"]


def test_a_problem_with_the_same_tasks_gets_its_own_ledger():
    """Same syndromes, so the same task list, but other logical labels: a finished ledger of one must not exhaust the other (external review,
    2026-11-02: the first version hashed only the task list and reported this threshold exhausted, missing a witness of weight 10)."""
    p = sample_problem()
    d = distance_of(p)
    zero = Problem("zero labels", p.nrows, 1, p.h, [0] * p.ncols, p.row_meta)
    with tempfile.TemporaryDirectory() as tmp:
        path = tmp + "/ledger"
        old = run(zero, d, path)
        assert old["status"] == "exhausted"
        new = run(p, d, path)
        assert new["tasks"] == old["tasks"] and new["status"] == "found" and new["best"] == d
        assert len(glob.glob(path + ".K*")) == 2


def test_a_header_that_disagrees_is_refused():
    p = sample_problem()
    K = distance_of(p) - 1
    with tempfile.TemporaryDirectory() as tmp:
        path = tmp + "/ledger"
        run(p, K, path)
        f = ledger_file(path)
        body = lines(f)
        with open(f, "w") as out:
            out.write(body[0].replace("tasks=", "tasks=9") + "\n")
        try:
            run(p, K, path)
        except RuntimeError as e:
            assert "ledger" in str(e)
        else:
            raise AssertionError("a ledger whose header disagrees was accepted")


def test_slices_are_not_exhaustive_until_merged():
    p = sample_problem()
    K = distance_of(p) - 1
    plain = run(p, K)
    with tempfile.TemporaryDirectory() as tmp:
        a, b = tmp + "/a", tmp + "/b"
        ra = run(p, K, a, (0, 2))
        assert ra["status"] == "slice_done" and not ra["solutions_complete"]
        rb = run(p, K, b, (1, 2))
        assert rb["status"] == "slice_done"
        fa, fb = ledger_file(a), ledger_file(b)
        la, lb = lines(fa), lines(fb)
        assert la[0] == lb[0] and len(la) + len(lb) - 2 == plain["tasks"]
        # slices with different moduli may cover the tasks too
        for part in ((0, 2), (1, 4), (3, 4)):
            run(p, K, tmp + "/mixed", part)
        assert run(p, K, tmp + "/mixed")["status"] == "exhausted"
        assert sum(run(p, K, tmp + "/mixed")["nodes"][3:]) == 0
        # a threshold with slices only does not raise the lower bound
        search.set_ledger(tmp + "/c", (0, 2))
        try:
            dist = search.distance(p, k_table=1, kmax=K, start=K)
            assert dist["lower_bound"] == K and dist["runs"][-1]["status"] == "slice_done"
        finally:
            search.set_ledger()
        # merged, a run without a slice finds every task finished and only then reports the threshold exhausted
        name = os.path.basename(fa).replace("a.K", "m.K")
        with open(os.path.join(tmp, name), "w") as out:
            out.write("\n".join(la + lb) + "\n")
        final = run(p, K, tmp + "/m")
        assert final["status"] == "exhausted" and sum(final["nodes"][3:]) == 0
        # with one slice missing the run searches that slice itself
        name = os.path.basename(fa).replace("a.K", "q.K")
        with open(os.path.join(tmp, name), "w") as out:
            out.write("\n".join(la) + "\n")
        rest = run(p, K, tmp + "/q")
        assert rest["status"] == "exhausted" and sum(rest["nodes"][3:]) == sum(rb["nodes"][3:])


def test_a_stopped_task_is_not_marked():
    p = sample_problem()
    d = distance_of(p)
    with tempfile.TemporaryDirectory() as tmp:
        path = tmp + "/ledger"
        stopped = run(p, d, path, time_limit=1e-9)
        # one thread sees the deadline in its first task; with more, a short task may finish first, and then it is rightly marked
        if search.lib().gm_num_threads() == 1:
            assert stopped["status"] == "timeout" and len(lines(ledger_file(path))) == 1
        resumed = run(p, d, path)
        assert resumed["status"] == "found" and resumed["best"] == d and search.verify(p, resumed["solutions"][0])


def test_a_malformed_part_is_refused():
    try:
        search.set_ledger("x", (2, 2))
    except ValueError:
        pass
    else:
        raise AssertionError("a slice outside its range was accepted")
    search.set_ledger()


def test_the_environment_turns_nothing_on():
    """The benchmark pipeline must never see a ledger or a slice (external review, 2026-11-02: with GM_SLICE in the environment the first version
    let the pipeline certify exact 8 on a problem of distance 6)."""
    spec = importlib.util.spec_from_file_location("ours_pipeline_review", os.path.join(ROOT, "bench", "adapters", "ours_pipeline.py"))
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    h, labels = [], []
    for length, offset in [(6, 0), (8, 6)]:
        for j in range(length):
            h.append((1 << (offset + j)) | (1 << (offset + (j + 1) % length)))
            labels.append(int(j == 0))
    problem = adapter.common.Prob("cycles 6 and 8", "full", 14, 1, h, labels, {"track": "code"})
    config = adapter.configuration({"symmetry": 0, "cover": 0, "k_table": 1, "kmax": 8, "dp": 0})
    trace = adapter.common.Trace()
    pipeline = adapter.Pipeline(problem, config, trace, None, lambda *args: None)
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["GM_SLICE"] = "1/2"
        os.environ["GM_LEDGER"] = tmp + "/env"
        try:
            pipeline.run()
            assert trace.lower == trace.upper == 6
            assert not glob.glob(tmp + "/env*")
        finally:
            pipeline.close()
            os.environ.pop("GM_SLICE")
            os.environ.pop("GM_LEDGER")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
