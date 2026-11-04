# Launchers used on our compute server

These shell scripts started the long runs behind the reports. They are kept as a record of the exact
commands and resource settings. They assume our machine: the repository checked out at
`~/claude_runs/circuit_distance`, a Python environment at `~/miniconda3/envs/planarnet`, external
solvers under `bench/external/`, and a pinned set of CPU cores. Adapt the paths at the top of each
file before using them elsewhere. All of them are meant to be run from the repository root.

| script | what it ran |
|---|---|
| `run_bb288_all.sh`, `run_post.sh` | the BB72 to BB288 study (docs/notes/BB_CIRCUITS.md) |
| `server_bb360.sh`, `server_bb360_Z_topdown.sh`, `server_bench1.sh` | covering-bound runs (docs/notes/PHASE4.md) |
| `server_cornucopia.sh`, `server_design_*.sh`, `server_remaining.sh`, `server_batch3.sh` | published circuits, batches 2 and 3 (docs/notes/PAPERS.md) |
| `chain_b.sh`, `chain_c.sh` | the benchmark passes after the first tier (docs/BENCHMARK.md) |
| `hyp_lins_queue.sh`, `hyp_queue.sh` | tiling lists with GAP and exact distances of the hyperbolic codes |
| `chain_after_dm4ri.sh`, `sparseL2_split.sh` | after the dist-m4ri 0.14.7 pass: its early-stopped second-tier runs again in pure cluster mode, and the integer-programming and SAT tools on the sparse logical basis (docs/BENCHMARK.md) |
| `redo_gurobi_d11.sh`, `redo_gurobi_w8bb.sh`, `redo_gurobi_mm324.sh`, `redo_dm4ri_rw.sh` | single runs repeated after a failure or a harness fix, as listed in docs/BENCHMARK.md |
| `rebuild_manifest.py`, `rebuild_manifest_dm4ri.py` | put back the manifest entries that harnesses running at the same time had overwritten (marked `reconstructed`) |
| `server_cornucopia_check.sh`, `server_cornucopia_isd.sh` | the check of the Cornucopia distances: one-cycle circuits in the authors' setting, the large memory circuits with the covering bound, and the randomized witness search (docs/notes/PAPERS.md, results/cornucopia/) |
| `mem_guard.sh` | stops this project's jobs if their total memory passes a limit |
