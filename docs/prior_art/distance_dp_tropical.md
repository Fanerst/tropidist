# Prior-art check, front 1: exact distance algorithms, trellis and width-based DP, tensor networks and tropical algebra

Checked on 2026-10-25 with web search and primary sources: arXiv abstract and HTML pages, full-text PDFs read locally, Crossref metadata, and repository and publisher records. Each item lists the URL actually opened. Anything I could not open or check is marked **[unverified]**.

Labels for the paper's components, used throughout:
- **(a)** dense Rank DP over a column order or rank decomposition, with 2^(cut rank) states;
- **(b)** weight-truncated sparse DP with a meet-in-the-middle (MITM) weight split;
- **(c)** weight-bounded depth-first search with MITM completion tables;
- **(T)** framing the minimum as a "tropical partition function";
- **(W)** the polynomial (weight-enumerator) extension;
- **(R)** the rank-width / subspace-overlap theory.

Novelty-risk labels: **same idea**, **related but different**, **background**.

---

## 0. Bottom line

1. **(a) is the classical trellis (Viterbi) recursion, or its branch-decomposition version, in the min-plus semiring.**
   - The state count 2^dim(span H_P ∩ span H_F) is exactly the minimal-trellis state count given by the state-space theorem. This is my derivation, from Forney 1994, Kschischang–Sorokine 1995 and Ollivier–Tillich 2006.
   - The same subspace S(A,X) = span(A|X) ∩ span(A|E−X) is the DP state space in Cunningham–Geelen 2007.
   - The width notion (dimension of the intersection of the sums on the two sides) is the one defined by Jeong–Kim–Oum (2017, 2021).
   - Trellis-based weight distributions and enumerators already exist for classical codes (Desaki–Fujiwara–Kasami 1994) and for stabilizer codes (Ollivier–Tillich 2006).
   - A tree-decomposition DP for the distance of classical codes appeared in 2025 (Peng et al.).
2. **(T) is not new as a viewpoint.**
   - Liu–Wang–Zhang (PRL 2021) present tropical tensor networks explicitly as the zero-temperature limit of the partition function, and say they are equivalent to dynamic programming.
   - Sommers–Huse–Gullans (PRR 2025) already computed code distances by contracting a tensor network in the tropical algebra, but only for tree (concatenated) codes.
   - Nelson et al. (PRR 2025) used a tropical tensor network for minimum-weight decoding.
3. **(W) is well precedented.**
   - Trellises: Desaki 1994; Ollivier–Tillich 2006.
   - Branch decompositions: Hliněný 2006, via the Tutte polynomial and Greene's theorem.
   - Tensor networks: Farrelly–Tuckett–Stace 2022; Cao–Lackey; Cao–Gullans–Lackey–Wang 2024.
   - Generic semiring tensor networks with truncated polynomials: Liu et al. 2023.
   - For circuits: circuit weight enumerators were defined in October 2026 (Ghosh–Boche–Tanggara), and exact counts of minimum-weight failing configurations were reported in 2025 (Beverland et al.).
4. **The MITM ingredients of (b) and (c) are classical.**
   - Dumer's matching bipartition (1986/1989) and Stern 1989; WJH 2026 benchmarks a MITM implementation (QubitSerf, MeetMiddleMW).
   - For (b), the closest precedent is BEAST (Bocharova et al., IEEE TIT 2004): a bidirectional forward/backward search over code trees for low-weight trellis paths.
5. **The syndrome-driven branching of (c) is the principle of the connected-cluster algorithm.**
   - Connected cluster: Dumer–Kovalev–Pryadko. dist-m4ri already accepts Stim detector error models (DEMs).
   - Stim's undetectable-logical-error search and the decision tree in "Fail fast" (Beverland et al. 2025) work the same way.
   - Branch-and-bound with trellis (DP) lower bounds inside a search goes back to Garello et al. (2001) for turbo codes.
6. **What I found nowhere:**
   - any DP, trellis or tensor-network method for exact *circuit-level* (DEM) distance;
   - any tropical evaluation of distances of general (non-tree) quantum codes or circuits;
   - any combination of a sparse weight-truncated rank DP with a MITM weight split for quantum codes or circuits.

   The most recent benchmark (Webster–Jacob–Higgott, arXiv:2603.22532 v2) contains no DP, trellis or tensor-network method. These gaps are where the novelty claims can honestly sit.
7. **Cross-front flag (not my front, but important).** Strikis–Browne–Beverland (arXiv:2603.05481, 2026) prove that circuit distance is bounded by the distance of an "extended code". That code is the data errors plus one column per residual (hook) error.
   - The bound runs d_circ ≥ d_ext for single-ancilla circuits, with equality for non-interleaved circuits.
   - This is close to the paper's "time collapse" relaxation, whose columns are single data errors plus hook patterns. It must be cited and the difference explained.

---

## 1. Classical exact and probabilistic distance algorithms

### 1.1 Brouwer–Zimmermann (BZ), Grassl, Magma

**M. Grassl, "Computing Extensions of Linear Codes," Proc. IEEE ISIT 2007, pp. 476–480; arXiv:0704.2596.**
- Opened: https://arxiv.org/abs/0704.2596; full text read from https://arxiv.org/pdf/0704.2596.
- **Lineage.** Section II.B describes the minimum-weight algorithm that Magma implements. It is based on Zimmermann's algorithm (K.-H. Zimmermann, TU Hamburg-Harburg Tech. Rep. 3-96, 1996; Betten et al., *Codierungstheorie*, Springer 1998), which improved one by Brouwer.
- **How it works.** It uses several systematic generator matrices with information sets I_j. It encodes all information vectors of weight w under every matrix. The minimum weight seen is the upper bound. A certified lower bound sums, over j, the quantity max(0, (w+1) − (k − r_j)), where r_j is the relative rank of I_j. The algorithm stops when the two bounds meet.
- **Cost.** About μ·Σ_{w≤w0} C(k,w)(q−1)^(w−1) encodings, which is exponential in w0 ≈ d/μ.
- **Magma reference.** The citable reference for the Magma implementation is Grassl, "Searching for linear codes with large minimum distance," in *Discovering Mathematics with Magma*, Springer 2006, pp. 287–313. I have it from the reference lists of Grassl 2007 and of WJH 2026; the chapter itself was not opened.
- **Not reachable.** The Magma handbook page returned HTTP 401.
- **Overlap.** Same certificate logic as (c): exhausting weight threshold K proves d > K, and bounds are kept two-sided. The mechanism differs: BZ enumerates over information sets of a generator matrix and is not syndrome-driven.
- **Risk.** Background. It is the standard exact baseline. Two-sided certified intervals are not new.

**F. Hernando, F. D. Igual, G. Quintana-Ortí, "Algorithm 994: Fast implementations of the Brouwer–Zimmermann algorithm for the computation of the minimum distance of a random linear code," ACM Trans. Math. Softw. 45(2), 2019, DOI 10.1145/3302389.**
- Seen only in repository records in search results (portalcientific.uji.es) and in the preprint arXiv:1603.06757 listing. **[metadata not opened directly]**
- Content: vectorized and parallel BZ implementations, plus a later distributed-memory version.
- Risk: background.

**F. Hernando, G. Quintana-Ortí, M. Grassl, "Fast Algorithms and Implementations for Computing the Minimum Distance of Quantum Codes," ACM Trans. Quantum Comput. 7(2), art. 12 (2026); arXiv:2408.10743.**
- Opened: https://arxiv.org/abs/2408.10743.
- Content: three BZ-based algorithms for the symplectic distance of stabilizer codes. The authors report gains of more than an order of magnitude over licensed tools.
- Risk: background. This is the state of the art for BZ on quantum codes.

**G. White, M. Grassl, "A New Minimum Weight Algorithm for Additive Codes," Proc. IEEE ISIT 2006, pp. 1119–1123.**
- Seen in the WJH reference list (opened, below).
- Content: BZ for GF(4)-additive (stabilizer) codes. WJH say Magma appears to use it for non-CSS codes.
- Risk: background.

### 1.2 Information-set and collision (ISD) methods

Bibliographic details for this group are as given in the reference lists of DKP 2017 (opened at https://ar5iv.labs.arxiv.org/html/1611.07164) and WJH 2026 (opened), plus Crossref where noted.

- **Prange (1962)**, "The use of information sets in decoding cyclic codes," IRE Trans. Inf. Theory 8(5):5–9. The first ISD method.
- **Lee–Brickell (1988)**, EUROCRYPT 1988, LNCS 330, pp. 275–280.
- **J. S. Leon (1988)**, "A probabilistic algorithm for computing minimum weights of large error-correcting codes," IEEE TIT 34(5):1354–1359, DOI 10.1109/18.21270.
  - Random column permutations plus systematic forms find low-weight words. It is a Lee–Brickell variant.
  - It gives only upper bounds.
- **J. Stern (1989)**, "A method for finding codewords of small weight," Coding Theory and Applications, LNCS 388, pp. 106–113, DOI 10.1007/BFb0019850 (Crossref opened).
  - A collision step splits the information set into two halves and matches partial syndromes. This is a MITM weight split.
- **I. Dumer (1986, 1989, 1991).**
  - Works: "On syndrome decoding of linear codes" (Proc. 9th All-Union Symp., 1986); "Two decoding algorithms for linear codes," Probl. Peredachi Inf. 25(1):24–32 (1989); "On minimum distance decoding of linear codes" (5th Soviet–Swedish Workshop, 1991).
  - Matching bipartition, also called sort-and-match: enumerate all vectors of weight about w/2 on each half and match their syndromes. The complexity exponent is roughly the square root of exhaustive syndrome enumeration; DKP give h(δ)/2 for classical codes.
  - **[original Russian sources not opened]**
- **A. Canteaut, F. Chabaud (1998)**, "A new algorithm for finding minimum-weight words in a linear code: application to McEliece's cryptosystem and to narrow-sense BCH codes of length 511," IEEE TIT 44(1):367–378, DOI 10.1109/18.651067 (Crossref opened).
  - ISD with iterative (Markov-chain) information-set updates.
  - Per the HAL preprint abstract shown in search results, it determined some previously unknown minimum distances of length-511 BCH codes. **[HAL page not opened]**
- **A. Becker, A. Joux, A. May, A. Meurer (BJMM, 2012)**, "Decoding random binary linear codes in 2^{n/20}: How 1+1=0 improves information set decoding," EUROCRYPT 2012, LNCS 7237, pp. 520–536, DOI 10.1007/978-3-642-29011-4_31 (Crossref opened).
  - Representation and collision ISD.
  - DKP quote a worst-case exponent of 0.1019 for it, against 0.1163 for Dumer 1991.
- **Deterministic covering-set variants**: Kruk (1989) and Coffey–Goodman (1990), cited by WJH.

**Overlap.** MITM is central to (b) and (c), so the MITM idea itself is prior art. ISD methods give only upper bounds unless covering designs are used.

**Risk.** Same idea for the MITM component. Otherwise background (heuristic upper bounds).

### 1.3 Hardness background (one line each)

- Vardy, "The intractability of computing the minimum distance of a code," IEEE TIT 43(6):1757–1766 (1997). Crossref opened.
- Downey–Fellows–Vardy–Whittle, SIAM J. Comput. 29(2):545–570 (1999), on parameterized complexity in coding theory. Crossref opened.
- Kapshikar–Kundu, IEEE TIT 69(10):6293–6302 (2023), on hardness for quantum codes. Seen in the WJH reference list.
- Jia, Peng, Liu, Wang, Yan, arXiv:2606.23161 (2026). The exact-weight problem is W[1]-complete in the weight, even for regular LDPC Tanner graphs. Opened: https://arxiv.org/abs/2606.23161.
- Takeaway: weight-parameterized search (component (c)) cannot be FPT in d in general. Width-parameterized DP (components (a) and (b)) is the natural FPT route.

---

## 2. Quantum-code and circuit-distance tools

**I. Dumer, A. A. Kovalev, L. P. Pryadko, "Distance verification for classical and quantum LDPC codes," IEEE TIT 63(7):4675–4686 (2017), DOI 10.1109/TIT.2017.2690381; arXiv:1611.07164.**
- Opened: https://arxiv.org/abs/1611.07164, https://ar5iv.labs.arxiv.org/html/1611.07164, and the Crossref record.
- Predecessors: Dumer–Kovalev–Pryadko, ISIT 2014, "Numerical techniques for finding the distances of quantum codes"; and PRL 115, 050502 (2015).
- **What it covers.**
  - It reviews sliding window (Evseev), matching bipartition (Dumer), punctured bipartition, covering sets (Prange) and Stern-type methods for stabilizer codes.
  - It gives complexity bounds for LDPC ensembles.
  - It introduces the irreducible (connected) cluster algorithm. That algorithm grows a candidate from a fixed start position, at each step adding symbols that satisfy the first unsatisfied check. Minimum-weight codewords are irreducible, so the search is complete.
  - The cluster algorithm's complexity exponent is δ·log₂(γ_m(m−1)). WJH quote O([2(m−1)]^d) for qubit codes with check weight m.
  - For quantum codes the found vector must lie in C⊥ \ C.
  - The paper never mentions trellises, DP or tensor networks.
- **Overlap.** Branching on a fired (unsatisfied) detector and growing only connected, syndrome-driven sets is the core of (c). The paper's rule of picking the fired detector with the fewest candidate columns is a variable-ordering refinement.
- **Risk.** Same idea for (c)'s branching principle. Must cite. Novelty in (c) can only come from refinements: ordering, the MITM tail, thresholds and relaxations.

**L. P. Pryadko, W. Zeng, dist-m4ri (GitHub, 2024; README updated after WJH 2026).**
- Opened: https://github.com/QEC-pages/dist-m4ri.
- Multithreaded C and Python. It offers random window (RW, upper bounds) and connected cluster (CC, exact or certified lower bounds), and can run both at once.
- **It accepts Stim detector error models and Stim circuits directly**, so circuit distance by connected cluster already exists. Its benchmarks include surface-code, bivariate-bicycle (BB) and Mitten circuits.
- Risk: background and the main competitor. It shows that exact circuit distance via syndrome-driven search is not new in itself.

**L. P. Pryadko, V. A. Shabashov, V. K. Kozin, "QDistRnd: A GAP package for computing the distance of quantum error-correcting codes," J. Open Source Softw. 7(71):4120 (2022); arXiv:2308.15140.**
- Opened: https://arxiv.org/abs/2308.15140.
- A random information-set algorithm for GF(q) CSS and stabilizer codes. It gives upper bounds with no performance guarantee, plus an empirical convergence criterion.
- Risk: background.

**M. Webster, A. Jacob, O. Higgott, "Distance-Finding Algorithms for Quantum Codes and Circuits," arXiv:2603.22532 (v1 23 Mar 2026; v2 14 Aug 2026).**
- Opened: https://arxiv.org/abs/2603.22532 and https://arxiv.org/html/2603.22532. Full PDF text, including the whole reference list, read locally.
- **Scope.** It benchmarks exact methods: BZ (Magma), connected cluster (m4riCC), MaxSAT (CLISAT, via Stim-style WCNF) and MIP (Gurobi, SCIP). It also benchmarks heuristics: RW, QDistRnd, the new evolutionary QDistEvol, BP-OSD and three Stim methods. The test set covers classical codes, quantum codes and circuits (surface, color and BB), with an 8-hour limit per run, and the code is released as the codeDistance package.
- **DEM formulation.** It defines circuit distance as the minimum weight of a vector in ker H but not in ker L. This is the same problem as the paper's.
- **MITM.** Section 4.3.1 describes the matching bipartition ("meet in the middle") for CSS and non-CSS codes, with complexity O((2ne/d)^{d/2}) for CSS codes. Implementations are QubitSerf (Cercelescu 2024), Qiskit QEC (under 63 qubits) and their own MeetMiddleMW.
- **Conclusions.**
  - m4riCC is best for low-degree LDPC codes and for surface and color circuits; Gurobi is best for BB circuits.
  - BB circuits were the hardest; exact methods resolved only a few of them.
  - **No DP, trellis, tensor-network, tropical or weight-enumerator computation appears anywhere in the text or references** (only the MacWilliams identity, used for enumeration).
- Risk: must cite as the benchmark and baseline. It also documents the gap the paper fills.

**Solver-based exact methods.**
- **Stim, `shortest_error_sat_problem`.**
  - Builds a WDIMACS MaxSAT instance whose optimum is the circuit's fault distance (Stim PR #703 by N. Shutty, 2024, cited by WJH).
  - Stim's `shortest_graphlike_error` is exact for graphlike errors only.
  - Opened: Stim API docs, https://raw.githubusercontent.com/quantumlib/Stim/main/doc/python_api_reference_vDev.md.
  - Stim paper: C. Gidney, Quantum 5, 497 (2021). **[paper not opened]**
- **N. Lacroix et al. (Google Quantum AI), "Scaling and logic in the color code on a superconducting quantum processor," arXiv:2412.14256.**
  - Opened: https://arxiv.org/html/2412.14256, Appendix C.2.
  - It used Stim's MaxSAT encoding with a CASHWMaxSAT solver to verify d_circ = d for superdense color-code circuits at d = 3, 5, 7.
  - For distances up to 15 only Stim's heuristic search was used, which gives upper bounds.
  - This supports the paper's claim that d = 11 had not been certified before. **[journal version not checked]**
- **D. Ruiz, J. Guillaud, A. Leverrier, M. Mirrahimi, C. Vuillot, "LDPC-cat codes for low-overhead quantum computing in 2D," Nat. Commun. 16, 1040 (2025); arXiv:2401.09541.**
  - Opened: https://arxiv.org/abs/2401.09541 and the HTML, Appendix B.1.
  - Exact distances via the z3 SAT solver with a weight bound and a dichotomic search.
  - Risk: background.
- **Y.-F. Chen, S. M. R. Jafari, C.-Y. Lai, "SAT, MaxSAT, and SMT for QLDPC Distance Computation: A Large-Scale Empirical Study," arXiv:2606.12445 (2026).**
  - Opened: https://arxiv.org/abs/2606.12445.
  - Branch-and-bound MaxSAT works best. BZ-style search loses its advantage on QLDPC codes.
  - Risk: background. Include it in the comparison discussion.
- **MIP formulations.**
  - Landahl–Anderson–Rice, arXiv:1108.5738 (2011), cited by Bravyi et al. and WJH. **[not opened]**
  - Bravyi, Cross, Gambetta, Maslov, Rall, Yoder, Nature 627:778–782 (2024); opened https://ar5iv.labs.arxiv.org/html/2308.07915.
    - Code distances of BB codes via that ILP.
    - Circuit distance only as an upper bound via BP-OSD: d_circ ≤ 10 for all 936 syndrome-cycle variants of [[144,12,12]].

**Circuit-level search and enumeration.**
- **Stim `search_for_undetectable_logical_errors`.** The docs say it is heuristic.
  - It starts from errors that cross an observable and keeps adding errors that cancel the lowest-index detection event.
  - It is truncated by limits on detection-event count and edge degree.
  - Overlap with (c): an untruncated version would be a syndrome-driven exhaustive search. Risk: related but different (heuristic, no certificate).
- **M. E. Beverland, M. Carroll, A. W. Cross, T. J. Yoder, "Fail fast: techniques to probe rare events in quantum error correction," arXiv:2511.15177 (2025).**
  - Opened: https://arxiv.org/abs/2511.15177 and the HTML, Section 4.2.
  - Exact enumeration of all minimum-weight logicals uses a decision tree that branches on an unsatisfied check and prunes with a lower bound on correction weight. For circuits it is augmented with symmetries and fault restrictions.
  - It exactly counts minimum-weight failing configurations.
  - Results: BB(6) circuit D = 6. BB(12) circuit ≤ 10 and BB(18) circuit ≤ 18 are upper bounds only. The tree enumerates logicals of a known D and does not certify distance.
  - Overlap: (c) (branching and pruning) and (W) (leading coefficient of the circuit enumerator).
  - Risk: related, and close in spirit for (c). Must cite. It also shows the BB circuit distances were open, which helps the paper.
- **L. Aghababaie Beni, O. Higgott, N. Shutty, "Tesseract: A Search-Based Decoder for Quantum Error Correction," arXiv:2503.10988 (2025).**
  - Opened: https://arxiv.org/abs/2503.10988.
  - An A* most-likely-error decoder on DEMs. It is a decoder, not a distance method.
  - Risk: background.

**Cross-front: A. Strikis, D. E. Browne, M. E. Beverland, "High-performance syndrome extraction circuits for quantum codes," arXiv:2603.05481 (2026).**
- Opened: https://arxiv.org/abs/2603.05481 and the HTML (Theorem 1, Proposition 3, Corollary 1, Proposition 4).
- **Extended code.** Data columns plus one column per residual (hook) error, each the mod-2 sum of its data columns.
- **Bounds.** d_circ ≥ d_ext for single-ancilla circuits. Non-interleaved circuits have d′_circ = d_ext and d′_circ ≤ d_circ.
- **Claimed reduction.** This reduces circuit distance to a code-capacity-sized problem.
- **Gross code.** No non-interleaving circuit reaches d_circ = 12.
- **Overlap.** Not (a), (b) or (c), but close to the paper's time-collapse relaxation, whose columns are data errors plus hook patterns and which gives a lower bound.
- **Risk.** Related, possibly the same idea for the collapse bound in the single-ancilla case. Must be cited and distinguished: the paper's collapse is a general certified relaxation obtained by summing detectors across rounds.

---

## 3. Trellis complexity, width parameters and DP for minimum distance

### 3.1 Trellis basics (the core of component (a))

- **J. K. Wolf, "Efficient maximum likelihood decoding of linear block codes using a trellis," IEEE TIT 24(1):76–80 (1978).** Crossref opened.
  - The syndrome trellis: states are partial syndromes H_P e_P, at most 2^(n−k) of them, and Viterbi decodes on it.
- **R. J. McEliece, "On the BCJR trellis for linear block codes," IEEE TIT 42(4):1072–1092 (1996).** Crossref opened.
  - Shows the BCJR/Wolf trellis is minimal.
- **G. D. Forney, "Dimension/length profiles and trellis complexity of linear block codes," IEEE TIT 40(6):1741–1752 (1994)**, and **F. R. Kschischang, V. Sorokine, "On the trellis structure of block codes," IEEE TIT 41(6):1924–1937 (1995).** Crossref opened for both.
  - State-space theorem: dim S_k = dim C − dim C_P − dim C_F, where C_P and C_F are the past and future subcodes.
  - Verified in Forney's MIT 6.451 notes, Ch. 10 (Theorem 10.2): https://ocw.mit.edu/courses/6-451-principles-of-digital-communication-ii-spring-2005/1b67ae9f5c124c3bd56c8649afa5af47_chap10.pdf. Full text read.
- **A. Vardy, "Trellis structure of codes," in *Handbook of Coding Theory*, V. Pless, W. C. Huffman (eds.), Elsevier, 1998.**
  - The standard survey. **[chapter not opened; existence confirmed via library records and Forney's notes]**

**Identity worth stating in the paper (my derivation from the state-space theorem).**
- Take C = ker A with A = H, or A = [H; L], and a column split (P, F).
- Then dim C − dim C_P − dim C_F = r(A_P) + r(A_F) − r(A) = dim(span A_P ∩ span A_F).
- So the Rank DP's 2^(cut rank) table is the state set of the minimal syndrome trellis at that cut.
- Its maximum over a column order is the trellis-width, which Kashyap relates to matroid pathwidth. Over a tree it is the branch-width-type width, which for a matroid is λ − 1.
- Carrying L multiplies the state count by at most 2^k.

**Overlap.** (a) is Viterbi in the min-plus semiring on the minimal syndrome trellis (or tree realization) of ker H, with the logical label carried along. Like the trellis, its cost does not depend on d.

**Risk.** Same idea. The novelty of (a) cannot be the recursion itself.

### 3.2 Weight distributions and enumerators from trellises

**Y. Desaki, T. Fujiwara, T. Kasami, "A method for computing the weight distribution of a block code by using its trellis diagram," IEICE Trans. Fundamentals E77-A(8):1230–1237 (1994).**
- Content: counts codewords of weight at most w by trellis DP. Efficient when the trellis is simple; used for the (128,36) extended BCH code.
- **[abstract seen via search-engine excerpt of the IEICE page; the IEICE server was unreachable, so full text not opened]**
- Overlap: (a), (W), and the weight truncation of (b).
- Risk: same idea, for classical codes.

**H. Ollivier, J.-P. Tillich, "Trellises for stabilizer codes: definition and uses," Phys. Rev. A 74, 032304 (2006); arXiv:quant-ph/0512041.**
- Opened: https://arxiv.org/abs/quant-ph/0512041 and https://ar5iv.labs.arxiv.org/html/quant-ph/0512041.
- **What it shows.**
  - Minimal trellises for stabilizer codes, whose state dimension is n + k minus the dimensions of the past and future subgroups.
  - Min-sum on the trellis gives the most likely error; sum-product gives marginals.
  - Polynomials kept at the vertices give the weight enumerator, at cost linear in the number of trellis vertices.
  - The distance is not discussed explicitly, but it follows from the enumerator, or from min-sum restricted to nontrivial logical classes.
- Overlap: (a) and (W) for quantum codes.
- Risk: same idea, for quantum codes. Must cite.

**E. Sabo, A. B. Aloshious, K. R. Brown, "Trellis decoding for qudit stabilizer codes and its application to qubit topological codes," IEEE Trans. Quantum Eng. (2024); arXiv:2106.08251.**
- Opened: https://arxiv.org/abs/2106.08251.
- Viterbi trellis decoders for stabilizer codes; trellis edge count as a measure of difficulty.
- Risk: background.

### 3.3 Tree (cycle-free) realizations: the tree version of (a)

- **G. D. Forney, "Codes on graphs: normal realizations," IEEE TIT 47(2):520–548 (2001)**, and **"Codes on graphs: constraint complexity of cycle-free realizations of linear codes," IEEE TIT 49(7):1597–1610 (2003).** Crossref opened for both.
  - On each edge of a cycle-free realization, the minimal state dimension is dim C − dim C_J − dim C_J̄, where J and J̄ are the coordinates on the two sides of the edge.
  - Content verified via Kashyap 2009 below.
- **N. Kashyap, "Constraint complexity of realizations of linear codes on arbitrary graphs," IEEE TIT 55(11):4864–4877 (2009); arXiv:0805.2199.**
  - Opened: https://ar5iv.labs.arxiv.org/html/0805.2199 and the Crossref record.
  - Defines the treewidth of a code (best cycle-free realization) and its pathwidth (best trellis), and shows κ_path/κ_tree = O(log n).
- **N. Kashyap, A. Thangaraj, "The treewidth of MDS and Reed–Muller codes," IEEE TIT 58(7) (2012); arXiv:1102.2734.**
  - Opened: https://arxiv.org/abs/1102.2734. **[pages not verified]**
  - Treewidth equals trellis-width for MDS and Reed–Muller codes. It is presented as the parameter for ML-decoding complexity.

**Overlap.** These give the tree-decomposition version of (a) and its width, which is (R).

**Risk.** Same idea for the width theory.

### 3.4 Width parameters and finding good orders and trees (the theory side, (R))

- **N. Kashyap, "Matroid pathwidth and code trellis complexity," SIAM J. Discrete Math. 22(1):256–272 (2008), DOI 10.1137/070691152; arXiv:0705.1384.**
  - Opened: https://arxiv.org/abs/0705.1384 and the Crossref record.
  - Relates trellis-width (minimum trellis state complexity) to matroid pathwidth.
  - Computing it is NP-hard; codes of bounded trellis-width form a minor-closed class.
  - Risk: same idea for "linear rank-width of a code"; must cite.
- **G. B. Horn, F. R. Kschischang, "On the intractability of permuting a block code to minimize trellis complexity," IEEE TIT 42(6):2042–2048 (1996)**, and **T. Kasami, T. Takata, T. Fujiwara, S. Lin, "On the optimum bit orders with respect to the state complexity of trellis diagrams for binary linear codes," IEEE TIT 39(1):242–245 (1993).** Crossref opened for both.
  - Choosing the column order is hard; work on good orders exists.
  - Risk: background for column-order heuristics.
- **J. Jeong, E. J. Kim, S. Oum, "The 'art of trellis decoding' is fixed-parameter tractable," IEEE TIT 63(11):7178–7205 (2017); arXiv:1507.02184.**
  - Opened: https://arxiv.org/abs/1507.02184.
  - The width of a linear layout of subspaces is the maximum dimension of the intersection between the sum of the earlier subspaces and the sum of the later ones.
  - An FPT algorithm constructs a layout of width ≤ k. Trellis-width, matroid path-width and linear rank-width are special cases.
  - Risk: same idea and the same definition as the linear case of "subspace overlap".
- **J. Jeong, E. J. Kim, S. Oum, "Finding branch-decompositions of matroids, hypergraphs, and more," SIAM J. Discrete Math. 35(4):2544–2617 (2021); arXiv:1711.01381.**
  - Opened: https://arxiv.org/abs/1711.01381 and the Crossref record.
  - The tree version: the width of a tree edge is the dimension of the intersection of the sums on the two sides. An FPT construction is given.
  - Risk: same idea and the same definition as the tree case of "subspace overlap".
- **P. Hliněný, S. Oum, "Finding branch-decompositions and rank-decompositions," SIAM J. Comput. 38(3):1012–1032 (2008).** Crossref opened.
  - Risk: background.

### 3.5 FPT and DP algorithms parameterized by branch-width or treewidth

- **P. Hliněný, "Branch-width, parse trees, and monadic second-order logic for matroids," J. Combin. Theory Ser. B 96(3):325–351 (2006).**
  - Opened: Crossref record and https://www.muni.cz/en/research/publications/589863.
  - Content: matroid parse trees; MSO-definable properties of bounded-branch-width matroids represented over finite fields are recognized by tree automata (Courcelle-style). The author mentions applications in coding theory.
  - Risk: background. This is a meta-theorem, and the author's MFCS 2003 version itself notes impractical constants.
- **P. Hliněný, "The Tutte polynomial for matroids of bounded branch-width," Combin. Probab. Comput. 15(3):397–409 (2006), DOI 10.1017/S0963548305007297.**
  - Opened: preprint https://www.fi.muni.cz/~hlineny/papers/bwtutte-cpc.pdf, full text read.
  - A recursive formula over a parse tree of a branch decomposition computes the Tutte polynomial in polynomial time with a fixed exponent: O(n^6 log n log log n) for fixed width and field.
  - The paper lists the weight enumerator of a linear code among the Tutte specializations, via C. Greene, Stud. Appl. Math. 55(2):119–128 (1976) (Crossref opened).
  - Overlap: (W), and (a) on trees.
  - Risk: same idea in theory. Weight enumerators parameterized by branch-width are known.
- **W. H. Cunningham, J. Geelen, "On integer programming and the branch-width of the constraint matrix," IPCO 2007, LNCS 4513, pp. 158–166, DOI 10.1007/978-3-540-72792-7_13.**
  - Opened: https://math.uwaterloo.ca/~whcunnin/bw.pdf (full text read) and the Crossref record.
  - The DP over a branch decomposition of the column matroid uses partial right-hand-side vectors lying in S(A,X) = span(A|X) ∩ span(A|E−X), with dim S = λ − 1.
  - This gives a pseudo-polynomial ILP algorithm for bounded branch-width; a practical implementation followed (Margulies–Ma–Hicks, INFORMS J. Comput. 25(4), 2013).
  - Overlap: (a) and (R). It is exactly the same state-space construction, over Z≥0 instead of GF(2).
  - Risk: same idea (different field and problem). Strongly recommended citation.
- **Q. Peng, K. Liu, G. Yan, G. Wang, "Linear complexity computation of code distance and minimum size of trapping sets for LDPC codes with bounded treewidth," arXiv:2509.13040 (v1 2025, v2 Jan 2026).**
  - Opened: https://arxiv.org/abs/2509.13040 and https://arxiv.org/html/2509.13040.
  - A nice-tree-decomposition DP on the Tanner graph computes the minimum distance (case b = 0) and minimum trapping sets, and counts the minimizers.
  - Cost is O(n·4^k) for treewidth k, and O(n·2^k) for path decompositions.
  - Classical only: no logical-coset condition and no quantum codes. States are subsets of bag nodes, not a linear-algebra compression.
  - Overlap: (a), with cost independent of d, and the counting part of (W).
  - Risk: same idea for classical code distance. Must cite; the paper's distinction is the GF(2) subspace states, quantum and circuit L-constraints, and scale.
- **M. Kumar, H. Raddum, S. Varadharajan, "Graphs and self-dual additive codes over GF(4)," WCC 2019 (venue per the Simula record).**
  - Opened: https://web-backend.simula.no/sites/default/files/publications/files/graph_codes.pdf.
  - Rank-width of graph codes; weight enumerators via binary decision diagrams.
  - Risk: background (minor).

### 3.6 Semiring view of trellis and junction-tree DP

- **S. M. Aji, R. J. McEliece, "The generalized distributive law," IEEE TIT 46(2):325–343 (2000).** Crossref opened.
  - DP on junction trees over any commutative semiring. Viterbi (min-sum) and BCJR/sum-product are instances.
  - Risk: background for (T) and (W). Swapping min-plus for polynomials is standard.
- **A. Heim, V. Sidorenko, U. Sorger, "Trellis computations," arXiv:0711.2873 (2007).**
  - Opened: https://arxiv.org/abs/0711.2873.
  - Moments and distributions on trellises over commutative semirings.
  - Risk: background.

---

## 4. Tensor networks, weight enumerators and tropical algebra

**J.-G. Liu, L. Wang, P. Zhang, "Tropical tensor network for ground states of spin glasses," Phys. Rev. Lett. 126, 090506 (2021); arXiv:2008.06888.**
- Opened: https://arxiv.org/abs/2008.06888 and https://ar5iv.labs.arxiv.org/html/2008.06888.
- **What it does.**
  - Contracts the tensor network in the tropical (max-plus) semiring. This is presented as computing the partition function directly in the zero-temperature limit.
  - Recovers the ground-state configuration by automatic differentiation, and counts degeneracy by mixing the tropical and ordinary algebras.
  - Sizes: up to 1024 spins on a square lattice.
- **Their own remark on DP.** The authors write that the approach is "not conceptually new since there can be equivalent dynamic programming" formulations, and that on trees it equals max-sum.
- Overlap: (T), and (W) through degeneracy counting.
- Risk: same framing, applied to spin glasses. The paper's "tropical partition function" should cite this as the source of the term and viewpoint.

**J.-G. Liu, X. Gao, M. Cain, M. D. Lukin, S.-T. Wang, "Computing solution space properties of combinatorial optimization problems via generic tensor networks," SIAM J. Sci. Comput. 45(3):A1239–A1270 (2023), DOI 10.1137/22M1501787; arXiv:2205.03718.**
- Opened: https://arxiv.org/abs/2205.03718 and https://ar5iv.labs.arxiv.org/html/2205.03718.
- **Element types it swaps in:**
  - tropical numbers, with a counting variant;
  - "extended tropical of order k" (the k best values);
  - polynomials (e.g. the independence polynomial);
  - truncated polynomials, keeping only the largest or the smallest orders;
  - set and bit-string algebras for enumeration.
- Complexity is stated via treewidth; the conclusion links tropical tensor networks to DP.
- Overlap: (T), (W), and the weight truncation of (b) (truncated polynomials, k-best tropical).
- Risk: same algebraic toolkit on a different problem (independent sets). Cite for the semiring and truncation machinery.

**T. Farrelly, D. K. Tuckett, T. M. Stace, "Local tensor-network codes," New J. Phys. 24, 043015 (2022), DOI 10.1088/1367-2630/ac5e87; arXiv:2109.11996.**
- Opened: https://arxiv.org/abs/2109.11996 and https://ar5iv.labs.arxiv.org/html/2109.11996.
- **Method.** Contracting code tensors with "weight tensors" gives the histogram of weights in each logical coset. The distance is the first weight at which nontrivial cosets have nonzero counts.
- **Cost.** Polynomial for holographic codes; the method is also efficient for some local log-depth 1D circuit codes.
- The paper does not mention a tropical semiring, min-plus, trellises or DP.
- Overlap: (a) and (W), for code distance by contraction (counting semiring with a weight index).
- Risk: same idea for code distance by contraction. Different semiring, and codes rather than circuits.

**C. Cao, B. Lackey, "Quantum weight enumerators and tensor networks," arXiv:2211.02756 (2022/2023).**
- Opened: https://arxiv.org/abs/2211.02756.
- Journal version cited by Sommers et al. as IEEE TIT 70, 3512 (2024). **[journal record not independently verified]**
- Content: tensor enumerators whose trace is compatible with tensor-network contraction; general quantum MacWilliams identities.
- Overlap: (W).
- Risk: related.

**C. Cao, M. J. Gullans, B. Lackey, Z. Wang, "Quantum Lego expansion pack: enumerators from tensor networks," PRX Quantum 5, 030313 (2024); arXiv:2308.05152.**
- Opened: https://arxiv.org/abs/2308.05152 and https://ar5iv.labs.arxiv.org/html/2308.05152.
- **Method and cost.**
  - Tensor-network contraction computes quantum weight enumerators and hence distances.
  - Cost is O(|V|·exp(|C_max|)), where C_max is the largest edge cut.
  - The authors claim exponential speedups for some degenerate codes.
- **Examples:** [[256,1,16]] rotated surface code in about 20 minutes on a laptop; 2D color code [[91,1,11]].
- No truncation at the target weight, no tropical algebra, no trellis.
- Overlap: (a) and (W), for codes with a known tensor-network structure.
- Risk: same idea for enumerators and distances by contraction, on codes. Any "exponential speedup" claim should be compared with this.

**G. M. Sommers, D. A. Huse, M. J. Gullans, "Dynamically generated concatenated codes and their phase diagrams," Phys. Rev. Research 7, 023086 (2025); arXiv:2409.13801.**
- Opened: https://arxiv.org/abs/2409.13801 and https://arxiv.org/html/2409.13801, Supplement §II.2.
- **Method.** To get distances alone, they contract the tree-code tensor network in the tropical algebra: multiplication becomes addition, addition becomes minimum, 0 maps to ∞ and 1 maps to 0.
- **Output:** the minimum logical weight in each logical class (d₁, d₂, d₃), and from these, recursions for the distance.
- For the tropical algebra they cite Maclagan–Sturmfels; for enumerators, Cao–Lackey and Cao et al.
- Overlap: (T) and (a). This is an explicit tropical tensor-network computation of code distance.
- Risk: **same idea, limited to tree (concatenated) codes.** It is the closest prior work to "distance = tropical contraction" and must be cited.

**J. Nelson, G. Bentsen, S. T. Flammia, M. J. Gullans, "Fault-tolerant quantum memory using low-depth random circuit codes," Phys. Rev. Research 7, 013040 (2025); arXiv:2311.17985.**
- Opened: https://arxiv.org/abs/2311.17985 and https://authors.library.caltech.edu/records/r1ar3-agj87.
- An ML decoder written as a tensor-network contraction; its tropical version does minimum-weight decoding.
- Overlap: (T).
- Risk: related (decoding, not distance).

**Tensor-network decoders and statistical-mechanics mappings (background for (T)).**
- **Decoders:**
  - Bravyi–Suchara–Vargo, Phys. Rev. A 90, 032326 (2014); opened https://arxiv.org/abs/1405.4883.
  - Chubb, arXiv:2101.04125 (2021); opened https://arxiv.org/abs/2101.04125.
  - Piveteau–Chubb–Renes, PRX Quantum 5, 040303 (2024), which includes circuit-level noise; opened https://arxiv.org/abs/2310.10722.
- **Mappings:**
  - Chubb–Flammia, Ann. Inst. Henri Poincaré D 8(2):269–321 (2021), covering correlated noise and fault tolerance; opened https://arxiv.org/abs/1809.10704.
  - Aitchison–Béri, "Spacetime spins," arXiv:2512.21991 (2025), mapping circuit-level logical classes to partition functions; opened https://arxiv.org/abs/2512.21991.
- **Implication.** Logical-class partition functions for circuits and their tensor-network contraction exist. The circuit distance is their zero-temperature limit restricted to trivial syndrome and nontrivial class. So the "tropical partition function" is a natural, unpublished-but-obvious specialization, not a new object.

**S. Ghosh, H. Boche, A. Tanggara, "Fault tolerance of quantum circuits with tensor networks and symplectic geometry," arXiv:2610.03429 (v1 2 Oct 2026, v2 16 Oct 2026).**
- Opened: https://arxiv.org/abs/2610.03429 and https://arxiv.org/html/2610.03429.
- **Content.**
  - Closed-form detection and logical-effect matrices for circuit distance.
  - Multivariate *circuit weight enumerators* and MacWilliams identities for them.
  - LP upper bounds on circuit distance, including flag-circuit constraints.
  - Example: Hastings–Haah honeycomb Floquet circuit with distance 4.
- No exact contraction-based distance algorithm is visible in the text I read.
- Overlap: (W), for circuits.
- Risk: related and concurrent. Cite it if the paper presents circuit enumerators.

---

## 5. Earlier unifications of DP and search, and the zero-temperature view

**R. Garello, P. Pierleoni, S. Benedetto, "Computing the free distance of turbo codes and serially concatenated codes with interleavers: algorithms and applications," IEEE J. Sel. Areas Commun. 19(5):800–812 (2001).**
- Mechanism read in Y. Ould-Cheikh-Mouhamedou's McGill thesis, Ch. 4.2: https://www.mmsp.ece.mcgill.ca/Theses/2005/Ould-Cheikh-MouhamedouT2005.pdf (full text read). **[original paper not opened]**
- **How it works.**
  - The exact distance comes from a recursive search over input bits ("constrained subcodes").
  - At each node, a lower bound is computed with modified Viterbi (min-sum) passes on the constituent trellises, with branches inconsistent with the fixed bits given effectively infinite weight.
  - Nodes whose bound exceeds the current best are pruned.
- **Result:** d_free = 40 for a rate-1/3 turbo code with an interleaver of length 3568 (per the abstract shown in search results).
- Overlap: a precedent for unifying trellis DP (as bounds) with search.
- Risk: related but different. DP is used as a bound inside the search, not as an alternative evaluator or MITM completion.

**I. Bocharova, M. Handlery, R. Johannesson, B. Kudryashov, "A BEAST for prowling in trees," IEEE TIT 50(6):1295–1302 (2004), DOI 10.1109/TIT.2004.828093**, and **"BEAST decoding of block codes obtained via convolutional codes," IEEE TIT 51(5):1880–1891 (2005).**
- Opened: https://lup.lub.lu.se/record/276239 and https://lup.lub.lu.se/record/244441.
- The abstracts describe a bidirectional forward/backward search over code trees that finds low-weight trellis paths, gives weight spectra and free distances, and found new best convolutional and tail-biting codes.
- Secondary descriptions in search results add the details: forward and backward trees stored only up to a weight bound, then matched on common states with the target combined weight. **[these internal details not verified in full text]**
- Overlap: (b). This is a MITM weight split on a trellis, with weight-truncated partial tables.
- Risk: **same core idea as (b)**, in the convolutional and tail-biting setting. Must cite.

**E. Rosnes, Ø. Ytrehus.**
- Works: "Improved algorithms for the determination of turbo-code weight distributions," IEEE Trans. Commun. 53(1):20–26 (2005); "An efficient algorithm to find all small-size stopping sets of low-density parity-check matrices," IEEE TIT 55(9):4167–4178 (2009); and, with M. A. Ambroze and M. Tomlinson, the Addendum, IEEE TIT 58(1):164–171 (2012).
- Opened: Crossref records and https://researchportal.plymouth.ac.uk/en/publications/addendum-to-an-efficient-algorithm-to-find-all-small-size-stoppin/.
- Branch-and-bound tree searches for low-weight structures. The keywords include minimum distance and weight spectrum. **[algorithm details and the minimum-distance extension not verified]**
- Overlap: (c).
- Risk: related.

**The zero-temperature view.**
- The weight enumerator is a partition function, and the minimum distance is its lowest-order exponent (tropicalization). This is implicit in the trellis and tensor-network enumerator literature above, and explicit in Liu–Wang–Zhang 2021 for spin glasses.
- I found no paper that names the circuit distance a "tropical partition function". A search for the exact phrase returned only unrelated tropical-limit papers from statistical physics.

---

## 6. Searches that found nothing (negative results; useful for claims)

- DP, trellis or tensor-network computation of *circuit-level* (DEM) distance. The search covered:
  - WJH 2026 (text and references);
  - Stim documentation;
  - the dist-m4ri README;
  - Beverland et al. 2025, Lacroix et al., Strikis et al. and Ghosh et al. 2026;
  - general searches on "circuit distance" combined with "tensor network", "trellis", "transfer matrix" or "dynamic programming".

  None found.
- Tropical evaluation of distances of non-tree quantum codes or circuits. Found only for tree codes (Sommers et al. 2025); counting-semiring tensor networks exist for codes (Farrelly 2022; Cao et al. 2024).
- A sparse, weight-truncated rank (subspace-state) DP with a MITM weight split for quantum codes. Closest: BEAST for convolutional codes; Desaki 1994 (weight-bounded trellis counting); Liu 2023 (truncated polynomials).
- Exact certified circuit distances for the instances the paper cites. No prior certificate found for:
  - the [[144,12,12]] or [[288,12,18]] BB circuits: only upper bounds in Bravyi et al. 2024 and Beverland et al. 2025, and only a few BB circuits solved in WJH;
  - the superdense color-code circuit at d = 11: exact MaxSAT only up to d = 7 in Lacroix et al.

---

## 7. Implications for our novelty claims

### 7.1 Clearly prior art: must be cited, must not be claimed

1. **The DP recursion of (a).**
   - It is the min-plus (Viterbi) recursion on the minimal syndrome trellis (Wolf 1978; BCJR and McEliece 1996), with states counted by the state-space theorem (Forney 1994; Kschischang–Sorokine 1995; Vardy 1998). Its tree version follows from cycle-free realizations (Forney 2001, 2003; Kashyap 2009).
   - Computing weight distributions and minimum distances by trellis DP is old: Desaki–Fujiwara–Kasami 1994 for classical codes, Ollivier–Tillich 2006 for stabilizer codes.
   - A treewidth DP for the distance of classical codes exists (Peng et al. 2025).
2. **The width theory of (R).**
   - The state space S(A,X) = span(A|X) ∩ span(A|E−X) and DP over branch decompositions: Cunningham–Geelen 2007.
   - The width defined as the dimension of the intersection of the sums on the two sides, for linear layouts and branch decompositions: Jeong–Kim–Oum 2017, 2021.
   - Trellis-width related to matroid pathwidth, and NP-hard: Kashyap 2008. Hardness of the optimal permutation: Horn–Kschischang 1996.
   - FPT results by branch-width: Hliněný 2006 (both papers).
3. **The polynomial and enumerator extension of (W).** Swapping the semiring is standard (GDL, Aji–McEliece 2000). It is done for:
   - trellises: Desaki 1994; Ollivier–Tillich 2006;
   - branch decompositions, via Tutte and Greene: Hliněný 2006;
   - tensor networks: Farrelly et al. 2022; Cao–Lackey; Cao et al. 2024;
   - with truncated polynomials and k-best tropical numbers: Liu et al. 2023.

   For circuits, circuit weight enumerators (Ghosh et al. 2026) and exact counts of minimum-weight failures (Beverland et al. 2025) already exist.
4. **The tropical framing of (T).** The tropical tensor network as the zero-temperature partition function, equivalent to DP: Liu–Wang–Zhang 2021; Liu et al. 2023. Tropical contraction for code distance of tree codes: Sommers–Huse–Gullans 2025. Tropical tensor network for minimum-weight decoding: Nelson et al. 2025.
5. **MITM.** Matching bipartition (Dumer 1986/1989), Stern 1989 and Dumer 1991, plus existing MITM distance codes (QubitSerf, MeetMiddleMW in WJH). A forward/backward weight split on trellises: BEAST 2004.
6. **Syndrome-driven exhaustive search with weight thresholds, as in (c).**
   - Connected cluster (DKP 2014, 2015, 2017), implemented in dist-m4ri *with DEM input*.
   - Stim's undetectable-error search, and the decision tree in Fail fast (Beverland et al. 2025).
   - Branch-and-bound with DP lower bounds (Garello et al. 2001; Rosnes–Ytrehus).
   - Two-sided certified bounds as in BZ (Grassl; Magma).
7. **Exact circuit distance as such.** MaxSAT via Stim (Lacroix et al.; WJH), MIP (WJH, Gurobi and SCIP), and CC (dist-m4ri, WJH).

### 7.2 What appears new, as far as this search reaches

- Applying trellis or rank-decomposition DP, both the dense form and the weight-truncated sparse form, to **exact circuit-level distance of detector error models** at scale (10⁴–10⁵ fault mechanisms). No DP, trellis or tensor-network method appears in any circuit-distance work found.
- A **tropical (min-plus) treatment of distances for general, non-tree quantum codes and circuits**, with three evaluators of the same function (dense DP, sparse truncated DP, search). The novelty is the unification and the evaluators, not the semiring.
- The **combination in (b)**: a GF(2) subspace-state DP truncated by weight and combined by a MITM weight split at a cut. Closest precedent: BEAST, for convolutional codes.
- The specific **search engine and pipeline**:
  - branching on the fired detector with the fewest candidates;
  - a MITM syndrome table replacing the last k levels;
  - the time-collapse relaxation;
  - a lift step;
  - DP evaluators.

  This holds only if the time collapse is differentiated from Strikis–Browne–Beverland's extended-code bound.
- The **certified values** reported in the notes: superdense color code d = 11, [[288,12,18]] BB circuit d = 16, and the [[1044,526,12]] circuit d = 10. No prior certificates were found; existing results are upper bounds or exact values for smaller d only.
- A statement that the trellis-width of a DEM in time order is bounded by checks per round, independent of the number of rounds, appears new as an *application*. It is a direct corollary of the state-space theorem, so present it as an observation or proposition, not a deep result.

### 7.3 Claims that need careful wording

- Not "a new dynamic program for minimum distance". Instead: "the classical trellis/branch-decomposition recursion (min-plus Viterbi), specialized to ker H with a logical label and applied to DEMs". State the identity from §3.1: 2^(cut rank) is the minimal-trellis state count, as in Forney 1994, Kashyap 2008 and Cunningham–Geelen 2007.
- **Use the name "rank-width" with care.**
  - Rank-width (Oum–Seymour) is a graph parameter.
  - For codes, the established notions are trellis-width (related to matroid pathwidth, Kashyap) and code treewidth or branch-width (Forney, Kashyap, Hliněný).
  - "Subspace-overlap width" is the width of Jeong–Kim–Oum 2017/2021.
  - Do not present it as a new parameter. If a new name is kept, say it coincides with these.
- **"Tropical partition function".** Present it as a viewpoint borrowed from Liu–Wang–Zhang 2021 and from the statistical-mechanics mapping (Dennis et al.; Chubb–Flammia), and note that Sommers–Huse–Gullans 2025 already contracted tropical networks for distances of tree codes. Claim the general circuit-level formulation and its evaluators, not the concept.
- **"Polynomial extension to weight enumerators".** Say it is the standard semiring substitution (GDL). Cite the trellis (Desaki; Ollivier–Tillich), branch-width (Hliněný) and tensor-network (Farrelly; Cao et al.; Liu et al.) precedents. For circuits, cite Ghosh et al. 2026 and Beverland et al. 2025. Claim only what is specific: e.g. weight-truncated enumerators of DEMs, or exact leading coefficients at new sizes.
- **"Meet in the middle".** Attribute it to Dumer and Stern. For the DP version, cite BEAST. Claim the integration with subspace-state tables and the use for certification.
- **"Cost independent of the distance".** True for dense (a), but it is the classical property of trellis decoding (O(n·2^width)). Do not present it as a discovery.
- **"First exact" or "first certified" circuit distances.** Restrict to specific instances and sizes. MaxSAT, MIP and CC already give exact circuit distances on small and medium circuits, and dist-m4ri reads DEMs.
- **Speedup claims against tensor-network enumerator methods.** Cao et al. 2024 claim exponential speedups for some degenerate codes. Any comparison should be on the same instances, or worded as complementary (their method needs a known tensor-network structure; the paper's works from H and L alone).
- **Time collapse (outside this front).** Cite Strikis–Browne–Beverland 2026. Explain whether the collapse bound reduces to their d_circ ≥ d_ext in the single-ancilla case, and how it differs: no circuit-class assumptions, obtained by summing detectors across rounds, certified by construction.

### 7.4 Minimal must-cite list for this front

- **Exact distance baselines:** Grassl 2006/2007 (BZ, Magma); Hernando–Quintana-Ortí–Grassl 2026.
- **ISD and MITM:** Leon 1988; Stern 1989; Dumer 1989/1991; Canteaut–Chabaud 1998.
- **Quantum and circuit distance tools:** DKP 2017 with dist-m4ri; QDistRnd; WJH 2026; Stim (MaxSAT encoding and heuristic search); Beverland et al. 2025; Strikis et al. 2026.
- **Trellis and width theory:** Wolf 1978; Forney 1994; Kschischang–Sorokine 1995; Vardy 1998; Forney 2003; Kashyap 2008; Jeong–Kim–Oum 2017/2021; Cunningham–Geelen 2007; Hliněný 2006 (Tutte).
- **DP for distances and enumerators:** Desaki–Fujiwara–Kasami 1994; Ollivier–Tillich 2006; Peng et al. 2025.
- **Semiring and tropical tensor networks:** Aji–McEliece 2000; Liu–Wang–Zhang 2021; Liu et al. 2023.
- **Tensor networks for code distance:** Farrelly–Tuckett–Stace 2022; Cao–Gullans–Lackey–Wang 2024; Sommers–Huse–Gullans 2025.
- **DP inside search:** BEAST 2004; Garello et al. 2001.
- **Circuit enumerators:** Ghosh–Boche–Tanggara 2026.

### Not verified (re-check before citing)

- Vardy 1998 chapter content.
- Desaki 1994 full text (abstract only, via search engine).
- Cao–Lackey journal version (IEEE TIT 70, 3512, as cited by Sommers et al.).
- BEAST internal mechanics (abstract-level only).
- Garello 2001 original text (mechanics taken from a thesis).
- Rosnes–Ytrehus algorithm details.
- Landahl–Anderson–Rice 2011 (MIP), not opened.
- Hernando–Igual–Quintana-Ortí 2019 metadata (repository listing only).
- Kashyap–Thangaraj 2012 pages.
- Lacroix et al. journal version.
- Magma handbook (HTTP 401).
- Dumer's 1986/1989/1991 Russian sources (only as cited by DKP).
