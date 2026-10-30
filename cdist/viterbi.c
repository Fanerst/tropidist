// Dense min-plus sweep over a syndrome trellis (linear Rank DP, tropical semiring).
// Table entry T[s] = minimum number of faults among processed columns whose
// partial parities on the active rows equal s.  INF = 255.  Every addition
// saturates at INF, so each entry is min(true value, 255): exact below 255;
// kernel.py rejects a final 255 of a feasible query (a cost of at least 255).
//
// Build: cc -O3 -march=native -fopenmp -shared -fPIC viterbi.c -o libviterbi.so
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#ifdef _OPENMP
#include <omp.h>
#endif
#if defined(__AVX2__)
#include <immintrin.h>
#endif

#define INF 255

static inline uint8_t inc(uint8_t v) { return (uint8_t)(v + (v != INF)); }

// x[i] <- min(x[i], y[i]+1), y[i] <- min(y[i], x[i]+1) on two disjoint runs.
static inline void relax_run(uint8_t *restrict x, uint8_t *restrict y, uint64_t len) {
    for (uint64_t i = 0; i < len; i++) {
        uint8_t a = x[i], b = y[i];
        uint8_t a1 = inc(a), b1 = inc(b);
        x[i] = a < b1 ? a : b1;
        y[i] = b < a1 ? b : a1;
    }
}

// Same with y indexed through a fixed permutation of a 64-entry block.
static inline void relax_perm64(uint8_t *x, uint8_t *y, const uint8_t *perm) {
#if defined(__AVX2__)
    // perm[i] = i ^ m with m < 64: bits 0-3 permute inside a 16-byte lane,
    // bit 4 swaps lanes, bit 5 swaps the two 32-byte halves.
    unsigned m = perm[0];
    __m256i idx = _mm256_setr_epi8(0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,
                                   0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15);
    __m256i shuf = _mm256_xor_si256(idx, _mm256_set1_epi8((char)(m & 15)));
    __m256i y0 = _mm256_loadu_si256((const __m256i *)y);
    __m256i y1 = _mm256_loadu_si256((const __m256i *)(y + 32));
    __m256i x0 = _mm256_loadu_si256((const __m256i *)x);
    __m256i x1 = _mm256_loadu_si256((const __m256i *)(x + 32));
    if (m & 32) { __m256i t = x0; x0 = x1; x1 = t; }
    if (m & 16) { x0 = _mm256_permute2x128_si256(x0, x0, 1); x1 = _mm256_permute2x128_si256(x1, x1, 1); }
    x0 = _mm256_shuffle_epi8(x0, shuf);   // x0[k] now pairs with y0[k]
    x1 = _mm256_shuffle_epi8(x1, shuf);
    __m256i one = _mm256_set1_epi8(1);
    __m256i nx0 = _mm256_min_epu8(x0, _mm256_adds_epu8(y0, one));
    __m256i nx1 = _mm256_min_epu8(x1, _mm256_adds_epu8(y1, one));
    __m256i ny0 = _mm256_min_epu8(y0, _mm256_adds_epu8(x0, one));
    __m256i ny1 = _mm256_min_epu8(y1, _mm256_adds_epu8(x1, one));
    _mm256_storeu_si256((__m256i *)y, ny0);
    _mm256_storeu_si256((__m256i *)(y + 32), ny1);
    nx0 = _mm256_shuffle_epi8(nx0, shuf);  // the shuffle is an involution
    nx1 = _mm256_shuffle_epi8(nx1, shuf);
    if (m & 16) { nx0 = _mm256_permute2x128_si256(nx0, nx0, 1); nx1 = _mm256_permute2x128_si256(nx1, nx1, 1); }
    if (m & 32) { __m256i t = nx0; nx0 = nx1; nx1 = t; }
    _mm256_storeu_si256((__m256i *)x, nx0);
    _mm256_storeu_si256((__m256i *)(x + 32), nx1);
#else
    for (int i = 0; i < 64; i++) {
        uint8_t a = x[perm[i]], b = y[i];
        uint8_t a1 = inc(a), b1 = inc(b);
        x[perm[i]] = a < b1 ? a : b1;
        y[i] = b < a1 ? b : a1;
    }
#endif
}

// T[s] <- min(T[s], T[s ^ h] + 1) for all s, in place.  n = table size.
void dp_update(uint8_t *T, uint64_t n, uint64_t h) {
    if (h == 0 || n < 2) return;
    int hb = 63 - __builtin_clzll(h);
    uint64_t half = 1ULL << hb;          // pairs: s (bit hb = 0)  <->  (s ^ hl) + half
    uint64_t hl = h ^ half;
    if (n >= 128 && hb >= 6) {
        uint64_t hl_hi = hl & ~63ULL;
        unsigned m = (unsigned)(hl & 63);
        uint8_t perm[64];
        for (int i = 0; i < 64; i++) perm[i] = (uint8_t)(i ^ m);
        uint64_t nblk = n >> 6;          // 64-entry blocks
        uint64_t hbb = half >> 6;
        #pragma omp parallel for schedule(static)
        for (uint64_t blk = 0; blk < nblk; blk++) {
            if (blk & hbb) continue;
            uint8_t *x = T + (blk << 6);
            uint8_t *y = T + (((blk << 6) ^ hl_hi) | half);
            if (m == 0) relax_run(x, y, 64);
            else relax_perm64(x, y, perm);   // y[i] pairs with x[i ^ m]
        }
    } else if (n >= 128) {
        // h lies inside the low 6 bits: pairs stay inside one 64-entry block
        uint64_t nblk = n >> 6;
        #pragma omp parallel for schedule(static)
        for (uint64_t blk = 0; blk < nblk; blk++) {
            uint8_t *B = T + (blk << 6);
            for (unsigned s = 0; s < 64; s++) {
                if (s & half) continue;
                unsigned t = s ^ (unsigned)h;
                uint8_t a = B[s], b = B[t];
                uint8_t a1 = inc(a), b1 = inc(b);
                B[s] = a < b1 ? a : b1;
                B[t] = b < a1 ? b : a1;
            }
        }
    } else {
        for (uint64_t s = 0; s < n; s++) {
            if (s & half) continue;
            uint64_t t = s ^ h;
            uint8_t a = T[s], b = T[t];
            uint8_t a1 = inc(a), b1 = inc(b);
            T[s] = a < b1 ? a : b1;
            T[t] = b < a1 ? b : a1;
        }
    }
}

// New top bit that the current column flips: T[n + (s ^ hl)] = T[s] + 1.
// The lower half is unchanged.  The buffer must hold 2n entries.
void dp_expand_update(uint8_t *T, uint64_t n, uint64_t hl) {
    uint8_t *U = T + n;
    if (n >= 64) {
        uint64_t hl_hi = hl & ~63ULL;
        unsigned m = (unsigned)(hl & 63);
        uint64_t nblk = n >> 6;
        #pragma omp parallel for schedule(static)
        for (uint64_t blk = 0; blk < nblk; blk++) {
            const uint8_t *x = T + (blk << 6);
            uint8_t *y = U + ((blk << 6) ^ hl_hi);
            if (m == 0) for (int i = 0; i < 64; i++) y[i] = inc(x[i]);
            else for (int i = 0; i < 64; i++) y[i ^ m] = inc(x[i]);
        }
    } else {
        for (uint64_t s = 0; s < n; s++) U[s ^ hl] = inc(T[s]);
    }
}

// Copy between non-overlapping regions, in parallel for large lengths.
static void par_copy(uint8_t *dst, const uint8_t *src, uint64_t len) {
    const uint64_t chunk = 1ULL << 20;
    if (len <= 4 * chunk) { memcpy(dst, src, len); return; }
    #pragma omp parallel for schedule(static)
    for (uint64_t o = 0; o < len; o += chunk)
        memcpy(dst + o, src + o, (len - o < chunk) ? (len - o) : chunk);
}

// Keep the states whose bit `pos` equals `target`, dropping that bit.
// In place; returns the new size n/2.
// Output block k comes from input block 2k+target (blocks of 2^pos entries).
// For k in [a, 2a) the writes lie below block 2a and the reads at or above
// it, so each such phase is free of conflicts and later phases still read
// untouched data.
uint64_t dp_select(uint8_t *T, uint64_t n, int pos, int target) {
    uint64_t blk = 1ULL << pos;
    uint64_t nb = n >> (pos + 1);
    if (nb == 0) return n;
    if (target) par_copy(T, T + blk, blk);
    if (blk >= (1ULL << 22)) {
        for (uint64_t k = 1; k < nb; k++)
            par_copy(T + k * blk, T + (2 * k + (uint64_t)target) * blk, blk);
    } else {
        for (uint64_t a = 1; a < nb; a <<= 1) {
            uint64_t hi = (2 * a < nb) ? 2 * a : nb;
            #pragma omp parallel for schedule(static) if (hi - a > 64)
            for (uint64_t k = a; k < hi; k++)
                memcpy(T + k * blk, T + (2 * k + (uint64_t)target) * blk, blk);
        }
    }
    return n >> 1;
}

void dp_fill(uint8_t *T, uint64_t n, uint8_t v) {
    uint64_t chunk = 1ULL << 22;
    if (n <= chunk) { memset(T, v, n); return; }
    #pragma omp parallel for schedule(static)
    for (uint64_t o = 0; o < n; o += chunk) memset(T + o, v, (n - o < chunk) ? (n - o) : chunk);
}

// Histogram of table values (for diagnostics): hist[v] = #states with cost v.
void dp_hist(const uint8_t *T, uint64_t n, uint64_t *hist) {
    for (int v = 0; v < 256; v++) hist[v] = 0;
    #pragma omp parallel
    {
        uint64_t loc[256];
        for (int v = 0; v < 256; v++) loc[v] = 0;
        #pragma omp for schedule(static) nowait
        for (uint64_t s = 0; s < n; s++) loc[T[s]]++;
        #pragma omp critical
        for (int v = 0; v < 256; v++) hist[v] += loc[v];
    }
}

int dp_num_threads(void) {
#ifdef _OPENMP
    return omp_get_max_threads();
#else
    return 1;
#endif
}

// Weighted variant: T[s] <- min(T[s], T[s ^ h] + w), saturating at INF.
void dp_update_w(uint8_t *T, uint64_t n, uint64_t h, int w) {
    if (h == 0 || n < 2) return;
    int hb = 63 - __builtin_clzll(h);
    uint64_t half = 1ULL << hb;
    #pragma omp parallel for schedule(static) if (n >= (1ULL << 16))
    for (uint64_t s = 0; s < n; s++) {
        if (s & half) continue;
        uint64_t t = s ^ h;
        unsigned a = T[s], b = T[t];
        unsigned a1 = a + (unsigned)w, b1 = b + (unsigned)w;
        if (a1 > INF) a1 = INF;
        if (b1 > INF) b1 = INF;
        T[s] = (uint8_t)(a < b1 ? a : b1);
        T[t] = (uint8_t)(b < a1 ? b : a1);
    }
}
