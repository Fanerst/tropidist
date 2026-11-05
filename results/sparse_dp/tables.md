### Validation: distance found by each method

| instance | known d | MITM sched | MITM | MITM+h | fwd+h | fwd | dense DP | search |
|---|---|---|---|---|---|---|---|---|
| color d7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 |
| color d9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| color d11 | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 11 |
| color d13 | 13 | 13 | 13 | 13 | 13 | 13 | 13 | 13 |
| color d15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 |
| color d17 | 17 | 17 | 17 | 17 | 17 | 17 | 17 | 17 |
| color d19 | 19 | 19 | 19 | 19 | 19 | 19 | 19 | 19 |
| color d21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 |
| color d23 | 23 | 23 | 23 | 23 | 23 | 23 | 23 | ≥ 21 (timeout) |
| color d25 | 25 | 25 | 25 | 25 | 25 | 25 | 25 | ≥ 21 (timeout) |
| color d27 | 27 | 27 | 27 | 27 | 27 | budget | 27 | ≥ 21 (timeout) |
| concat_steane_L2 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| hypercube_L2 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| concat_steane_L3 | 27 | 27 | 27 | 27 | 27 | 27 | 27 | ≥ 22 (timeout) |
| hypercube_L3 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |
| concat_steane_L4 | 81 | 81 | 81 | 81 | 81 | 81 | 81 | ≥ 18 (timeout) |
| gross | 12 | 12 | 12 | 12 | budget | budget | too wide | 12 |
| bb72 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| bb90 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| bb108 | 10 | 10 | 10 | 10 | 10 | ≥ 10 (budget at K = 10) | 10 | 10 |
| superdense d3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| superdense d5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| superdense d7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 |
| superdense d9 | 9 | 9 | 9 | 9 | ≥ 9 (budget at K = 9) | budget | too wide | 9 |
| superdense d11 | 10..11 (open) | 11‡ | 11‡ | budget | budget | budget | too wide | ≥ 8 (timeout) |
| surface d3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| surface d5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| surface d7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 |
| surface d9 | 9 | 9 | 9 | 9 | 9 | budget | too wide | 9 |
| surface d11 | 11 | 11† | budget† | error | error | error | too wide | 11 |

† numpy tables (the trellis needs 62 row slots, the C tables hold 56). ‡ dedicated runs, see *Superdense d11*.

### Time (seconds, one thread)

Sparse: the sweep at K = d − 1 for every observable, plus the one at K = d that stops at its first solution and returns the witness; the split probes are included. Search: every threshold from K = 1, and in brackets its last two (d − 1 and d). Dense DP: one untruncated sweep per observable. Bold: the fastest method. Width: the rows of the trellis active at its widest cut, counting the reduced logical row; the dense table there has 2^width entries. It exceeds the cut rank by one on every color code except d25 and on the concatenated Steane and hypercube codes, where the reduced logical row is active at the widest cut without adding to the rank, and equals the cut rank on the bivariate bicycle codes and the circuits.

| instance | regime | columns | width | d | dense DP | search | MITM sched | MITM | MITM+h | fwd+h | fwd |
|---|---|---|---|---|---|---|---|---|---|---|---|
| color d7 | narrow | 37 | 8 | 7 | **0.001** | 0.003 (0.000) | 0.008 | 0.008 | 0.01 | 0.008 | 0.004 |
| color d9 | narrow | 61 | 9 | 9 | **0.001** | 0.005 (0.000) | 0.01 | 0.01 | 0.02 | 0.01 | 0.006 |
| color d11 | narrow | 91 | 11 | 11 | **0.001** | 0.009 (0.002) | 0.02 | 0.02 | 0.02 | 0.02 | 0.01 |
| color d13 | narrow | 127 | 13 | 13 | **0.001** | 0.04 (0.02) | 0.03 | 0.03 | 0.03 | 0.03 | 0.01 |
| color d15 | narrow | 169 | 16 | 15 | **0.003** | 0.29 (0.18) | 0.05 | 0.04 | 0.05 | 0.11 | 0.02 |
| color d17 | narrow | 217 | 17 | 17 | **0.003** | 2.48 (1.59) | 0.06 | 0.06 | 0.07 | 0.16 | 0.03 |
| color d19 | narrow | 271 | 20 | 19 | **0.03** | 22.2 (14.1) | 0.21 | 0.21 | 0.27 | 1.44 | 0.15 |
| color d21 | narrow | 331 | 22 | 21 | **0.11** | 194 (122) | 0.60 | 0.60 | 0.72 | 6.41 | 0.53 |
| color d23 | narrow | 397 | 23 | 23 | **0.07** | ≥ 21 (timeout) | 0.65 | 0.44 | 0.55 | 8.14 | 0.64 |
| color d25 | narrow | 469 | 25 | 25 | **0.37** | ≥ 21 (timeout) | 1.80 | 1.81 | 2.20 | 50.0 | 4.42 |
| color d27 | narrow | 547 | 28 | 27 | **0.86** | ≥ 21 (timeout) | 6.75 | 4.31 | 5.61 | 168 | budget |
| concat_steane_L2 | narrow | 49 | 7 | 9 | **0.001** | 0.005 (0.000) | 0.01 | 0.01 | 0.01 | 0.009 | 0.004 |
| hypercube_L2 | narrow | 36 | 6 | 4 | **0.002** | 0.002 (0.000) | 0.10 | 0.10 | 0.13 | 0.03 | 0.01 |
| concat_steane_L3 | narrow | 343 | 10 | 27 | **0.002** | ≥ 22 (timeout) | 0.07 | 0.07 | 0.08 | 0.05 | 0.03 |
| hypercube_L3 | narrow | 216 | 22 | 8 | 1.59 | **0.04 (0.03)** | 2.24 | 2.20 | 3.00 | 7.85 | 8.52 |
| concat_steane_L4 | narrow | 2401 | 13 | 81 | **0.02** | ≥ 18 (timeout) | 0.50 | 0.46 | 0.66 | 0.45 | 0.20 |
| gross | expanding | 144 | 40 | 12 | too wide | **0.06 (0.03)** | 5.59 | 5.56 | 7.41 | budget | budget |
| bb72 | expanding | 72 | 20 | 6 | 0.08 | **0.003 (0.000)** | 0.15 | 0.14 | 0.20 | 0.12 | 0.15 |
| bb90 | expanding | 90 | 26 | 10 | 2.85 | **0.01 (0.006)** | 0.19 | 0.18 | 0.25 | 87.2 | 30.1 |
| bb108 | expanding | 108 | 30 | 10 | 78.5 | **0.01 (0.005)** | 0.24 | 0.26 | 0.32 | 28.0 | ≥ 10 (budget at K = 10) |
| superdense d3 | local circuit | 70 | 7 | 3 | **0.001** | 0.002 (0.000) | 0.02 | 0.02 | 0.02 | 0.01 | 0.007 |
| superdense d5 | local circuit | 414 | 15 | 5 | **0.003** | 0.03 (0.01) | 0.10 | 0.10 | 0.12 | 0.22 | 0.06 |
| superdense d7 | local circuit | 1248 | 25 | 7 | 2.59 | 2.42 (2.12) | **0.57** | 0.59 | 0.76 | 19.6 | 66.3 |
| superdense d9 | local circuit | 2788 | 39 | 9 | too wide | 378 (339) | **10.1** | 13.9 | 18.6 | ≥ 9 (budget at K = 9) | budget |
| superdense d11 | local circuit | 5250 | 55 | 11 | too wide | ≥ 8 (timeout) | **772‡** | 1158‡ | budget | budget | budget |
| surface d3 | local circuit | 55 | 6 | 3 | **0.001** | 0.002 (0.000) | 0.01 | 0.01 | 0.02 | 0.01 | 0.005 |
| surface d5 | local circuit | 301 | 14 | 5 | **0.004** | 0.008 (0.001) | 0.07 | 0.06 | 0.09 | 0.04 | 0.05 |
| surface d7 | local circuit | 883 | 26 | 7 | 18.3 | **0.06 (0.02)** | 0.28 | 0.29 | 0.36 | 0.73 | 33.6 |
| surface d9 | local circuit | 1945 | 42 | 9 | too wide | **0.98 (0.61)** | 5.74 | 8.13 | 7.25 | 124 | budget |
| surface d11 | local circuit | 3631 | 62 | 11 | too wide | **36.1 (28.0)** | 1664† | budget† | error | error | error |

### States kept, against the dense table

2^w: entries of the dense table at the widest cut; dense work: entries the dense DP updates per observable. For the sparse sweeps at K = d − 1: the split a (for a schedule, its values along the sweep), the largest table, the states summed over all cuts, both directions and all observables, and the bytes of the tables held at the peak (checkpoints included); then the process's peak memory.

| instance | 2^w | dense work | MITM sched a | peak | total | tables | MITM a | peak | total | fwd+h peak | fwd+h total | peak memory (MITM sched) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| color d7 | 256 | 2956 | 4→3 | 37 | 571 | 992 B | 3 | 37 | 567 | 178 | 1159 | 0.04 GB |
| color d9 | 512 | 9388 | 4 | 57 | 1539 | 2.0 kB | 4 | 57 | 1539 | 216 | 3969 | 0.04 GB |
| color d11 | 2048 | 3.6e4 | 4 | 326 | 5508 | 6.8 kB | 4 | 326 | 5508 | 832 | 1.4e4 | 0.04 GB |
| color d13 | 8192 | 1.6e5 | 6 | 463 | 1.5e4 | 15.7 kB | 6 | 463 | 1.5e4 | 3477 | 5.3e4 | 0.04 GB |
| color d15 | 6.6e4 | 1.8e6 | 5 | 3973 | 1.9e5 | 145.2 kB | 5 | 3973 | 1.9e5 | 6.3e4 | 8.5e5 | 0.04 GB |
| color d17 | 1.3e5 | 3.1e6 | 7 | 7552 | 2.1e5 | 141.4 kB | 7 | 7552 | 2.1e5 | 4.4e4 | 1.1e6 | 0.04 GB |
| color d19 | 1.0e6 | 3.8e7 | 5 | 9.7e4 | 4.9e6 | 2.8 MB | 5 | 9.7e4 | 4.9e6 | 1.0e6 | 1.8e7 | 0.06 GB |
| color d21 | 4.2e6 | 1.7e8 | 6 | 2.8e5 | 1.7e7 | 8.7 MB | 6 | 2.8e5 | 1.7e7 | 4.2e6 | 8.2e7 | 0.09 GB |
| color d23 | 8.4e6 | 2.4e8 | 8 | 5.2e5 | 1.4e7 | 6.0 MB | 9 | 3.1e5 | 9.2e6 | 2.5e6 | 7.6e7 | 0.10 GB |
| color d25 | 3.4e7 | 1.3e9 | 10 | 1.5e6 | 3.9e7 | 26.5 MB | 10 | 1.5e6 | 3.9e7 | 8.9e6 | 3.8e8 | 0.23 GB |
| color d27 | 2.7e8 | 4.1e9 | 10 | 8.8e6 | 1.7e8 | 91.3 MB | 11 | 5.1e6 | 1.1e8 | 5.9e7 | 1.3e9 | 1.13 GB |
| concat_steane_L2 | 128 | 1372 | 4 | 20 | 494 | 464 B | 4 | 20 | 494 | 73 | 716 | 0.04 GB |
| hypercube_L2 | 64 | 1532 | 2 | 6 | 2917 | 160 B | 2 | 6 | 2901 | 29 | 9159 | 0.04 GB |
| concat_steane_L3 | 1024 | 3.4e4 | 9 | 223 | 1.2e4 | 6.5 kB | 10 | 196 | 1.2e4 | 712 | 2.1e4 | 0.04 GB |
| hypercube_L3 | 4.2e6 | 4.5e8 | 4 | 386 | 2.1e6 | 21.6 kB | 4 | 386 | 2.1e6 | 5.2e4 | 1.9e8 | 0.05 GB |
| concat_steane_L4 | 8192 | 8.5e5 | 25 | 1844 | 3.1e5 | 23.4 kB | 27 | 1757 | 3.0e5 | 6216 | 5.4e5 | 0.05 GB |
| gross | 1.1e12 | 2.9e13 | 4 | 4.5e5 | 1.8e8 | 10.0 MB | 4 | 4.5e5 | 1.8e8 | – | – | 0.12 GB |
| bb72 | 1.0e6 | 1.3e7 | 4→3 | 137 | 6.4e4 | 5.9 kB | 3 | 137 | 6.4e4 | 2813 | 5.3e5 | 0.04 GB |
| bb90 | 6.7e7 | 1.3e9 | 4 | 7692 | 1.9e6 | 224.8 kB | 4 | 7692 | 1.9e6 | 2.2e6 | 3.1e8 | 0.04 GB |
| bb108 | 1.1e9 | 3.4e10 | 4 | 1.3e4 | 2.4e6 | 262.7 kB | 4 | 1.3e4 | 2.4e6 | 2.9e6 | 3.6e8 | 0.04 GB |
| superdense d3 | 128 | 4624 | 2→1 | 15 | 527 | 664 B | 2 | 19 | 654 | 16 | 434 | 0.04 GB |
| superdense d5 | 3.3e4 | 3.5e6 | 3→2 | 424 | 5.6e4 | 25.2 kB | 2 | 611 | 7.1e4 | 1710 | 1.8e5 | 0.04 GB |
| superdense d7 | 3.4e7 | 1.2e10 | 4→3 | 9943 | 4.1e6 | 982.7 kB | 3 | 2.9e4 | 5.7e6 | 2.1e5 | 4.6e7 | 0.04 GB |
| superdense d9 | 5.5e11 | 2.8e14 | 5→4 | 4.4e5 | 3.6e8 | 60.2 MB | 4 | 1.6e6 | 5.3e8 | 3.8e7 | 1.2e10 | 0.28 GB |
| superdense d11 | 3.6e16 | 4.4e19 | 7→6→5 | 2.7e7 | 4.4e10 | 5.0 GB | 5 | 1.2e8 | 6.2e10 | – | – | 15.13 GB |
| surface d3 | 64 | 2156 | 2→1 | 10 | 251 | 320 B | 2 | 9 | 290 | 7 | 139 | 0.04 GB |
| surface d5 | 1.6e4 | 2.7e6 | 3→2 | 175 | 2.6e4 | 12.1 kB | 3 | 183 | 3.0e4 | 211 | 2.4e4 | 0.04 GB |
| surface d7 | 6.7e7 | 3.2e10 | 5→4→3 | 5717 | 2.2e6 | 612.3 kB | 4 | 6683 | 3.1e6 | 1.7e4 | 3.7e6 | 0.04 GB |
| surface d9 | 4.4e12 | 4.7e15 | 6→5→4 | 2.8e5 | 2.3e8 | 41.2 MB | 4 | 1.3e6 | 3.5e8 | 2.8e6 | 7.0e8 | 0.18 GB |
| surface d11 | 4.6e18 | 9.2e21 | 8→7→6→5 | 1.8e7 | 2.6e10 | 3.9 GB | – | – | – | – | – | 19.95 GB |

### Superdense d11: the four runs

| run | split a | result | backward sweep | forward sweep | traceback | total | largest table | states (all cuts) | peak memory |
|---|---|---|---|---|---|---|---|---|---|
| K = 10, a = 5 | 5 | none of weight ≤ 10 | 152 s | 656 s | – | 808 s | 1.2e8 | 6.2e10 | 56.0 GB |
| K = 10, schedule | 7→6→5 | none of weight ≤ 10 | 53.1 s | 617 s | – | 670 s | 2.7e7 | 4.4e10 | 11.5 GB |
| K = 11, a = 6 | 6 | weight 11, witness checked | 151 s | 0.02 s | 199 s | 351 s | 1.2e8 | 3.2e10 | 93.5 GB |
| K = 11, schedule + 1 | 8→7→6 | weight 11, witness checked | 43.7 s | 2.51 s | 55.4 s | 102 s | 2.5e7 | 8.9e9 | 15.1 GB |

