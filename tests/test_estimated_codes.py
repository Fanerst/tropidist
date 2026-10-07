"""Plain verification of every rebuilt code and all required control witnesses."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "papers"))
sys.path.insert(0, str(ROOT))
import estimated_codes as codes
import stabcode


def commute(hx, hz, n):
    """Sparse-column GF(2) product, independent of the builders."""
    columns = [0] * n
    for i, row in enumerate(hz):
        for j in stabcode.bits(row):
            columns[j] ^= 1 << i
    for row in hx:
        syndrome = 0
        for j in stabcode.bits(row):
            syndrome ^= columns[j]
        assert syndrome == 0, "CSS product is nonzero"


def logical(hx, hz, n, basis, support, weight):
    assert len(support) == len(set(support)) == weight
    assert all(isinstance(j, int) and 0 <= j < n for j in support)
    v = sum(1 << j for j in support)
    checks, stabilizers = (hz, hx) if basis == "Z" else (hx, hz)
    assert all(stabcode.parity(v & row) == 0 for row in checks)
    reduced, pivots = stabcode.rref(stabilizers)
    for row, pivot in zip(reduced, pivots):
        if v >> pivot & 1:
            v ^= row
    assert v != 0, "witness lies in the stabilizer row space"


def main():
    names = [c["name"] for c in codes.CODES]
    assert len(names) == len(set(names)), "registry names must be unique"
    required = {
        "mm_t4_r5_216_12_14", "mm_t3_r5_288_12_16", "mm_t3_r6_324_12_20",
        "mm_t10_r1_630_70_9", "mm_t5_r2_96_12_8", "mm_t4_r17_486_24_12",
        "w8bb_144_6_ge15", "w8bb_72_14_8", "w8bb_144_16_10", "w8bb_144_10_12",
        "qgpu_136_8_14", "qgpu_198_18_10", "qgpu_24_8_3",
        "balanced_390_78_16", "balanced_550_110_18", "balanced_160_32_10",
        "balanced_240_48_12", "balanced_320_64_14", "llmbb_360_12_24_V",
    }
    assert required.issubset(names), required.difference(names)
    controls = 0
    for c in codes.CODES:
        assert c["status"] in {"control", "open"}
        assert all(key in c for key in ("name", "arxiv", "n", "k", "d_claimed", "locator"))
        hx, hz, n = codes.matrices(c["name"])
        assert all(isinstance(row, int) and 0 <= row < 1 << n for row in hx + hz)
        commute(hx, hz, n)
        k = n - stabcode.rank(hx) - stabcode.rank(hz)
        assert (n, k) == (c["n"], c["k"]), (c["name"], n, k)
        paper = (c.get("paper_n", n), c.get("paper_k", k))
        if paper != (n, k):
            assert c["name"] == "mm_t3_r5_288_12_16" and paper == (288, 12) and k == 0
        for perm in codes.symmetries(c["name"]):
            assert len(hx) == len(hz) == len(perm)
            assert sorted(perm) == list(range(len(hx)))
        if c["status"] == "control":
            controls += 1
            for basis in "ZX":
                support = codes.control_witness(c["name"], basis)
                logical(hx, hz, n, basis, support, c["d_claimed"])
    # Check every returned local witness, including newly certified open codes.
    out = ROOT / "results/papers3/estdist/local.json"
    verified = 0
    if out.exists():
        for c in json.loads(out.read_text())["codes"]:
            hx, hz, n = codes.matrices(c["name"])
            for basis, result in c["distance"].items():
                assert all(any(r["K"] == w and r["status"] == "exhausted" and r.get("best") is None
                               for r in result["runs"])
                           for w in range(1, result["lower_bound"]))
                if result.get("witness") is not None:
                    logical(hx, hz, n, basis, result["witness"], result["upper_bound"])
                    verified += 1
                if result.get("d") is not None:
                    assert result["d"] == result["lower_bound"] == result["upper_bound"]
            if c.get("d") is not None:
                assert c["d"] == min(r["lower_bound"] for r in c["distance"].values())
                assert c["d"] == min(r["upper_bound"] for r in c["distance"].values()
                                    if r.get("upper_bound") is not None)
    assert controls == 9
    print(f"PASS: CSS and (n,k) for {len(names)} codes; "
          f"both witnesses for {controls} controls; {verified} local witnesses")


if __name__ == "__main__":
    main()
