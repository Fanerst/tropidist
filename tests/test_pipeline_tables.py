"""The pipeline's lookup tables (bench/adapters/ours_pipeline.py): built up front within EAGER_TABLE_BYTES, and
deepened during the search only after a paired trial on a sample of the anchors.  The answer must not depend on
the depth, the trial must be recorded, and no table may outlive its search."""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "bench"), os.path.join(ROOT, "bench", "adapters")]

import common
import ours_pipeline as OP
import stim_families


def run(prob, values, **constants):
    saved = {k: getattr(OP, k) for k in constants}
    try:
        cfg = OP.configuration(values)
        for k, v in constants.items():
            setattr(OP, k, v)
        tr = common.Trace()
        tr.t0 = time.monotonic()
        tr.lb(1)
        pipe = OP.Pipeline(prob, cfg, tr, time.monotonic() + 120, lambda trace, wit, notes: None)
        try:
            pipe.run()
        finally:
            pipe.close()
        assert pipe.tables == [] and pipe.table_bytes == 0
        return tr, pipe
    finally:
        for k, v in saved.items():
            setattr(OP, k, v)


def trials(pipe):
    return [t for st in pipe.notes["stages"].values() for t in st.get("deepen", [])]


def test_deepening(tmp_path):
    circ, _ = stim_families.surface_circuit(5)
    meta = {"family": "surface", "description": "test", "n": 25, "k": 1, "basis": "Z", "rounds": 5,
            "source": "stim_families.surface_circuit(5)", "truth": {"sector": (5, "exact", "graph-like distance")}}
    common.export_circuit_instance("surf5", circ, [], meta, root=str(tmp_path))
    prob = common.load(str(tmp_path / "surf5"), "sector")
    plain = {"collapse": 0, "lift": 0, "window": 0}       # the sector search alone, from weight 1
    # Tables of depth 1 up front, and a trial after every exhausted level. A required gain of 0 keeps every
    # deeper table, an infinite one none.
    for gain, decision in ((0.0, "deeper table"), (float("inf"), "kept")):
        tr, pipe = run(prob, plain, EAGER_TABLE_BYTES=1, DEEPEN_FACTOR=0.0, DEEPEN_GAIN=gain)
        assert tr.lower == tr.upper == 5 and common.check_witness(prob, pipe.witness)
        ts = trials(pipe)
        assert ts and {t["decision"] for t in ts} == {decision}, ts
        assert len(ts) == 1 and ts[0]["sample_anchors"] >= 1 and ts[0]["k"] == 2, ts   # k_table = 2: one step
    # deepen=0: depth 1 throughout, no trial
    tr, pipe = run(prob, dict(plain, deepen=0), EAGER_TABLE_BYTES=1, DEEPEN_FACTOR=0.0)
    assert tr.lower == tr.upper == 5 and not trials(pipe)
    # the defaults on this small circuit: depth 2 up front, so nothing to deepen
    tr, pipe = run(prob, {})
    assert tr.lower == tr.upper == 5 and not trials(pipe)
