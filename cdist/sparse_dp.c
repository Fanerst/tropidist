// Weight-truncated sparse min-plus sweep over a syndrome trellis (see sparse_dp.py).
//
// A table is an array of packed states, sorted by key and with distinct keys:
//     x = key | (value << 56),   key = partial parities of the active rows (bit = row slot, at most 56 slots).
// One column step  T'[s] = min(T[s], T[s ^ upd] + 1)  is done as
//   1. candidates s ^ upd with value + 1 from the states below the cap, filtered by the rows that close at this
//      column (their bits must equal the targets, then are cleared) and by the lookahead bound;
//   2. an LSD radix sort of the candidates by key;
//   3. a linear merge with the (filtered, cleared, re-bounded) old table, keeping the smaller value; candidates
//      that are new or improve a value are also written to the list of changed states.
//
// Build: cc -O3 -march=native -fopenmp -shared -fPIC sparse_dp.c -o libsparse_dp.so
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#ifdef _OPENMP
#include <omp.h>
#endif

#define KEYMASK ((1ULL << 56) - 1)
#define VAL(x) ((int)((x) >> 56))
#define QW 720720LL            // the lookahead weights are multiples of 1/QW

typedef struct {
    int ncls;                  // number of weight classes (0: no lookahead)
    const uint64_t *mask;      // slot mask of each class
    const int64_t *w;          // weight of each class, in units of 1/QW
    int64_t extra;             // constant part (target row still wholly ahead)
    uint64_t tmask;            // active target-1 rows: remaining parity = state ^ tmask
    int K;                     // total threshold
    int on;
} bound_t;

static inline int hbound(const bound_t *b, uint64_t key) {
    uint64_t u = key ^ b->tmask;
    int64_t tot = b->extra;
    for (int c = 0; c < b->ncls; c++) tot += b->w[c] * (int64_t)__builtin_popcountll(u & b->mask[c]);
    return (int)((tot + QW - 1) / QW);
}

static inline int keep(const bound_t *b, uint64_t key, int v) {
    return !b->on || v + hbound(b, key) <= b->K;
}

#define DB 12
#define NB (1 << DB)

// Sort x[0..m) by the low nbits bits; tmp has room for m entries.  Stable LSD radix sort, skipping digits on
// which all keys agree.
static void radix_sort(uint64_t *x, uint64_t *tmp, int64_t m, int nbits) {
    if (m < 2) return;
    if (m < 64) {                                   // insertion sort
        for (int64_t i = 1; i < m; i++) {
            uint64_t v = x[i], k = v & KEYMASK;
            int64_t j = i - 1;
            while (j >= 0 && (x[j] & KEYMASK) > k) { x[j + 1] = x[j]; j--; }
            x[j + 1] = v;
        }
        return;
    }
    uint64_t *src = x, *dst = tmp;
    int64_t *cnt = (int64_t *)malloc(sizeof(int64_t) * NB);
    for (int shift = 0; shift < nbits; shift += DB) {
        int bits = nbits - shift < DB ? nbits - shift : DB;
        uint64_t dm = (1ULL << bits) - 1;
        memset(cnt, 0, sizeof(int64_t) * NB);
        for (int64_t i = 0; i < m; i++) cnt[(src[i] >> shift) & dm]++;
        int64_t first = (int64_t)((src[0] >> shift) & dm);
        if (cnt[first] == m) continue;              // every key has this digit: nothing to do
        int64_t s = 0;
        for (int64_t d = 0; d <= (int64_t)dm; d++) { int64_t c = cnt[d]; cnt[d] = s; s += c; }
        for (int64_t i = 0; i < m; i++) { uint64_t v = src[i]; dst[cnt[(v >> shift) & dm]++] = v; }
        uint64_t *t = src; src = dst; dst = t;
    }
    free(cnt);
    if (src != x) memcpy(x, src, sizeof(uint64_t) * (size_t)m);
}

static bound_t make_bound(int ncls, const uint64_t *mask, const int64_t *w, int64_t extra, uint64_t tmask, int K,
                          int on) {
    bound_t b = {ncls, mask, w, extra, tmask, K, on};
    return b;
}

// Reorder x[0..m), sorted by key k, into the order of k ^ upd.  For each set bit b of upd, from the highest: the
// elements agreeing on the bits above b form runs (contiguous, and sorted by the lower bits); in each run the
// part with bit b set moves in front of the part with bit b clear.  One pass per bit of upd; keys unchanged.
static void xor_reorder(uint64_t *x, uint64_t *tmp, int64_t m, uint64_t upd) {
    uint64_t *src = x, *dst = tmp;
    for (int b = 63; b >= 0; b--) {
        if (!((upd >> b) & 1)) continue;
        uint64_t bit = 1ULL << b;
        int64_t i = 0;
        while (i < m) {
            uint64_t hi = (src[i] & KEYMASK) >> b >> 1;
            int64_t j = i, split = -1;
            while (j < m && ((src[j] & KEYMASK) >> b >> 1) == hi) {
                if (split < 0 && (src[j] & bit)) split = j;
                j++;
            }
            if (split < 0 || split == i) {                     // one part only: unchanged
                memcpy(dst + i, src + i, sizeof(uint64_t) * (size_t)(j - i));
            } else {
                int64_t n1 = j - split;
                memcpy(dst + i, src + split, sizeof(uint64_t) * (size_t)n1);
                memcpy(dst + i + n1, src + i, sizeof(uint64_t) * (size_t)(split - i));
            }
            i = j;
        }
        uint64_t *t = src; src = dst; dst = t;
    }
    if (src != x) memcpy(x, src, sizeof(uint64_t) * (size_t)m);
}

// Step 1+2: candidates of a[0..n) into cand (room for n), sorted.  Returns their number.  sort: 0 radix sort,
// 1 xor_reorder (the candidates are the sorted sources XOR upd, then filtered: a subsequence of that order).
int64_t sp_candidates(const uint64_t *a, int64_t n, uint64_t upd, uint64_t sel_mask, uint64_t sel_bits, int cap,
                      int ncls, const uint64_t *mask, const int64_t *w, int64_t extra, uint64_t tmask, int K,
                      int use_h, int nbits, uint64_t *cand, uint64_t *tmp, int sort) {
    if (!upd) return 0;
    bound_t b = make_bound(ncls, mask, w, extra, tmask, K, use_h);
    uint64_t clr = ~sel_mask & KEYMASK;
    int64_t m = 0;
    if (sort) {
        // keep the source keys (sorted), reorder them by k ^ upd, then apply the XOR, filters and the bound
        for (int64_t i = 0; i < n; i++) {
            uint64_t x = a[i];
            if (VAL(x) >= cap) continue;
            uint64_t t = (x & KEYMASK) ^ upd;
            if ((t & sel_mask) != sel_bits) continue;
            cand[m++] = x;
        }
        xor_reorder(cand, tmp, m, upd);
        int64_t k = 0;
        for (int64_t i = 0; i < m; i++) {
            uint64_t x = cand[i];
            int v = VAL(x) + 1;
            uint64_t t = ((x & KEYMASK) ^ upd) & clr;
            if (!keep(&b, t, v)) continue;
            cand[k++] = t | ((uint64_t)v << 56);
        }
        return k;
    }
    for (int64_t i = 0; i < n; i++) {
        uint64_t x = a[i];
        int v = VAL(x);
        if (v >= cap) continue;
        uint64_t t = (x & KEYMASK) ^ upd;
        if ((t & sel_mask) != sel_bits) continue;
        t &= clr;
        if (!keep(&b, t, v + 1)) continue;
        cand[m++] = t | ((uint64_t)(v + 1) << 56);
    }
    radix_sort(cand, tmp, m, nbits);
    return m;
}

// Step 3: merge a[0..n) (filtered by the closing rows, cleared, re-bounded, values > cap dropped) with the sorted
// candidates.  out needs room for n + m, ch (may be NULL) for m.  States with value >= keep_below (if > 0) go to
// ch only.  Returns the size of out; *nch = number of changed states.
int64_t sp_merge(const uint64_t *a, int64_t n, const uint64_t *cand, int64_t m, uint64_t sel_mask,
                 uint64_t sel_bits, int cap, int keep_below, int ncls, const uint64_t *mask, const int64_t *w,
                 int64_t extra, uint64_t tmask, int K, int use_h, uint64_t *out, uint64_t *ch, int64_t *nch) {
    bound_t b = make_bound(ncls, mask, w, extra, tmask, K, use_h);
    uint64_t clr = ~sel_mask & KEYMASK;
    int64_t i = 0, j = 0, no = 0, nc = 0;
    int kb = keep_below > 0 ? keep_below : 1 << 30;
    if (cap + 1 < kb) kb = cap + 1;                                    // old states above the cap leave too
    uint64_t ka = 0;
    int va = 0, have = 0;
    for (;;) {
        while (!have && i < n) {
            uint64_t x = a[i++];
            uint64_t k = x & KEYMASK;
            if ((k & sel_mask) == sel_bits) { ka = k & clr; va = VAL(x); have = 1; }
        }
        if (!have && j >= m) break;
        if (have && (j >= m || ka < (cand[j] & KEYMASK))) {           // old state only
            if (va < kb && keep(&b, ka, va)) out[no++] = ka | ((uint64_t)va << 56);
            have = 0;
        } else {
            uint64_t c = cand[j++];
            uint64_t kc = c & KEYMASK;
            int vc = VAL(c);
            if (have && ka == kc) {                                    // both: keep the smaller value
                have = 0;
                if (vc < va) {
                    if (ch) ch[nc++] = c;
                    if (vc < kb) out[no++] = c;                         // (candidates passed the bound)
                } else if (va < kb && keep(&b, ka, va)) {
                    out[no++] = ka | ((uint64_t)va << 56);
                }
            } else {                                                   // new state
                if (ch) ch[nc++] = c;
                if (vc < kb) out[no++] = c;
            }
        }
    }
    if (nch) *nch = nc;
    return no;
}

// Join the changed forward states f[0..nf) (sorted by key) with a backward table bt[0..nb) (sorted): the least
// value(f) + value(b) over pairs with key(b) = key(f) ^ tmask.  tmask has at most one bit.  Returns the least
// total (or -1) and the forward / backward packed states attaining it.
int sp_join(const uint64_t *f, int64_t nf, const uint64_t *bt, int64_t nb, uint64_t tmask, uint64_t *fbest,
            uint64_t *bbest) {
    int best = -1;
    if (!nf || !nb) return -1;
    // f split by the bit of tmask: each part stays sorted after the XOR
    for (int part = 0; part < (tmask ? 2 : 1); part++) {
        int64_t p = 0;
        for (int64_t i = 0; i < nf; i++) {
            uint64_t k = f[i] & KEYMASK;
            if (tmask && (((k & tmask) != 0) != part)) continue;
            uint64_t q = k ^ tmask;
            // advance p to the first backward key >= q (galloping)
            if (p < nb && (bt[p] & KEYMASK) < q) {
                int64_t step = 1, lo = p, hi;
                while (lo + step < nb && (bt[lo + step] & KEYMASK) < q) { lo += step; step <<= 1; }
                hi = lo + step < nb ? lo + step : nb;      // bt[hi] >= q or hi == nb; bt[lo] < q
                while (hi - lo > 1) {
                    int64_t mid = (lo + hi) >> 1;
                    if ((bt[mid] & KEYMASK) < q) lo = mid; else hi = mid;
                }
                p = hi;
            }
            if (p < nb && (bt[p] & KEYMASK) == q) {
                int tot = VAL(f[i]) + VAL(bt[p]);
                if (best < 0 || tot < best) { best = tot; *fbest = f[i]; *bbest = bt[p]; }
            }
        }
    }
    return best;
}

// Number of states of each value (hist[0..256)).
void sp_hist(const uint64_t *a, int64_t n, int64_t *hist) {
    memset(hist, 0, sizeof(int64_t) * 256);
    for (int64_t i = 0; i < n; i++) hist[VAL(a[i])]++;
}

int sp_num_threads(void) {
#ifdef _OPENMP
    return omp_get_max_threads();
#else
    return 1;
#endif
}
