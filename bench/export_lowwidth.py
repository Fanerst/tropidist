"""Trial instances for the regime of small decomposition width and large distance, where the dense Rank DP should
beat search-based methods: code-capacity problems of

  color_cc_d{d}        triangular 6.6.6 color codes, d = 11..35 (plaquettes read off Stim's color_code:memory_xyz
                       circuit, as in scripts/dp_vs_search_local.py); three checks per bulk qubit, so not graph-like
  concat_steane_L{L}   the Steane code concatenated L times, [[7^L, 1, 3^L]] (checks of every level, with the
                       weight-3 logical representative of each block)
  hypercube_L{L}       many-hypercube codes (concatenated [[6,4,2]], [[6^L, 4^L, 2^L]]), a contrast: their many
                       logical qubits make every top-level cut wide

Each is written like the code instances of the benchmark (bench/common.export_code_instance) into
bench/instances_lowwidth/, a separate directory: these are not part of the standard benchmark.

usage: python bench/export_lowwidth.py [out_dir]
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT), str(ROOT / "papers"), str(ROOT / "scripts")]
import common
import stabcode

STEANE_CHECKS = [0b1010101, 0b1100110, 0b1111000]       # Hamming [7,4,3]; bit i is qubit i
STEANE_LOGICAL = 0b0000111                               # weight-3 logical representative (qubits 0, 1, 2)


def concat_steane(L):
    def logical(level, start):
        if level == 0:
            return 1 << start
        size = 7 ** (level - 1)
        return sum(logical(level - 1, start + i * size) for i in range(7) if (STEANE_LOGICAL >> i) & 1)
    checks = []
    for level in range(1, L + 1):
        size = 7 ** (level - 1)
        for start in range(0, 7 ** L, 7 ** level):
            subs = [logical(level - 1, start + i * size) for i in range(7)]
            checks += [sum(subs[i] for i in range(7) if (h >> i) & 1) for h in STEANE_CHECKS]
    return checks, list(checks), 7 ** L                  # self-dual: H_X = H_Z


def hypercube(L):
    """Concatenated [[6,4,2]] (stabilisers X^6, Z^6; logicals X_0 X_{m+1}, Z_{m+1} Z_5, m = 0..3): a level-l block
    is six level-(l-1) blocks; for each logical index j of the sub-blocks one [[6,4,2]] code acts on their j-th
    logical qubits."""
    def block(level, start):
        """(X checks, Z checks, X logicals, Z logicals) of the block of 6^level qubits starting at `start`."""
        if level == 0:
            return [], [], [1 << start], [1 << start]
        size = 6 ** (level - 1)
        subs = [block(level - 1, start + i * size) for i in range(6)]
        xs = [c for s in subs for c in s[0]]
        zs = [c for s in subs for c in s[1]]
        xl, zl = [], []
        for j in range(len(subs[0][2])):
            xs.append(sum(s[2][j] for s in subs))
            zs.append(sum(s[3][j] for s in subs))
            for m in range(4):
                xl.append(subs[0][2][j] ^ subs[m + 1][2][j])
                zl.append(subs[m + 1][3][j] ^ subs[5][3][j])
        return xs, zs, xl, zl
    xs, zs, _, _ = block(L, 0)
    return xs, zs, 6 ** L


def main(out=str(HERE / "instances_lowwidth")):
    import dp_vs_search_local as dvs
    specs = [("color_cc_d%d" % d, "color_cc", lambda d=d: dvs.color_code(d), d,
              "triangular 6.6.6 color code") for d in (11, 15, 19, 23, 27, 31, 35)]
    specs += [("concat_steane_L%d" % L, "concat_steane", lambda L=L: concat_steane(L), 3 ** L,
               "Steane code concatenated %d times" % L) for L in (2, 3, 4)]
    specs += [("hypercube_L%d" % L, "hypercube", lambda L=L: hypercube(L), 2 ** L,
               "many-hypercube code (concatenated [[6,4,2]])") for L in (2, 3, 4)]
    for name, family, build, d, source in specs:
        hx, hz, n = build()
        _, k = stabcode.css_parameters(hx, hz, n)
        meta = {"family": family, "k": k, "rounds": None, "description": "%s, [[%d,%d,%d]]" % (source, n, k, d),
                "source": {"track": "code", "family": family, "builder": "bench/export_lowwidth.py", "key": name},
                "truth": {"full": (d, "exact", source)}}
        out_meta = common.export_code_instance(name, hx, hz, n, "Z", None, meta, root=out)
        v = out_meta["variants"]["full"]
        print(name, "[[%d,%d,%d]]" % (n, k, d), "rows", v["rows"], "cols", v["cols"], "obs", v["obs"], flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
