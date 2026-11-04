"""python -m cdist on a stored circuit, on a Stim-generated circuit without sector coordinates, and on matrices."""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "bench"))
import common


def run(args, tmp):
    out = os.path.join(tmp, "record.json")
    subprocess.run([sys.executable, "-m", "cdist", *args, "--out", out, "--threads", "2"], cwd=ROOT, check=True,
                   capture_output=True, text=True)
    return json.load(open(out))


def test_stored_circuit():
    with tempfile.TemporaryDirectory() as tmp:
        rec = run(["circuits/bb72_r6_Z.stim"], tmp)
    assert rec["status"] == "exact" and rec["lower_bound"] == rec["upper_bound"] == 6 and rec["witness_ok"]
    assert rec["replay"]["result"] == "pass" and rec["replay"]["fired_detectors"] == []


def test_generated_circuit():
    import stim
    circ = stim.Circuit.generated("surface_code:rotated_memory_z", distance=3, rounds=3,
                                  after_clifford_depolarization=1e-3, before_measure_flip_probability=1e-3)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "surface3.stim")
        circ.to_file(path)
        rec = run([path], tmp)
    assert rec["lower_bound"] == rec["upper_bound"] == 3 and rec["replay"]["result"] == "pass"


def test_matrices():
    # Steane code: H_X and L_X give d_Z = 3
    hx = ["1010101", "0110011", "0001111"]
    lx = ["1111111"]
    cols = lambda rows: [sum(1 << r for r, row in enumerate(rows) if row[j] == "1") for j in range(7)]
    with tempfile.TemporaryDirectory() as tmp:
        common.write_mtx(os.path.join(tmp, "H.mtx"), cols(hx), len(hx))
        common.write_mtx(os.path.join(tmp, "L.mtx"), cols(lx), len(lx))
        rec = run(["--matrices", os.path.join(tmp, "H.mtx"), os.path.join(tmp, "L.mtx")], tmp)
    assert rec["status"] == "exact" and rec["lower_bound"] == rec["upper_bound"] == 3 and rec["witness_ok"]


if __name__ == "__main__":
    test_stored_circuit()
    test_generated_circuit()
    test_matrices()
    print("ok")
