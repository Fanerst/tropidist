# Re-certification with the corrected kernel (20 October 2026)

Up to commit `ce6aada`, the search kernel (`cdist/gmitm.c`) in its labelled mode reconstructed a completion after
a table hit only up to the cost the fingerprint table reported. Under a fingerprint collision that can miss a
solution (paper, Appendix C.2; `tests/test_collision.py` reproduces the counterexample). The kernel now always
reconstructs with the full remaining budget, in both modes. Label-free runs, which include every benchmark run,
were never affected.

An audit of every certified value reported outside the two benchmarks found no labelled negative threshold with a
failed reconstruction (`false_hits` > 0). Such a threshold is certified as it stands (Appendix C.2). The claims
whose records do not store that count, or whose lower bound came from a lifting step whose searches did not record
it, were repeated with the corrected kernel. All values were reproduced.

| claim | rerun | record | result |
|---|---|---|---|
| BB288 circuit [[288,12,18]], X basis: d = 16 | `scripts/run_topdown.py` with W = 15 on the stored enumeration (`results/enum_bb288_r18_X.json`), 32 threads | `topdown_bb288_r18_X_W15.json` (+ `.log`) | no fault set of weight <= 15 (5546 orbit searches); d = 16 with the stored witness |
| BB360 circuit [[360,12,24]], X basis: d >= 19 | `scripts/recert_lifts.py`: the 27 stored orbit representatives (4380 minimum collapsed solutions), slack 0 | `lift_bb360_r24_X.json` | none lifts: d >= 19 |
| BB360 circuit, Z basis: d >= 17 | `scripts/recert_lifts.py`: 1 orbit (180 solutions) | `lift_bb360_r24_Z.json` | none lifts: d >= 17 |
| 57 self-dual BB codes (arXiv:2510.05211): code distances | `papers/selfdual_bb.py` | `selfdual_bb.json` (+ `.log`) | all 57 equal to the earlier values |
| 11 GALA codes (arXiv:2608.07431): code distances, both bases | `papers/gala_codes.py` | `gala_codes.json` (+ `.log`) | all equal |
| Kasai [[232,62,12]]: code distance, both bases | `papers/kasai_codes.py` | `kasai_232.json` (+ `.log`) | 12, 12 |
| routing codes [[200,24,14]] and [[200,16,17]]: both bases | `papers/routing_code200.py` | `routing_code_200_24.json`, `routing_code_200_16.json` (+ `.log`) | 14, 14 and 17, 17 |
| mitten [[150,30,10]] and [[200,40,12]]: code distances (data errors only) | `scripts/recert_mitten_codes.py` (replaces a producer script missing from the repository) | `mitten_code_distance.json` | 10, 10 and 12, 12 |
| sequential self-dual BB designs, 57 codes: best circuit distance; GALA [[132,30,12]] design: the paper's order and another best order | `scripts/recert_designs.py`: exact distance of the winning order in both bases (other orders need only their witnesses) | `designs.json`, per-task files in `designs/` | all equal to the reported best values, in both bases |

`logs/` holds copies of the server logs that certify, with zero failed reconstructions at every negative threshold,
the values whose only record is a log. These are the one-round windows of BB360, the BB756 code distance >= 28, the
single-layer windows of the BB study, and the BB code distances that the benchmark also certifies.

The records written by the new scripts (`run_topdown.py`, `recert_lifts.py`, `recert_designs.py`,
`recert_mitten_codes.py`) store `kernel_sha256`, the SHA-256 of the `cdist/gmitm.c` that produced them
(`e06fcfa4...`, the corrected kernel). The records of the unchanged paper scripts (`selfdual_bb.py`,
`gala_codes.py`, `kasai_codes.py`, `routing_code200.py`) do not store it; they were produced in the same session
with the same corrected kernel, after `tests/test_collision.py` passed.
