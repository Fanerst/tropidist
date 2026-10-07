# estdist: paper definitions and exact code-distance checks

Network sources are the five named arXiv papers. Definitions are embedded in
`papers/estimated_codes.py`; no external dataset or downloaded executable code
is required. `n,k` in the registry are the actual rebuilt dimensions; `paper_n,
paper_k` preserve a differing published claim. `open` records retain their paper
classification after an exact local search succeeds.

Sources: [MM v2](https://arxiv.org/html/2601.18879v2),
[weight-eight BB](https://arxiv.org/html/2609.06572),
[QGPU](https://arxiv.org/pdf/2603.05398),
[balanced products](https://arxiv.org/html/2607.27644), and
[LLM search](https://arxiv.org/html/2606.02418).

## Construction conventions

- **BB, 2609.06572 and 2606.02418:** on Z_l x Z_m, row index i*m+j;
  H_X=[A|B], H_Z=[B^T|A^T]. A monomial x^a y^b in a non-transposed
  block gives column ((i+a) mod l)*m+(j+b) mod m. Two unit-axis translations
  generate the full translation group; the kernel independently validates them.
  Locators: weight-eight paper Sec2.2 Eq4, Tables1/2; LLM SecIII.1 Eq1 and
  Supplemental Material I Table3.
- **MM, 2601.18879v2:** use R=F2[variables]/(v_i^ell_i-1), and the Koszul
  boundary on increasing subsets. Physical qubits are (q-subset, ring point),
  q=floor(t/2), with lexicographic points and subset order. Boundary sends
  (S,p) to (S\{i},p+e) for each monomial e of f_i, with GF(2) cancellation.
  H_X=boundary_q, H_Z=boundary_(q+1)^T. Locators: Eq67, AppendixE
  Eqs99/100 and AppendixF Tables2–11. For even t all nonidentity ring
  translations act identically in both check-block orders. Odd t has different
  numbers of X/Z rows, so the shared-permutation interface returns no candidates.
- **Clustered lifted products, 2603.05398:** a seed entry [a,b] denotes x^a+x^b,
  [] denotes zero. Use H_X=[H_a tensor I | I tensor H_b] and
  H_Z=[I tensor H_b* | H_a* tensor I], where star transposes the seed and
  negates cyclic exponents. Binary block row t has column t+e mod p;
  check/qubit cluster order is (i,j,t). Locators: Eq5; AppendixH TablesVI/VII
  (PDF p25); distances TableI and AppendixF TableIV. Cyclic shifts of t act in
  every cluster; identity is filtered out by the existing symmetry helper.
- **Balanced products, 2607.27644:** group elements x^i y^j are indexed
  i*ell2+j; multiplication is (i,j)(a,b)=(i+q^j a mod ell1,j+b mod ell2).
  Eq49 defines L[g]|h>=|gh> and R[g]|h>=|hg>, with no inverse in R.
  Let A=L[a], B=L[b], C=R[c], D=R[d]. In five data blocks, Eq1 gives
  H_X=[[A,0,B,0,C^T],[0,A,0,B,D^T]] and
  H_Z=[[C,D,0,0,A^T],[0,0,C,D,B^T]]. Locators: Eq13,
  Table3, AppendixA Table8, AppendixC.4 before Eq83. Center elements supply
  shared permutations of both check blocks (AppendixD.3 Eqs133/134, Table13).
  Table10 and Eq21 supply verified target witnesses on blocks(1,3) for
  physical Z, blocks(1,2) for physical X, by the identity-index row of the
  left/right regular representations.

Driver basis follows `stabcode`: basis Z searches physical X logical operators
against H_Z; basis X searches physical Z against H_X. Saved witness lists are
physical data-qubit indices, including when the problem deduplicates columns.
A found witness is certified exact only after all smaller thresholds were
exhausted. Published claims never seed the lower bound. Timeouts retain only the
last independently exhausted bound. JSON preserves every threshold's node
counts and seconds and resumes only if the rebuilt matrix SHA256 agrees.
A verified witness meeting the minimum of both certified sector lower bounds
closes the overall code distance; later invocations retain a larger sector
lower bound without searching that sector again.
When a verified witness is already available, the driver searches only through
one less than its weight: exhausting those thresholds closes the certificate.

## Version differences, interpretations, and excluded constructions

- The MM task locators correspond to an earlier layout. v2 has Julia examples
  in AppendixE and code tables in AppendixF. v1 does not contain the requested
  288/324/630 definitions, so all MM table rows here consistently use v2.
- MM Eqs94/95 place transposes inconsistently with their displayed map arrows.
  The implementation uses the boundary shapes in Eqs99/100: rows on degree
  q-1 for H_X and degree q+1 for H_Z, columns on degree q for both. These
  shapes also reproduce Table7's X/Z row weights8/6.
- The weight-eight BB paper Lemma3.11 states column weight8. Eq4 gives
  column weight4 in each individual H_X/H_Z and total X+Z degree8; the
  explicit matrix definition is used.
- MM Table3 row5 prints periods(4,2,2,3) with polynomials containing y^3.
  Their literal quotient-ring expansion gives [[288,0]], not [[288,12]].
  No period or polynomial was altered. The registry records k=0 and paper_k=12;
  the driver reports that a logical code distance is undefined for this entry.
- MM Table2 row33, labeled [[624,12,14]], prints xz^{1}1. The literal term
  is x*z^1*1, and it rebuilds k12. A possible intended xz^11 is not substituted.
- MM Table6 row25 prints `1+w48` among terms `1+w^a`. This is interpreted as
  `1+w^48`, with the literal text retained in the registry. It rebuilds [[294,6]].
- The task labels QGPU [[24,8,3]] as a control; the paper's AppendixF TableIV
  treats all CC distances as estimates. Its task-designated control label is
  retained and its distance independently certified locally.
- The LLM [[360,12,d]] target is ambiguous. SupplementalI Table3 classV† is a
  completely defined CSS BB [[360,12,d<=24]], included as the named BB target
  even though the extra-instance cap is20. The main Table2's new PBB
  [[360,12,d<=24]] and [[360,12,d<=20]] use mixed stabilizers and cannot satisfy
  the required CSS `(hx,hz,n)` interface. Both rebuild n360,k12 as general
  stabilizer codes; X-support rank174 plus Z-support rank322 differs from
  stabilizer rank348. They cannot become CSS by row operations. AppendixF's
  tested Clifford reductions do not include these two entries. Their complete
  four-polynomial definitions are recorded below; they are excluded from CODES.
  The CSS classV text supplies no explicit weight24 support. The deterministic
  logical span supplied independently verified weight30 supports in both bases,
  so local upper bounds30 are separately certified rather than inferred from
  the paper's24 claim.
- LLM SupplementalI Table3 does not give an individual optimality flag for ten
  additional n360 CSS classes. They are conservatively marked open. Tables1/2
  explicitly certify the n144/n288 additional codes, so those are not expanded.
  ClassA uses the first supplemental representative B=y^6+x^7+x^14, rather
  than the alternative main-table representative. ClassZprime has check weight6
  and classeprime check weight10; no check-weight assumption modifies them.
- Additional instances include all completely specified open MM rows with
  n<=700,d_claimed<=20 (Table7 is exact only at n<=290), all ten QGPU CC rows,
  the second defined BB lower-bound row, two additional balanced products,
  and all qualifying uncertified CSS LLM rows. Unspecified members of a census
  are not registry entries. Extra exact controls not requested are omitted.

## Per-code data

In the following table, exponent lists are monomial supports, not executable
expressions. BB tuples give `(l,m),A,B`; MM tuples give `periods,polynomial
supports`; CC tuples give `p,H_a,H_b`; balanced tuples give
`n,k,d,status,(ell1,ell2,q),a,b,c,d`. Metadata includes the original polynomial
text for MM. Locators are unique within the cited paper.

| name | arXiv | rebuilt (n,k) | claimed d | status | locator | definition |
|---|---|---|---|---|---|---|
| `qgpu_24_8_3` | 2603.05398 | (24,8) | 3 | control | Table I; Appendix H, Table VI; Eq. (5); Appendix F Table IV | `(3, [[[0, 2], [1, 2]], [[0, 1], [1, 2]]], [[[0, 2], [1, 2]], [[0, 1], [0, 1]]])` |
| `w8bb_72_14_8` | 2609.06572 | (72,14) | 8 | control | Table 2, row 1 | `((6, 6), [(0, 0), (4, 4), (0, 5), (1, 5)], [(0, 0), (4, 1), (1, 2), (3, 2)])` |
| `mm_t5_r2_96_12_8` | 2601.18879 | (96,12) | 8 | control | v2 Appendix F Table 5, data row 2; Eqs.67,99,100 | `([2, 2, 2, 2], ['wy+wz+w+1', 'wxz+wy+wz+w', 'wxyz+w+xyz+y', 'wxyz+w+yz+1'])` |
| `w8bb_144_16_10` | 2609.06572 | (144,16) | 10 | control | Table 1, row 1 | `((12, 6), [(0, 0), (11, 0), (0, 5), (9, 5)], [(3, 2), (8, 2), (4, 3), (9, 3)])` |
| `w8bb_144_10_12` | 2609.06572 | (144,10) | 12 | control | Table 1, row 2 | `((8, 9), [(4, 2), (1, 3), (0, 5), (5, 8)], [(0, 0), (4, 2), (2, 3), (6, 5)])` |
| `balanced_160_32_10` | 2607.27644 | (160,32) | 10 | control | Table 3 | `(160, 32, 10, 'control', (16, 2, 9), [(0, 0), (13, 0), (14, 1)], [(0, 0), (3, 1), (13, 1)], [(0, 0), (14, 0), (12, 1)], [(0, 0), (7, 0), (11, 0)])` |
| `balanced_240_48_12` | 2607.27644 | (240,48) | 12 | control | Table 3 | `(240, 48, 12, 'control', (12, 4, 7), [(0, 0), (8, 1), (7, 2)], [(0, 0), (2, 0), (5, 1)], [(0, 0), (4, 1), (2, 3)], [(0, 0), (4, 0), (9, 0)])` |
| `mm_t4_r17_486_24_12` | 2601.18879 | (486,24) | 12 | control | v2 Appendix F Table 4, data row 17; Eqs.67,99,100 | `([3, 3, 3, 3], ['1+wx+x^{2}y', '1+xy+y^{2}z', '1+yz+wz^{2}', '1+wz+w^{2}x'])` |
| `qgpu_40_8_5` | 2603.05398 | (40,8) | 5 | open | Table I; Appendix H, Table VI; Eq. (5); Appendix F Table IV | `(5, [[[1, 3], [1, 4]], [[1, 4], [1, 4]]], [[[0, 1], [3, 4]], [[0, 4], [0, 4]]])` |
| `qgpu_54_18_3` | 2603.05398 | (54,18) | 3 | open | Table I; Appendix H, Table VII; Eq. (5); Appendix F Table IV | `(3, [[[1, 2], [], [0, 1]], [[1, 2], [0, 1], []], [[], [0, 2], [0, 2]]], [[[0, 1], [0, 2], []], [[], [1, 2], [0, 2]], [[0, 2], [], [1, 2]]])` |
| `qgpu_56_8_7` | 2603.05398 | (56,8) | 7 | open | Table I; Appendix H, Table VI; Eq. (5); Appendix F Table IV | `(7, [[[1, 5], [1, 3]], [[0, 2], [0, 3]]], [[[2, 5], [0, 1]], [[5, 6], [4, 6]]])` |
| `qgpu_88_8_10` | 2603.05398 | (88,8) | 10 | open | Table I; Appendix H, Table VI; Eq. (5); Appendix F Table IV | `(11, [[[1, 5], [5, 6]], [[2, 3], [5, 9]]], [[[0, 3], [8, 10]], [[5, 7], [3, 7]]])` |
| `qgpu_90_18_5` | 2603.05398 | (90,18) | 5 | open | Table I; Appendix H, Table VII; Eq. (5); Appendix F Table IV | `(5, [[[0, 1], [], [0, 4]], [[0, 3], [0, 2], []], [[], [0, 4], [0, 2]]], [[[0, 4], [0, 2], []], [[], [0, 3], [0, 1]], [[0, 1], [], [0, 3]]])` |
| `mm_t2_r1_96_12_4` | 2601.18879 | (96,12) | 4 | open | v2 Appendix F Table 2, data row 1; Eqs.67,99,100 | `([2, 2, 2, 2], ['wz+xyz', 'w+xyz', 'wyz+xy', 'xyz+xz'])` |
| `mm_t4_r1_96_44_4` | 2601.18879 | (96,44) | 4 | open | v2 Appendix F Table 4, data row 1; Eqs.67,99,100 | `([2, 2, 2, 2], ['(1+x)(1+yz)', '(1+y)(1+zw)', '(1+z)(1+wx)', '(1+w)(1+xy)'])` |
| `qgpu_104_8_11` | 2603.05398 | (104,8) | 11 | open | Table I; Appendix H, Table VI; Eq. (5); Appendix F Table IV | `(13, [[[1, 5], [2, 5]], [[1, 4], [9, 10]]], [[[2, 8], [0, 8]], [[1, 9], [1, 3]]])` |
| `qgpu_126_18_7` | 2603.05398 | (126,18) | 7 | open | Table I; Appendix H, Table VII; Eq. (5); Appendix F Table IV | `(7, [[[1, 4], [], [2, 4]], [[1, 3], [2, 5], []], [[], [0, 5], [0, 3]]], [[[5, 6], [5, 6], []], [[], [1, 3], [0, 1]], [[1, 2], [], [4, 6]]])` |
| `qgpu_136_8_14` | 2603.05398 | (136,8) | 14 | open | Table I; Appendix H, Table VI; Eq. (5); Appendix F Table IV | `(17, [[[13, 16], [5, 15]], [[6, 16], [0, 3]]], [[[1, 7], [8, 10]], [[8, 10], [5, 16]]])` |
| `mm_t8_r1_140_20_6` | 2601.18879 | (140,20) | 6 | open | v2 Appendix F Table 8, data row 1; Eqs.67,99,100 | `([7], ['1+u', '1+u^{2}', '1+u^{3}', '1+u^{4}', '1+u^{5}', '1+u^{6}'])` |
| `mm_t2_r2_144_6_8` | 2601.18879 | (144,6) | 8 | open | v2 Appendix F Table 2, data row 2; Eqs.67,99,100 | `([2, 2, 3, 2], ['wxy+z', 'wx+wyz', 'wx+xy^{2}', 'xyz+y^{2}z'])` |
| `mm_t3_r1_144_12_8` | 2601.18879 | (144,12) | 8 | open | v2 Appendix F Table 3, data row 1; Eqs.67,99,100 | `([3, 2, 2, 2], ['w^{2}xyz+wy+yz', 'w^{2}y+wxz+x', 'w^{2}x+wz+xy', 'w^{2}yz+w+1'])` |
| `mm_t4_r2_144_12_8` | 2601.18879 | (144,12) | 8 | open | v2 Appendix F Table 4, data row 2; Eqs.67,99,100 | `([2, 2, 2, 3], ['wxy+xyz', 'y+zx+yx+zw', 'x+zyxw', 'z+y+x+zyx'])` |
| `w8bb_144_10_ge11` | 2609.06572 | (144,10) | 11 | open | Table 1, row 6 | `((12, 6), [(0, 0), (8, 1), (1, 3), (2, 5)], [(0, 0), (11, 0), (1, 1), (0, 4)])` |
| `mm_t3_r2_144_12_12` | 2601.18879 | (144,12) | 12 | open | v2 Appendix F Table 3, data row 2; Eqs.67,99,100 | `([3, 2, 2, 2], ['w^{2}xy+w+xyz', 'w^{2}x+wxy+z', 'w^{2}xz+wx+xyz', 'w^{2}yz+wxy+xyz'])` |
| `w8bb_144_6_ge15` | 2609.06572 | (144,6) | 15 | open | Table 1, row 9 | `((8, 9), [(0, 0), (4, 2), (0, 4), (0, 7)], [(0, 0), (2, 6), (5, 7), (7, 8)])` |
| `mm_t6_r1_156_6_10` | 2601.18879 | (156,6) | 10 | open | v2 Appendix F Table 6, data row 1; Eqs.67,99,100 | `([26], ['1+w^{16}', '1+w^{19}', '1+w^{22}', '1+w^{22}'])` |
| `mm_t8_r2_160_20_6` | 2601.18879 | (160,20) | 6 | open | v2 Appendix F Table 8, data row 2; Eqs.67,99,100 | `([8], ['1+u', '1+u^{3}', '1+u^{4}', '1+u^{5}', '1+u^{6}', '1+u^{7}'])` |
| `mm_t6_r2_162_6_9` | 2601.18879 | (162,6) | 9 | open | v2 Appendix F Table 6, data row 2; Eqs.67,99,100 | `([27], ['1+w^{7}', '1+w^{13}', '1+w^{15}', '1+w^{24}'])` |
| `mm_t6_r4_168_12_7` | 2601.18879 | (168,12) | 7 | open | v2 Appendix F Table 6, data row 4; Eqs.67,99,100 | `([28], ['1+w^{4}', '1+w^{6}', '1+w^{8}', '1+w^{18}'])` |
| `mm_t6_r3_168_6_9` | 2601.18879 | (168,6) | 9 | open | v2 Appendix F Table 6, data row 3; Eqs.67,99,100 | `([28], ['1+w^{4}', '1+w^{7}', '1+w^{13}', '1+w^{19}'])` |
| `mm_t6_r5_174_6_11` | 2601.18879 | (174,6) | 11 | open | v2 Appendix F Table 6, data row 5; Eqs.67,99,100 | `([29], ['1+w^{2}', '1+w^{8}', '1+w^{20}', '1+w^{24}'])` |
| `mm_t8_r3_180_20_6` | 2601.18879 | (180,20) | 6 | open | v2 Appendix F Table 8, data row 3; Eqs.67,99,100 | `([9], ['1+u', '1+u^{3}', '1+u^{4}', '1+u^{6}', '1+u^{7}', '1+u^{8}'])` |
| `mm_t6_r6_180_6_10` | 2601.18879 | (180,6) | 10 | open | v2 Appendix F Table 6, data row 6; Eqs.67,99,100 | `([30], ['1+w^{3}', '1+w^{13}', '1+w^{21}', '1+w^{28}'])` |
| `mm_t6_r7_186_6_11` | 2601.18879 | (186,6) | 11 | open | v2 Appendix F Table 6, data row 7; Eqs.67,99,100 | `([31], ['1+w', '1+w^{14}', '1+w^{19}', '1+w^{23}'])` |
| `mm_t2_r3_192_6_8` | 2601.18879 | (192,6) | 8 | open | v2 Appendix F Table 2, data row 3; Eqs.67,99,100 | `([4, 2, 2, 2], ['w^{2}xz+z', 'w^{2}yz+wyz', 'w^{3}x+xyz', 'w^{3}xyz+w^{2}z'])` |
| `mm_t6_r8_192_6_11` | 2601.18879 | (192,6) | 11 | open | v2 Appendix F Table 6, data row 8; Eqs.67,99,100 | `([32], ['1+w^{8}', '1+w^{25}', '1+w^{26}', '1+w^{29}'])` |
| `mm_t4_r3_192_12_12` | 2601.18879 | (192,12) | 12 | open | v2 Appendix F Table 4, data row 3; Eqs.67,99,100 | `([2, 2, 2, 4], ['wxyz^{3}+xyz  +xz^{3}+xz^{2}', 'wxz^{2}+wyz^{3}  +w+1', 'wy+wz^{2}  +xyz^{2}+xz', 'wxyz+wy  +xz^{3}+z^{3}'])` |
| `mm_t6_r9_198_6_10` | 2601.18879 | (198,6) | 10 | open | v2 Appendix F Table 6, data row 9; Eqs.67,99,100 | `([33], ['1+w^{3}', '1+w^{7}', '1+w^{16}', '1+w^{21}'])` |
| `qgpu_198_18_10` | 2603.05398 | (198,18) | 10 | open | Table I; Appendix H, Table VII; Eq. (5); Appendix F Table IV | `(11, [[[4, 9], [], [5, 7]], [[4, 6], [2, 8], []], [[], [7, 10], [3, 8]]], [[[3, 4], [6, 10], []], [[], [2, 3], [8, 10]], [[0, 7], [], [9, 10]]])` |
| `mm_t8_r4_200_20_7` | 2601.18879 | (200,20) | 7 | open | v2 Appendix F Table 8, data row 4; Eqs.67,99,100 | `([10], ['1+u', '1+u^{3}', '1+u^{6}', '1+u^{7}', '1+u^{8}', '1+u^{9}'])` |
| `mm_t6_r10_204_6_12` | 2601.18879 | (204,6) | 12 | open | v2 Appendix F Table 6, data row 10; Eqs.67,99,100 | `([34], ['1+w^{5}', '1+w^{8}', '1+w^{9}', '1+w^{23}'])` |
| `mm_t6_r11_210_6_11` | 2601.18879 | (210,6) | 11 | open | v2 Appendix F Table 6, data row 11; Eqs.67,99,100 | `([35], ['1+w^{13}', '1+w^{25}', '1+w^{29}', '1+w^{34}'])` |
| `mm_t3_r4_216_24_9` | 2601.18879 | (216,24) | 9 | open | v2 Appendix F Table 3, data row 4; Eqs.67,99,100 | `([2, 2, 3, 3], ['wy^{2}z^{2}+x+yz^{2}', 'wxz^{2}+xy^{2}z+y', 'wxy^{2}z+wxyz^{2}+wxz^{2}', 'wyz+xy^{2}+z'])` |
| `mm_t2_r4_216_6_12` | 2601.18879 | (216,6) | 12 | open | v2 Appendix F Table 2, data row 4; Eqs.67,99,100 | `([2, 2, 3, 3], ['wxy+xy^{2}', 'wy+xyz^{2}', 'xy^{2}+y^{2}z', 'wxyz^{2}+xz'])` |
| `mm_t3_r3_216_12_12` | 2601.18879 | (216,12) | 12 | open | v2 Appendix F Table 3, data row 3; Eqs.67,99,100 | `([2, 2, 3, 3], ['wxy^{2}+wz^{2}+x', 'wxyz^{2}+wy^{2}z+x', 'wxy^{2}z^{2}+xyz^{2}+xz^{2}', 'wz+w+xy^{2}z'])` |
| `mm_t4_r4_216_12_12` | 2601.18879 | (216,12) | 12 | open | v2 Appendix F Table 4, data row 4; Eqs.67,99,100 | `([2, 2, 3, 3], ['wxy+xyz', 'y+zx+yx+zw', 'x+zyxw', 'z+y+x+zyx'])` |
| `mm_t6_r12_216_6_12` | 2601.18879 | (216,6) | 12 | open | v2 Appendix F Table 6, data row 12; Eqs.67,99,100 | `([36], ['1+w^{3}', '1+w^{21}', '1+w^{26}', '1+w^{35}'])` |
| `mm_t4_r5_216_12_14` | 2601.18879 | (216,12) | 14 | open | v2 Appendix F Table 4, data row 5; Eqs.67,99,100 | `([2, 2, 3, 3], ['wz^{2}+xy^{2}z  +xy^{2}+y', 'wxy^{2}z^{2}+wxz^{2}  +wy^{2}z+y^{2}z^{2}', 'wxy^{2}z^{2}+wxyz  +xy^{2}z+x', 'wxz^{2}+wyz  +wz^{2}+xz'])` |
| `mm_t8_r5_220_20_8` | 2601.18879 | (220,20) | 8 | open | v2 Appendix F Table 8, data row 5; Eqs.67,99,100 | `([11], ['1+u', '1+u^{3}', '1+u^{5}', '1+u^{7}', '1+u^{8}', '1+u^{10}'])` |
| `mm_t6_r13_222_6_11` | 2601.18879 | (222,6) | 11 | open | v2 Appendix F Table 6, data row 13; Eqs.67,99,100 | `([37], ['1+w^{4}', '1+w^{17}', '1+w^{22}', '1+w^{34}'])` |
| `mm_t6_r14_228_6_12` | 2601.18879 | (228,6) | 12 | open | v2 Appendix F Table 6, data row 14; Eqs.67,99,100 | `([38], ['1+w^{3}', '1+w^{24}', '1+w^{30}', '1+w^{37}'])` |
| `mm_t6_r15_234_6_13` | 2601.18879 | (234,6) | 13 | open | v2 Appendix F Table 6, data row 15; Eqs.67,99,100 | `([39], ['1+w', '1+w^{14}', '1+w^{30}', '1+w^{36}'])` |
| `mm_t2_r5_240_12_7` | 2601.18879 | (240,12) | 7 | open | v2 Appendix F Table 2, data row 5; Eqs.67,99,100 | `([5, 2, 2, 2], ['w^{4}y+w^{3}x', 'w^{4}x+w^{3}', 'w^{4}y+wx', 'w^{4}z+w^{2}yz'])` |
| `mm_t8_r6_240_20_8` | 2601.18879 | (240,20) | 8 | open | v2 Appendix F Table 8, data row 6; Eqs.67,99,100 | `([12], ['1+u', '1+u^{2}', '1+u^{3}', '1+u^{5}', '1+u^{9}', '1+u^{10}'])` |
| `mm_t4_r8_240_18_10` | 2601.18879 | (240,18) | 10 | open | v2 Appendix F Table 4, data row 8; Eqs.67,99,100 | `([2, 2, 2, 5], ['wxyz^{3}+wxz^{2}  +wz^{3}+z', 'wxyz^{4}+wxy  +wx+xy', 'wyz^{4}+wyz^{3}  +wz^{2}+yz^{3}', 'wxyz+wx  +wyz^{4}+wz'])` |
| `mm_t2_r6_240_6_12` | 2601.18879 | (240,6) | 12 | open | v2 Appendix F Table 2, data row 6; Eqs.67,99,100 | `([5, 2, 2, 2], ['w^{4}xy+xz', 'w^{3}+w^{2}z', 'w^{3}xyz+wy', 'w^{2}y+w'])` |
| `mm_t6_r16_240_6_12` | 2601.18879 | (240,6) | 12 | open | v2 Appendix F Table 6, data row 16; Eqs.67,99,100 | `([40], ['1+w^{2}', '1+w^{5}', '1+w^{11}', '1+w^{26}'])` |
| `mm_t4_r7_240_12_16` | 2601.18879 | (240,12) | 16 | open | v2 Appendix F Table 4, data row 7; Eqs.67,99,100 | `([2, 2, 2, 5], ['wxz+wz^{4}  +xyz^{3}+yz', 'wz^{3}+xz^{4}  +yz^{2}+z', 'wz^{2}+xz  +yz^{4}+z', 'xz^{4}+yz^{3}  +z^{3}+z^{2}'])` |
| `mm_t6_r17_246_6_12` | 2601.18879 | (246,6) | 12 | open | v2 Appendix F Table 6, data row 17; Eqs.67,99,100 | `([41], ['1+w', '1+w^{12}', '1+w^{23}', '1+w^{37}'])` |
| `mm_t6_r18_252_6_12` | 2601.18879 | (252,6) | 12 | open | v2 Appendix F Table 6, data row 18; Eqs.67,99,100 | `([42], ['1+w^{9}', '1+w^{17}', '1+w^{19}', '1+w^{30}'])` |
| `mm_t6_r19_258_6_12` | 2601.18879 | (258,6) | 12 | open | v2 Appendix F Table 6, data row 19; Eqs.67,99,100 | `([43], ['1+w^{15}', '1+w^{16}', '1+w^{34}', '1+w^{39}'])` |
| `mm_t8_r7_260_20_10` | 2601.18879 | (260,20) | 10 | open | v2 Appendix F Table 8, data row 7; Eqs.67,99,100 | `([13], ['1+u^{5}', '1+u^{7}', '1+u^{9}', '1+u^{10}', '1+u^{11}', '1+u^{12}'])` |
| `mm_t6_r20_264_6_13` | 2601.18879 | (264,6) | 13 | open | v2 Appendix F Table 6, data row 20; Eqs.67,99,100 | `([44], ['1+w^{6}', '1+w^{7}', '1+w^{21}', '1+w^{26}'])` |
| `mm_t6_r21_270_6_14` | 2601.18879 | (270,6) | 14 | open | v2 Appendix F Table 6, data row 21; Eqs.67,99,100 | `([45], ['1+w^{9}', '1+w^{24}', '1+w^{32}', '1+w^{38}'])` |
| `mm_t6_r22_276_6_14` | 2601.18879 | (276,6) | 14 | open | v2 Appendix F Table 6, data row 22; Eqs.67,99,100 | `([46], ['1+w^{19}', '1+w^{32}', '1+w^{34}', '1+w^{43}'])` |
| `mm_t9_r1_280_35_4` | 2601.18879 | (280,35) | 4 | open | v2 Appendix F Table 9, data row 1; Eqs.67,99,100 | `([8], ['1+t', '1+t^{2}', '1+t^{3}', '1+t^{4}', '1+t^{5}', '1+t^{6}', '1+t^{7}'])` |
| `mm_t8_r8_280_20_9` | 2601.18879 | (280,20) | 9 | open | v2 Appendix F Table 8, data row 8; Eqs.67,99,100 | `([14], ['1+u', '1+u^{2}', '1+u^{3}', '1+u^{4}', '1+u^{5}', '1+u^{11}'])` |
| `mm_t6_r23_282_6_13` | 2601.18879 | (282,6) | 13 | open | v2 Appendix F Table 6, data row 23; Eqs.67,99,100 | `([47], ['1+w^{23}', '1+w^{25}', '1+w^{28}', '1+w^{39}'])` |
| `mm_t2_r8_288_12_8` | 2601.18879 | (288,12) | 8 | open | v2 Appendix F Table 2, data row 8; Eqs.67,99,100 | `([2, 2, 2, 6], ['wz^{3}+xyz^{2}', 'wxz^{2}+xyz', 'wxz^{2}+w', 'wyz^{5}+xyz^{3}'])` |
| `mm_t2_r7_288_6_12` | 2601.18879 | (288,6) | 12 | open | v2 Appendix F Table 2, data row 7; Eqs.67,99,100 | `([2, 2, 3, 4], ['wxy+xz^{2}', 'wxz^{2}+wy^{2}', 'xyz^{3}+z^{2}', 'wxy+w'])` |
| `mm_t4_r9_288_24_12` | 2601.18879 | (288,24) | 12 | open | v2 Appendix F Table 4, data row 9; Eqs.67,99,100 | `([2, 2, 2, 6], ['wxyz^{5}+wyz^{2}  +xyz^{4}+y', 'wxyz^{5}+wxy  +wz+xyz', 'wxyz^{4}+wyz^{5}  +wyz^{4}+z^{4}', 'wxz^{4}+wyz^{4}  +wz^{3}+z^{5}'])` |
| `mm_t6_r24_288_6_13` | 2601.18879 | (288,6) | 13 | open | v2 Appendix F Table 6, data row 24; Eqs.67,99,100 | `([48], ['1+w^{22}', '1+w^{23}', '1+w^{41}', '1+w^{43}'])` |
| `mm_t3_r5_288_12_16` | 2601.18879 | (288,0) | 16 | open | v2 Appendix F Table 3, data row 5; Eqs.67,99,100 | `([4, 2, 2, 3], ['w^{2}y^{3}z+wxyz+y^{2}', 'w^{2}yz+w+xy^{3}', 'w^{2}y^{3}z+wy^{3}+y^{3}z', 'w^{2}x+wy^{3}+yz'])` |
| `mm_t6_r25_294_6_14` | 2601.18879 | (294,6) | 14 | open | v2 Appendix F Table 6, data row 25; Eqs.67,99,100 | `([49], ['1+w^{9}', '1+w^{15}', '1+w^{22}', '1+w^{48}'])` |
| `mm_t7_r45_300_10_9` | 2601.18879 | (300,10) | 9 | open | v2 Appendix F Table 7, data row 45; Eqs.67,99,100 | `([30], ['1+v^{4}', '1+v^{5}', '1+v^{18}', '1+v^{19}', '1+v^{28}'])` |
| `mm_t8_r9_300_20_9` | 2601.18879 | (300,20) | 9 | open | v2 Appendix F Table 8, data row 9; Eqs.67,99,100 | `([15], ['1+u', '1+u^{3}', '1+u^{5}', '1+u^{6}', '1+u^{8}', '1+u^{11}'])` |
| `mm_t6_r26_300_6_13` | 2601.18879 | (300,6) | 13 | open | v2 Appendix F Table 6, data row 26; Eqs.67,99,100 | `([50], ['1+w^{12}', '1+w^{16}', '1+w^{21}', '1+w^{23}'])` |
| `mm_t6_r27_306_6_14` | 2601.18879 | (306,6) | 14 | open | v2 Appendix F Table 6, data row 27; Eqs.67,99,100 | `([51], ['1+w', '1+w^{36}', '1+w^{39}', '1+w^{46}'])` |
| `mm_t7_r46_310_10_8` | 2601.18879 | (310,10) | 8 | open | v2 Appendix F Table 7, data row 46; Eqs.67,99,100 | `([31], ['1+v^{3}', '1+v^{15}', '1+v^{18}', '1+v^{22}', '1+v^{23}'])` |
| `mm_t6_r28_312_6_13` | 2601.18879 | (312,6) | 13 | open | v2 Appendix F Table 6, data row 28; Eqs.67,99,100 | `([52], ['1+w^{8}', '1+w^{17}', '1+w^{41}', '1+w^{42}'])` |
| `mm_t9_r2_315_35_6` | 2601.18879 | (315,35) | 6 | open | v2 Appendix F Table 9, data row 2; Eqs.67,99,100 | `([9], ['1+t', '1+t^{2}', '1+t^{3}', '1+t^{4}', '1+t^{5}', '1+t^{7}', '1+t^{8}'])` |
| `mm_t6_r29_318_6_13` | 2601.18879 | (318,6) | 13 | open | v2 Appendix F Table 6, data row 29; Eqs.67,99,100 | `([53], ['1+w', '1+w^{19}', '1+w^{21}', '1+w^{29}'])` |
| `mm_t7_r47_320_10_9` | 2601.18879 | (320,10) | 9 | open | v2 Appendix F Table 7, data row 47; Eqs.67,99,100 | `([32], ['1+v', '1+v^{3}', '1+v^{9}', '1+v^{11}', '1+v^{17}'])` |
| `mm_t8_r10_320_20_9` | 2601.18879 | (320,20) | 9 | open | v2 Appendix F Table 8, data row 10; Eqs.67,99,100 | `([16], ['1+u', '1+u^{3}', '1+u^{5}', '1+u^{7}', '1+u^{10}', '1+u^{15}'])` |
| `balanced_320_64_14` | 2607.27644 | (320,64) | 14 | control | Table 3 | `(320, 64, 14, 'control', (16, 4, 3), [(0, 0), (1, 0), (0, 1)], [(0, 0), (2, 0), (13, 3)], [(0, 0), (12, 1), (2, 3)], [(0, 0), (12, 0), (11, 2)])` |
| `mm_t2_r9_324_6_12` | 2601.18879 | (324,6) | 12 | open | v2 Appendix F Table 2, data row 9; Eqs.67,99,100 | `([2, 3, 3, 3], ['wxz+yz^{2}', 'wxyz+xz', 'wx^{2}z+y^{2}z^{2}', 'wxy^{2}+wxz^{2}'])` |
| `mm_t6_r30_324_6_14` | 2601.18879 | (324,6) | 14 | open | v2 Appendix F Table 6, data row 30; Eqs.67,99,100 | `([54], ['1+w^{9}', '1+w^{11}', '1+w^{44}', '1+w^{48}'])` |
| `mm_t4_r11_324_18_18` | 2601.18879 | (324,18) | 18 | open | v2 Appendix F Table 4, data row 11; Eqs.67,99,100 | `([2, 3, 3, 3], ['wx^{2}z+wy^{2}z  +wz^{2}+x^{2}yz^{2}', 'wx^{2}y^{2}z+wx^{2}yz^{2}  +wxy^{2}z^{2}+x^{2}z', 'wxy+wxz  +wx+y^{2}z', 'wx^{2}y^{2}z+w*y^{2}  +wz+w'])` |
| `mm_t3_r6_324_12_20` | 2601.18879 | (324,12) | 20 | open | v2 Appendix F Table 3, data row 6; Eqs.67,99,100 | `([2, 3, 3, 3], ['wx^{2}y+x^{2}y^{2}+z', 'wy+xy+y^{2}z^{2}', 'wx^{2}z+wyz+yz^{2}', 'wx^{2}y^{2}+wxyz^{2}+xy^{2}z'])` |
| `mm_t7_r48_330_10_9` | 2601.18879 | (330,10) | 9 | open | v2 Appendix F Table 7, data row 48; Eqs.67,99,100 | `([33], ['1+v^{2}', '1+v^{7}', '1+v^{8}', '1+v^{11}', '1+v^{12}'])` |
| `mm_t6_r31_330_6_14` | 2601.18879 | (330,6) | 14 | open | v2 Appendix F Table 6, data row 31; Eqs.67,99,100 | `([55], ['1+w^{15}', '1+w^{39}', '1+w^{46}', '1+w^{51}'])` |
| `mm_t2_r10_336_6_12` | 2601.18879 | (336,6) | 12 | open | v2 Appendix F Table 2, data row 10; Eqs.67,99,100 | `([2, 2, 2, 7], ['wx+z^{2}', 'wxz^{2}+z^{6}', 'wx+wz^{2}', 'wxz^{4}+wyz^{6}'])` |
| `mm_t3_r7_336_18_12` | 2601.18879 | (336,18) | 12 | open | v2 Appendix F Table 3, data row 7; Eqs.67,99,100 | `([2, 2, 2, 7], ['wxyz^{6}+wx+z^{2}', 'wz^{3}+xyz^{6}+z^{4}', 'xy+xz^{5}+yz^{4}', 'wxyz^{3}+wyz+wy'])` |
| `mm_t6_r32_336_6_14` | 2601.18879 | (336,6) | 14 | open | v2 Appendix F Table 6, data row 32; Eqs.67,99,100 | `([56], ['1+w^{13}', '1+w^{41}', '1+w^{49}', '1+w^{43}'])` |
| `mm_t7_r49_340_10_9` | 2601.18879 | (340,10) | 9 | open | v2 Appendix F Table 7, data row 49; Eqs.67,99,100 | `([34], ['1+v^{3}', '1+v^{7}', '1+v^{18}', '1+v^{19}', '1+v^{29}'])` |
| `mm_t8_r11_340_20_10` | 2601.18879 | (340,20) | 10 | open | v2 Appendix F Table 8, data row 11; Eqs.67,99,100 | `([17], ['1+u^{5}', '1+u^{7}', '1+u^{9}', '1+u^{11}', '1+u^{14}', '1+u^{15}'])` |
| `mm_t6_r33_342_6_14` | 2601.18879 | (342,6) | 14 | open | v2 Appendix F Table 6, data row 33; Eqs.67,99,100 | `([57], ['1+w', '1+w^{15}', '1+w^{46}', '1+w^{49}'])` |
| `mm_t6_r34_348_6_15` | 2601.18879 | (348,6) | 15 | open | v2 Appendix F Table 6, data row 34; Eqs.67,99,100 | `([58], ['1+w^{22}', '1+w^{43}', '1+w^{55}', '1+w^{56}'])` |
| `mm_t9_r3_350_35_6` | 2601.18879 | (350,35) | 6 | open | v2 Appendix F Table 9, data row 3; Eqs.67,99,100 | `([10], ['1+t', '1+t^{2}', '1+t^{3}', '1+t^{4}', '1+t^{5}', '1+t^{7}', '1+t^{9}'])` |
| `mm_t7_r50_350_10_9` | 2601.18879 | (350,10) | 9 | open | v2 Appendix F Table 7, data row 50; Eqs.67,99,100 | `([35], ['1+v^{3}', '1+v^{5}', '1+v^{9}', '1+v^{19}', '1+v^{34}'])` |
| `mm_t6_r35_354_6_15` | 2601.18879 | (354,6) | 15 | open | v2 Appendix F Table 6, data row 35; Eqs.67,99,100 | `([59], ['1+w^{33}', '1+w^{39}', '1+w^{42}', '1+w^{47}'])` |
| `mm_t7_r51_360_10_8` | 2601.18879 | (360,10) | 8 | open | v2 Appendix F Table 7, data row 51; Eqs.67,99,100 | `([36], ['1+v^{8}', '1+v^{9}', '1+v^{15}', '1+v^{19}', '1+v^{31}'])` |
| `llmbb_360_24_10_eprime` | 2606.02418 | (360,24) | 10 | open | Supplemental Material I Table 3 class e′; Eq. (1) | `((15, 12), [[0, 0], [0, 2], [0, 10], [1, 0], [14, 0]], [[0, 0], [0, 2], [0, 10], [2, 0], [13, 0]])` |
| `llmbb_360_24_10_fprime` | 2606.02418 | (360,24) | 10 | open | Supplemental Material I Table 3 class f′; Eq. (1) | `((30, 6), [[0, 1], [0, 2], [3, 0]], [[0, 1], [0, 2], [21, 0]])` |
| `llmbb_360_26_10_aprime` | 2606.02418 | (360,26) | 10 | open | Supplemental Material I Table 3 class a′; Eq. (1) | `((15, 12), [[0, 0], [1, 1], [3, 3], [7, 7]], [[0, 0], [1, 11], [3, 9], [7, 5]])` |
| `mm_t8_r12_360_20_10` | 2601.18879 | (360,20) | 10 | open | v2 Appendix F Table 8, data row 12; Eqs.67,99,100 | `([18], ['1+u^{3}', '1+u^{7}', '1+u^{11}', '1+u^{13}', '1+u^{16}', '1+u^{17}'])` |
| `mm_t2_r12_360_12_11` | 2601.18879 | (360,12) | 11 | open | v2 Appendix F Table 2, data row 12; Eqs.67,99,100 | `([2, 2, 3, 5], ['y^{2}z+yz^{3}', 'wy^{2}z^{3}+xy^{2}', 'wz^{3}+xyz^{2}', 'wyz^{3}+xy^{2}'])` |
| `llmbb_360_16_12_gprime` | 2606.02418 | (360,16) | 12 | open | Supplemental Material I Table 3 class g′; Eq. (1) | `((15, 12), [[0, 0], [4, 2], [13, 4]], [[0, 0], [2, 4], [4, 10]])` |
| `llmbb_360_16_12_hprime` | 2606.02418 | (360,16) | 12 | open | Supplemental Material I Table 3 class h′; Eq. (1) | `((15, 12), [[0, 0], [1, 4], [2, 2]], [[0, 0], [2, 4], [4, 2]])` |
| `llmbb_360_18_12_bprime` | 2606.02418 | (360,18) | 12 | open | Supplemental Material I Table 3 class b′; Eq. (1) | `((15, 12), [[0, 0], [1, 1], [4, 4], [6, 6]], [[0, 0], [1, 11], [4, 8], [6, 6]])` |
| `llmbb_360_24_12_Yprime` | 2606.02418 | (360,24) | 12 | open | Supplemental Material I Table 3 class Y′; Eq. (1) | `((15, 12), [[0, 0], [1, 1], [4, 4], [9, 9]], [[0, 0], [1, 11], [4, 8], [9, 3]])` |
| `mm_t2_r11_360_6_12` | 2601.18879 | (360,6) | 12 | open | v2 Appendix F Table 2, data row 11; Eqs.67,99,100 | `([2, 2, 3, 5], ['xz^{3}+y^{2}z', 'wx+wz^{2}', 'wxy^{2}+y^{2}z^{2}', 'wxyz^{3}+wxz^{2}'])` |
| `llmbb_360_16_14_A` | 2606.02418 | (360,16) | 14 | open | Supplemental Material I Table 3 class A; Eq. (1) | `((15, 12), [[0, 2], [0, 4], [3, 0]], [[0, 6], [7, 0], [14, 0]])` |
| `llmbb_360_16_14_Zprime` | 2606.02418 | (360,16) | 14 | open | Supplemental Material I Table 3 class Z′; Eq. (1) | `((15, 12), [[0, 0], [0, 4], [3, 2]], [[0, 0], [2, 4], [4, 2]])` |
| `llmbb_360_20_14_Wprime` | 2606.02418 | (360,20) | 14 | open | Supplemental Material I Table 3 class W′; Eq. (1) | `((30, 6), [[0, 0], [1, 0], [3, 4], [6, 2]], [[0, 0], [0, 2], [3, 2], [6, 4]])` |
| `mm_t6_r36_360_6_15` | 2601.18879 | (360,6) | 15 | open | v2 Appendix F Table 6, data row 36; Eqs.67,99,100 | `([60], ['1+w^{4}', '1+w^{18}', '1+w^{25}', '1+w^{44}'])` |
| `llmbb_360_8_18_cprime` | 2606.02418 | (360,8) | 18 | open | Supplemental Material I Table 3 class c′; Eq. (1) | `((15, 12), [[0, 0], [1, 1], [2, 1]], [[0, 0], [2, 3], [3, 2]])` |
| `llmbb_360_8_18_dprime` | 2606.02418 | (360,8) | 18 | open | Supplemental Material I Table 3 class d′; Eq. (1) | `((15, 12), [[0, 0], [1, 1], [3, 2]], [[0, 0], [1, 1], [13, 3]])` |
| `llmbb_360_12_24_V` | 2606.02418 | (360,12) | 24 | open | Supplemental Material I Table 3 class V†; Eq. (1) | `((30, 6), [[0, 1], [0, 2], [9, 0]], [[0, 3], [25, 0], [26, 0]])` |
| `mm_t6_r37_366_6_15` | 2601.18879 | (366,6) | 15 | open | v2 Appendix F Table 6, data row 37; Eqs.67,99,100 | `([61], ['1+w^{30}', '1+w^{38}', '1+w^{47}', '1+w^{48}'])` |
| `mm_t7_r52_370_10_9` | 2601.18879 | (370,10) | 9 | open | v2 Appendix F Table 7, data row 52; Eqs.67,99,100 | `([37], ['1+v^{2}', '1+v^{4}', '1+v^{21}', '1+v^{27}', '1+v^{28}'])` |
| `mm_t6_r38_372_6_16` | 2601.18879 | (372,6) | 16 | open | v2 Appendix F Table 6, data row 38; Eqs.67,99,100 | `([62], ['1+w^{42}', '1+w^{46}', '1+w^{55}', '1+w^{57}'])` |
| `mm_t6_r39_378_6_17` | 2601.18879 | (378,6) | 17 | open | v2 Appendix F Table 6, data row 39; Eqs.67,99,100 | `([63], ['1+w^{11}', '1+w^{44}', '1+w^{46}', '1+w^{56}'])` |
| `mm_t7_r53_380_10_8` | 2601.18879 | (380,10) | 8 | open | v2 Appendix F Table 7, data row 53; Eqs.67,99,100 | `([38], ['1+v^{2}', '1+v^{9}', '1+v^{16}', '1+v^{17}', '1+v^{35}'])` |
| `mm_t8_r13_380_20_10` | 2601.18879 | (380,20) | 10 | open | v2 Appendix F Table 8, data row 13; Eqs.67,99,100 | `([19], ['1+u^{2}', '1+u^{3}', '1+u^{5}', '1+u^{6}', '1+u^{11}', '1+u^{12}'])` |
| `mm_t8_r14_380_20_11` | 2601.18879 | (380,20) | 11 | open | v2 Appendix F Table 8, data row 14; Eqs.67,99,100 | `([19], ['1+u^{9}', '1+u^{13}', '1+u^{14}', '1+u^{15}', '1+u^{16}', '1+u^{17}'])` |
| `mm_t2_r14_384_12_8` | 2601.18879 | (384,12) | 8 | open | v2 Appendix F Table 2, data row 14; Eqs.67,99,100 | `([2, 2, 2, 8], ['wyz+xyz^{6}', 'wxyz^{4}+wz^{6}', 'wxyz^{6}+wz^{7}', 'wxy+xz^{5}'])` |
| `mm_t2_r13_384_6_12` | 2601.18879 | (384,6) | 12 | open | v2 Appendix F Table 2, data row 13; Eqs.67,99,100 | `([2, 2, 2, 8], ['wz^{4}+xz^{7}', 'xz^{2}+yz', 'wyz^{5}+wyz^{4}', 'xyz^{7}+x'])` |
| `mm_t4_r14_384_24_16` | 2601.18879 | (384,24) | 16 | open | v2 Appendix F Table 4, data row 14; Eqs.67,99,100 | `([2, 2, 4, 4], ['wxyz^{3}+wy^{2}z^{3}  +xy^{2}+y^{2}z', 'wxyz^{2}+wxz^{3}  +wy^{3}z+xyz^{3}', 'wxy^{3}z+wxz^{2}  +wy^{2}z^{3}+xyz^{2}', 'wxy^{3}z+wxz^{3}  +xy^{2}z^{2}+xy^{2}z'])` |
| `mm_t6_r40_384_6_17` | 2601.18879 | (384,6) | 17 | open | v2 Appendix F Table 6, data row 40; Eqs.67,99,100 | `([64], ['1+w^{6}', '1+w^{10}', '1+w^{43}', '1+w^{51}'])` |
| `mm_t9_r4_385_35_7` | 2601.18879 | (385,35) | 7 | open | v2 Appendix F Table 9, data row 4; Eqs.67,99,100 | `([11], ['1+t', '1+t^{2}', '1+t^{3}', '1+t^{4}', '1+t^{6}', '1+t^{8}', '1+t^{10}'])` |
| `mm_t7_r54_390_10_9` | 2601.18879 | (390,10) | 9 | open | v2 Appendix F Table 7, data row 54; Eqs.67,99,100 | `([39], ['1+v^{5}', '1+v^{15}', '1+v^{21}', '1+v^{23}', '1+v^{35}'])` |
| `mm_t6_r41_390_6_15` | 2601.18879 | (390,6) | 15 | open | v2 Appendix F Table 6, data row 41; Eqs.67,99,100 | `([65], ['1+w^{8}', '1+w^{15}', '1+w^{39}', '1+w^{59}'])` |
| `balanced_390_78_16` | 2607.27644 | (390,78) | 16 | open | Table 3 | `(390, 78, 16, 'open', (26, 3, 3), [(0, 0), (17, 1), (14, 2)], [(0, 0), (16, 0), (3, 1)], [(0, 0), (24, 0), (8, 1)], [(0, 0), (21, 0), (0, 1)])` |
| `mm_t6_r42_396_6_15` | 2601.18879 | (396,6) | 15 | open | v2 Appendix F Table 6, data row 42; Eqs.67,99,100 | `([66], ['1+w^{12}', '1+w^{13}', '1+w^{32}', '1+w^{38}'])` |
| `mm_t7_r55_400_10_9` | 2601.18879 | (400,10) | 9 | open | v2 Appendix F Table 7, data row 55; Eqs.67,99,100 | `([40], ['1+v^{18}', '1+v^{28}', '1+v^{31}', '1+v^{33}', '1+v^{39}'])` |
| `mm_t8_r15_400_20_10` | 2601.18879 | (400,20) | 10 | open | v2 Appendix F Table 8, data row 15; Eqs.67,99,100 | `([20], ['1+u^{8}', '1+u^{11}', '1+u^{14}', '1+u^{15}', '1+u^{17}', '1+u^{18}'])` |
| `mm_t8_r16_400_20_11` | 2601.18879 | (400,20) | 11 | open | v2 Appendix F Table 8, data row 16; Eqs.67,99,100 | `([20], ['1+u^{3}', '1+u^{7}', '1+u^{11}', '1+u^{14}', '1+u^{16}', '1+u^{19}'])` |
| `mm_t8_r17_400_20_12` | 2601.18879 | (400,20) | 12 | open | v2 Appendix F Table 8, data row 17; Eqs.67,99,100 | `([20], ['1+u', '1+u^{2}', '1+u^{3}', '1+u^{6}', '1+u^{9}', '1+u^{15}'])` |
| `mm_t6_r43_402_6_16` | 2601.18879 | (402,6) | 16 | open | v2 Appendix F Table 6, data row 43; Eqs.67,99,100 | `([67], ['1+w^{7}', '1+w^{9}', '1+w^{45}', '1+w^{57}'])` |
| `mm_t6_r44_408_6_15` | 2601.18879 | (408,6) | 15 | open | v2 Appendix F Table 6, data row 44; Eqs.67,99,100 | `([68], ['1+w^{4}', '1+w^{46}', '1+w^{49}', '1+w^{52}'])` |
| `mm_t7_r56_410_10_10` | 2601.18879 | (410,10) | 10 | open | v2 Appendix F Table 7, data row 56; Eqs.67,99,100 | `([41], ['1+v^{7}', '1+v^{14}', '1+v^{25}', '1+v^{26}', '1+v^{38}'])` |
| `mm_t6_r45_414_6_16` | 2601.18879 | (414,6) | 16 | open | v2 Appendix F Table 6, data row 45; Eqs.67,99,100 | `([69], ['1+w^{9}', '1+w^{19}', '1+w^{24}', '1+w^{53}'])` |
| `mm_t9_r5_420_35_6` | 2601.18879 | (420,35) | 6 | open | v2 Appendix F Table 9, data row 5; Eqs.67,99,100 | `([12], ['1+t', '1+t^{3}', '1+t^{6}', '1+t^{7}', '1+t^{8}', '1+t^{10}', '1+t^{11}'])` |
| `mm_t7_r57_420_10_9` | 2601.18879 | (420,10) | 9 | open | v2 Appendix F Table 7, data row 57; Eqs.67,99,100 | `([42], ['1+v^{15}', '1+v^{23}', '1+v^{29}', '1+v^{31}', '1+v^{37}'])` |
| `mm_t8_r18_420_20_12` | 2601.18879 | (420,20) | 12 | open | v2 Appendix F Table 8, data row 18; Eqs.67,99,100 | `([21], ['1+u^{7}', '1+u^{11}', '1+u^{13}', '1+u^{15}', '1+u^{18}', '1+u^{19}'])` |
| `mm_t6_r46_420_6_15` | 2601.18879 | (420,6) | 15 | open | v2 Appendix F Table 6, data row 46; Eqs.67,99,100 | `([70], ['1+w^{2}', '1+w^{13}', '1+w^{32}', '1+w^{56}'])` |
| `mm_t6_r47_426_6_17` | 2601.18879 | (426,6) | 17 | open | v2 Appendix F Table 6, data row 47; Eqs.67,99,100 | `([71], ['1+w^{15}', '1+w^{19}', '1+w^{29}', '1+w^{35}'])` |
| `mm_t7_r58_430_10_10` | 2601.18879 | (430,10) | 10 | open | v2 Appendix F Table 7, data row 58; Eqs.67,99,100 | `([43], ['1+v^{9}', '1+v^{10}', '1+v^{13}', '1+v^{16}', '1+v^{28}'])` |
| `mm_t2_r15_432_12_12` | 2601.18879 | (432,12) | 12 | open | v2 Appendix F Table 2, data row 15; Eqs.67,99,100 | `([2, 2, 2, 9], ['wyz^{3}+xz^{7}', 'wyz+yz^{5}', 'xyz^{5}+z^{7}', 'wxz^{7}+wyz^{3}'])` |
| `mm_t6_r48_432_6_16` | 2601.18879 | (432,6) | 16 | open | v2 Appendix F Table 6, data row 48; Eqs.67,99,100 | `([72], ['1+w^{5}', '1+w^{13}', '1+w^{50}', '1+w^{60}'])` |
| `mm_t2_r16_432_6_18` | 2601.18879 | (432,6) | 18 | open | v2 Appendix F Table 2, data row 16; Eqs.67,99,100 | `([2, 3, 3, 4], ['wx+x^{2}z', 'wy^{2}z^{3}+xyz', 'x^{2}yz+y^{2}', 'xy^{2}z^{3}+xyz'])` |
| `mm_t3_r9_432_24_18` | 2601.18879 | (432,24) | 18 | open | v2 Appendix F Table 3, data row 9; Eqs.67,99,100 | `([2, 2, 3, 6], ['wxz+wy^{2}z^{4}  +xy', 'wxy^{2}+wxyz  +wx', 'wxy^{2}z^{4}+wyz  +xz^{2}', 'wxy^{2}z^{5}+wyz^{4}  +xz^{4}'])` |
| `mm_t6_r49_438_6_17` | 2601.18879 | (438,6) | 17 | open | v2 Appendix F Table 6, data row 49; Eqs.67,99,100 | `([73], ['1+w^{18}', '1+w^{29}', '1+w^{32}', '1+w^{63}'])` |
| `mm_t7_r59_440_10_10` | 2601.18879 | (440,10) | 10 | open | v2 Appendix F Table 7, data row 59; Eqs.67,99,100 | `([44], ['1+v', '1+v^{10}', '1+v^{16}', '1+v^{21}', '1+v^{25}'])` |
| `mm_t8_r19_440_20_11` | 2601.18879 | (440,20) | 11 | open | v2 Appendix F Table 8, data row 19; Eqs.67,99,100 | `([22], ['1+u^{7}', '1+u^{9}', '1+u^{12}', '1+u^{17}', '1+u^{18}', '1+u^{19}'])` |
| `mm_t6_r50_444_6_17` | 2601.18879 | (444,6) | 17 | open | v2 Appendix F Table 6, data row 50; Eqs.67,99,100 | `([74], ['1+w^{6}', '1+w^{26}', '1+w^{49}', '1+w^{59}'])` |
| `mm_t7_r60_450_10_10` | 2601.18879 | (450,10) | 10 | open | v2 Appendix F Table 7, data row 60; Eqs.67,99,100 | `([45], ['1+v^{4}', '1+v^{10}', '1+v^{84}', '1+v^{21}', '1+v^{26}'])` |
| `mm_t6_r51_450_6_16` | 2601.18879 | (450,6) | 16 | open | v2 Appendix F Table 6, data row 51; Eqs.67,99,100 | `([75], ['1+w^{5}', '1+w^{49}', '1+w^{63}', '1+w^{64}'])` |
| `mm_t9_r6_455_35_7` | 2601.18879 | (455,35) | 7 | open | v2 Appendix F Table 9, data row 6; Eqs.67,99,100 | `([13], ['1+t^{2}', '1+t^{6}', '1+t^{7}', '1+t^{8}', '1+t^{9}', '1+t^{10}', '1+t^{11}'])` |
| `mm_t9_r7_455_35_7` | 2601.18879 | (455,35) | 7 | open | v2 Appendix F Table 9, data row 7; Eqs.67,99,100 | `([13], ['1+t', '1+t^{2}', '1+t^{4}', '1+t^{5}', '1+t^{6}', '1+t^{10}', '1+t^{12}'])` |
| `mm_t6_r52_456_6_16` | 2601.18879 | (456,6) | 16 | open | v2 Appendix F Table 6, data row 52; Eqs.67,99,100 | `([76], ['1+w^{17}', '1+w^{28}', '1+w^{68}', '1+w^{74}'])` |
| `mm_t7_r61_460_10_10` | 2601.18879 | (460,10) | 10 | open | v2 Appendix F Table 7, data row 61; Eqs.67,99,100 | `([46], ['1+v^{9}', '1+v^{16}', '1+v^{20}', '1+v^{42}', '1+v^{43}'])` |
| `mm_t8_r20_460_20_12` | 2601.18879 | (460,20) | 12 | open | v2 Appendix F Table 8, data row 20; Eqs.67,99,100 | `([23], ['1+u^{4}', '1+u^{7}', '1+u^{12}', '1+u^{14}', '1+u^{18}', '1+u^{20}'])` |
| `mm_t6_r53_462_6_17` | 2601.18879 | (462,6) | 17 | open | v2 Appendix F Table 6, data row 53; Eqs.67,99,100 | `([77], ['1+w^{9}', '1+w^{26}', '1+w^{37}', '1+w^{53}'])` |
| `mm_t6_r54_468_6_17` | 2601.18879 | (468,6) | 17 | open | v2 Appendix F Table 6, data row 54; Eqs.67,99,100 | `([78], ['1+w^{24}', '1+w^{33}', '1+w^{38}', '1+w^{65}'])` |
| `mm_t7_r62_470_10_9` | 2601.18879 | (470,10) | 9 | open | v2 Appendix F Table 7, data row 62; Eqs.67,99,100 | `([47], ['1+v^{17}', '1+v^{38}', '1+v^{39}', '1+v^{40}', '1+v^{44}'])` |
| `mm_t6_r55_474_6_17` | 2601.18879 | (474,6) | 17 | open | v2 Appendix F Table 6, data row 55; Eqs.67,99,100 | `([79], ['1+w^{7}', '1+w^{10}', '1+w^{12}', '1+w^{61}'])` |
| `mm_t2_r19_480_24_8` | 2601.18879 | (480,24) | 8 | open | v2 Appendix F Table 2, data row 19; Eqs.67,99,100 | `([2, 2, 4, 5], ['wxy^{3}z^{2}+xz', 'wz^{3}+yz', 'wy^{2}z^{3}+y^{3}z^{4}', 'wyz^{4}+y^{2}z'])` |
| `mm_t7_r63_480_10_10` | 2601.18879 | (480,10) | 10 | open | v2 Appendix F Table 7, data row 63; Eqs.67,99,100 | `([48], ['1+v^{8}', '1+v^{11}', '1+v^{15}', '1+v^{17}', '1+v^{38}'])` |
| `mm_t2_r18_480_12_12` | 2601.18879 | (480,12) | 12 | open | v2 Appendix F Table 2, data row 18; Eqs.67,99,100 | `([2, 2, 4, 5], ['wxy^{2}z^{4}+wz^{2}', 'wxz+xy^{2}z^{4}', 'wxy^{2}z^{2}+xy^{2}', 'xy^{3}z+xyz^{3}'])` |
| `mm_t8_r21_480_20_12` | 2601.18879 | (480,20) | 12 | open | v2 Appendix F Table 8, data row 21; Eqs.67,99,100 | `([24], ['1+u^{15}', '1+u^{16}', '1+u^{19}', '1+u^{20}', '1+u^{22}', '1+u^{23}'])` |
| `mm_t2_r17_480_6_16` | 2601.18879 | (480,6) | 16 | open | v2 Appendix F Table 2, data row 17; Eqs.67,99,100 | `([2, 2, 2, 10], ['w+xz^{8}', 'wxz^{7}+w', 'wxz^{7}+xyz^{3}', 'wyz+wz^{7}'])` |
| `mm_t6_r56_480_6_16` | 2601.18879 | (480,6) | 16 | open | v2 Appendix F Table 6, data row 56; Eqs.67,99,100 | `([80], ['1+w^{7}', '1+w^{13}', '1+w^{35}', '1+w^{44}'])` |
| `mm_t4_r18_486_66_9` | 2601.18879 | (486,66) | 9 | open | v2 Appendix F Table 4, data row 18; Eqs.67,99,100 | `([3, 3, 3, 3], ['(1+x)(1+yz)', '(1+y)(1+zw)', '(1+z)(1+wx)', '(1+w)(1+xy)'])` |
| `mm_t3_r11_486_24_12` | 2601.18879 | (486,24) | 12 | open | v2 Appendix F Table 3, data row 11; Eqs.67,99,100 | `([3, 3, 3, 3], ['wyz+y^{2}z^{2}  +y^{2}', 'w^{2}z^{2}+x^{2}y^{2}z^{2}  +z', 'w^{2}x^{2}z^{2}+wx^{2}y^{2}z  +wy^{2}z', 'w^{2}x^{2}y^{2}z+wz  +x^{2}z^{2}'])` |
| `mm_t6_r57_486_6_17` | 2601.18879 | (486,6) | 17 | open | v2 Appendix F Table 6, data row 57; Eqs.67,99,100 | `([81], ['1+w', '1+w^{14}', '1+w^{21}', '1+w^{64}'])` |
| `mm_t9_r8_490_35_7` | 2601.18879 | (490,35) | 7 | open | v2 Appendix F Table 9, data row 8; Eqs.67,99,100 | `([14], ['1+t', '1+t^{3}', '1+t^{7}', '1+t^{8}', '1+t^{9}', '1+t^{11}', '1+t^{12}'])` |
| `mm_t9_r9_490_35_7` | 2601.18879 | (490,35) | 7 | open | v2 Appendix F Table 9, data row 9; Eqs.67,99,100 | `([14], ['1+t^{3}', '1+t^{4}', '1+t^{6}', '1+t^{7}', '1+t^{9}', '1+t^{12}', '1+t^{13}'])` |
| `mm_t7_r64_490_10_10` | 2601.18879 | (490,10) | 10 | open | v2 Appendix F Table 7, data row 64; Eqs.67,99,100 | `([49], ['1+v^{8}', '1+v^{10}', '1+v^{21}', '1+v^{34}', '1+v^{45}'])` |
| `mm_t6_r58_492_6_16` | 2601.18879 | (492,6) | 16 | open | v2 Appendix F Table 6, data row 58; Eqs.67,99,100 | `([82], ['1+w^{8}', '1+w^{21}', '1+w^{27}', '1+w^{38}'])` |
| `mm_t6_r59_498_6_18` | 2601.18879 | (498,6) | 18 | open | v2 Appendix F Table 6, data row 59; Eqs.67,99,100 | `([83], ['1+w^{7}', '1+w^{9}', '1+w^{31}', '1+w^{79}'])` |
| `mm_t7_r65_500_10_11` | 2601.18879 | (500,10) | 11 | open | v2 Appendix F Table 7, data row 65; Eqs.67,99,100 | `([50], ['1+v^{3}', '1+v^{21}', '1+v^{36}', '1+v^{41}', '1+v^{49}'])` |
| `mm_t2_r21_504_12_10` | 2601.18879 | (504,12) | 10 | open | v2 Appendix F Table 2, data row 21; Eqs.67,99,100 | `([2, 2, 3, 7], ['wx+xyz^{4}', 'wyz^{2}+y', 'wy^{2}z^{4}+wyz', 'wyz^{5}+z^{2}'])` |
| `mm_t2_r20_504_6_17` | 2601.18879 | (504,6) | 17 | open | v2 Appendix F Table 2, data row 20; Eqs.67,99,100 | `([2, 2, 3, 7], ['wxyz^{4}+wz', 'wy^{2}z^{3}+xz^{3}', 'wy^{2}z^{5}+xy^{2}z', 'wyz^{2}+yz'])` |
| `mm_t3_r12_504_12_18` | 2601.18879 | (504,12) | 18 | open | v2 Appendix F Table 3, data row 12; Eqs.67,99,100 | `([2, 2, 3, 7], ['y^{2}z^{4}+yz^{5}  +z', 'xy^{2}z^{3}+xz^{6}  +yz^{4}', 'wxz+xy^{2}z^{4}  +yz^{2}', 'wz^{3}+xy^{2}z^{5}  +xyz'])` |
| `mm_t6_r60_504_6_18` | 2601.18879 | (504,6) | 18 | open | v2 Appendix F Table 6, data row 60; Eqs.67,99,100 | `([84], ['1+w^{15}', '1+w^{45}', '1+w^{68}', '1+w^{73}'])` |
| `mm_t7_r66_510_10_11` | 2601.18879 | (510,10) | 11 | open | v2 Appendix F Table 7, data row 66; Eqs.67,99,100 | `([51], ['1+v^{8}', '1+v^{18}', '1+v^{20}', '1+v^{27}', '1+v^{37}'])` |
| `mm_t6_r61_510_6_17` | 2601.18879 | (510,6) | 17 | open | v2 Appendix F Table 6, data row 61; Eqs.67,99,100 | `([85], ['1+w^{5}', '1+w^{22}', '1+w^{55}', '1+w^{84}'])` |
| `mm_t6_r62_516_6_20` | 2601.18879 | (516,6) | 20 | open | v2 Appendix F Table 6, data row 62; Eqs.67,99,100 | `([86], ['1+w^{5}', '1+w^{13}', '1+w^{62}', '1+w^{69}'])` |
| `mm_t7_r67_520_10_10` | 2601.18879 | (520,10) | 10 | open | v2 Appendix F Table 7, data row 67; Eqs.67,99,100 | `([52], ['1+v^{5}', '1+v^{23}', '1+v^{39}', '1+v^{45}', '1+v^{51}'])` |
| `mm_t8_r23_520_20_14` | 2601.18879 | (520,20) | 14 | open | v2 Appendix F Table 8, data row 23; Eqs.67,99,100 | `([26], ['1+u^{3}', '1+u^{5}', '1+u^{7}', '1+u^{16}', '1+u^{17}', '1+u^{22}'])` |
| `mm_t6_r63_522_6_20` | 2601.18879 | (522,6) | 20 | open | v2 Appendix F Table 6, data row 63; Eqs.67,99,100 | `([87], ['1+w^{39}', '1+w^{54}', '1+w^{77}', '1+w^{80}'])` |
| `mm_t9_r10_525_35_8` | 2601.18879 | (525,35) | 8 | open | v2 Appendix F Table 9, data row 10; Eqs.67,99,100 | `([15], ['1+t^{2}', '1+t^{3}', '1+t^{6}', '1+t^{7}', '1+t^{8}', '1+t^{10}', '1+t^{11}'])` |
| `mm_t9_r11_525_35_9` | 2601.18879 | (525,35) | 9 | open | v2 Appendix F Table 9, data row 11; Eqs.67,99,100 | `([15], ['1+t', '1+t^{2}', '1+t^{3}', '1+t^{4}', '1+t^{5}', '1+t^{8}', '1+t^{9}'])` |
| `balanced_525_105_18` | 2607.27644 | (525,105) | 18 | open | Appendix A, Table 8 | `(525, 105, 18, 'open', (35, 3, 11), [(0, 0), (22, 0), (1, 2)], [(0, 0), (4, 0), (16, 2)], [(0, 0), (34, 0), (12, 1)], [(0, 0), (28, 1), (31, 1)])` |
| `mm_t2_r23_528_12_12` | 2601.18879 | (528,12) | 12 | open | v2 Appendix F Table 2, data row 23; Eqs.67,99,100 | `([2, 2, 2, 11], ['wz^{10}+wz^{9}', 'yz^{10}+z^{6}', 'wz^{5}+xyz', 'wxyz^{6}+yz^{10}'])` |
| `mm_t2_r22_528_6_16` | 2601.18879 | (528,6) | 16 | open | v2 Appendix F Table 2, data row 22; Eqs.67,99,100 | `([2, 2, 2, 11], ['xyz^{5}+z^{2}', 'y+z^{9}', 'wxz^{3}+xyz^{7}', 'wyz^{10}+xyz^{4}'])` |
| `mm_t7_r68_530_10_12` | 2601.18879 | (530,10) | 12 | open | v2 Appendix F Table 7, data row 68; Eqs.67,99,100 | `([53], ['1+v^{8}', '1+v^{21}', '1+v^{29}', '1+v^{39}', '1+v^{40}'])` |
| `mm_t2_r25_540_18_7` | 2601.18879 | (540,18) | 7 | open | v2 Appendix F Table 2, data row 25; Eqs.67,99,100 | `([2, 3, 3, 5], ['wxy^{2}z^{2}+x^{2}y^{2}z^{2}', 'wxyz^{2}+xy', 'x^{2}y+xyz^{2}', 'x^{2}y^{2}+y^{2}z^{2}'])` |
| `mm_t7_r69_540_10_12` | 2601.18879 | (540,10) | 12 | open | v2 Appendix F Table 7, data row 69; Eqs.67,99,100 | `([54], ['1+v', '1+v^{8}', '1+v^{37}', '1+v^{41}', '1+v^{51}'])` |
| `mm_t8_r24_540_20_13` | 2601.18879 | (540,20) | 13 | open | v2 Appendix F Table 8, data row 24; Eqs.67,99,100 | `([27], ['1+u^{3}', '1+u^{4}', '1+u^{14}', '1+u^{19}', '1+u^{22}', '1+u^{25}'])` |
| `mm_t2_r24_540_6_18` | 2601.18879 | (540,6) | 18 | open | v2 Appendix F Table 2, data row 24; Eqs.67,99,100 | `([2, 3, 3, 5], ['wx^{2}yz+wxy^{2}z^{2}', 'xz+1', 'wz+x^{2}yz^{2}', 'wx^{2}yz+wx'])` |
| `mm_t7_r70_550_10_10` | 2601.18879 | (550,10) | 10 | open | v2 Appendix F Table 7, data row 70; Eqs.67,99,100 | `([55], ['1+v^{26}', '1+v^{35}', '1+v^{37}', '1+v^{39}', '1+v^{41}'])` |
| `balanced_550_110_18` | 2607.27644 | (550,110) | 18 | open | Table 3 | `(550, 110, 18, 'open', (22, 5, 3), [(0, 0), (10, 0), (5, 2)], [(0, 0), (8, 0), (2, 3)], [(0, 0), (7, 0), (16, 1)], [(0, 0), (1, 0), (6, 4)])` |
| `mm_t9_r12_560_35_8` | 2601.18879 | (560,35) | 8 | open | v2 Appendix F Table 9, data row 12; Eqs.67,99,100 | `([16], ['1+t^{2}', '1+t^{4}', '1+t^{6}', '1+t^{7}', '1+t^{11}', '1+t^{13}', '1+t^{15}'])` |
| `mm_t7_r71_560_10_11` | 2601.18879 | (560,10) | 11 | open | v2 Appendix F Table 7, data row 71; Eqs.67,99,100 | `([56], ['1+v^{30}', '1+v^{35}', '1+v^{46}', '1+v^{48}', '1+v^{53}'])` |
| `mm_t8_r25_560_20_14` | 2601.18879 | (560,20) | 14 | open | v2 Appendix F Table 8, data row 25; Eqs.67,99,100 | `([28], ['1+u', '1+u^{6}', '1+u^{12}', '1+u^{13}', '1+u^{23}', '1+u^{24}'])` |
| `mm_t7_r72_570_10_11` | 2601.18879 | (570,10) | 11 | open | v2 Appendix F Table 7, data row 72; Eqs.67,99,100 | `([57], ['1+v^{8}', '1+v^{17}', '1+v^{30}', '1+v^{45}', '1+v^{56}'])` |
| `mm_t4_r20_576_64_6` | 2601.18879 | (576,64) | 6 | open | v2 Appendix F Table 4, data row 20; Eqs.67,99,100 | `([2, 3, 4, 4], ['(1+x)(1+yz)', '(1+y)(1+zw)', '(1+z)(1+wx)', '(1+w)(1+xy)'])` |
| `mm_t2_r28_576_18_8` | 2601.18879 | (576,18) | 8 | open | v2 Appendix F Table 2, data row 28; Eqs.67,99,100 | `([2, 2, 3, 8], ['wy^{2}z+xy^{2}z^{4}', 'wy^{2}z^{5}+xy^{2}z^{6}', 'wxyz^{2}+xyz', 'wxyz^{4}+y'])` |
| `mm_t2_r26_576_12_12` | 2601.18879 | (576,12) | 12 | open | v2 Appendix F Table 2, data row 26; Eqs.67,99,100 | `([2, 2, 2, 12], ['wxz^{10}+y', 'wxz^{8}+yz^{5}', 'xz^{7}+xz^{5}', 'wyz^{4}+xyz^{2}'])` |
| `mm_t2_r27_576_6_16` | 2601.18879 | (576,6) | 16 | open | v2 Appendix F Table 2, data row 27; Eqs.67,99,100 | `([2, 2, 3, 8], ['wy^{2}+z^{6}', 'wy^{2}z^{3}+1', 'wxy^{2}+wyz^{6}', 'wxy^{2}+wyz^{6}'])` |
| `mm_t7_r73_580_10_12` | 2601.18879 | (580,10) | 12 | open | v2 Appendix F Table 7, data row 73; Eqs.67,99,100 | `([58], ['1+v^{21}', '1+v^{32}', '1+v^{39}', '1+v^{43}', '1+v^{46}'])` |
| `mm_t8_r26_580_20_14` | 2601.18879 | (580,20) | 14 | open | v2 Appendix F Table 8, data row 26; Eqs.67,99,100 | `([29], ['1+u^{3}', '1+u^{5}', '1+u^{9}', '1+u^{12}', '1+u^{18}', '1+u^{25}'])` |
| `mm_t7_r74_590_10_11` | 2601.18879 | (590,10) | 11 | open | v2 Appendix F Table 7, data row 74; Eqs.67,99,100 | `([59], ['1+v^{5}', '1+v^{6}', '1+v^{9}', '1+v^{31}', '1+v^{38}'])` |
| `mm_t9_r13_595_35_10` | 2601.18879 | (595,35) | 10 | open | v2 Appendix F Table 9, data row 13; Eqs.67,99,100 | `([17], ['1+t^{2}', '1+t^{5}', '1+t^{8}', '1+t^{10}', '1+t^{11}', '1+t^{13}', '1+t^{16}'])` |
| `mm_t2_r30_600_24_9` | 2601.18879 | (600,24) | 9 | open | v2 Appendix F Table 2, data row 30; Eqs.67,99,100 | `([2, 2, 5, 5], ['y^{4}z^{3}+yz', 'xy^{3}+xy^{2}z^{4}', 'wy^{3}z^{4}+wy^{3}', 'y^{3}z^{2}+yz'])` |
| `mm_t2_r31_600_12_10` | 2601.18879 | (600,12) | 10 | open | v2 Appendix F Table 2, data row 31; Eqs.67,99,100 | `([2, 2, 5, 5], ['y^{3}z^{3}+yz', 'wyz+xy^{3}z', 'wy^{3}z^{2}+wy^{2}z^{2}', 'wy^{2}z+wy^{2}'])` |
| `mm_t7_r75_600_10_10` | 2601.18879 | (600,10) | 10 | open | v2 Appendix F Table 7, data row 75; Eqs.67,99,100 | `([60], ['1+v^{5}', '1+v^{12}', '1+v^{21}', '1+v^{35}', '1+v^{59}'])` |
| `mm_t8_r27_600_20_14` | 2601.18879 | (600,20) | 14 | open | v2 Appendix F Table 8, data row 27; Eqs.67,99,100 | `([30], ['1+u^{11}', '1+u^{12}', '1+u^{16}', '1+u^{17}', '1+u^{21}', '1+u^{29}'])` |
| `mm_t2_r29_600_6_17` | 2601.18879 | (600,6) | 17 | open | v2 Appendix F Table 2, data row 29; Eqs.67,99,100 | `([2, 2, 5, 5], ['xy^{2}+xz', 'wz^{4}+yz^{4}', 'xz^{2}+y^{2}z^{3}', 'wxz^{4}+y^{2}z'])` |
| `mm_t7_r76_610_10_12` | 2601.18879 | (610,10) | 12 | open | v2 Appendix F Table 7, data row 76; Eqs.67,99,100 | `([61], ['1+v^{23}', '1+v^{32}', '1+v^{39}', '1+v^{43}', '1+v^{49}'])` |
| `mm_t7_r77_620_10_11` | 2601.18879 | (620,10) | 11 | open | v2 Appendix F Table 7, data row 77; Eqs.67,99,100 | `([62], ['1+v^{9}', '1+v^{13}', '1+v^{35}', '1+v^{42}', '1+v^{50}'])` |
| `mm_t8_r28_620_20_15` | 2601.18879 | (620,20) | 15 | open | v2 Appendix F Table 8, data row 28; Eqs.67,99,100 | `([31], ['1+u^{4}', '1+u^{5}', '1+u^{14}', '1+u^{16}', '1+u^{19}', '1+u^{28}'])` |
| `mm_t2_r33_624_12_14` | 2601.18879 | (624,12) | 14 | open | v2 Appendix F Table 2, data row 33; Eqs.67,99,100 | `([2, 2, 2, 13], ['wyz^{12}+xz^{7}', 'wz^{9}+wz', 'xz^{1}1+yz^{8}', 'wxyz^{3}+xyz^{4}'])` |
| `mm_t2_r32_624_6_18` | 2601.18879 | (624,6) | 18 | open | v2 Appendix F Table 2, data row 32; Eqs.67,99,100 | `([2, 2, 2, 13], ['xz^{6}+yz^{9}', 'xyz^{7}+xz', 'wxyz^{11}+wyz^{12}', 'wyz^{10}+xz^{5}'])` |
| `balanced_625_125_20` | 2607.27644 | (625,125) | 20 | open | Appendix A, Table 8 | `(625, 125, 20, 'open', (25, 5, 6), [(0, 0), (6, 0), (1, 1)], [(0, 0), (24, 1), (21, 3)], [(0, 0), (3, 2), (11, 3)], [(0, 0), (4, 0), (6, 2)])` |
| `mm_t10_r1_630_70_9` | 2601.18879 | (630,70) | 9 | open | v2 Appendix F Table 10, data row 1; Eqs.67,99,100 | `([9], ['1+s', '1+s^{2}', '1+s^{3}', '1+s^{4}', '1+s^{5}', '1+s^{6}', '1+s^{7}', '1+s^{8}'])` |
| `mm_t9_r14_630_35_9` | 2601.18879 | (630,35) | 9 | open | v2 Appendix F Table 9, data row 14; Eqs.67,99,100 | `([18], ['1+t^{3}', '1+t^{4}', '1+t^{6}', '1+t^{8}', '1+t^{11}', '1+t^{13}', '1+t^{17}'])` |
| `mm_t7_r78_630_10_12` | 2601.18879 | (630,10) | 12 | open | v2 Appendix F Table 7, data row 78; Eqs.67,99,100 | `([63], ['1+v', '1+v^{16}', '1+v^{36}', '1+v^{44}', '1+v^{50}'])` |
| `mm_t7_r79_640_10_13` | 2601.18879 | (640,10) | 13 | open | v2 Appendix F Table 7, data row 79; Eqs.67,99,100 | `([64], ['1+v^{4}', '1+v^{32}', '1+v^{39}', '1+v^{45}', '1+v^{69}'])` |
| `mm_t8_r29_640_20_15` | 2601.18879 | (640,20) | 15 | open | v2 Appendix F Table 8, data row 29; Eqs.67,99,100 | `([32], ['1+u', '1+u^{2}', '1+u^{5}', '1+u^{7}', '1+u^{11}', '1+u^{13}'])` |
| `mm_t4_r22_648_60_9` | 2601.18879 | (648,60) | 9 | open | v2 Appendix F Table 4, data row 22; Eqs.67,99,100 | `([3, 3, 3, 4], ['(1+x)(1+yz)', '(1+y)(1+zw)', '(1+z)(1+wx)', '(1+w)(1+xy)'])` |
| `mm_t2_r35_648_12_12` | 2601.18879 | (648,12) | 12 | open | v2 Appendix F Table 2, data row 35; Eqs.67,99,100 | `([2, 2, 3, 9], ['xy^{2}z^{4}+xy^{2}z^{3}', 'wx+xz^{8}', 'wz^{7}+y^{2}z^{2}', 'wy^{2}z^{2}+z^{5}'])` |
| `mm_t7_r80_650_10_10` | 2601.18879 | (650,10) | 10 | open | v2 Appendix F Table 7, data row 80; Eqs.67,99,100 | `([65], ['1+v^{18}', '1+v^{41}', '1+v^{55}', '1+v^{61}', '1+v^{64}'])` |
| `mm_t7_r81_660_10_11` | 2601.18879 | (660,10) | 11 | open | v2 Appendix F Table 7, data row 81; Eqs.67,99,100 | `([66], ['1+v^{36}', '1+v^{38}', '1+v^{49}', '1+v^{50}', '1+v^{57}'])` |
| `mm_t8_r30_660_20_15` | 2601.18879 | (660,20) | 15 | open | v2 Appendix F Table 8, data row 30; Eqs.67,99,100 | `([33], ['1+u^{5}', '1+u^{8}', '1+u^{13}', '1+u^{14}', '1+u^{29}', '1+u^{32}'])` |
| `mm_t9_r15_665_35_10` | 2601.18879 | (665,35) | 10 | open | v2 Appendix F Table 9, data row 15; Eqs.67,99,100 | `([19], ['1+t^{8}', '1+t^{9}', '1+t^{13}', '1+t^{14}', '1+t^{16}', '1+t^{17}', '1+t^{18}'])` |
| `mm_t7_r82_670_10_12` | 2601.18879 | (670,10) | 12 | open | v2 Appendix F Table 7, data row 82; Eqs.67,99,100 | `([67], ['1+v^{4}', '1+v^{44}', '1+v^{51}', '1+v^{53}', '1+v^{66}'])` |
| `mm_t2_r38_672_24_11` | 2601.18879 | (672,24) | 11 | open | v2 Appendix F Table 2, data row 38; Eqs.67,99,100 | `([2, 2, 4, 7], ['wy^{3}z+wy^{3}', 'wxyz^{4}+wz^{6}', 'y^{2}z^{2}+1', 'wxy^{3}+wz^{2}'])` |
| `mm_t2_r37_672_12_12` | 2601.18879 | (672,12) | 12 | open | v2 Appendix F Table 2, data row 37; Eqs.67,99,100 | `([2, 2, 2, 14], ['wz^{13}+xz^{9}', 'wxyz^{5}+yz^{13}', 'wxz^{8}+wyz^{11}', 'wxz^{8}+yz^{11}'])` |
| `mm_t2_r36_672_6_18` | 2601.18879 | (672,6) | 18 | open | v2 Appendix F Table 2, data row 36; Eqs.67,99,100 | `([2, 2, 4, 7], ['wxy^{3}z^{3}+w', 'wy^{3}z+y^{2}z^{4}', 'xyz^{2}+xz^{3}', 'xy+y^{3}z^{2}'])` |
| `mm_t7_r83_680_10_11` | 2601.18879 | (680,10) | 11 | open | v2 Appendix F Table 7, data row 83; Eqs.67,99,100 | `([68], ['1+v^{11}', '1+v^{14}', '1+v^{16}', '1+v^{61}', '1+v^{67}'])` |
| `mm_t8_r31_680_20_15` | 2601.18879 | (680,20) | 15 | open | v2 Appendix F Table 8, data row 31; Eqs.67,99,100 | `([34], ['1+u^{9}', '1+u^{20}', '1+u^{22}', '1+u^{23}', '1+u^{26}', '1+u^{27}'])` |
| `mm_t7_r84_690_10_12` | 2601.18879 | (690,10) | 12 | open | v2 Appendix F Table 7, data row 84; Eqs.67,99,100 | `([69], ['1+v^{3}', '1+v^{9}', '1+v^{25}', '1+v^{42}', '1+v^{65}'])` |
| `mm_t10_r2_700_70_8` | 2601.18879 | (700,70) | 8 | open | v2 Appendix F Table 10, data row 2; Eqs.67,99,100 | `([10], ['1+s', '1+s^{2}', '1+s^{3}', '1+s^{4}', '1+s^{5}', '1+s^{6}', '1+s^{7}', '1+s^{9}'])` |
| `mm_t9_r16_700_35_10` | 2601.18879 | (700,35) | 10 | open | v2 Appendix F Table 9, data row 16; Eqs.67,99,100 | `([20], ['1+t^{6}', '1+t^{9}', '1+t^{12}', '1+t^{13}', '1+t^{17}', '1+t^{18}', '1+t^{19}'])` |
| `mm_t7_r85_700_10_11` | 2601.18879 | (700,10) | 11 | open | v2 Appendix F Table 7, data row 85; Eqs.67,99,100 | `([70], ['1+v^{26}', '1+v^{36}', '1+v^{41}', '1+v^{46}', '1+v^{59}'])` |
| `mm_t8_r32_700_20_15` | 2601.18879 | (700,20) | 15 | open | v2 Appendix F Table 8, data row 32; Eqs.67,99,100 | `([35], ['1+u^{2}', '1+u^{10}', '1+u^{16}', '1+u^{23}', '1+u^{27}', '1+u^{32}'])` |

## Non-CSS LLM definitions excluded from the interface

- [[360,12,d<=24]]: l=30, m=6; A=[[1, 2], [4, 3], [4, 4]], B=[[0, 0], [1, 5], [5, 4]], C=[[1, 0], [4, 0]], D=[[1, 2], [4, 2]]. Locator: Main Table 2; Sec III.2 Eq.(2); Appendix F.
- [[360,12,d<=20]]: l=30, m=6; A=[[13, 4], [22, 2], [22, 3]], B=[[0, 0], [5, 2], [13, 1]], C=[[13, 3], [22, 3]], D=[[13, 1], [22, 1]]. Locator: Main Table 2; Sec III.2 Eq.(2); Appendix F.

## Local limits and lead commands

The driver defaults OMP_NUM_THREADS to2 and reads any supplied value before
loading the kernel. The installed macOS library reports one actual thread
(no OpenMP in this build), while requested threads2 are recorded separately.
Lookup degree3 is used at n<=300 (worst table approximately272MiB), and degree2
above300. Default invocation budget570s is a soft limit that also reserves time
for threshold calls; it is not a hard process timeout. Search call limits may
be reduced below the requested per-threshold cap to fit this invocation budget.
Set ESTDIST_TOTAL_SECONDS=0 on the lead server. No long or remote jobs were run
here. Circuit layers/detectors/DEM counts and sector reduction are inapplicable
to this code-distance-only task.

The local results, costs, and individual lead commands are documented in
`results/papers3/estdist/local.json` and `results/papers3/estdist/remaining.md`.

## Independent discrepancy audits

Original HTML cells and independent closed-form t=4 matrices were checked for
Table6 rows1/32 ([[156,6,10]], [[336,6,14]]) and Table2 rows27/33
([[576,6,16]], [[624,12,14]]). The saved exact witnesses verify against those
independent matrices. Original rows156/576 repeat H=I, so a seed typo in the
paper is possible; no replacement was made. The624 conclusion is conditional
on the documented literal xz^{1}1 reading.

For Table8 row16, [[400,20,(11,11)]], the source gives period20 and binomial
exponents(3,7,11,14,16,19). An independent t=6 expansion matches every matrix
row. Both weight12 witnesses are logical. Independent searches through weight11
with cover=False and no symmetry rank/anchors exhausted in0.782s/0.579s,
visiting2,141,789/2,081,438 nodes. Thus this instance has exact distance12
and contradicts the printed11 claim without relying on those pruning options.
PDF typography was not verified; these source audits use arXiv HTML.

For requested Table3 row6, the unambiguous source gives periods(2,3,3,3)
and claimed [[324,12,(20,20)]]. An independent fixed t=4 block expansion
matches every registry matrix row: both check ranks156, check weights9, and
k12. Both saved weight18 supports have zero syndrome and increase stabilizer
rank156 to157. Together with exhausted thresholds1–17, they certify distance18
in both bases, correcting the paper's randomized estimate20.
