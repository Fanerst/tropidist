"""What the benchmark tests expect on a fresh checkout, under pytest: the two fixture instances of
bench/make_fixtures.py (only their meta.json is tracked) and the ignored scratch folders the tests write into.
Run as scripts, the tests need `python bench/make_fixtures.py` first."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pytest_sessionstart(session):
    fixtures = (("fx_bb72_code", "full.H.mtx"), ("fx_sdbb16_r3", "circuit.stim"))
    if not all(os.path.exists(os.path.join(ROOT, "bench", "instances", *f)) for f in fixtures):
        subprocess.run([sys.executable, os.path.join(ROOT, "bench", "make_fixtures.py")], check=True,
                       stdout=subprocess.DEVNULL)
    for d in ("results/bench_dev/distm4ri", "results/bench_dev/heuristics", "results/bench_dev/solvers",
              "logs/bench_dev/solvers"):
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
