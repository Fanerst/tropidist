# tropidist: certified code and circuit distances

The distance of a quantum error-correcting code is the least weight of an undetectable logical error. The circuit
distance of a syndrome-extraction circuit is the least number of faults that flip a logical observable without
changing any detector. This repository computes both exactly. Each value comes with a certificate: a proof by
exhaustion that no lighter error exists, and an explicit error of that weight, which for circuits is replayed in Stim.
Where a run does not finish, the result is the interval between the two.

Each distance is a minimum of tropical partition functions. Three exact evaluators compute it:
- a dense rank-based dynamic program (Rank DP), whose cost depends on the width of the problem and not on the distance;
- a sparse Rank DP truncated at a weight threshold, with a meet-in-the-middle split;
- a weight-bounded search with completion tables and the symmetry of the code.

For circuits, certified relaxations first shrink the problem: an exact reduction to the detectors of one memory basis,
a collapse of all rounds into one that bounds the distance from below, and lifting of the collapsed solutions back to
the circuit.

The method and the results are described in the paper *Certifying quantum code and circuit distances at scale* by
Bin Cheng, Naixu Guo and Feng Pan, [arXiv:2611.08247](https://arxiv.org/abs/2611.08247) (2026).

## Results in brief

- **Benchmark, 74 hardware-scale codes and circuits.** With one thread and 600 s per run the method certifies 59,
  and 70 once a second tier of 32 threads and one hour is added. All other exact solvers combined certify 38 and 53.
  Records: `results/bench`, `results/bench_tierB`; report: [docs/BENCHMARK.md](docs/BENCHMARK.md).
- **The prior benchmark** (Webster, Jacob and Higgott, arXiv:2603.22532), 126 CSS codes and circuits. Under its own
  limits (one core, 8 GB, eight hours) the method certifies 95, against 73 for its five exact methods together. Every
  value they certify agrees with ours.
- **Scale.** The largest certified cases are a code distance of 24 for the modular hyperbolic code
  [[31200,1954]], and memory circuits with up to 8×10^5 fault mechanisms.
- **Audit of 26 recent papers.** In ten of them, published code or circuit distances are higher than the certified
  values, by at least eight in the worst case: [docs/AUDIT.md](docs/AUDIT.md), with every value in
  [docs/audit_items.csv](docs/audit_items.csv).
- **Applications:**
  - IBM's two-gross code [[288,12,18]] has circuit distance 16 with its standard schedule, and 84 of all 8,496
    uniform depth-seven schedules reach 18 at one noisy cycle;
  - the merged codes of published logical measurements are certified;
  - gross-code chips with dead check qubits are certified one by one, in minutes per chip.

## Quick start

Requirements: Python 3.9 or later, Stim 1.15 or later, NumPy, and a C compiler available as `cc`. The kernels are
compiled on first use, with OpenMP where the compiler supports it. Run every command from the repository root.

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# circuit distance of the [[72,12,6]] bivariate bicycle memory circuit, six rounds: 6, in about a second
.venv/bin/python -m cdist circuits/bb72_r6_Z.stim --out bb72.json

# any Stim circuit, with threads and a time limit in seconds
.venv/bin/python -m cdist my_circuit.stim --threads 8 --time-limit 3600

# a code, or any problem min |e| with He = 0 and Le != 0, from two MatrixMarket files (H_X and L_X give d_Z)
.venv/bin/python -m cdist --matrices H.mtx L.mtx
```

`python -m cdist` runs the configuration used for every reported benchmark run (`bench/adapters/ours_pipeline.py`
with `dp=2`). For a CSS memory circuit whose detectors carry the coordinates (check, 0, round, type), it uses the
reduction to one memory basis, the time collapse, lifting and the translations of the detector coordinates. This
holds for the circuits in `circuits/` and those built in `papers/`. Other circuits are searched on their full detector
error model.

The record holds:
- `lower_bound` and `upper_bound`;
- `witness`, the columns of the fault set, checked against the matrices;
- `replay`, the fault set inserted into the noiseless circuit (no detector fires, the observables flip);
- `trace`, the time at which each bound was reached.

Published circuits and codes are built by the modules in `papers/`, for example:

```sh
# a rebuilt modular surface-code circuit of arXiv:2610.03682: 8
.venv/bin/python papers/run_parallel.py hypsurf q6_L5_NZ_fb Z out.json 5 3 12
# code distance of a [[128,12,8]] hyperbolic color code: 8
.venv/bin/python papers/hyperbolic_run.py out.json lins444_40_L2 20 60
```

## Reproducing the paper

| part of the paper | code | records |
|---|---|---|
| figures and Supplementary tables | `docs/make_ncs_figures.py OUTDIR` (figures and most tables), `bench/make_paper_tables.py OUTDIR` (benchmark tables); `docs/sync_paper.sh PAPER_DIR` runs both and copies their output into a checkout of the paper | all below |
| benchmark | instances exported by `bench/export_all.py` and `bench/export_wjh.py`; runs by `bench/run_matrix.py` (pinned cores, bounded memory, resumable) and `bench/tier_b.py`; one adapter per solver in `bench/adapters/` | `results/bench*` |
| audit of published values | builders and drivers in `papers/`, reading notes in `papers/new/` | `results/papers*`, `results/cornucopia`, `results/planar_dp` |
| IBM's bicycle architecture | `papers/ibm_bicycle*.py` | `results/ibm`, `results/ibm_matched`, `results/bb288_scan` |
| logical measurements | `papers/surgery_codes.py`, `papers/ssip_exact.py`, `papers/ssip_gauge_fix.py` | `results/surgery` |
| chips with dead checks | scripts in `results/defect_study` | `results/defect_study` |
| circuits of Bravyi et al.'s public code | `papers/bravyi_repo_circuit.py`, `papers/bravyi_repo_check.py` | `results/failfast` |
| replay of every circuit witness | `bench/replay_witnesses.py` | `results/bench_replay` |

[results/README.md](results/README.md) lists every folder of records. The figures and the benchmark tables also read
third-party files that are not included (below): the prior benchmark's result sheets and the mitten authors' repository.

## Layout

| path | content |
|---|---|
| `cdist/` | the library: problem construction and reductions, the search kernel (C), the dense and the truncated Rank DP, lifting, replay in Stim, and the command `python -m cdist` |
| `bench/` | the benchmark: instance registry, one adapter per solver, harness, tables; [bench/METHODS.md](bench/METHODS.md) surveys distance methods (4 October 2026) and [bench/INSTANCES.md](bench/INSTANCES.md) lists the instances |
| `papers/` | builders and drivers for published and designed circuits and codes; `papers/new/` has a reading note per paper with the choices made in rebuilding its circuits |
| `scripts/` | further drivers (top-down lifting, enumeration, windows) and one-off studies; `scripts/server/` holds the launchers of the long runs on our servers |
| `circuits/` | stored bivariate bicycle memory circuits, including the Stim files of Google's tesseract-decoder (Apache 2.0, see [circuits/NOTICE.md](circuits/NOTICE.md)) |
| `results/` | the records behind every table and figure |
| `docs/` | the audit, the benchmark report, the figure generator; [docs/notes/](docs/notes/) has the dated working notes of the development |
| `tests/` | tests of the kernels against brute force, of the builders and of the benchmark harness |

## Tests

```sh
.venv/bin/python -m pytest tests        # about two minutes
```

## External material that is not included

Third-party data and software are not redistributed here. The parts of the code that need them say so; everything
else runs without them.

| needed for | what | where it goes |
|---|---|---|
| mitten circuits (`papers/mitten_circuit.py`) | `processor_codes/mitten` of github.com/a7b/yarn, commit `1b58edd`; file list with checksums in `papers/mitten/manifest.json` | `papers/mitten/mitten/` |
| structured mitten circuits and code distances (`papers/smitten_*.py`) | `processor_codes/structured_mitten` and `processor_codes/abelian_poly_LP` of the same commit (same manifest) | `papers/mitten/structured_mitten/`, `papers/mitten/abelian_poly_LP/` |
| amplified-code circuits (`papers/amplified_circuit.py`) | github.com/zijian-liang/dp_certificates_github, commit `0772a00` | `papers/amplified/repo/` |
| cross-check of the Cornucopia circuits (`papers/cornucopia_crosscheck.py`) | github.com/ZhideLu/Cornucopia_code, commit `fc12c97` | `papers/downloads/cornucopia_repo/` |
| Kasai's codes (`papers/kasai_codes.py`) | the `.npz` files of kasai.ict.eng.isct.ac.jp/pair_partition_cpm_css_codes_20260714.html | `papers/downloads/kasai/` |
| universal adapters (`papers/surgery_codes.py`) | check matrices of Zenodo record 10.5281/zenodo.17527545 (`data_qLDPC_surgery.zip`, CC-BY 4.0) | any folder, given on the command line |
| SSIP's gross-code merges (`papers/ssip_exact.py`, `papers/ssip_gauge_fix.py`) | github.com/CQCL/SSIP, commit `8e4d771` | any folder, given on the command line |
| circuits of Bravyi et al.'s public code (`papers/bravyi_repo_check.py`) | `decoder_setup.py` of github.com/sbravyi/BivariateBicycleCodes, commit `fa77e33` | any folder, given on the command line |
| benchmark competitors (`bench/adapters/`) | dist-m4ri 0.9.0 and 0.14.7, CASHWMaxSAT-CorePlus, enMaxCDCL, Qubitserf 0.1.0, OR-Tools; Gurobi (license needed; `gurobipy`, or `gurobi_cl` from `$GUROBI_HOME/bin`) | `bench/external/`, or pass `binary=` to the adapter |
| comparison with arXiv:2603.22532 (`bench/export_wjh.py`, `bench/wjh_compare.py`), the benchmark tables and the figures | github.com/m-webster/codeDistancePYPI, commit `a4afe9c` (MIT license): its circuits, code constructions and result sheets | `papers/downloads/codedistance/` |
| new hyperbolic tilings (`papers/hyperbolic_lins.g`) | GAP 4.15 with the LINS package; the lists used for the reported results are in `results/papers4/hyperbolic/` | |

Not included because they are regenerated on demand: the exported benchmark matrices (`python bench/export_all.py`
and `python bench/export_wjh.py`; each instance keeps its `meta.json`), the circuits of `circuits/papers/`, compiled
kernels, and run logs.

## Scope

- Research code. The full pipeline expects a CSS memory experiment whose detectors carry coordinates (check, 0,
  round, type), or a small builder module per code as in `papers/`, which also supplies the symmetries.
- A circuit distance refers to the circuit as built here, from a published description, and to the stated fault
  model. Where a paper's circuit files are not public, the choices made in rebuilding it are listed in its note in
  `papers/new/`.

## License and citation

MIT; see [LICENSE](LICENSE). The third-party files in `circuits/` are under the Apache License 2.0
([circuits/NOTICE.md](circuits/NOTICE.md)). If you use this software, please cite the paper:

```bibtex
@misc{cheng2026certifying,
  title         = {Certifying quantum code and circuit distances at scale},
  author        = {Cheng, Bin and Guo, Naixu and Pan, Feng},
  year          = {2026},
  eprint        = {2611.08247},
  archivePrefix = {arXiv},
  primaryClass  = {quant-ph},
  url           = {https://arxiv.org/abs/2611.08247}
}
```
