"""Export memory instructions of papers/ibm_bicycle.py (IBM's setting) as benchmark instances (bench/common.py
format: variants full, sector and collapsed, with the lattice translations as symmetries), so that the benchmark's
pipeline certifies their distance:

    python papers/ibm_bicycle_export.py KEY BASIS CYCLES ROOT          (schedule from IBM_SCHEDULE)
    python bench/adapters/ours_pipeline.py --instance ROOT/NAME --variant sector --config dp=2 \
        --threads 32 --time-limit 7200 --out OUT.json
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT, os.path.join(ROOT, "bench")]

import bb6_depth7 as B
import common
import ibm_bicycle as IB
import stabcode


def main(key, basis, cycles, root):
    cycles = int(cycles)
    sched, stag = IB.schedule_from_env()
    circ = IB.build_instruction(key, basis, cycles, 1e-3, sched)
    n, k = stabcode.css_parameters(*B.matrices(key))
    name = f"ibm_{key}_{stag}_c{cycles}_{basis}"
    meta = {"track": "circuit", "family": "ibm_bicycle", "n": n, "k": k, "basis": basis, "rounds": cycles,
            "description": f"{key} memory instruction, {cycles} noisy cycle(s) between noise-free boundaries, "
                           f"schedule {stag}, the setting of arXiv:2506.03094",
            "source": {"builder": "papers/ibm_bicycle.py", "key": key, "schedule": stag, "cycles": cycles}}
    out = common.export_circuit_instance(name, circ, B.translations(key), meta, root=root)
    print(name, {v: (x["rows"], x["cols"], x["symmetries"]) for v, x in out["variants"].items()})


if __name__ == "__main__":
    main(*sys.argv[1:])
