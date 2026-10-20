# Next steps (parked)

Written 7 October 2026. Nothing here is started unless it says so.

## 1. Circuit distance of the color-code circuits of arXiv:2610.03682

The paper's main simulations use modular color-code circuits and state no circuit distance for them.
We have their code distances (docs/PAPERS.md, fourth batch) and the circuit distances of the
surface-code circuits, but not these. Three things to try, in this order.

**1a. Rebuild the paper's modular circuits, smallest and best-documented first.**

- Fixed by the text: two measure qubits per bulk hexagon, prepared as a Bell pair and each coupled
  to three data qubits; an m-qubit cat state for plaquettes that cross module boundaries; an X
  subround then a Z subround; the "up-middle-down" gate order; a flag detector on every
  non-syndrome measure qubit.
- Fixed only by figures (S10 to S19, M3): which three data qubits each measure qubit takes, how many
  measure qubits a skewed boundary plaquette gets (2 or 3) and in which module they sit, the order
  of each cat chain. These have to be read from high-resolution renders of the figures and written
  down before any code is written.
- Order: quadrilateral modules first, since the text describes them in most detail: [[128,12,8]] at
  L = 2 (320 qubits), then [[288,12,12]] and [[512,12,16]]. Then the octagon modules of the main
  simulations: [[64,8,6]], [[128,12,8]], [[512,36,12]].
- Checks available: qubits per module (4L²+2L and 16L²+8) and the totals the paper prints (320, 672,
  1152; 144, 288, 1152); every detector deterministic in Stim; every gate nearest-neighbour inside a
  module or along a seam; the cat-preparation depths stated in the captions.
- Question answered: do the flagged circuits keep the full code distance (6, 8, 12, 16), and if not,
  which faults break it? The search cost at distance 12 to 16 is not estimated; these circuits have
  less symmetry than the bivariate bicycle ones.

**1b. Report a range, not one number.** For every choice the figures leave open, compute the
distance under each alternative, as was done for the surface-code schedules. If the answer is the
same for all, the uncertainty of the reading does not matter; if it varies, that is a finding about
the design.

**1c. An idealised version that ignores the module layout.** Bell- and cat-flagged extraction on the
same codes with a canonical split of each plaquette and no planarity constraint. Fully defined
without the figures. It answers a more general question (can flagged extraction of this kind keep
the distance of these codes, and with which gate order?) and makes no claim to be the paper's
circuit.

**Risks.** No number in the paper can confirm the rebuild, so the result would be "our
reconstruction, under listed assumptions". The module figures have not yet been read at high
resolution; the one seen at page resolution was not legible.

**Cleaner alternative.** Ask the authors for the Stim circuit files. Then 1a and 1b become a direct
computation, and the 15 closed code-distance ranges are a natural thing to send along.

## 2. Other open items

- **Name of the method.** Provisionally the "tropical partition function method" (Feng, 20 October 2026),
  as in the paper draft; "CLIMB" is no longer used. To be confirmed with Bin.
- **Ablation of the lookup table.** The ablation in docs/BENCHMARK.md never switches off the
  meet-in-the-middle table. A run with the table reduced to single columns was started and stopped
  on 7 October; 32 of 39 records exist on the server under `results/bench_ablation_stopped/` and are
  not used anywhere.
- **Rectangle modules** of the hyperbolic surface-code circuits (shift and boundary-first fallback of
  the schedule) are not rebuilt.
- **Kernel limit of 16320 checks.** It blocks the PSL(2,23) and PSL(2,25) color codes at L of 3 or
  more, and the (6,6,6) code [[34944,1096,26-30]].
- **Codes of distance 30 or more** ([[21504,340,36-38]], [[21120,444,30-32]]): about a factor 3 per
  unit of weight; needs a better bound inside the search, not more hardware.
- **Open circuits:** the [[360,12,24]] circuit (17 to 21) and the mitten circuits with 500 qubits or
  more.
- **Not yet built:** the coset codes of arXiv:2606.17268 (they need GAP, which is now installed on
  the server), the Stairway circuits of arXiv:2603.00228 (Zenodo supplement not downloaded), the Vine
  codes (Zenodo 20746752, not downloaded).
- **Not compared in the benchmark:** Gurobi (no licence) and the codeDistance package.
