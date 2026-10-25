# Front 3: prior art for the search and DP techniques (coding theory, cryptanalysis, combinatorial search)

Prior-art check, 2026-10-25. It covers the two methods of the paper:

- **(A)** a weight-truncated min-plus DP along a column order. It is bidirectional: a backward table with weights ≤ K−a, and a forward sweep with weights ≤ a−1 whose new states are joined with that table at every cut. The split may decrease along the sweep, and states are pruned by an admissible covering lookahead.
- **(B)** a depth-first search over canonical prefixes. It branches on an unsatisfied check with earlier siblings forbidden, and finishes with one lookup in a syndrome-keyed table of all column subsets of size ≤ k. It uses a covering bound, pruning by a relaxed problem's table, and iterative deepening.

**How well each source was checked:**

- **[F]** I read the relevant part of the full text.
- **[A]** I read the abstract or a bibliographic page.
- **[S]** I verified it only through a named secondary source.
- **[U]** not verified: the citation comes from memory or a search snippet, and the details may be wrong.

Quotes are kept under 15 words.

---

## 0. Bottom line

1. **At its core, (A) is BEAST.** BEAST was published by Bocharova, Handlery, Johannesson and Kudryashov (2002, 2004 and 2005), and it runs on the BCJR/Wolf syndrome trellis. The fullest description I could read is in Hug's 2012 Lund thesis [F]. That description already contains the following:
   - trellis states are partial syndromes;
   - the threshold is split, T = T_F + T_B;
   - the forward frontier (nodes whose weight first reaches T_F) is matched with backward nodes of weight ≤ T_B, when their states are equal and their depths are complementary;
   - matching happens at every depth;
   - thresholds are raised iteratively;
   - a nondecreasing metric is stated as the condition for exactness;
   - one may raise only one side's threshold.

   With Hamming metric, T_F = a and T_B = K−a, this is exactly the a−1 / a / K−a arithmetic of (A).
   - **Older roots.** The fact that a balanced split point always exists goes back to Dumer's sliding split-syndrome decoding (1986 and 1989) [S]. A bidirectional min-weight search that keeps the lowest weight per state and prunes at about half the bound already appears in Larsen (1973), for free distance [S].
2. **What BEAST, as described, does not have:**
   - **Merging equal states (a min-plus DP).** BEAST uses code trees, with paths kept separate, because it counts spectra and backtracks.
   - **A covering lookahead.** BEAST only uses length or depth constraints.
   - **A split that depends on position along the sweep.** BEAST's split is fixed per threshold and adapted only between iterations.
   - **Any use on quantum codes or circuits.**

   These are the defensible differences. Each one has close analogs elsewhere:
   - Viterbi merging, and Larsen's per-state minimum weights.
   - The lookahead bounds of FAST (1989), Garello–Pierleoni–Benedetto (2001) and A* decoding (1993, 1996), and the covering bound J(t−ℓ−1) of Bocharova et al. (2012).
   - Dynamic half-way points (Tilk et al. 2017), the GBFHS split function (2018) and fractional MM (2017).
3. **(B) combines known pieces.** It is closest to the irreducible-cluster (IC) / connected-cluster (CC) search of Dumer, Kovalev and Pryadko, and to the partial-syndrome tree search "Algorithm MD" of Bocharova et al. (2012). Its components and their sources:
   - **Branching on the first unsatisfied check** comes from DKP (2015 and 2017; [F] for the 2017 paper). Its complexity is about (m−1)^d for binary and CSS codes, with m the row weight.
   - **Duplicate-free canonical enumeration of clusters** appears in Kovalev–Dumer–Pryadko (2013) [F].
   - **Partial-syndrome tree search with the covering bound "syndrome weight > J(t−ℓ−1)"** is in Bocharova et al. (2012) [F].
   - **LP-relaxation branch-and-bound** is in Rosnes–Ytrehus (2009 and 2012) [S], with branch-and-cut in Keha–Duman (2010) [S].
   - **Finishing with a lookup in a table of all states near the goal** is perimeter search (Dillenburg–Nelson 1994; Manzini 1995) [A], or Dumer-style sort-and-match.
   - **The relaxed problem's table** is a pattern database (Culberson–Schaeffer 1998) [A].
   - **Iterative deepening** is IDA* (Korf 1985) [A].
4. **Urgent: the main baseline has recently converged on (B).** The CC mode of **dist-m4ri** now has all of the following, verified from its README and git history [F]:
   - clusters start from the smallest column;
   - a cluster is extended only by the columns of the first row of its syndrome (in the source since at least 2026-09-18);
   - the **last column is found by a hash lookup** of the remaining syndrome, a meet-in-the-middle with k = 1 (commit `3e03f1e`, 2026-10-11);
   - rows are sorted by weight (2026-10-14).

   **Stim's `search_for_undetectable_logical_errors`** is a breadth-first search over states (detector set, observable mask). It merges equal states and branches only on errors touching the lowest-index detector [F, code]. It is labelled heuristic only because of its truncation options.
5. **Gaps I found.** I found no prior use of either of these for exact code or circuit distance:
   - a BEAST-type bidirectional trellis DP;
   - a perimeter-style table of all subsets of size ≤ k with k ≥ 2.

   The 2026 benchmark by Webster–Jacob–Higgott names no DP, trellis or meet-in-the-middle exact method [A]. The quantum front should check Sabo's 2022 Georgia Tech dissertation, whose abstract claims a trellis-based minimum-distance algorithm for stabilizer codes; I could not see its details.

---

## 1. BEAST and other bidirectional trellis and tree searches for distance

### 1.1 BEAST: Bidirectional Efficient Algorithm for Searching code Trees

**Citations:**

- I. E. Bocharova, M. Handlery, R. Johannesson, B. D. Kudryashov, "A BEAST for prowling in trees," *IEEE Trans. Inf. Theory* 50(6):1295–1302, 2004, DOI 10.1109/TIT.2004.828093 [A]. Opened: https://www.lunduniversity.lu.se/lup/publication/48a7d791-8ef2-4be4-8f66-1cedeccb9af8 and https://lup.lub.lu.se/record/276239
- Conference precursor: same authors, "How to efficiently find the minimum distance of tailbiting codes," ISIT 2002, p. 259 [A]. Opened: https://lup.lub.lu.se/record/629027
- Block-code decoding:
  - Bocharova, Johannesson, Kudryashov, Lončar, "BEAST decoding for block codes," ITG SCC 2004 (ITG-Fachbericht 181), pp. 173–178 [A]. Opened: https://portal.research.lu.se/en/publications/beast-decoding-for-block-codes-2/
  - Bocharova, Handlery, Johannesson, Kudryashov, "BEAST decoding of block codes obtained via convolutional codes," *IEEE Trans. Inf. Theory* 51(5):1880–1891, 2005 [A]. Opened: https://lup.lub.lu.se/record/244441
- List and soft-output decoding:
  - Lončar, Johannesson, Bocharova, Kudryashov, "Soft-output BEAST decoding with application to product codes," *IEEE Trans. Inf. Theory* 54(3):1036–1049, 2008 [A]. Opened: https://www.lunduniversity.lu.se/lup/publication/3cfe5457-1446-4b25-82a0-27e4fe8636df
  - M. Lončar, *Taming of the BEAST*, PhD thesis, Lund University, 2007 [A]. Opened: https://lup.lub.lu.se/record/598933

**Most detailed accessible description:** F. Hug, *Codes on Graphs and More*, PhD thesis, Lund University, 2012, Sec. 2.2 and 2.4 [F]. Opened: https://lup.lub.lu.se/search/files/5325251/2439722.pdf (record https://lup.lub.lu.se/search/publication/285413fb-05d9-431f-9907-534d636738e3). The original IEEE papers are paywalled, so the mechanics below come from Hug's thesis. Hug is a co-author from the same group.

**What it does:**

- **Trellis and states.** The block-code trellis is the BCJR/Wolf trellis. A state at depth t is the partial syndrome of the first t symbols, built from the columns of H (Hug, Sec. 2.2).
- **Spectral component A_w.** BEAST grows a forward code tree from the root and a backward tree from the "toor" (end node), with w = w_F + w_B chosen freely; balanced is best.
  - The forward set is the nodes whose weight equals w_F while their parent's weight is below w_F.
  - The backward set is the nodes whose weight equals w_B while their children's weights exceed w_B.
  - Pairs are matched when they have equal state and ℓ_F + ℓ_B = N, and each match is one codeword.
  - The motivating claim (Hug, eq. 2.42) is that every weight-w codeword passes through some intermediate node splitting its weight about evenly.
- **ML decoding (Algorithm BML).** BEAST uses a threshold T = T_F + T_B.
  - Forward nodes are expanded while their metric is below T_F. A child whose metric reaches T_F is stored in F.
  - B holds all backward nodes with metric ≤ T_B.
  - Pairs are matched by state and complementary depth. If no match has a sum ≤ T, T is raised.
  - The thesis notes that BEAST, unlike Viterbi, needs a metric that is nondecreasing along the path.
  - It suggests raising only T_F or only T_B, so that one tree can be reused.
- **Results reported.** BEAST found new convolutional and tailbiting codes with record free distance, and decoded with much less work than Viterbi on the minimal trellis (2004 and 2005 abstracts).

**How close it is to (A):** almost identical in structure.

- **Same as (A):**
  - **States:** the partial syndrome, which equals the active-row syndrome on valid paths.
  - **Weight split:** with T_F = a and T_B = K−a, forward nodes are expanded at weight ≤ a−1, the new frontier states have weight a, the backward table has weight ≤ K−a, and the total is ≤ K.
  - **Join:** equal state and complementary depth, at every depth.
  - **Iterative thresholds,** and exactness from monotone metrics.
- **Different from (A):**
  - BEAST uses **trees**: each node has a unique parent, and equal states at the same depth are not merged. (A) keeps the least weight per (cut, state), Viterbi-style.
  - BEAST prunes only by length or depth, while (A) uses a covering lookahead.
  - BEAST's split is fixed within an iteration, while (A) lets it decrease along the sweep.

**Novelty risk: very high.** The bidirectional, weight-split, state-matched trellis search is BEAST, so (A) must cite it as the base algorithm.

### 1.2 Larsen's bidirectional free-distance algorithm, and its parent BCFJ

- K. J. Larsen, "Comments on 'An efficient algorithm for computing free distance'," *IEEE Trans. Inf. Theory* 19(4):577–579, 1973.
- L. Bahl, C. Cullum, W. Frazer, F. Jelinek, "An efficient algorithm for computing free distance," *IEEE Trans. Inf. Theory* 18(3):437–439, 1972.

Both are [S] via Z. Abreu, J. Rosenthal, M. Schaller, "Algorithms for computing the free distance of convolutional codes," arXiv:2402.02982, 2024 [F]. Opened: https://arxiv.org/pdf/2402.02982

**What it does.** Larsen's algorithm grows forward and backward paths on the convolutional state diagram and stores each reached state with its type (forward or backward). When several paths reach a state, it keeps the lowest weight. A forward state meeting a backward state gives a codeword. Extensions heavier than about half the current upper bound, (W*+n−1)/2, are pruned. Abreu et al. show that Larsen's correctness proof is incomplete, but the algorithm works. They also give a new generalized bidirectional algorithm that keeps the lowest weight per state.

**How close it is to (A).** This is a 1973 bidirectional min-weight search that merges states, with a meeting threshold near half the bound. It runs on a time-invariant state diagram rather than a finite, time-varying block-code trellis.

**Novelty risk: high** for any claim that state-merging bidirectional min-weight search is new.

### 1.3 FAST (Cedervall–Johannesson)

- M. Cedervall, R. Johannesson, "A fast algorithm for computing distance spectrum of convolutional codes," *IEEE Trans. Inf. Theory* 35(6):1146–1159, 1989. Known through arXiv:2402.02982 [S] and a Lund record (search only).

**What it does.** FAST is a depth-first or stack search of the code tree. It prunes a state when its weight is below the column distance needed to return to zero, which it reads from the position of the last nonzero entry of the state. This is an admissible lookahead for distance search, and the 1989 abstract says it is faster than bidirectional search.

**How close it is to (A).** It is precedent for **admissible lookahead pruning** in exact trellis distance search. Its bound comes from code structure; (A)'s covering bound is a different bound with the same role.

**Novelty risk: medium** for the lookahead idea itself.

### 1.4 Bidirectional sequential decoding

- S. Kallel, K. Li, "Bidirectional sequential decoding," *IEEE Trans. Inf. Theory* 43(4):1319–1326, 1997.
- V. Šenk, P. Radivojac, "The bidirectional stack algorithm," ISIT 1997, p. 500.

Both are [S] from the references of arXiv:2210.15787 (opened).

These are bidirectional tree searches for decoding that meet in the middle. They are context only, since they decode rather than compute distance. **Novelty risk: low.**

### Table 1. (A) compared with BEAST and Larsen

| Feature | (A) | BEAST (2004/05, per Hug 2012) | Larsen 1973 |
|---|---|---|---|
| State | partial syndrome on active rows | partial syndrome (BCJR/Wolf trellis) | encoder state (convolutional code) |
| Equal states merged at a cut | yes (least weight kept) | no (code trees) | yes (lowest weight per state) |
| Weight split | forward ≤ a−1 (new states ≤ a), backward ≤ K−a | T_F + T_B = T; frontier at T_F, backward ≤ T_B | about half of the upper bound |
| Join | at every cut, by state | equal state and ℓ_F + ℓ_B = N (all depths) | forward meets backward at the same state |
| Threshold loop | iterative deepening over K | thresholds raised; option to raise one side only | upper bound tightened |
| Split varies along the sweep | yes (may decrease) | not described | no |
| Admissible lookahead | covering (LP-dual) bound | depth or length constraints only | no |
| Target | min weight with He = 0, Le ≠ 0 (code or detector error model) | A_w, d_min, ML decoding (classical codes) | free distance |

---

## 2. Dumer's split-syndrome decoding, Stern, and meet-in-the-middle for minimum-weight words

### 2.1 Dumer's split-syndrome (sort-and-match) decoding, as restated by Dumer–Kovalev–Pryadko

**Citations:**

- I. I. Dumer, "On syndrome decoding of linear codes," Proc. 9th All-Union Symp. Redundancy in Information Systems, 1986, vol. 2, pp. 157–159 (in Russian).
- I. I. Dumer, "Two decoding algorithms for linear codes," *Probl. Peredachi Inf.* 25(1):24–32, 1989 (in Russian).

These are [S]: the citations as given in DKP 2017, and the 1989 abstract seen in a search snippet. The abstract describes nearest-codeword decoding with time about 2^{n(1−R)/2}.

**Restatement read:** I. Dumer, A. A. Kovalev, L. P. Pryadko, "Distance verification for classical and quantum LDPC codes," *IEEE Trans. Inf. Theory* 63(7):4675ff, 2017; arXiv:1611.07164, Sec. III-B "matching bipartition" [F]. Opened: https://arxiv.org/pdf/1611.07164. The end page is 4686 per dblp and 4690 per the dist-m4ri README.

**What it does.** The coordinates are split into a cyclic "left" window of length ⌊n/2⌋ and its complementary "right" window. For a weight-d vector, some window position i gives weights ⌊d/2⌋ on the left and ⌈d/2⌉ on the right; DKP's wording is "At least one choice of position i". The method enumerates all such half-weight vectors in both windows, computes their syndromes, and sorts them to find equal pairs. The exponent is h_q(δ)/2. It is deterministic and works for any linear code, and DKP apply it to the stabilizer setting through C⊥.

**How close it is:**

- **To (A).** Dumer's argument that a balanced split position exists is exactly what makes joining at every cut complete. It is also BEAST's argument. (A) replaces the explicit enumeration of fixed-weight halves with DP tables on the trellis. Those tables merge equal syndromes and keep only the active rows, so they are smaller.
- **To (B).** It is the archetype of a syndrome-keyed table matched against a second enumeration.

**Novelty risk: high** for any claim that splitting the weight and matching on syndromes is new.

### 2.2 Information-set decoding with collisions: Stern, Dumer, and successors

- J. Stern, "A method for finding codewords of small weight," *Coding Theory and Applications*, LNCS 388, pp. 106–113, 1989 (conference 1988) [A, bibliographic]. Probabilistic search for low-weight words.
- J. S. Leon, "A probabilistic algorithm for computing minimum weights of large error-correcting codes," *IEEE Trans. Inf. Theory* 34(5):1354–1359, 1988 [A, dblp via search].
- I. Dumer, "On minimum distance decoding of linear codes," Proc. 5th Joint Soviet-Swedish Int. Workshop Inf. Theory, 1991, pp. 50–52 [S].
- M. Finiasz, N. Sendrier, "Security bounds for the design of code-based cryptosystems," ASIACRYPT 2009, pp. 88–105 [S].
- A. May, A. Meurer, E. Thomae, "Decoding random linear codes in Õ(2^{0.054n})," ASIACRYPT 2011, pp. 107–124 [S].
- A. Becker, A. Joux, A. May, A. Meurer, "Decoding random binary linear codes in 2^{n/20}: how 1+1=0 improves information set decoding," EUROCRYPT 2012, pp. 520–536 [S].

All [S] items above are via H. Wu, J. Zhuang, "Syndrome decoding meets multiple instances," arXiv:2209.06656 [F]. Opened: https://arxiv.org/pdf/2209.06656

Not opened: A. Canteaut, F. Chabaud, *IEEE Trans. Inf. Theory* 44(1):367–378, 1998 [U]; ball-collision decoding by Bernstein–Lange–Peters, CRYPTO 2011 [U].

**What they do.** After Gaussian elimination on a random information set, the matrix splits into an exact part (H̃₁e′ = s₁ on l rows) and an approximate part. Dumer and Stern solve the exact part by meet-in-the-middle: weight-p/2 halves are matched on the syndrome window. MMT and BJMM add representations and multi-level trees.

**How close it is.** It shares the syndrome-keyed collision with (B)'s final lookup. But these methods are probabilistic or average-case and built on information sets. (B) is deterministic, works on the full syndrome, and has no information set.

**Novelty risk: low** for the exactness of (B). Cite these as the origin of syndrome-collision meet-in-the-middle.

### 2.3 Supercode decoding

- A. Barg, E. Krouk, H. C. A. van Tilborg, "On the complexity of minimum distance decoding of long linear codes," *IEEE Trans. Inf. Theory*, 1999 [A]. Volume and pages not verified. Opened: https://www.nokia.com/bell-labs/publications-and-media/publications/on-the-complexity-of-minimum-distance-decoding-of-long-linear-codes

**What it does.** It combines covering-set and split-syndrome ideas with decoding of supercodes, and gets the lowest asymptotic exponents of its time. **Novelty risk: low.** Background only.

### 2.4 Generic meet-in-the-middle

- E. Horowitz, S. Sahni, "Computing partitions with applications to the knapsack problem," *JACM*, 1974 [U, search].
- R. Schroeppel, A. Shamir, "A T = O(2^{n/2}), S = O(2^{n/4}) algorithm for certain NP-complete problems," MIT LCS TM-147 (1980) and SIAM J. Comput. (1981) [U]. Seen only in search results, not opened (DSpace record https://dspace.mit.edu/handle/1721.1/148974); the SIAM details are not verified.

These are generic meet-in-the-middle by splitting and matching on sums. **Novelty risk: none** for the paper, but it is the right generic citation.

---

## 3. Trellis-based distance and spectrum computation with pruning, A* searches, and bidirectional search in general

### 3.1 The syndrome trellis and its minimality

- L. R. Bahl, J. Cocke, F. Jelinek, J. Raviv, *IEEE Trans. Inf. Theory* 20(2):284–287, 1974 [U; cited in Hug 2012].
- J. K. Wolf, "Efficient maximum likelihood decoding of linear block codes using a trellis," *IEEE Trans. Inf. Theory* 24(1), 1978 [A via secondary sources].
- R. J. McEliece, "On the BCJR trellis for linear block codes," *IEEE Trans. Inf. Theory*, July 1996 [A, Caltech record via search].

**What they do.** The states are partial syndromes. The BCJR trellis has the fewest edges, states and other complexity measures in a given coordinate order, so (A)'s active-row states are the standard minimal-trellis states.

**Column order** has its own literature:

- T. Kasami et al., *IEEE Trans. Inf. Theory* 39(1):242–245, 1993 [A], on optimal bit orders.
- G. B. Horn, F. R. Kschischang, *IEEE Trans. Inf. Theory* 42(6):2042–2048, 1996 [A], showing that choosing the permutation that minimizes trellis complexity is NP-hard.

**Novelty risk: high** for the state definition and the column-order idea. Cite them.

### 3.2 Weight distribution of a block code from its trellis

- Y. Desaki, T. Fujiwara, T. Kasami, "A method for computing the weight distribution of a block code by using its trellis diagram," *IEICE Trans. Fundamentals* E77-A(8):1230–1237, 1994 [U].

I saw only the bibliographic snippet, which describes counting codewords up to a given weight on the trellis. The IEICE page is behind a CAPTCHA, which I did not attempt.

**How close it is.** It is likely a sum-product (counting) DP on the trellis with per-state partial weight distributions truncated at a weight, which is the counting analog of (A) without meet-in-the-middle. This needs checking. **Novelty risk: medium (unverified).**

### 3.3 Branch-and-bound with trellis lower bounds (turbo codes)

- R. Garello, P. Pierleoni, S. Benedetto, "Computing the free distance of turbo codes and serially concatenated codes with interleavers: algorithms and applications," *IEEE JSAC* 19(5):800–812, 2001.
- E. Rosnes, Ø. Ytrehus, "Improved algorithms for the determination of turbo-code weight distributions," *IEEE Trans. Commun.* 53(1):20–26, 2005.

Both are [S] via Rosnes–Ytrehus, arXiv:cs/0602072, Sec. V-C [F]. Opened: https://arxiv.org/pdf/cs/0602072

**What it does.** It is a branch-and-bound over constraint sets that fix input bits one by one. The lower bound w′(F) is the minimum, over the trellis vertices reachable under the constraints, of (forward weight to the vertex) plus (exact minimum weight from the vertex to the end). The second term is precomputed by a backward Viterbi pass. A constrained Viterbi pass is used when several vertices are reachable.

**How close it is.**

- **To (A).** It combines a forward partial weight with a backward table of exact remaining minimum weights, which is the classical form of a backward table used for pruning.
- **To (B).** It is precedent for pruning with a relaxed problem's exact table: each constituent trellis, taken separately, is a relaxation.

**Novelty risk: medium–high** for "backward table plus forward sweep" used as a bound.

### 3.4 A* or priority-first ML decoding of block codes

- Y. S. Han, C. R. P. Hartmann, C.-C. Chen, "Efficient priority-first search maximum-likelihood soft-decision decoding of linear block codes," *IEEE Trans. Inf. Theory* 39(5):1514–1523, 1993 [A via dblp and secondary sources].
- L. Ekroot, S. Dolinar, "A* decoding of block codes," *IEEE Trans. Commun.* 44:1052–1056, 1996 [U]. The volume and pages come from a patent citation; JPL TDA Progress Report 42-117 (1994) is the precursor.

**What they do.** A* search with admissible heuristics on a code trellis or tree. **How close:** precedent for admissible lookahead in exact searches over code trellises. **Novelty risk: medium.**

### 3.5 Low-weight subtrellises

- H. T. Moorthy, S. Lin, T. Kasami, "Soft-decision decoding of binary linear block codes based on an iterative search algorithm," *IEEE Trans. Inf. Theory*, May 1997 [A via secondary records].
- Follow-ups by Koumoto, Takata, Kasami and Lin [U].

**What they do.** They build a "minimum-weight subtrellis" containing only codewords at minimum distance from a candidate, then search it. The construction details were not verified because the NASA and IEICE pages were blocked. **How close:** an explicit weight-restricted trellis. **Novelty risk: medium (unverified).**

### 3.6 DP on tree decompositions for distance

- Q. Peng, K. Liu, G. Yan, G. Wang, "Linear complexity computation of code distance and minimum size of trapping sets for LDPC codes with bounded treewidth," arXiv:2509.13040, 2025 [A]. Opened: https://arxiv.org/abs/2509.13040

**What it does.** An exact algorithm, linear in n, for bounded-treewidth Tanner graphs given a tree decomposition. **How close:** it generalizes path (trellis) DP; the abstract mentions no weight truncation or meet-in-the-middle. **Novelty risk: medium** for "exact DP for code distance" as a class. (A)'s path-order truncated version is a special and different case.

### 3.7 Bidirectional heuristic search in AI

**Earlier work:**

- I. Pohl, "Bi-directional search," *Machine Intelligence* 6:127–140, 1971 [A].
- H. Kaindl, G. Kainz, "Bidirectional heuristic search reconsidered," *JAIR* 7:283–317, 1997 [A]. Opened: https://arxiv.org/abs/cs/9712102
- R. C. Holte, A. Felner, G. Sharon, N. R. Sturtevant, "Bidirectional search that is guaranteed to meet in the middle," AAAI 2016, pp. 3411–3417; journal version *AIJ* 252, 2017 [A].
- **Fractional MM, fMM(p):** E. Shaham, A. Felner, J. Chen, N. R. Sturtevant, SoCS 2017, pp. 82–90 [S]. In fMM, forward g-values are limited to a fraction p of C* and backward g-values to 1−p. It was described in S. Shperberg et al., SoCS 2019 [F]. Opened: https://ojs.aaai.org/index.php/SOCS/article/download/18508/18299

**GBFHS:** M. Barley, P. Riddle, C. Linares López, S. Dobson, I. Pohl, "GBFHS: a generalized breadth-first heuristic search algorithm," SoCS 2018 [F]. Opened: https://ojs.aaai.org/index.php/SOCS/article/download/18452/18243

- **How it works.** Iterative deepening runs over an f-limit, fLim. A user-chosen **split function** divides gLSum = fLim − ε + 1 between g-limits for the forward and backward directions. A node is expanded only if f ≤ fLim and g < gLim. The split must never lower a g-limit, and searches stop at the first collision.
- **Arithmetic match with (A).** Take unit costs (ε = 1) and fLim = K, so gLSum = K. A split gLim_F = a, gLim_B = K−a then expands forward nodes at g ≤ a−1, whose generated children have g ≤ a. Backward generated nodes have g ≤ K−a, and collisions are checked on generated nodes. That is exactly (A)'s a−1 / a / K−a arithmetic, with admissible heuristics as the lookahead.
- **How close it is to (A):** the same threshold/split/meet logic, on general graphs. **Novelty risk: medium–high** for the "split of the threshold between directions" and for iterative deepening over K.

### 3.8 Perimeter search, the meet-in-the-middle table in AI

- J. F. Dillenburg, P. C. Nelson, "Perimeter search," *Artificial Intelligence* 65(1):165–178, 1994 [A, bibliographic].
- G. Manzini, "BIDA*: an improved perimeter search algorithm," *Artificial Intelligence* 75(2):347–360, 1995 [A].

**What they do.** A breadth-first search from the goal stores every state within depth d (the "perimeter") in a table. Then IDA* runs from the start and stops when it generates a perimeter state.

**How close it is to (B).** It is essentially (B)'s final step: a DFS with iterative deepening that ends with one lookup in a table of all states within k steps of the goal. Here the goal is a zero syndrome with a nonzero logical, and "within k steps" means all column subsets of size ≤ k, keyed by syndrome.

**Novelty risk: high** for the idea behind the lookup. Cite these together with Dumer.

### 3.9 Bounded bidirectional DP in operations research

- G. Righini, M. Salani, "Symmetry helps: bounded bi-directional dynamic programming for the elementary shortest path problem with resource constraints," *Discrete Optimization* 3(3):255–273, 2006 [A].
- C. Tilk, A.-K. Rothenbächer, T. Gschwind, S. Irnich, "Asymmetry matters: dynamic half-way points in bidirectional labeling for solving shortest path problems with resource constraints faster," *EJOR* 261(2):530–539, 2017 [A].

**What they do.** Forward and backward labels are extended only up to a "half-way point" of a resource, and then joined. Tilk et al. move the half-way point dynamically, according to the current state of both searches.

**How close it is to (A).** It is a direct analog of (A)'s weight split and of a split that changes during the search, in a different field.

**Novelty risk: medium** for "variable split" as a concept.

---

## 4. Branch-and-bound and LP bounds, canonical enumeration, and automorphisms

### 4.1 Dumer–Kovalev–Pryadko: irreducible and linked clusters (the closest prior art for (B))

**Citations:**

- DKP 2017 (citation in §2.1), Sec. V, "Irreducible-cluster (IC) technique" [F].
- A. A. Kovalev, I. Dumer, L. P. Pryadko, "Linked-cluster technique for finding the distance of a quantum LDPC code," arXiv:1302.1845, 2013 [F]. Opened: https://arxiv.org/pdf/1302.1845; the venue is not verified.
- I. Dumer, A. A. Kovalev, L. P. Pryadko, *Phys. Rev. Lett.* 115, 050502, 2015 [S], cited by DKP 2017 as the binary version.

**What they do:**

- **IC.** A minimum-weight codeword is irreducible (DKP Lemma 3), so its support is connected. Each run starts from a position j₀. At each step it takes **the first parity check in the ordered list of unsatisfied checks** and adds new symbols that satisfy it. For binary codes, exactly one new bit is added per step. The run succeeds when no check is left unsatisfied.
  - The complexity is 2^{F n} with F = δ·log₂(γ_m(m−1)) (Proposition 8). Table II gives γ_m = 1 for q = 2, so the cost is about (m−1)^d.
  - The same exponent holds for CSS codes. General qubit stabilizer codes have γ = 2.
- **Linked cluster, 2013.** It enumerates all connected clusters of size w on the bit-adjacency graph. Starting from position i, it uses only neighbors "to the right" of i, and at each level only positions after the one added last. The authors state that no cluster is produced twice; this is a canonical, Redelmeier-style enumeration.

**How close it is to (B).**

- **Same:** branching on an unsatisfied check, a weight-bounded DFS, the canonical start column, and the (m−1)^d complexity bound.
- **Not present:** the "earlier siblings forbidden" rule inside the unsatisfied-check branching (IC has no explicit rule against duplicates), any covering or LP bound, any meet-in-the-middle finish, and any relaxed-problem table.

**Novelty risk: very high** for the DFS skeleton of (B) and for any (r−1)^d-type complexity statement.

### 4.2 dist-m4ri CC mode (software, the paper's baseline)

- Repository: https://github.com/QEC-pages/dist-m4ri. I opened the README at master (v0.14.7, fetched 2026-10-25), the README at commit `1f46277` (2026-09-18), the source `src/dist_m4ri.c` at `1f46277` and at `caef294` (2024-07-31), and the commit list through the GitHub API [F].

**What it does now:**

- Clusters grow from each start column i using only columns j > i.
- A cluster is extended only by the columns of the **first row of its syndrome**. In the 2026-09-18 source this is `row = syn[w]->vec[0]`, with `col > col_min`; the 2024 code looped over all nonzero syndrome rows.
- Weights are scanned w = 1, 2, ….
- The **last column is found by a hash lookup** of the remaining syndrome: commit `3e03f1e`, "CC mode (method=2) speedup – last bit hash lookup", 2026-10-11.
- Rows are sorted by weight: commit of 2026-10-14.
- It runs in parallel with a random-window information-set search (the "RW" mode) to bracket the distance.
- **No sibling exclusion:** branches only require col > start and a column not already in the cluster, so a set can be reached through different orders. I saw no covering bound.

**How close it is to (B).** It is (B) with k = 1, without canonical sibling exclusion, without the covering bound and without the relaxed table.

**Novelty risk: very high**, and it is time-sensitive. These features are only weeks old. The paper should cite the dist-m4ri version or commit it was benchmarked against, and acknowledge that the hash lookup and first-row rule are independent and concurrent.

### 4.3 Stim's search for undetectable logical errors

- Docs: https://raw.githubusercontent.com/quantumlib/Stim/main/doc/python_api_reference_vDev.md. Code: https://raw.githubusercontent.com/quantumlib/Stim/main/src/stim/search/hyper/algo.cc [F].

**What it does.** It is a breadth-first search over states (sorted detector set, observable mask), starting from every error that crosses an observable.

- From the current state it only adds errors touching **the lowest-index active detector**.
- Visited states are deduplicated in a map, so equal states are merged.
- It succeeds when the detector set is empty and the observable mask is nonzero.
- Truncations on the size of the detector set and on edge degree make it officially a heuristic method.

**How close it is.**

- **To (A).** Its state is (syndrome, logical) with merging, as in (A), but there is no layer or cut order, the state is the full syndrome rather than active rows, and it is unidirectional with no meet-in-the-middle.
- **To (B).** It uses the same branching rule (lowest unsatisfied detector).

**Novelty risk: medium.** It is a quantum-specific precedent for both the state definition and the branching rule.

### 4.4 Bocharova–Hug–Johannesson–Kudryashov–Satyukov, Algorithm MD

- I. E. Bocharova, F. Hug, R. Johannesson, B. D. Kudryashov, R. V. Satyukov, "Searching for voltage graph-based LDPC tailbiting codes with large girth," arXiv:1108.0840 (2011); *IEEE Trans. Inf. Theory* (2012), DOI 10.1109/TIT.2011.2176717 (volume and pages not verified) [F]. Opened: https://arxiv.org/pdf/1108.0840. The same algorithm is in Hug's thesis, Sec. 3.5 [F].

**What it does:**

- Trees of columns, where each node carries (depth, partial syndrome).
- It branches on a nonzero position of the partial syndrome, giving at most K−1 children per nonzero position.
- A label (column) may appear only once on a path.
- **Pruning:** a node is not extended if its syndrome weight exceeds J·(t − ℓ − 1), since each column cancels at most J ones. A block-wise version gives a stronger bound for circulant structure.
- It uses quasi-cyclic **symmetry to fix the root** to one of the first c columns.
- d_min is the smallest depth at which the syndrome reaches zero; otherwise it certifies d_min ≥ t.

**How close it is to (B).**

- **Same:** unsatisfied-check branching on a partial-syndrome state, the **same covering bound** as (B) and (A) (unsatisfied rows divided by the maximum rows per column), and an automorphism-reduced root.
- **Not present:** meet-in-the-middle, sibling exclusion and a relaxed table.

**Novelty risk: very high** for the covering bound and for symmetry reduction of the first column.

### 4.5 Rosnes–Ytrehus and Wang–Kulkarni–Poor: exhaustive stopping-set and codeword search

- E. Rosnes, Ø. Ytrehus, "An efficient algorithm to find all small-size stopping sets of low-density parity-check matrices," *IEEE Trans. Inf. Theory* 55(9):4167–4178, 2009; ISIT 2007 version pp. 2936–2940. Bibliographic details opened at https://sites.google.com/a/simula.no/eirik-rosnes/publications and in the references of https://ar5iv.arxiv.org/html/1205.2590.
- E. Rosnes, Ø. Ytrehus, M. A. Ambroze, M. Tomlinson, "Addendum to 'An efficient algorithm to find all small-size stopping sets of low-density parity-check matrices'," *IEEE Trans. Inf. Theory* 58(1):164–171, 2012. Keywords include branch-and-bound, tree search, minimum distance and weight spectrum [A]. Opened: https://researchportal.plymouth.ac.uk/en/publications/addendum-to-an-efficient-algorithm-to-find-all-small-size-stoppin/

**Mechanism [S].** A secondary summary says the following. It is in a 2022 *Theoretical Computer Science* article, "On the complexity of and solutions to the minimum stopping and trapping set problems"; the page was blocked, and I saw only a search snippet.

- each variable is constrained in or out, or left free;
- lower bounds come from LP relaxations;
- the algorithm branches on the free variable whose neighboring checks have the most free nodes;
- it reached stopping sets of size 26 in codes with thousands of bits.

Rosnes–Ambroze–Tomlinson (2014, arXiv:1205.2590) [F] use it for exact lower bounds on minimum and stopping distance. They also use a doubly transitive automorphism group to fix columns in support matrices.

**Wang–Kulkarni–Poor:** C.-C. Wang, S. R. Kulkarni, H. V. Poor, "Finding all small error-prone substructures in LDPC codes," *IEEE Trans. Inf. Theory* 55(5):1976–1999, 2009 [A]. Opened: https://collaborate.princeton.edu/en/publications/finding-all-small-error-prone-substructures-in-ldpc-codes/. It is an exhaustive tree-pruning search exploiting sparsity. It finds all stopping sets of size ≤ 13 and trapping sets of size ≤ 11 for n ≈ 500, and shows that the exhaustive enumeration is NP-complete.

**How close it is to (B).** It is exact branch-and-bound over sparse parity checks with LP-based bounds, and include/exclude branching avoids duplicates.

**Novelty risk: high** for "LP-dual bound in an exact search for low-weight structures."

### 4.6 Integer programming bounds for minimum distance

- A. B. Keha, T. M. Duman, "Minimum distance computation of LDPC codes using a branch and cut algorithm," *IEEE Trans. Commun.* 58:1072–1079, 2010 [S, from a reference list]; ISIT 2008 version [A]. Opened: https://asu.elsevierpure.com/en/publications/a-branch-and-cut-algorithm-for-finding-the-minimum-distance-of-a-/
- J. Feldman, M. J. Wainwright, D. R. Karger, "Using linear programming to decode binary linear codes," *IEEE Trans. Inf. Theory* 51(3), 2005, DOI 10.1109/TIT.2004.842696 [A].
  - They define the **fractional distance**, the minimum weight over nonzero vertices of the fundamental polytope, which can be computed by LP.
  - Since codewords are vertices of that polytope, it is at most d_min. This lower-bound reading is mine; I did not check it in their text.

**Novelty risk: medium–high** for LP-type bounds on minimum distance in general. (A) and (B)'s cheap dual-feasible covering bound is a weak special case.

### 4.7 Brouwer–Zimmermann and automorphisms

- M. Grassl, "Computing extensions of linear codes," arXiv:0704.2596, 2007, Sec. II [F]. Opened: https://arxiv.org/pdf/0704.2596
  - It describes the Brouwer–Zimmermann algorithm (Zimmermann TR 3-96, 1996): several systematic generator matrices whose information sets are as disjoint as possible, and a lower bound Σ_j max(0, (w+1) − (k − r_j)) after enumerating information vectors of weight ≤ w.
  - It states that partial knowledge of the automorphism group (cyclic or quasi-cyclic codes) improves the bound, citing C.-L. Chen 1970, Grassl 2006 and G. White 2005.
- Related: M. Grassl, "Searching for linear codes with large minimum distance," in *Discovering Mathematics with Magma*, Springer 2006, pp. 287–313 [S].
- P. Lisoněk, L. Trummer, "Algorithms for the minimum weight of linear codes," *Adv. Math. Commun.* 10:195–207, 2016 [A, author page via search]. It chooses information sets by matroid partitioning.
- F. Hernando, F. D. Igual, G. Quintana-Ortí, arXiv:1603.06757 [F, header only]. Fast implementations of Brouwer–Zimmermann.

**How close it is.** These are the standard exact distance algorithm and its symmetry reductions. Using code automorphisms to restrict the first column of a support to orbit representatives is standard: White's quasi-cyclic version of Brouwer–Zimmermann, Bocharova 2012, Rosnes et al. 2014, and dist-m4ri's `start=` option.

**Novelty risk: high** for symmetry reduction.

### 4.8 Canonical enumeration

- B. D. McKay, "Isomorph-free exhaustive generation," *J. Algorithms* 26(2):306–324, 1998 [A].
- D. H. Redelmeier, "Counting polyominoes: yet another attack," *Discrete Math.* 36:191–203, 1981 [A].
- Orderly generation (Read; Faradžev, 1978) [U].

**How close it is.** (B)'s "earlier siblings forbidden" on an unsatisfied check is ordinary include/exclude disjoint branching. With a fixed rule for choosing the check, each set is generated at most once. This is the same device as Redelmeier's untried set and as KDP's "positions to the right". It is not full canonical augmentation up to isomorphism.

**Novelty risk: high** for the device. It is standard and should be presented as such.

### 4.9 Relaxed-problem tables and iterative deepening

- J. C. Culberson, J. Schaeffer, "Pattern databases," *Computational Intelligence* 14(3):318–334, 1998 [A]. Exact costs of an abstracted (relaxed) problem are stored and used as an admissible heuristic.
- G. Verfaillie, M. Lemaître, T. Schiex, "Russian doll search for solving constraint optimization problems," AAAI-96, pp. 181–187 [A]. The optimal costs of nested subproblems are used as bounds.
- R. E. Korf, "Depth-first iterative-deepening: an optimal admissible tree search," *Artificial Intelligence* 27(1):97–109, 1985 [A].

**How close it is to (B).** (B)'s relaxed-problem pruning is a pattern database, and its threshold loop is IDA*. Within coding theory, the Garello–Pierleoni–Benedetto bound of §3.3 is a relaxed-table bound.

**Novelty risk: high** for the concepts.

---

## 5. Truncated or bounded min-plus DP and tensor networks

### 5.1 Branch-and-bound strategies for DP

- T. L. Morin, R. E. Marsten, "Branch-and-bound strategies for dynamic programming," *Operations Research* 24(4):611–627, 1976 [A]. Seen via search; https://pubsonline.informs.org/doi/10.1287/opre.24.4.611

**What it does.** It fathoms DP states using relaxations and bounds, removing states whose subpolicies cannot be optimal.

**How close it is to (A).** Dropping DP states above an upper bound K, and pruning them with an admissible lower bound, is exactly this general scheme.

**Novelty risk: high** for "truncated DP" as a concept.

### 5.2 Generic tensor networks: truncated polynomials and top-K tropical numbers

- J.-G. Liu, X. Gao, M. Cain, M. D. Lukin, S.-T. Wang, "Computing solution space properties of combinatorial optimization problems via generic tensor networks," arXiv:2205.03718, 2022 [F]. Journal version: SIAM J. Sci. Comput., 2023 (details not verified). Opened: https://arxiv.org/pdf/2205.03718

**What it does.** Tensor elements are taken in semirings:

- **Truncated polynomial algebra:** keep only the largest (or smallest) few orders of each element's polynomial (Sec. 6.3).
- **"Extended tropical" numbers:** keep the K largest values (Sec. 8). Section 6.3 also mentions keeping only the smallest orders.

The tensors themselves stay dense.

**How close it is to (A).** The truncation is in the **value domain**, applied to each element relative to its own extreme. (A) truncates the **state space** sparsely, dropping entries above a global weight K. That uses a different monotonicity argument and gives a different cost model.

**Novelty risk: low–medium.** Cite it to separate the two notions.

### 5.3 Tropical tensor networks

- J.-G. Liu, L. Wang, P. Zhang, "Tropical tensor network for ground states of spin glasses," *Phys. Rev. Lett.* 126, 090506, 2021 [A]. Opened: https://arxiv.org/abs/2008.06888

**What it does.** Exact contraction of dense min-plus or max-plus tensor networks, with no truncation. **Novelty risk: low** (background for the min-plus view).

### 5.4 Quantum weight enumerators from tensor networks

- C. Cao, B. Lackey, "Quantum weight enumerators and tensor networks," arXiv:2211.02756 [F, keyword search].
- C. Cao, M. J. Gullans, B. Lackey, Z. Wang, "Quantum Lego expansion pack: enumerators from tensor networks," arXiv:2308.05152 [F, keyword search].
- B. Pato, J. Vanlerberghe, K. R. Brown, "Hyper-optimized Quantum Lego contraction schedules," arXiv:2510.08210, 2025 [F, keyword search]. Opened: https://arxiv.org/pdf/2510.08210

**What they do.** Full enumerator polynomials are computed by contraction, and the distance is read off. Pato et al. show that stabilizer-code tensors are highly sparse and add a sparse cost function.

I found **no weight truncation** in any of the three: searching for "truncat" found only a figure caption in Cao et al.

**How close it is.** Sparse, but not truncated. **Novelty risk: low–medium.** Sparse plus weight-threshold contraction for distance appears unclaimed in these works.

### 5.5 Summary for item 5

I did not find a min-plus tensor-network contraction or DP that keeps **only entries with weight ≤ K** as a sparse table, used as an exact distance method. The closest analogs:

- BEAST's weight-limited trees (§1.1);
- low-weight subtrellises (§3.5) and truncated trellis weight distributions (§3.2), neither verified;
- the fathoming of Morin–Marsten (§5.1);
- Stim's truncated breadth-first search (§4.3), which is heuristic.

---

## 6. (B) compared with the closest prior art

| Feature | (B) | DKP IC (2017) / KDP linked cluster (2013) | dist-m4ri CC (Oct 2026) | Bocharova et al. 2012, Algorithm MD | Perimeter search (1994/95) |
|---|---|---|---|---|---|
| Search | DFS, weight-bounded | runs over steps with backtracking; clusters "to the right" | DFS, weight scan | tree up to depth t | IDA* |
| Branching | on an unsatisfied check | first unsatisfied check (IC) | first row of the syndrome | any nonzero syndrome position (≤ K−1 children) | domain moves |
| Duplicate control | earlier siblings forbidden | canonical "positions to the right" (2013); none stated (IC) | start = smallest column only | label used once per path | — |
| Finish | lookup in a table of all ≤ k subsets keyed by syndrome | none | hash lookup of the last column (k = 1) | — | lookup in the perimeter table (depth d) |
| Bound | covering (LP dual) plus relaxed table | weight only | weight only | syndrome weight > J(t−ℓ−1) | admissible heuristic (front to perimeter) |
| Symmetry | (if used) orbit representatives | none | `start=` for quasi-cyclic codes | quasi-cyclic root fixing | — |

---

## 7. Implications for our novelty claims

### (A): is it essentially BEAST or Dumer applied to quantum codes and circuits?

**Largely yes.**

- The **algorithmic core** is BEAST (§1.1) on the syndrome trellis:
  - the threshold split T_F + T_B;
  - forward frontier against backward table, matched by equal state and complementary depth;
  - nondecreasing metric as the exactness condition;
  - iterative thresholds and adaptive raising of one side.
- Its **completeness argument** is Dumer's: a balanced split position always exists (Dumer 1986/1989; also BEAST's eq. 2.42).
- Its **meeting threshold near half the bound, with merged states**, appears in Larsen (1973).
- The **truncation** is branch-and-bound DP fathoming (Morin–Marsten 1976), and the **lookahead** has precedents in FAST, GPB, A* decoding and Bocharova's J(t−ℓ−1) bound.

**What is plausibly different and defensible, stated modestly:**

1. **State merging, so the method is a min-plus DP rather than a tree search.** Keeping the least weight per (cut, active-row syndrome) is exact for minimum weight and can be far smaller than BEAST's trees, which BEAST needs for counting and backtracking. The step is simple, but BEAST does not have it.
2. **A split that depends on position (non-increasing along the sweep), with joins at every cut.** BEAST fixes the split per threshold. Analogs exist outside coding theory: dynamic half-way points (Tilk et al. 2017), the GBFHS split function (2018) and fMM (2017). If the paper proves correctness for a non-increasing split sequence, that small lemma is citable as new for this setting.
3. **The covering lookahead inside a bidirectional trellis DP,** with c_max taken over the remaining columns. This refines Bocharova et al.'s J(t−ℓ−1) and should be credited to them.
4. **The problem and the application:** minimum weight with He = 0 and Le ≠ 0, where the terminal set is a zero syndrome with nonzero logical parity, on quantum CSS codes and **circuit-level detector error models**. Columns are ordered in time and states are kept on active detectors. I found no prior BEAST or trellis method for circuit distance. The WJH 2026 benchmark names none, and Stim's search is unordered and heuristic. The quantum front should check Sabo (2022) before any "first trellis method for stabilizer distance" claim.

**Wording I would recommend:**

> "a min-plus, weight-truncated variant of the BEAST bidirectional trellis search [Bocharova et al. 2004, 2005], using Dumer's split argument [1986, 1989], adapted to detector error models"

**Do not claim novelty for:** meet-in-the-middle at a cut, splitting the weight between directions, threshold truncation, partial-syndrome trellis states, or iterative deepening.

### (B): how it relates to meet-in-the-middle, information-set decoding and branch-and-bound

(B) is an exact branch-and-bound that assembles known components:

- **Skeleton:** the DKP irreducible/connected-cluster search (2013/2015/2017), with the same first-unsatisfied-check branching and the (m−1)^d bound.
- **Covering bound:** Bocharova et al. 2012, with LP relaxations in Rosnes–Ytrehus 2009/2012 and Keha–Duman 2010.
- **Canonical branching:** include/exclude, as in KDP 2013 and Redelmeier.
- **Final lookup:** perimeter search / BIDA*, or syndrome collision as in Dumer and Stern.
- **Relaxed table:** pattern databases, the Garello–Pierleoni–Benedetto bound, Russian doll search.
- **Threshold loop:** IDA*.

It is **not** information-set decoding: it uses no information sets, it is deterministic and exact, and it matches on the full syndrome. Credible novelty is:

- the **specific combination** for exact code or circuit distance, especially a table of all subsets of size ≤ k with **k ≥ 2**, keyed by the full (detector, observable) syndrome, combined with a duplicate-free unsatisfied-check DFS and a cheap dual covering bound;
- the **empirical reach**.

**Must-dos:**

1. Cite dist-m4ri's October 2026 CC changes (first-row extension, last-column hash lookup = k = 1, row sorting), and state the dist-m4ri version or commit used in comparisons. Independent concurrent convergence should be acknowledged.
2. Present any complexity statement, for example ≈ (r−1)^{d−k} DFS leaves times one lookup, with C(n, ≤ k) memory, as the perimeter-search tradeoff applied to DKP's bound, not as a new kind of bound.
3. For hardness context, cite C. Jia, Q. Peng, K. Liu, G. Wang, G. Yan, "On the intractability of the minimum distance problem for regular LDPC codes," arXiv:2606.23161, 2026 [A]. Opened: https://arxiv.org/abs/2606.23161. They show:
   - NP-completeness of the "weight ≤ w" version for fixed (J, K)-regular graphs;
   - W[1]-completeness of the **exact-weight** version, parameterized by w.

   Claims of fixed-parameter-tractable behaviour should therefore be stated for "weight ≤ d with bounded row weight", which is DKP's bound, and not for exact weight.

**Positioning note:** M. Webster, A. Jacob, O. Higgott, "Distance-finding algorithms for quantum codes and circuits," arXiv:2603.22532, 2026 [A]. Opened: https://arxiv.org/abs/2603.22532. It benchmarks Brouwer–Zimmermann, connected cluster, SAT and MIP as exact methods. A fair claim is that (A) and (B) bring classical BEAST-type trellis meet-in-the-middle and perimeter-type meet-in-the-middle into quantum and circuit distance computation. A claim that these search ideas are new is not fair.

---

## 8. What I could and could not verify

- **Read in full:**
  - Hug's 2012 thesis (BEAST and Algorithm MD);
  - Bocharova et al., arXiv:1108.0840;
  - DKP 2017, Sections III-B and V;
  - KDP 2013;
  - Rosnes–Ytrehus, arXiv:cs/0602072 (the GPB description);
  - Abreu–Rosenthal–Schaller 2024 (Larsen and FAST);
  - Grassl 2007 (Brouwer–Zimmermann and automorphisms);
  - GBFHS 2018;
  - Shperberg et al. 2019 (fMM);
  - the Liu et al. generic tensor network paper;
  - the dist-m4ri README, commits and source;
  - Stim's docs and code;
  - Wu–Zhuang 2022 (the Dumer information-set-decoding description).
- **Abstract or bibliographic only:**
  - the original BEAST IEEE papers, which are paywalled;
  - Lončar 2008 and the Lončar thesis;
  - WKP 2009;
  - the Rosnes–Ytrehus addendum;
  - McKay; Pohl; Kaindl–Kainz; MM;
  - perimeter search and BIDA*;
  - pattern databases;
  - Righini–Salani; Tilk et al.; Morin–Marsten;
  - Russian doll search; IDA*;
  - Keha–Duman (ISIT); FWK; Lisoněk–Trummer; Barg et al.;
  - Han–Hartmann–Chen; Moorthy–Lin–Kasami;
  - Kasami et al.; Horn–Kschischang; McEliece; Wolf;
  - WJH 2026; Jia et al. 2026; Peng et al. 2025;
  - Sabo's 2022 talk abstract.
- **Secondary or unverified:**
  - the Dumer 1986/1989 originals (via DKP; mathnet.ru was unreachable);
  - the internals of Rosnes–Ytrehus 2009, where the LP-relaxation bound comes from a secondary snippet;
  - Desaki–Fujiwara–Kasami 1994 (IEICE CAPTCHA, not attempted);
  - the low-weight subtrellis constructions (NASA and IEICE pages blocked);
  - Ekroot–Dolinar volume and pages (from a patent citation);
  - Canteaut–Chabaud and ball-collision (from memory);
  - Bocharova et al. 2012 journal volume and pages;
  - the venues of KDP 2013 and of the generic tensor network journal version.
- **Not attempted:** the IEICE and Anubis-protected OAPEN pages (bot checks were not bypassed), and the Springer chapter "An exhaustive tree search for stopping sets of LDPC codes" (Tomlinson et al., 2017).
