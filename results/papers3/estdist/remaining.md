# Remaining estimated-code distance searches

Snapshot: `local.json`; 250 registry entries, 4 unresolved logical codes. Actual local kernel threads: 1.

CSV blanks mean unknown or not run. Per-basis unknown distances remain blank even when the overall code distance is exact.

Cost estimates use the last two to four consecutive exhausted thresholds only. Found and timed-out searches are excluded because their counts are incomplete. Growth g is the median successive node-count ratio; seconds per node comes from the latest exhausted timing of at least 0.01s. When all timings are shorter, an explicitly labeled 0.01s floor at the last exhausted threshold supplies a conservative baseline for noisy sub-10ms measurements. Predicted threshold costs are summed through the paper's claimed weight across unresolved bases, or one less than an independently verified upper bound when that already closes the certificate. The displayed /3 to ×10 range is empirical, not rigorous, and excludes setup/table building, server speed differences, and work above the claim. No family estimates are borrowed.

Commands use independent output files, so they start from weight 1. A matching matrix-hash checkpoint copied from local.json into that file permits resumption. Forecasts concern remaining work after the local certificates, so fresh runs repeat completed thresholds. Per-threshold caps are at least1800s, increased to three times the largest predicted remaining basis cost when needed. A timeout preserves completed thresholds, but the interrupted threshold restarts; increase its cap if it repeatedly times out.

## Parameter discrepancies

- `mm_t3_r5_288_12_16`: rebuilt [[288,0]], paper [[288,12]], claimed d=16. No logical distance exists and no server command is supplied. Locator: v2 Appendix F Table 3, data row 5; Eqs.67,99,100.

## Commands and empirical cost

### llmbb_360_12_24_V

arXiv:2606.02418; open; rebuilt [[360,12]], paper [[360,12]], claimed d=24. Local overall bounds: 21 ≤ d ≤ 30.

- Z basis: Through K=24: approximately 1.59h; broad range 31.9min–15.9h. g=2.891; exhausted history: K=17: 5079420 nodes, 2.836s; K=18: 14580363 nodes, 7.004s; K=19: 42151228 nodes, 21.81s; K=20: 122122492 nodes, 54.5s; seconds/node=4.463e-07 from K=20 (54.5s)
- X basis: Through K=24: approximately 1.27h; broad range 25.5min–12.7h. g=2.909; exhausted history: K=17: 4307366 nodes, 2.304s; K=18: 12464855 nodes, 5.163s; K=19: 36261084 nodes, 14.18s; K=20: 105644281 nodes, 42.6s; seconds/node=4.032e-07 from K=20 (42.6s)

Combined remaining search estimate through claimed weight: approximately 2.87h; broad range 57.3min–1.19days.

```sh
OMP_NUM_THREADS=2 ESTDIST_TOTAL_SECONDS=0 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/server_llmbb_360_12_24_V.json 24 17210 llmbb_360_12_24_V
```

Locator: Supplemental Material I Table 3 class V†; Eq. (1).

### balanced_525_105_18

arXiv:2607.27644; open; rebuilt [[525,105]], paper [[525,105]], claimed d=18. Local overall bounds: 14 ≤ d ≤ unknown.

- Z basis: Through K=18: approximately 9.29min; broad range 3.1min–1.55h. g=3.047; exhausted history: K=10: 103957 nodes, 0.06823s; K=11: 315604 nodes, 0.2235s; K=12: 961696 nodes, 0.6807s; K=13: 2984444 nodes, 1.431s; seconds/node=4.796e-07 from K=13 (1.431s)
- X basis: Through K=18: approximately 9.4min; broad range 3.13min–1.57h. g=3.04; exhausted history: K=10: 106762 nodes, 0.06408s; K=11: 321179 nodes, 0.2655s; K=12: 976402 nodes, 0.8529s; K=13: 3058575 nodes, 1.463s; seconds/node=4.784e-07 from K=13 (1.463s)

Combined remaining search estimate through claimed weight: approximately 18.7min; broad range 6.23min–3.12h.

```sh
OMP_NUM_THREADS=2 ESTDIST_TOTAL_SECONDS=0 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/server_balanced_525_105_18.json 20 1800 balanced_525_105_18
```

Locator: Appendix A, Table 8.

### balanced_550_110_18

arXiv:2607.27644; open; rebuilt [[550,110]], paper [[550,110]], claimed d=18. Local overall bounds: 16 ≤ d ≤ 18.

- Z basis: Through K=17: approximately 7.98min; broad range 2.66min–1.33h. g=3.149; exhausted history: K=12: 1953673 nodes, 3.133s; K=13: 5976640 nodes, 2.654s; K=14: 18818680 nodes, 11.06s; K=15: 60432014 nodes, 36.65s; seconds/node=6.064e-07 from K=15 (36.65s)
- X basis: Through K=17: approximately 8.35min; broad range 2.78min–1.39h. g=3.169; exhausted history: K=12: 1829932 nodes, 3.005s; K=13: 5667229 nodes, 2.547s; K=14: 17962272 nodes, 11.02s; K=15: 58045387 nodes, 37.89s; seconds/node=6.528e-07 from K=15 (37.89s)

Combined remaining search estimate through claimed weight: approximately 16.3min; broad range 5.44min–2.72h.

```sh
OMP_NUM_THREADS=2 ESTDIST_TOTAL_SECONDS=0 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/server_balanced_550_110_18.json 20 1800 balanced_550_110_18
```

Locator: Table 3.

### balanced_625_125_20

arXiv:2607.27644; open; rebuilt [[625,125]], paper [[625,125]], claimed d=20. Local overall bounds: 14 ≤ d ≤ unknown.

- Z basis: Through K=20: approximately 49.8min; broad range 16.6min–8.3h. g=2.923; exhausted history: K=10: 95192 nodes, 0.1554s; K=11: 271312 nodes, 0.3775s; K=12: 793028 nodes, 1.205s; K=13: 2392339 nodes, 1.079s; seconds/node=4.511e-07 from K=13 (1.079s)
- X basis: Through K=20: approximately 49.4min; broad range 16.5min–8.23h. g=2.915; exhausted history: K=10: 94092 nodes, 0.1527s; K=11: 272415 nodes, 0.4245s; K=12: 794205 nodes, 1.177s; K=13: 2381520 nodes, 1.087s; seconds/node=4.566e-07 from K=13 (1.087s)

Combined remaining search estimate through claimed weight: approximately 1.65h; broad range 33.1min–16.5h.

```sh
OMP_NUM_THREADS=2 ESTDIST_TOTAL_SECONDS=0 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/server_balanced_625_125_20.json 20 8965 balanced_625_125_20
```

Locator: Appendix A, Table 8.
