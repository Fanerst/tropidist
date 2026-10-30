# Tour de gross's Table 2 in its own experiment (2026-10-30)

The NCS manuscript compares our decoder-independent bound for one noisy cycle of the two-gross memory instruction
(C = 1, measurement and reset fused into one timestep, Stim depolarizing channels) with the "Idle" rate of Tour de gross
(arXiv:2506.03094) Table 2. That rate comes from a different experiment:

- **Cycles.** App. A.7: "C = d*_circ repeated applications of a single idle cycle", with "the failure probability of the
  circuit divided by C": 18 cycles for the two-gross code, 10 for the gross code.
- **Timing.** Sec. 2.2 assumes that gates, initialisations and measurements each take one timestep. Fig. 4: the Z check
  qubit is prepared in timestep 0 and measured in 7; the X check qubit is prepared in 1 and measured in 8, while the Z
  check qubit is prepared for the next cycle. C cycles take 8C + 1 timesteps.
- **Noise.** Sec. 2.6 and App. A.7 linearise the noise: every fault is an independent event of probability q = p/15, and
  an event of probability m·p/15 becomes m such faults.
- **Observables.** App. A.7 prepares k Bell pairs and ends with a logical Bell measurement, so a failure is any logical
  error, X or Z.

## What was built

- `papers/ibm_bicycle_matched.py`: the instruction in that setting.
  - CNOT slot s runs in timestep 1 + s.
  - Each check qubit is prepared in the timestep before its first CNOT and measured in the timestep after its last.
    It idles only in between.
  - The standard schedule therefore takes 8C + 1 timesteps, as in Fig. 4. A schedule whose checks use slots 0 and 6
    takes 9 timesteps per cycle.
  - Noise is linearised: each of the 15 CNOT Paulis is one fault of probability q; idle X, Y and Z are five faults
    each; a preparation or measurement flip is fifteen faults.
  - Detectors, coordinates and observables are those of `papers/ibm_bicycle.py`.
- `papers/ibm_bicycle_matched_bound.py`: copies and bound.
  - It takes the C = 1 minimum fault sets with their translation orbits and places a copy in every cycle, found by
    shifted detector coordinates.
  - It checks each copy in the C-cycle detector error model and replays it with explicit Pauli faults
    (`cdist/replay.py`).
  - It evaluates the SI Proposition (disjoint halves, P_U with U the union of the family) over all copies and divides by C.
  - The code reproduces the published C = 1 bound exactly when given the fused builder (10^-30.861 and 10^-22.912).

All values below are log10 and are read from the records in this folder.

## Two-gross [[288,12,18]], standard schedule, C = 18

The X and Z bases give identical numbers to three decimals.

**The matched C = 1 instruction has distance 16.**
- Its detector error model has the same 12,672 mechanisms (same detectors, same observables) as
  `papers/ibm_bicycle.py`'s, in both bases. The sector problems are therefore identical, and the certified distance 16
  carries over.
- The timing changes only the 288 measurement-type mechanisms: their check qubit no longer idles in slot 0 or 6, so
  fused/matched = 1.263 at p = 1e-4. The linearisation changes mechanism probabilities by less than 10^-4 (relative) at
  1e-4 and 10^-3 at 1e-3.
- The minimum fault sets use none of the measurement-type mechanisms, so the C = 1 bound is unchanged (-30.86 at 1e-4,
  -22.91 at 1e-3). All 36 sets of each basis replay in the matched C = 1 circuit.

**Copies in 18 cycles: 36 sets × 18 = 648 per basis, all verified.**
- X basis: the orbit of the certified run's set. `pipe_*_X`, `bound_*_X` and `enum_*_X` give the same 36 sets.
- Z basis: the orbit of `pipe_*_Z`'s set. The weight-18 witness of `pipe_*_Z_2h` is not a minimum set and is not used.
- The 18-cycle circuit has 576 qubits, 5,760 detectors, 145 noisy timesteps and 213,408 mechanisms.
- Every copy fires no detector in its detector error model. **All 648 replay with explicit Pauli faults: no detector
  fires and the expected observables flip.**
- Copies in different cycles share no mechanism. The family is all 648 sets (5,184 mechanisms).

**Per-cycle bound** (SI Proposition on all copies, divided by C = 18):

| p | C = 1, manuscript | C = 1, matched | 18 cycles | **per cycle** | Table 2 | per cycle - Table 2 |
|---|---|---|---|---|---|---|
| 1e-4 | -30.86 | -30.86 | -29.47 | **-30.73** | -38.3 | **+7.57** |
| 2e-4 | – | -28.46 | -27.19 | -28.44 | | |
| 5e-4 | – | -25.29 | -24.36 | -25.61 | | |
| 7.322e-4 | -23.98 | -23.98 | -23.31 | -24.57 | | |
| 1e-3 | -22.91 | -22.91 | -22.55 | -23.80 | -20.1 | -3.70 |

**So at p = 1e-4 every decoder fails at least 10^7.57 ≈ 3.7 × 10^7 times more often per cycle than Table 2 projects.**
The C = 1 comparison gave 7.44 orders. Three effects separate the per-cycle bound from the C = 1 one:
- **18 copies.** The bound on the 18-cycle failure probability grows about 18-fold, which the division by C undoes.
- **Boundary faults.** Every mechanism of the X-basis sets fires detectors of round 1 only (a data error before the
  cycle's checks see it); those of the Z-basis sets fire round 2 only.
  - In the 18-cycle circuit, the 3-detector half of these mechanisms also collects faults from the neighbouring cycle:
    8.00 × 10^-5 → 9.33 × 10^-5 at 1e-4 (7/6). In the C = 1 instruction the noise-free boundary rounds remove these
    faults.
  - The 17 copies with such a neighbour (X: cycles 2-18; Z: cycles 1-17) contribute 10^0.256 more each.
- **Silence factor.** U now holds the copies of all 18 cycles, so prod_{U - E} (1 - p_j) is 10^-0.119 instead of
  10^-0.006.
- **Net:** at 1e-4 the per-cycle bound is 0.13 orders above the C = 1 one. At 1e-3 the silence factor (10^-1.19)
  dominates, and the per-cycle bound is 0.89 orders below the C = 1 one, still below Table 2's 10^-20.1.

## Gross [[144,12,12]], standard schedule, C = 10

- **Mechanisms and distance.** The matched C = 1 instruction has the same 6,336 mechanisms as the fused one, so
  distance 10 in both bases carries over. Again only the 144 measurement-type mechanisms change.
- **Minimum fault sets.** The exact enumeration in the matched C = 1 instruction gives all of them: 144 in Z (4 orbits)
  and 288 in X, the same numbers as in the fused instruction (SI table).
- **Replay.** All sets replay at C = 1, and all 1,440 (Z) and 2,880 (X) copies replay in the 10-cycle circuit.
- **Family.** It has 720 sets (Z) and 1,440 (X), ten times the C = 1 family. In X, the copies in adjacent cycles share
  72 mechanisms.

| p | basis | C = 1, matched | 10 cycles | per cycle | Table 2 |
|---|---|---|---|---|---|
| 1e-4 | Z | -17.59 | -16.31 | -17.31 | -14.8 |
| 1e-4 | X | -17.58 | -16.31 | -17.31 | |
| 1e-3 | Z | -12.64 | -11.94 | -12.94 | -8.8 |
| 1e-3 | X | -12.66 | -12.09 | -13.09 | |

The bound stays 2.5 orders below Table 2 at 1e-4 and 4.1-4.3 orders below at 1e-3, so there is no contradiction, as
before.

## The best distance-11 gross schedule, p_X = (1,0,6,4,3,2), p_Z = (3,4,2,5,6,0)

**It needs 9 timesteps per cycle.**
- Both check types have CNOTs in slots 0 and 6: X idles in slot 5, Z in slot 1.
- Each check qubit is therefore busy for 9 timesteps: preparation, the 7 CNOT slots, measurement.
- With one check qubit per check, consecutive cycles cannot overlap these, so C cycles take 9C timesteps. The standard
  schedule takes 8C + 1.

**Its circuit distance with 9 timesteps per cycle is 11 in both bases.**
- C = 1: the 9-timestep instruction has the fused instruction's 9 timesteps and its mechanisms, so the distance is 11.
  Re-certified in `gross_s106432_342560_9ts_c1_{Z,X}.json`.
- C = 10, in the matched setting: 11 (`gross_s106432_342560_9ts_c10_{Z,X}.json`).
  - The sector search (7,344 columns) exhausts weight 10 in 376 s (Z) and 265 s (X), and the weight-11 witnesses
    replay.
  - The Z search starts at 10 from the lifting argument. Its collapsed enumeration has 18 orbits (at most 1,296 sets),
    far below the solution cap.
- The six-cycle memory circuits of `papers/bb6_depth7.py`, in which all 428 schedules have distance 11, already use
  separate preparation and measurement timesteps, 9 per cycle.

**100 of the 428 distance-11 schedules fit 8 timesteps** (`timing_gross_d11.json`).
- Their X checks idle in slot 0 and their Z checks in slot 6, as in the standard schedule.
- The other 328, the best schedule among them, need 9 timesteps.
- In the matched timing, every one of the 428 keeps the mechanisms of its fused C = 1 instruction in both bases, so its
  C = 1 distance stays 11.

## Caveats

- **Bell-pair experiment.** Tour de gross detects X and Z logical errors in one Bell-pair experiment; we run the X- and
  Z-basis memories separately.
  - The noisy faults fire the same detectors in both experiments.
  - The joint law of the detectors and the X-type logical flips depends only on mechanisms merged by those effects,
    which are ours.
  - So the X-basis bound lower-bounds the probability that any decoder of their experiment mispredicts an X-type
    logical, and hence their failure probability. Likewise for Z.
  - The bounds of the two bases are equal. Their sum is not claimed.
- **Only copies of the C = 1 minimum fault sets enter.**
  - The 18-cycle circuit may have other undetected logical fault sets of weight 16 or less, for example spanning two
    cycles. They could only raise the bound.
  - The 18-cycle circuit's distance was not computed.
- **The silence factor comes from the proof.** U must contain every set used, so the factor grows with C:
  10^-0.12 at 1e-4 and 10^-1.19 at 1e-3 for 18 cycles.

## For the manuscript (not edited)

- **The "ten million" claim survives in the matched experiment:** 7.57 orders per cycle at p = 1e-4, against 7.44
  orders for C = 1.
- **Other per-cycle values change** from the C = 1 ones: 10^-23.8 at 1e-3 (C = 1: 10^-22.9) and 10^-24.6 at 7.3e-4
  (C = 1: 10^-24.0).
- **"with the same couplers and eight timesteps per cycle"** holds for 100 of the 428 distance-11 schedules, but not
  for the best one, which needs nine. Its distance stays 11 with nine.

## Reproduce

Runs on the Mac (2 threads each, under load) took 25-40 min. Most of that is the replays: 0.7 s per two-gross copy
when the machine is idle.

```
OMP_NUM_THREADS=2 python papers/ibm_bicycle_matched_bound.py bb288 X 18 16 results/ibm_matched/bound_bb288_standard_c18_X.json results/ibm/pipe_bb288_standard_c1_X.json,results/ibm/bound_bb288_standard_c1_X.json,results/ibm/enum_bb288_standard_c1_X.json
OMP_NUM_THREADS=2 python papers/ibm_bicycle_matched_bound.py bb288 Z 18 16 results/ibm_matched/bound_bb288_standard_c18_Z.json results/ibm/pipe_bb288_standard_c1_Z.json
OMP_NUM_THREADS=2 python papers/ibm_bicycle_matched_bound.py gross Z 10 10 results/ibm_matched/bound_gross_standard_c10_Z.json enumerate
OMP_NUM_THREADS=2 python papers/ibm_bicycle_matched_bound.py gross X 10 10 results/ibm_matched/bound_gross_standard_c10_X.json enumerate
IBM_SCHEDULE=1,0,6,4,3,2/3,4,2,5,6,0 OMP_NUM_THREADS=2 python papers/ibm_bicycle_matched.py gross Z 1 results/ibm_matched/gross_s106432_342560_9ts_c1_Z.json 24 600
IBM_SCHEDULE=1,0,6,4,3,2/3,4,2,5,6,0 OMP_NUM_THREADS=2 python papers/ibm_bicycle_matched.py gross Z 10 results/ibm_matched/gross_s106432_342560_9ts_c10_Z.json 24 1800
OMP_NUM_THREADS=2 python papers/ibm_bicycle_matched_timing.py results/ibm_matched/timing_gross_d11.json
```

The X-basis distance runs are the same with X.
