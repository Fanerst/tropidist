"""Cross-check of a structured-mitten circuit distance with the dp=2 pipeline (bench/adapters/ours_pipeline.py) on
the Stim circuit itself, independent of papers/mitten_effective.py and papers/run_mitten.py: the memory circuit is
exported with bench/common.export_circuit_instance (variants full, sector, collapsed; the check symmetries are the
group translations that papers/mitten_symmetry.py keeps) and the pipeline runs on its sector problem.

usage: python papers/smitten_pipeline.py CODE BASIS out.json [rounds] [threads] [seconds] [model]
  CODE as in papers/run_mitten.py ("structured_mitten/[[330,66,12]]"); model: two (default) or single_gates, the
  fault models of papers/smitten_check.py.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT, os.path.join(ROOT, "bench")]

import common
import mitten_circuit
import mitten_effective
import mitten_symmetry
from run_mitten import code_of
from smitten_check import MODELS


def main(name, basis, out, rounds=3, threads=8, seconds=3600, model="two"):
    code_dir, tag, (n, k, d) = code_of(name)
    eff = mitten_effective.effective_problem(code_dir, basis)
    cp = common.symmetric_subset(eff, list(mitten_symmetry.candidates(code_dir, eff.nrows)))
    circ = mitten_circuit.build(code_dir, basis, int(rounds), **MODELS[model])
    inst = f"{tag}_r{rounds}_{basis}_{model}"
    meta = dict(track="circuit", family="structured_mitten", n=n, k=k, basis=basis, rounds=int(rounds),
                description=f"{name}, published hook-free schedule, fault model {model}",
                source="github.com/a7b/yarn (papers/mitten/manifest.json)")
    with tempfile.TemporaryDirectory() as tmp:
        common.export_circuit_instance(inst, circ, cp, meta, root=tmp)
        subprocess.run([sys.executable, os.path.join(ROOT, "bench", "adapters", "ours_pipeline.py"),
                        "--instance", os.path.join(tmp, inst), "--variant", "sector", "--threads", str(threads),
                        "--time-limit", str(seconds), "--out", os.path.abspath(out), "--config", "dp=2"], check=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
