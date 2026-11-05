# Check of the Cornucopia distances (arXiv:2608.02773, arXiv:2610.19073)

Records of the check reported in docs/notes/PAPERS.md, section "Check of the Cornucopia distances" (20 and 21 October
2026). The table there is printed by `python scripts/summarize_cornucopia_check.py`. Every upper bound below is a
fault set checked in the detector error model and replayed in Stim. The runs of 20 and 21 October used the kernel with
sha256 `e06fcfa4…` (`cdist/gmitm.c`); the later runs on [[2304,1156,16]] name their own.

| file | producer | content |
|---|---|---|
| `code_distance_small.json` | `scripts/cornucopia_code_distance.py` (laptop, 1 thread) | d_X and d_Z of the codes with q = 7, 16, 25, 29 |
| `code_distance.json` | same (5090, 64 threads) | d_X and d_Z of q = 49, 64, 79; odd thresholds skipped (every logical has even weight) |
| `code_distance_noparity.json` | same, `--no-parity` | [[2844,1426]] with every threshold searched |
| `circ_q*_r1_{Z,X}_cx.json` | `papers/run_parallel.py`, one cycle, CNOT faults | exact circuit distance in the setting of the authors' search, q ≤ 29 |
| `circ_q49_r7_Z.json`, `circ_q64_r8_Z.json`, `circ_q79_r8_Z.json` | `papers/run_parallel.py`, N_c cycles, the paper's faults, covering bound | lower bounds from the time-collapsed problem (and for q = 49 the lifting step and a 3-hour search of the full sector problem at weight 12, which did not finish); the q = 64 and 79 runs were stopped during weight 12 |
| `circ_q64_r8_Z_k13.json` | `papers/run_parallel.py` (5090, 64 threads, from 2026-10-29; kernel of commit `c030477e`) | q = 64, 8 cycles, Z basis: time-collapsed problem exhausted up to weight 12, so lower bound 13 |
| `circ_q64_r8_Z_w13_s*.json` | same from weight 13, with `GM_LEDGER` and `GM_SLICE` (four servers, 2 to 5 November 2026; kernel of commit `65800ef5`, sha256 `7fbf93d0…`) | weight 13 in shares of its task list, each ending `slice_done` (below) |
| `circ_q64_r8_Z_w13_final.json` | same, without `GM_SLICE`, over the joined ledgers (5090c, 40 threads) | weight 13 exhausted, so lower bound 14; with the weight-14 fault set of `win_q64_r8_Z_t1.json`, the Z-basis circuit distance at 8 cycles is 14 |
| `win_q*_r*_Z_t1.json` | `scripts/window_search.py` (itp) | exact minimum over the faults of one window: N_c-cycle circuits (window t = 1) and one-cycle circuits (faults seen only by the final readout) |
| `transfer.json` | `scripts/cornucopia_transfer_check.py` | N_c-cycle fault sets replayed in the one-cycle circuit |
| `isd/*.json` | `scripts/run_isd.py` | calibration of the randomized witness search on [[900]] and [[1044]] (it finds nothing on the larger circuits) |
| `logs/5090/`, `logs/itp/` | | server logs of the October runs, including runs stopped before writing a record |
| `logs/w13/<server>/` | | logs of every weight-13 run, named by share; `*.stopped.log` are runs stopped when their share was split |

The earlier 6-cycle values for q ≤ 29 are in `results/papers2/cornucopia_q*_r6_*.json`.

## Weight 13 of [[2304,1156,16]] (2 to 5 November 2026)

Weight 13 of the time-collapsed problem has 251,040 tasks, the search prefixes of depth 2, each searched by one thread. A
first run without a ledger (5090, from 2026-10-30) was lost in a reboot of 5090 on 2026-11-02. With `GM_LEDGER` set,
the kernel appends each finished task to a ledger file named by the fingerprint of the problem and its task list
(`K13.96b880d6b8ec6c79`) and skips the tasks found there when it starts; `GM_SLICE=r/m` runs only the tasks whose
index is r mod m and ends with `slice_done`, never with exhausted (`tests/test_ledger.py`). When a share finished, a
slower one was split in two, the new half starting from a copy of its parent's ledger. The final shares:

| share (task index mod m) | server | threads | record | last run |
|---|---|---|---|---|
| 0/4 | 5090 | 220 | `circ_q64_r8_Z_w13_s0of4.json` | 21.6 h |
| 6/16 | 5090 | 170 | `circ_q64_r8_Z_w13_s6of16.json` | 2.9 h |
| 2/8 | 5090b | 84 | `circ_q64_r8_Z_w13_s2of8.json` | 14.8 h |
| 9/16 | 5090b | 84 | `circ_q64_r8_Z_w13_s9of16.json` | 2.7 h |
| 11/16 | 5090b | 80 | `circ_q64_r8_Z_w13_s11.json` | 13.5 h |
| 30/32 | 5090b | 84 | `circ_q64_r8_Z_w13_s30of32.json` | 1.1 h |
| 5/8 | 5090c | 49 | `circ_q64_r8_Z_w13_s5of8.json` | 20.1 h |
| 7/8 | 5090c | 40 | `circ_q64_r8_Z_w13_s7.json` | 24.5 h |
| 14/32 | 5090c | 49 | `circ_q64_r8_Z_w13_s14of32.json` | 1.1 h |
| 1/16 | h200 | 112 | `circ_q64_r8_Z_w13_s1of16.json` | 5.4 h |
| 3/16 | h200 | 76 | `circ_q64_r8_Z_w13_s3.json` | 24.9 h |

Together they cover every residue mod 32, and none found a solution. A record times only the last run of its share;
the runs before it left their finished tasks in the share's ledger. 5090c's share 6/8 was stopped without a record once
its remaining tasks were covered by 6/16, 14/32 and 30/32. The twelve ledgers (one per final share and that of 6/8)
hold 442,423 lines; together they contain all 251,040 task indices with the right fingerprint and no unusable line. One
run without `GM_SLICE` over their concatenation (`circ_q64_r8_Z_w13_final.json`, `logs/w13/5090c/w13_final.log`) found
all 251,040 tasks finished and reported weight 13 exhausted, which gives the lower bound 14. The ledgers are not kept: a
line is a task index and the index XOR the fingerprint, so the joined ledger says only that every task finished. From
the first share (5090, 2026-11-02 21:10) to the end of the final run (2026-11-05 06:04) took 2.4 days; the last task
to finish (index 99, share 3/16) ran about 25 hours on one thread.
