# Launchers used on our compute server

These shell scripts started the long runs behind the reports. They are kept as a record of the exact
commands and resource settings. They assume our machine: the repository checked out at
`~/claude_runs/circuit_distance`, a Python environment at `~/miniconda3/envs/planarnet`, external
solvers under `bench/external/`, and a pinned set of CPU cores. Adapt the paths at the top of each
file before using them elsewhere. All of them are meant to be run from the repository root.

| script | what it ran |
|---|---|
| `run_bb288_all.sh`, `run_post.sh` | the BB72 to BB288 study (docs/BB_CIRCUITS.md) |
| `server_bb360.sh`, `server_bb360_Z_topdown.sh`, `server_bench1.sh` | covering-bound runs (docs/PHASE4.md) |
| `server_cornucopia.sh`, `server_design_*.sh`, `server_remaining.sh`, `server_batch3.sh` | published circuits, batches 2 and 3 (docs/PAPERS.md) |
| `chain_b.sh`, `chain_c.sh` | the benchmark passes after the first tier (docs/BENCHMARK.md) |
| `hyp_lins_queue.sh`, `hyp_queue.sh` | tiling lists with GAP and exact distances of the hyperbolic codes |
| `mem_guard.sh` | stops this project's jobs if their total memory passes a limit |
