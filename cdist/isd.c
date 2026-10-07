// Randomised information-set search for low-weight undetected logical fault
// sets (upper bounds only).
//
// The matrix H (rows = checks, columns = faults) is kept in reduced row echelon
// form for a random set of pivot columns.  For every non-pivot column j the
// vector {j} + {pivot columns of the rows containing j} has zero syndrome; its
// weight is 1 + (number of rows containing j).  Each step swaps a few pivot /
// non-pivot columns at random and scans all non-pivot columns for a vector of
// weight below the current best whose logical label is nonzero.
//
// Nothing found proves nothing; anything found is a genuine solution and is
// re-verified by the caller.
//
// Build: cc -O3 -march=native -fopenmp -shared -fPIC isd.c -o libisd.so
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _OPENMP
#include <omp.h>
#endif

#define PLANES 7           // counts up to 127

static inline uint64_t rng_next(uint64_t *s) {     // xorshift64*
    uint64_t x = *s;
    x ^= x >> 12; x ^= x << 25; x ^= x >> 27;
    *s = x;
    return x * 0x2545F4914F6CDD1DULL;
}

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + 1e-9 * ts.tv_nsec;
}

// rows: m x wc words (bit j of row i = H[i][j]); lg: n x wl words.
// Returns the best weight found (<= start_best - 1) or -1.
// best_cols must hold m + 1 ints.
int isd_search(int m, int n, int wc, int wl, const uint64_t *rows_in, const uint64_t *lg,
               int start_best, int stop_at, int swaps_per_step, double time_limit, uint64_t seed,
               int *best_cols, int64_t *steps_out) {
    volatile int best = start_best;
    int found = -1;
    double deadline = now_sec() + time_limit;
    int64_t total_steps = 0;
    #pragma omp parallel
    {
        int tid = 0;
#ifdef _OPENMP
        tid = omp_get_thread_num();
#endif
        uint64_t rs = seed * 0x9E3779B97F4A7C15ULL + 0x1234567ULL * (uint64_t)(tid + 1);
        if (rs == 0) rs = 88172645463325252ULL;
        for (int i = 0; i < 20; i++) rng_next(&rs);
        uint64_t *R = (uint64_t *)malloc((size_t)m * wc * sizeof(uint64_t));
        memcpy(R, rows_in, (size_t)m * wc * sizeof(uint64_t));
        int *piv = (int *)malloc(m * sizeof(int));
        uint64_t *pivmask = (uint64_t *)calloc(wc, sizeof(uint64_t));
        uint64_t *pl = (uint64_t *)malloc((size_t)(PLANES + 1) * wc * sizeof(uint64_t));
        uint64_t *lv = (uint64_t *)malloc(wl * sizeof(uint64_t));
        int *perm = (int *)malloc(n * sizeof(int));
        int *cols = (int *)malloc((m + 1) * sizeof(int));
        // initial elimination in a random column order
        for (int j = 0; j < n; j++) perm[j] = j;
        for (int j = n - 1; j > 0; j--) {
            int k = (int)(rng_next(&rs) % (uint64_t)(j + 1));
            int t = perm[j]; perm[j] = perm[k]; perm[k] = t;
        }
        int r = 0;
        for (int q = 0; q < n && r < m; q++) {
            int j = perm[q];
            int w = j >> 6; uint64_t b = 1ULL << (j & 63);
            int p = -1;
            for (int i = r; i < m; i++) if (R[(size_t)i * wc + w] & b) { p = i; break; }
            if (p < 0) continue;
            if (p != r) for (int x = 0; x < wc; x++) {
                uint64_t t = R[(size_t)p * wc + x]; R[(size_t)p * wc + x] = R[(size_t)r * wc + x]; R[(size_t)r * wc + x] = t;
            }
            for (int i = 0; i < m; i++) if (i != r && (R[(size_t)i * wc + w] & b))
                for (int x = 0; x < wc; x++) R[(size_t)i * wc + x] ^= R[(size_t)r * wc + x];
            piv[r] = j; pivmask[w] |= b; r++;
        }
        int rank = r;       // rows rank..m-1 are zero
        int64_t steps = 0;
        while (best > stop_at) {
            if ((steps & 63) == 0 && now_sec() > deadline) break;
            steps++;
            // a few random pivot exchanges
            for (int sIdx = 0; sIdx < swaps_per_step; sIdx++) {
                int i = (int)(rng_next(&rs) % (uint64_t)rank);
                uint64_t *ri = R + (size_t)i * wc;
                int w0 = (int)(rng_next(&rs) % (uint64_t)wc);
                int j = -1;
                for (int x = 0; x < wc; x++) {
                    int w = (w0 + x) % wc;
                    uint64_t cand = ri[w] & ~pivmask[w];
                    if (cand) {
                        // random set bit of cand
                        int cnt = __builtin_popcountll(cand);
                        int pick = (int)(rng_next(&rs) % (uint64_t)cnt);
                        while (pick--) cand &= cand - 1;
                        j = w * 64 + __builtin_ctzll(cand);
                        break;
                    }
                }
                if (j < 0) continue;
                int w = j >> 6; uint64_t b = 1ULL << (j & 63);
                for (int k = 0; k < rank; k++) if (k != i && (R[(size_t)k * wc + w] & b)) {
                    uint64_t *rk = R + (size_t)k * wc;
                    for (int x = 0; x < wc; x++) rk[x] ^= ri[x];
                }
                int old = piv[i];
                pivmask[old >> 6] &= ~(1ULL << (old & 63));
                pivmask[w] |= b;
                piv[i] = j;
            }
            // column counts by bit-sliced addition; plane PLANES = overflow
            int thr = best - 2;                 // need 1 + count <= best - 1
            if (thr > (1 << PLANES) - 1) thr = (1 << PLANES) - 1;
            for (int x = 0; x < wc; x++) {
                uint64_t p_[PLANES + 1];
                for (int q = 0; q <= PLANES; q++) p_[q] = 0;
                for (int k = 0; k < rank; k++) {
                    uint64_t carry = R[(size_t)k * wc + x];
                    for (int q = 0; q < PLANES && carry; q++) {
                        uint64_t t = p_[q] & carry;
                        p_[q] ^= carry;
                        carry = t;
                    }
                    p_[PLANES] |= carry;
                }
                // candidates: count <= thr, not overflowed, not a pivot column
                uint64_t lt = 0, eq = ~0ULL;
                for (int q = PLANES - 1; q >= 0; q--) {
                    if ((thr >> q) & 1) { lt |= eq & ~p_[q]; eq &= p_[q]; }
                    else eq &= ~p_[q];
                }
                uint64_t cand = (lt | eq) & ~p_[PLANES] & ~pivmask[x];
                if (x == wc - 1 && (n & 63)) cand &= (1ULL << (n & 63)) - 1;
                while (cand) {
                    int j = x * 64 + __builtin_ctzll(cand);
                    cand &= cand - 1;
                    uint64_t b = 1ULL << (j & 63);
                    int wgt = 0;
                    for (int q = 0; q < wl; q++) lv[q] = lg[(size_t)j * wl + q];
                    cols[wgt++] = j;
                    for (int k = 0; k < rank; k++) if (R[(size_t)k * wc + x] & b) {
                        cols[wgt++] = piv[k];
                        for (int q = 0; q < wl; q++) lv[q] ^= lg[(size_t)piv[k] * wl + q];
                    }
                    int nz = 0;
                    for (int q = 0; q < wl; q++) nz |= (lv[q] != 0);
                    if (!nz) continue;
                    #pragma omp critical(isd_best)
                    {
                        if (wgt < best) {
                            best = wgt;
                            found = wgt;
                            for (int q = 0; q < wgt; q++) best_cols[q] = cols[q];
                        }
                    }
                }
            }
        }
        #pragma omp atomic
        total_steps += steps;
        free(R); free(piv); free(pivmask); free(pl); free(lv); free(perm); free(cols);
    }
    *steps_out = total_steps;
    return found;
}

int isd_num_threads(void) {
#ifdef _OPENMP
    return omp_get_max_threads();
#else
    return 1;
#endif
}
