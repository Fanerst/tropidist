# Check of the Cornucopia distances (arXiv:2608.02773, arXiv:2610.19073)

Records of the check reported in docs/notes/PAPERS.md, section "Check of the Cornucopia distances" (20 and 21 October
2026). The table there is printed by `python scripts/summarize_cornucopia_check.py`. Every upper bound below is a
fault set checked in the detector error model and replayed in Stim. All runs used the kernel with sha256
`e06fcfa4…` (`cdist/gmitm.c`).

| file | producer | content |
|---|---|---|
| `code_distance_small.json` | `scripts/cornucopia_code_distance.py` (laptop, 1 thread) | d_X and d_Z of the codes with q = 7, 16, 25, 29 |
| `code_distance.json` | same (5090, 64 threads) | d_X and d_Z of q = 49, 64, 79; odd thresholds skipped (every logical has even weight) |
| `code_distance_noparity.json` | same, `--no-parity` | [[2844,1426]] with every threshold searched |
| `circ_q*_r1_{Z,X}_cx.json` | `papers/run_parallel.py`, one cycle, CNOT faults | exact circuit distance in the setting of the authors' search, q ≤ 29 |
| `circ_q49_r7_Z.json`, `circ_q64_r8_Z.json`, `circ_q79_r8_Z.json` | `papers/run_parallel.py`, N_c cycles, the paper's faults, covering bound | lower bounds from the time-collapsed problem (and for q = 49 the lifting step and a 3-hour search of the full sector problem at weight 12, which did not finish); the q = 64 and 79 runs were stopped during weight 12 |
| `win_q*_r*_Z_t1.json` | `scripts/window_search.py` (itp) | exact minimum over the faults of one window: N_c-cycle circuits (window t = 1) and one-cycle circuits (faults seen only by the final readout) |
| `transfer.json` | `scripts/cornucopia_transfer_check.py` | N_c-cycle fault sets replayed in the one-cycle circuit |
| `isd/*.json` | `scripts/run_isd.py` | calibration of the randomized witness search on [[900]] and [[1044]] (it finds nothing on the larger circuits) |
| `logs/5090/`, `logs/itp/` | | server logs of all of the above, including runs stopped before writing a record |

The earlier 6-cycle values for q ≤ 29 are in `results/papers2/cornucopia_q*_r6_*.json`.
