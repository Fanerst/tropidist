// Weight-bounded exact search for  H e = 0, L e != 0  (sparse min-plus mode).
//
// A minimum solution S is enumerated through a canonical prefix A: start from
// an anchor column, then repeatedly pick an unsatisfied row (the one with the
// fewest available columns) and branch over the columns of S touching it;
// earlier siblings become forbidden, so every solution has exactly one
// canonical order per anchor.  When the remaining budget R = K - |A| drops to
// the table size k, the rest B = S \ A is found by one lookup in a table of
// all column subsets of size <= k keyed by syndrome (meet in the middle).
//
// The same lookup against the table of a *relaxed* problem (e.g. the
// time-collapsed one) is an admissible pruning test: if the relaxed residual
// cannot be cancelled within the budget, neither can the true one.
//
// Syndromes are identified by 128-bit XOR-linear hashes.  A hash collision can
// only create a spurious hit, never hide a solution, and every hit is
// re-derived explicitly before it is reported.
//
// Build: cc -O3 -march=native -fopenmp -shared -fPIC gmitm.c -o libgmitm.so
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/mman.h>
#ifdef _OPENMP
#include <omp.h>
#endif

#define WMAX 256     // syndrome words (rows <= 16384)
#define DMAX 40      // search depth
#define TMAX 4       // lookup tables per search
#define LEAF_MAX 1024 // candidates handled by the leaf fast path

// ------------------------------------------------------------------ tables
typedef struct {
    uint64_t mask;      // slots - 1
    uint64_t *key;      // 0 = empty.  compact: bit 63 set, bits 16..62 fingerprint, bits 0..15 logical
                        //             wide:    bit 63 set, bits 0..62 fingerprint; logical label in lgs[]
    uint64_t *lgs;      // wide tables only (more than 16 observables): full logical label per slot
    uint8_t *cost;      // 255 = slot not yet published
    int64_t count;
    int k;
} Table;

static inline uint64_t mk_key(uint64_t zl, uint64_t lg) {
    return (zl & 0x7FFFFFFFFFFF0000ULL) | (lg & 0xFFFF) | (1ULL << 63);
}

static void *big_alloc(size_t bytes) {
    void *p = NULL;
    size_t align = bytes >= (1UL << 21) ? (1UL << 21) : 64;
    size_t sz = (bytes + align - 1) / align * align;
    if (posix_memalign(&p, align, sz) != 0) return NULL;
#ifdef MADV_HUGEPAGE
    if (align > 64) madvise(p, sz, MADV_HUGEPAGE);
#endif
    return p;
}

void *tab_create(int log2slots, int wide) {
    Table *t = (Table *)calloc(1, sizeof(Table));
    uint64_t n = 1ULL << log2slots;
    t->mask = n - 1;
    // large tables are probed at random: back them with huge pages if possible
    t->key = (uint64_t *)big_alloc(n * sizeof(uint64_t));
    t->cost = (uint8_t *)big_alloc(n);
    if (!t->key || !t->cost) { free(t->key); free(t->cost); free(t); return NULL; }
    if (wide) {
        t->lgs = (uint64_t *)big_alloc(n * sizeof(uint64_t));
        if (!t->lgs) { free(t->key); free(t->cost); free(t); return NULL; }
    }
    #pragma omp parallel for schedule(static)
    for (uint64_t i = 0; i < n; i++) { t->key[i] = 0; t->cost[i] = 255; if (wide) t->lgs[i] = 0; }
    return t;
}

void tab_free(void *p) {
    Table *t = (Table *)p;
    if (!t) return;
    free(t->key); free(t->cost); free(t->lgs); free(t);
}

int64_t tab_count(void *p) { return ((Table *)p)->count; }

static inline void cost_min(Table *t, uint64_t i, uint8_t cost) {
    uint8_t old = t->cost[i];
    while (cost < old) {
        if (__sync_bool_compare_and_swap(&t->cost[i], old, cost)) break;
        old = t->cost[i];
    }
}

static inline void tab_insert(Table *t, uint64_t zh, uint64_t zl, uint64_t lg, uint8_t cost) {
    uint64_t i = zh & t->mask;
    if (!t->lgs) {
        uint64_t key = mk_key(zl, lg);
        for (;;) {
            uint64_t cur = t->key[i];
            if (cur == 0) {
                if (__sync_bool_compare_and_swap(&t->key[i], 0ULL, key)) {
                    __sync_fetch_and_add(&t->count, 1);
                    cur = key;
                } else {
                    cur = t->key[i];
                }
            }
            if (cur == key) { cost_min(t, i, cost); return; }
            i = (i + 1) & t->mask;
        }
    }
    // wide: several slots may carry the same syndrome fingerprint with
    // different logical labels.  The owner of a slot writes the label before
    // it publishes a cost, so a slot whose cost is still 255 is not yet readable.
    uint64_t key = zl | (1ULL << 63);
    for (;;) {
        uint64_t cur = t->key[i];
        if (cur == 0) {
            if (__sync_bool_compare_and_swap(&t->key[i], 0ULL, key)) {
                __sync_fetch_and_add(&t->count, 1);
                t->lgs[i] = lg;
                __sync_synchronize();
                cost_min(t, i, cost);
                return;
            }
            cur = t->key[i];
        }
        if (cur == key) {
            while (t->cost[i] == 255) { __sync_synchronize(); }
            if (t->lgs[i] == lg) { cost_min(t, i, cost); return; }
        }
        i = (i + 1) & t->mask;
    }
}

// Smallest cost of an entry with this syndrome hash, cost <= R and logical
// different from lg; -1 if none.
static inline int tab_lookup(const Table *t, uint64_t zh, uint64_t zl, uint64_t lg, int R) {
    uint64_t i = zh & t->mask;
    int best = -1;
    if (!t->lgs) {
        uint64_t fp = zl & 0x7FFFFFFFFFFF0000ULL;
        for (;;) {
            uint64_t cur = t->key[i];
            if (cur == 0) return best;
            if ((cur & 0x7FFFFFFFFFFF0000ULL) == fp && (cur & 0xFFFF) != (lg & 0xFFFF)) {
                int c = t->cost[i];
                if (c <= R && (best < 0 || c < best)) best = c;
            }
            i = (i + 1) & t->mask;
        }
    }
    uint64_t key = zl | (1ULL << 63);
    for (;;) {
        uint64_t cur = t->key[i];
        if (cur == 0) return best;
        if (cur == key && t->lgs[i] != lg) {
            int c = t->cost[i];
            if (c <= R && (best < 0 || c < best)) best = c;
        }
        i = (i + 1) & t->mask;
    }
}

static void build_rec(Table *t, int n, const uint64_t *zh, const uint64_t *zl, const uint64_t *lg,
                      int k, int start, int depth, uint64_t h, uint64_t l, uint64_t g) {
    for (int j = start; j < n; j++) {
        uint64_t h2 = h ^ zh[j], l2 = l ^ zl[j];
        uint64_t g2 = g ^ lg[j];
        tab_insert(t, h2, l2, g2, (uint8_t)(depth + 1));
        if (depth + 1 < k) build_rec(t, n, zh, zl, lg, k, j + 1, depth + 1, h2, l2, g2);
    }
}

// Insert every subset of size 0..k of the n columns.
void tab_build(void *p, int n, const uint64_t *zh, const uint64_t *zl, const uint64_t *lg, int k) {
    Table *t = (Table *)p;
    t->k = k;
    tab_insert(t, 0, 0, 0, 0);
    if (k < 1) return;
    #pragma omp parallel for schedule(dynamic, 1)
    for (int j = 0; j < n; j++) {
        tab_insert(t, zh[j], zl[j], lg[j], 1);
        if (k > 1) build_rec(t, n, zh, zl, lg, k, j + 1, 1, zh[j], zl[j], lg[j]);
    }
}

// ------------------------------------------------------------------ search
typedef struct {
    int W, N, M, wmax;
    const uint64_t *col;         // N*W
    const uint64_t *lg;          // N
    const int *row_start, *row_cols;
    const int *col_start, *col_rows;
    int ntab;
    const Table *tab[TMAX];
    const uint64_t *tzh[TMAX], *tzl[TMAX];
    int main_tab;                // index of the exact table (hit = solution), or -1
    const int *rank;             // anchor rank per column
    const int *ex_start, *ex_cols;   // per column: columns that cannot join it in a minimum solution
    // optional pattern budget: each column belongs to a class (-1: none); a
    // solution may use one column from each "on-pattern" class for free and at
    // most `slack` further columns
    const int *cls;
    const uint8_t *onpat;
    int nclass, slack;
    // optional kernel dominance: zero-syndrome, zero-logical column sets s.
    // A minimum solution e has |e & s| <= |s|/2 for each of them (otherwise
    // e ^ s is lighter), so once a prefix holds floor(|s|/2) columns of s the
    // rest of s is forbidden.  Pair exclusions are the case |s| = 3.
    int nks;
    const int *ks_start, *ks_cols;   // columns of each set
    const int *kc_start, *kc_ids;    // sets containing each column
    int cover;                   // covering bound at internal nodes
    int cover_ascent;
    // optional label-free mode (any number of observables): tables and states
    // carry no logical label, every syndrome match counts as a hit, and the
    // logical value of a complete zero-syndrome set is computed from full_lg
    const uint64_t *full_lg;     // N * lw words
    int lw;
    // covering bound data, in row_cols order: for W <= CB_W the column
    // syndromes (W words each), otherwise their rows padded to wmax with the
    // always-zero row W * 64
    const uint64_t *rc_bits;
    const int *rc_rows;
} Prob;

#define CB_W 8

static const int *g_cls = NULL;
static const uint8_t *g_onpat = NULL;
static int g_nclass = 0, g_slack = 0;
static int g_nks = 0;
static const int *g_ks_start = NULL, *g_ks_cols = NULL, *g_kc_start = NULL, *g_kc_ids = NULL;
static int g_kernel_mode = 0;    // 1: record zero-syndrome sets with zero logical instead of solutions
static const uint64_t *g_full_lg = NULL;
static int g_lw = 0;

void gm_set_full_labels(const uint64_t *lg, int lw) { g_full_lg = lg; g_lw = lw; }

void gm_set_kernel(int nks, const int *ks_start, const int *ks_cols, const int *kc_start, const int *kc_ids) {
    g_nks = nks; g_ks_start = ks_start; g_ks_cols = ks_cols; g_kc_start = kc_start; g_kc_ids = kc_ids;
}

void gm_set_kernel_mode(int on) { g_kernel_mode = on; }

static int g_cover = 0;        // 0: off; else test nodes with 4 |sigma| >= g_cover * R
static int g_cover_ascent = 0; // 1: improve the dual solution by one greedy ascent pass
void gm_set_cover(int gate4, int ascent) { g_cover = gate4; g_cover_ascent = ascent; }

void gm_set_pattern(const int *cls, const uint8_t *onpat, int nclass, int slack) {
    g_cls = cls; g_onpat = onpat; g_nclass = nclass; g_slack = slack;
}

typedef struct {
    uint64_t s[WMAX];
    uint64_t zh[TMAX], zl[TMAX];
    uint64_t lg;
} State;

typedef struct {
    const Prob *P;
    int K;
    int enum_all;
    int collect_depth;           // >0: stop at this depth and store the prefix
    State stack[DMAX + 2];
    int path[DMAX + 2];
    int pivot[DMAX + 2];
    uint8_t *forb;               // 0 free; d+1 = forbidden at depth d; 255 = forbidden by rank
    int *avail;                  // per row: free columns
    int64_t nodes[DMAX + 2];
    int64_t lookups, hits, false_hits, cover_pruned, ascent_pruned, cover_calls;
    double *cv_load;             // covering bound scratch: dual load per column
    int *cv_stamp;
    int cv_id;
    uint8_t *used;               // per class: pattern slot taken
    int extras;
    uint8_t *kcnt;               // per kernel set: columns of the prefix in it
    int how[DMAX + 2];
    // shared
    volatile int *stop;
    int *best;
    int sol_cap, sol_stride;
    int *sol_buf, *nsol;
    int *task_buf; int64_t *ntask; int64_t task_cap;
    double deadline;
    volatile int *timed_out;
} Ctx;

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + 1e-9 * ts.tv_nsec;
}

static inline int popcnt_state(const State *st, int W) {
    int c = 0;
    for (int w = 0; w < W; w++) c += __builtin_popcountll(st->s[w]);
    return c;
}

static inline void apply_col(const Prob *P, const State *a, State *b, int f) {
    const uint64_t *c = P->col + (size_t)f * P->W;
    for (int w = 0; w < P->W; w++) b->s[w] = a->s[w] ^ c[w];
    for (int t = 0; t < P->ntab; t++) {
        b->zh[t] = a->zh[t] ^ P->tzh[t][f];
        b->zl[t] = a->zl[t] ^ P->tzl[t][f];
    }
    b->lg = a->lg ^ P->lg[f];
}

static inline void forbid(Ctx *c, int f, uint8_t stamp) {
    const Prob *P = c->P;
    c->forb[f] = stamp;
    for (int i = P->col_start[f]; i < P->col_start[f + 1]; i++) c->avail[P->col_rows[i]]--;
}

static inline void unforbid(Ctx *c, int f) {
    const Prob *P = c->P;
    c->forb[f] = 0;
    for (int i = P->col_start[f]; i < P->col_start[f + 1]; i++) c->avail[P->col_rows[i]]++;
}

static inline int pat_ok(const Ctx *c, int f) {
    const Prob *P = c->P;
    if (!P->cls) return 1;
    int cl = P->cls[f];
    if (cl >= 0 && P->onpat[cl] && !c->used[cl]) return 1;
    return c->extras < P->slack;
}

// 0: over budget; 1: took the free slot of its class; 2: counted as an extra
static inline int pat_take(Ctx *c, int f) {
    const Prob *P = c->P;
    if (!P->cls) return 1;
    int cl = P->cls[f];
    if (cl >= 0 && P->onpat[cl] && !c->used[cl]) { c->used[cl] = 1; return 1; }
    if (c->extras >= P->slack) return 0;
    c->extras++;
    return 2;
}

static inline void pat_undo(Ctx *c, int f, int how) {
    const Prob *P = c->P;
    if (!P->cls) return;
    if (how == 1) c->used[P->cls[f]] = 0;
    else if (how == 2) c->extras--;
}

// Two columns whose sum is itself a column never occur together in a minimum
// solution (replace them by the sum).  Such partners of f are forbidden inside
// the subtree that contains f.
#define EX_STAMP 100
static inline void exclude_partners(Ctx *c, int f, int depth) {
    const Prob *P = c->P;
    if (!P->ex_start) return;
    uint8_t stamp = (uint8_t)(EX_STAMP + depth + 1);
    for (int i = P->ex_start[f]; i < P->ex_start[f + 1]; i++) {
        int g = P->ex_cols[i];
        if (c->forb[g] == 0) forbid(c, g, stamp);
    }
}

static inline void restore_partners(Ctx *c, int f, int depth) {
    const Prob *P = c->P;
    if (!P->ex_start) return;
    uint8_t stamp = (uint8_t)(EX_STAMP + depth + 1);
    for (int i = P->ex_start[f]; i < P->ex_start[f + 1]; i++) {
        int g = P->ex_cols[i];
        if (c->forb[g] == stamp) unforbid(c, g);
    }
}

#define KD_STAMP 150
static inline void kd_take(Ctx *c, int f, int depth) {
    const Prob *P = c->P;
    if (!P->nks) return;
    uint8_t stamp = (uint8_t)(KD_STAMP + depth + 1);
    for (int i = P->kc_start[f]; i < P->kc_start[f + 1]; i++) {
        int s = P->kc_ids[i];
        int sz = P->ks_start[s + 1] - P->ks_start[s];
        if (++c->kcnt[s] == sz / 2)
            for (int q = P->ks_start[s]; q < P->ks_start[s + 1]; q++) {
                int g = P->ks_cols[q];
                if (c->forb[g] == 0) forbid(c, g, stamp);
            }
    }
}

static inline void kd_undo(Ctx *c, int f, int depth) {
    const Prob *P = c->P;
    if (!P->nks) return;
    uint8_t stamp = (uint8_t)(KD_STAMP + depth + 1);
    for (int i = P->kc_start[f]; i < P->kc_start[f + 1]; i++) {
        int s = P->kc_ids[i];
        int sz = P->ks_start[s + 1] - P->ks_start[s];
        if (c->kcnt[s]-- == sz / 2)
            for (int q = P->ks_start[s]; q < P->ks_start[s + 1]; q++) {
                int g = P->ks_cols[q];
                if (c->forb[g] == stamp) unforbid(c, g);
            }
    }
}

// Is the logical value of the zero-syndrome set cols[0..a) nonzero?
static inline int sol_nonzero(const Prob *P, const State *st, const int *cols, int a) {
    if (!P->full_lg) return st->lg != 0;
    for (int w = 0; w < P->lw; w++) {
        uint64_t x = 0;
        for (int i = 0; i < a; i++) x ^= P->full_lg[(size_t)cols[i] * P->lw + w];
        if (x) return 1;
    }
    return 0;
}

static void record(Ctx *c, int weight, const int *cols) {
    #pragma omp critical(gm_record)
    {
        if (*c->best < 0 || weight < *c->best) *c->best = weight;
        if (*c->nsol < c->sol_cap) {
            int *dst = c->sol_buf + (size_t)(*c->nsol) * c->sol_stride;
            dst[0] = weight;
            for (int i = 0; i < weight && i + 1 < c->sol_stride; i++) dst[i + 1] = cols[i];
            (*c->nsol)++;
        }
    }
    if (!c->enum_all) *c->stop = 1;
}

// Enumerate sets B (|B| <= R) cancelling the syndrome of st with total logical != 0.
// cols[0..a) holds A; B is appended.  Columns of A are excluded, as are earlier
// siblings, so each B is produced once.  Returns the number of completions.
static int64_t complete(Ctx *c, const State *st, int a, int R, int *cols, uint8_t *tmpforb, int na0) {
    const Prob *P = c->P;
    int pc = popcnt_state(st, P->W);
    if (pc == 0) {
        if (sol_nonzero(P, st, cols, a) != g_kernel_mode) { record(c, a, cols); return 1; }
        return 0;
    }
    if (R <= 0 || pc > P->wmax * R) return 0;
    int r = -1;
    for (int w = 0; w < P->W && r < 0; w++)
        if (st->s[w]) r = w * 64 + __builtin_ctzll(st->s[w]);
    int64_t found = 0;
    int marked[4096];
    int nm = 0;
    State nx;
    for (int i = P->row_start[r]; i < P->row_start[r + 1]; i++) {
        int f = P->row_cols[i];
        if (tmpforb[f]) continue;
        apply_col(P, st, &nx, f);
        tmpforb[f] = 1;
        if (nm < 4096) marked[nm++] = f;
        cols[a] = f;
        found += complete(c, &nx, a + 1, R - 1, cols, tmpforb, na0);
        if (*c->stop) break;
    }
    for (int i = 0; i < nm; i++) tmpforb[marked[i]] = 0;
    return found;
}

// Covering bound.  The canonical completion B of a minimum solution through
// this node uses free columns only, and every defect row of the residual needs
// a column of B:  |B| >= min { sum_f x_f : sum_{free f at r} x_f >= 1 for every
// defect r, x >= 0 }.  Any feasible solution y of the dual (sum of y_r over
// the defects of a free column <= 1) is a lower bound.
//   1. y_r = 1 / max_{free f at r} |h_f & sigma|   (a column with o defects
//      carries load <= o / o)
//   2. optionally one greedy ascent pass: raise each y_r, rows with the fewest
//      free columns first, until some column at r is tight.
// Returns 1 if the bound exceeds R.
#define INV_MAX 1024
#define CV_MAX 512
static double inv_tab[INV_MAX + 1] = {0};

static int cover_prune(Ctx *c, const State *st, int R, int pc) {
    const Prob *P = c->P;
    double sum = 0.0, lim = R + 1e-9, inv_wmax = 1.0 / P->wmax;
    int left = pc;
    int ascent = P->cover_ascent && pc <= CV_MAX;
    int drow[CV_MAX];
    double dy[CV_MAX];
    int nd = 0;
    if (left * inv_wmax > lim) return 1;
    for (int w = 0; w < P->W; w++) {
        uint64_t x = st->s[w];
        while (x) {
            int r = w * 64 + __builtin_ctzll(x);
            x &= x - 1;
            left--;
            int m = 0;
            int i0 = P->row_start[r], i1 = P->row_start[r + 1];
            if (P->rc_bits) {
                const int NWORDS = P->W;
                const uint64_t *sw = st->s;
                const uint64_t *b = P->rc_bits + (size_t)i0 * NWORDS;
                const int *rc = P->row_cols;
#define CB_LOOP(NW)                                                      \
                for (int i = i0; i < i1; i++, b += NW) {                 \
                    int o = 0;                                           \
                    for (int w = 0; w < NW; w++) o += __builtin_popcountll(sw[w] & b[w]); \
                    o &= -(int)(c->forb[rc[i]] == 0);                    \
                    m = o > m ? o : m;                                   \
                }
                switch (P->W) {
                case 1: CB_LOOP(1) break;
                case 2: CB_LOOP(2) break;
                case 3: CB_LOOP(3) break;
                case 4: CB_LOOP(4) break;
                case 5: CB_LOOP(5) break;
                case 6: CB_LOOP(6) break;
                case 7: CB_LOOP(7) break;
                default: CB_LOOP(8) break;
                }
#undef CB_LOOP
            } else {
                int wm = P->wmax;
                for (int i = i0; i < i1; i++) {
                    const int *rr = P->rc_rows + (size_t)i * wm;
                    int o = 0;
                    for (int q = 0; q < wm; q++) o += (int)((st->s[rr[q] >> 6] >> (rr[q] & 63)) & 1);
                    o &= -(int)(c->forb[P->row_cols[i]] == 0);
                    m = o > m ? o : m;
                }
            }
            if (m == 0) return 1;            // no free column reaches this defect
            sum += inv_tab[m];
            // every remaining term lies in [1 / wmax, 1]
            if (sum + left * inv_wmax > lim) return 1;
            if (ascent) { drow[nd] = r; dy[nd] = inv_tab[m]; nd++; }
            else if (sum + left <= lim) return 0;
        }
    }
    if (!ascent) return 0;
    // loads of the columns under y
    int id = ++c->cv_id;
    double *load = c->cv_load;
    int *stamp = c->cv_stamp;
    const uint8_t *forb = c->forb;
    for (int i = 0; i < nd; i++) {
        int r = drow[i];
        double y = dy[i];
        for (int q = P->row_start[r]; q < P->row_start[r + 1]; q++) {
            int f = P->row_cols[q];
            if (forb[f]) continue;
            if (stamp[f] != id) { stamp[f] = id; load[f] = y; }
            else load[f] += y;
        }
    }
    // ascent, rows with the fewest free columns first
    int ord[CV_MAX];
    for (int i = 0; i < nd; i++) {
        int j = i, key = c->avail[drow[i]];
        while (j > 0 && c->avail[drow[ord[j - 1]]] > key) { ord[j] = ord[j - 1]; j--; }
        ord[j] = i;
    }
    for (int t = 0; t < nd; t++) {
        int r = drow[ord[t]];
        double slack = 1.0;
        for (int q = P->row_start[r]; q < P->row_start[r + 1]; q++) {
            int f = P->row_cols[q];
            if (forb[f]) continue;
            double s = 1.0 - load[f];
            if (s < slack) slack = s;
        }
        if (slack <= 1e-12) continue;
        for (int q = P->row_start[r]; q < P->row_start[r + 1]; q++) {
            int f = P->row_cols[q];
            if (!forb[f]) load[f] += slack;
        }
        sum += slack;
        if (sum > lim) { c->ascent_pruned++; return 1; }
    }
    return 0;
}

static void dfs(Ctx *c, int a) {
    const Prob *P = c->P;
    State *st = &c->stack[a];
    if (*c->stop) return;
    c->nodes[a]++;
    if ((c->nodes[a] & 0xFFFF) == 0 && c->deadline > 0 && now_sec() > c->deadline) {
        *c->timed_out = 1;
        *c->stop = 1;
        return;
    }
    int pc = popcnt_state(st, P->W);
    if (pc == 0) {
        if (sol_nonzero(P, st, c->path, a) != g_kernel_mode) record(c, a, c->path);
        return;
    }
    int R = c->K - a;
    if (R <= 0 || pc > P->wmax * R) return;
    if (P->cover && pc > R && 4 * pc >= P->cover * R && (P->main_tab < 0 || R > P->tab[P->main_tab]->k) &&
        (c->cover_calls++, cover_prune(c, st, R, pc))) {
        c->cover_pruned++;
        return;
    }
    for (int t = 0; t < P->ntab; t++) {
        if (R > P->tab[t]->k) continue;
        c->lookups++;
        int cost = tab_lookup(P->tab[t], st->zh[t], st->zl[t], P->full_lg ? 1 : st->lg, R);
        if (cost < 0) return;
        if (t == P->main_tab) {
            // the remainder exists (up to a hash collision): derive it explicitly
            int cols[2 * DMAX];
            for (int i = 0; i < a; i++) cols[i] = c->path[i];
            uint8_t *tmp = (uint8_t *)calloc(P->N, 1);
            for (int i = 0; i < a; i++) tmp[c->path[i]] = 1;
            // label-free: the cheapest syndrome match may have zero logical while a
            // larger completion within the budget is a solution, so use the full budget
            int64_t got = complete(c, st, a, (c->enum_all || P->full_lg) ? R : cost, cols, tmp, a);
            free(tmp);
            if (got > 0) c->hits++; else c->false_hits++;
            return;
        }
    }
    if (c->collect_depth > 0 && a == c->collect_depth) {
        #pragma omp critical(gm_task)
        {
            if (*c->ntask < c->task_cap) {
                int *dst = c->task_buf + (size_t)(*c->ntask) * c->collect_depth;
                for (int i = 0; i < a; i++) dst[i] = c->path[i];
            }
            (*c->ntask)++;
        }
        return;
    }
    if (a >= DMAX) return;
    // pivot: unsatisfied row with the fewest free columns
    int piv = -1, best = 1 << 30;
    for (int w = 0; w < P->W; w++) {
        uint64_t x = st->s[w];
        while (x) {
            int r = w * 64 + __builtin_ctzll(x);
            x &= x - 1;
            if (c->avail[r] < best) { best = c->avail[r]; piv = r; }
        }
    }
    if (best == 0) return;
    c->pivot[a] = piv;
    uint8_t stamp = (uint8_t)(a + 1);
    int mt = P->main_tab;
    int nrow = P->row_start[piv + 1] - P->row_start[piv];
    if (mt >= 0 && R - 1 <= P->tab[mt]->k && nrow <= LEAF_MAX && !(c->collect_depth > 0 && a + 1 <= c->collect_depth)) {
        // Children are decided by one lookup each: no bookkeeping is needed
        // for them.  Hash all candidates first so the probes can be prefetched.
        const Table *T = P->tab[mt];
        int cand[LEAF_MAX];
        uint64_t ch[LEAF_MAX], cl[LEAF_MAX];
        uint64_t cg[LEAF_MAX];
        int nc = 0;
        for (int i = P->row_start[piv]; i < P->row_start[piv + 1]; i++) {
            int f = P->row_cols[i];
            if (c->forb[f] || !pat_ok(c, f)) continue;
            uint64_t zh = st->zh[mt] ^ P->tzh[mt][f];
            cand[nc] = f; ch[nc] = zh; cl[nc] = st->zl[mt] ^ P->tzl[mt][f];
            cg[nc] = P->full_lg ? 1 : (st->lg ^ P->lg[f]);
            __builtin_prefetch(&T->key[zh & T->mask]);
            __builtin_prefetch(&T->cost[zh & T->mask]);
            nc++;
        }
        c->nodes[a + 1] += nc;
        c->lookups += nc;
        for (int j = 0; j < nc; j++) {
            if (tab_lookup(T, ch[j], cl[j], cg[j], R - 1) < 0) continue;
            // possible solution: take the general path for this child
            int f = cand[j];
            int how = pat_take(c, f);
            apply_col(P, st, &c->stack[a + 1], f);
            forbid(c, f, stamp);
            c->path[a] = f;
            c->nodes[a + 1]--;
            c->lookups--;
            dfs(c, a + 1);
            unforbid(c, f);
            pat_undo(c, f, how);
            if (*c->stop) break;
        }
        return;
    }
    for (int i = P->row_start[piv]; i < P->row_start[piv + 1]; i++) {
        int f = P->row_cols[i];
        if (c->forb[f]) continue;
        int how = pat_take(c, f);
        if (!how) continue;
        apply_col(P, st, &c->stack[a + 1], f);
        forbid(c, f, stamp);
        exclude_partners(c, f, a);
        kd_take(c, f, a);
        c->path[a] = f;
        dfs(c, a + 1);
        kd_undo(c, f, a);
        restore_partners(c, f, a);
        pat_undo(c, f, how);
        if (*c->stop) break;
    }
    for (int i = P->row_start[piv]; i < P->row_start[piv + 1]; i++) {
        int f = P->row_cols[i];
        if (c->forb[f] == stamp) unforbid(c, f);
    }
}

static void set_rank_forbidden(Ctx *c, int anchor) {
    const Prob *P = c->P;
    for (int r = 0; r < P->M; r++) c->avail[r] = P->row_start[r + 1] - P->row_start[r];
    for (int f = 0; f < P->N; f++) c->forb[f] = 0;
    for (int f = 0; f < P->N; f++)
        if (P->rank[f] < P->rank[anchor]) forbid(c, f, 255);
}

// Replay a prefix (path[0..len)) and continue the search below it.
static void run_prefix(Ctx *c, const int *prefix, int len) {
    const Prob *P = c->P;
    State *st = &c->stack[0];
    memset(st, 0, sizeof(State));
    int a = 0;
    // anchor
    apply_col(P, st, &c->stack[1], prefix[0]);
    forbid(c, prefix[0], 1);
    exclude_partners(c, prefix[0], 0);
    kd_take(c, prefix[0], 0);
    c->how[0] = pat_take(c, prefix[0]);
    c->path[0] = prefix[0];
    c->pivot[0] = -1;
    a = 1;
    int ok = 1, applied = 1;
    for (; a < len && ok; a++) {
        State *cur = &c->stack[a];
        int piv = -1, best = 1 << 30;
        for (int w = 0; w < P->W; w++) {
            uint64_t x = cur->s[w];
            while (x) {
                int r = w * 64 + __builtin_ctzll(x);
                x &= x - 1;
                if (c->avail[r] < best) { best = c->avail[r]; piv = r; }
            }
        }
        if (piv < 0) { ok = 0; break; }
        c->pivot[a] = piv;
        uint8_t stamp = (uint8_t)(a + 1);
        int found = 0;
        for (int i = P->row_start[piv]; i < P->row_start[piv + 1]; i++) {
            int f = P->row_cols[i];
            if (c->forb[f]) continue;
            if (!pat_ok(c, f)) continue;
            forbid(c, f, stamp);
            if (f == prefix[a]) { found = 1; break; }
        }
        if (!found) { ok = 0; a++; break; }
        apply_col(P, cur, &c->stack[a + 1], prefix[a]);
        exclude_partners(c, prefix[a], a);
        kd_take(c, prefix[a], a);
        c->how[a] = pat_take(c, prefix[a]);
        c->path[a] = prefix[a];
        applied = a + 1;
    }
    if (ok) dfs(c, len);
    // undo
    for (int d = a - 1; d >= 1; d--) {
        int piv = c->pivot[d];
        if (piv < 0) continue;
        if (d < applied) { kd_undo(c, prefix[d], d); restore_partners(c, prefix[d], d); pat_undo(c, prefix[d], c->how[d]); }
        uint8_t stamp = (uint8_t)(d + 1);
        for (int i = P->row_start[piv]; i < P->row_start[piv + 1]; i++) {
            int f = P->row_cols[i];
            if (c->forb[f] == stamp) unforbid(c, f);
        }
    }
    kd_undo(c, prefix[0], 0);
    restore_partners(c, prefix[0], 0);
    pat_undo(c, prefix[0], c->how[0]);
    unforbid(c, prefix[0]);
}

// Search for a solution of weight <= K.
//   returns 0 if the search space was exhausted, 1 if it stopped early
//   (first solution found with enum_all = 0), 2 on timeout.
//   *best = smallest weight recorded, or -1.
int gm_search(int W, int N, int M, int wmax,
              const uint64_t *col, const uint64_t *lg,
              const int *row_start, const int *row_cols,
              const int *col_start, const int *col_rows,
              int ntab, void **tabs, const uint64_t **tzh, const uint64_t **tzl, int main_tab,
              const int *rank, int n_anchor, const int *anchors,
              const int *ex_start, const int *ex_cols,
              int K, int enum_all, int task_depth, double time_limit,
              int64_t *nodes_out, int64_t *stats_out,
              int *best, int sol_cap, int sol_stride, int *sol_buf, int *nsol) {
    Prob P;
    P.W = W; P.N = N; P.M = M; P.wmax = wmax; P.col = col; P.lg = lg;
    P.row_start = row_start; P.row_cols = row_cols; P.col_start = col_start; P.col_rows = col_rows;
    P.ntab = ntab; P.main_tab = main_tab; P.rank = rank;
    P.ex_start = ex_start; P.ex_cols = ex_cols;
    P.cls = g_cls; P.onpat = g_onpat; P.nclass = g_nclass; P.slack = g_slack;
    P.cover = g_cover; P.cover_ascent = g_cover_ascent;
    P.full_lg = g_full_lg; P.lw = g_lw;
    for (int i = 1; i <= INV_MAX; i++) inv_tab[i] = 1.0 / i;
    if (wmax > INV_MAX) P.cover = 0;
    uint64_t *rc_bits = NULL;
    int *rc_rows = NULL;
    if (P.cover) {
        size_t nnz = (size_t)row_start[M];
        if (W <= CB_W) {
            rc_bits = (uint64_t *)calloc(nnz * W + 1, sizeof(uint64_t));
            for (size_t i = 0; i < nnz; i++)
                for (int w = 0; w < W; w++) rc_bits[i * W + w] = col[(size_t)row_cols[i] * W + w];
        } else {
            rc_rows = (int *)malloc((nnz * wmax + 1) * sizeof(int));
            for (size_t i = 0; i < nnz; i++) {
                int f = row_cols[i], q = 0;
                for (int t = col_start[f]; t < col_start[f + 1]; t++) rc_rows[i * wmax + q++] = col_rows[t];
                while (q < wmax) rc_rows[i * wmax + q++] = W * 64;    // State.s[W] stays zero
            }
        }
    }
    P.rc_bits = rc_bits; P.rc_rows = rc_rows;
    P.nks = g_nks; P.ks_start = g_ks_start; P.ks_cols = g_ks_cols; P.kc_start = g_kc_start; P.kc_ids = g_kc_ids;
    for (int t = 0; t < ntab; t++) { P.tab[t] = (const Table *)tabs[t]; P.tzh[t] = tzh[t]; P.tzl[t] = tzl[t]; }
    volatile int stop = 0, timed_out = 0;
    *best = -1; *nsol = 0;
    double deadline = time_limit > 0 ? now_sec() + time_limit : 0;
    for (int d = 0; d <= DMAX; d++) nodes_out[d] = 0;
    for (int i = 0; i < 8; i++) stats_out[i] = 0;

    // phase 1: collect prefixes of length task_depth (serial)
    int64_t task_cap = 1 << 22, ntask = 0;
    int td = task_depth < 1 ? 1 : task_depth;
    if (td > K) td = K;
    int *task_buf = (int *)malloc((size_t)task_cap * td * sizeof(int));
    {
        Ctx c; memset(&c, 0, sizeof(c));
        c.P = &P; c.K = K; c.enum_all = enum_all; c.collect_depth = td;
        c.forb = (uint8_t *)malloc(N); c.avail = (int *)malloc(M * sizeof(int));
        c.used = (uint8_t *)calloc(P.nclass > 0 ? P.nclass : 1, 1); c.extras = 0;
        c.kcnt = (uint8_t *)calloc(P.nks > 0 ? P.nks : 1, 1);
        c.cv_load = (double *)malloc((size_t)N * sizeof(double));
        c.cv_stamp = (int *)calloc(N, sizeof(int));
        c.stop = &stop; c.best = best; c.sol_cap = sol_cap; c.sol_stride = sol_stride;
        c.sol_buf = sol_buf; c.nsol = nsol; c.task_buf = task_buf; c.ntask = &ntask; c.task_cap = task_cap;
        c.deadline = deadline; c.timed_out = &timed_out;
        int last_rank = -(1 << 30);
        for (int i = 0; i < n_anchor && !stop; i++) {
            if (P.rank[anchors[i]] != last_rank) { set_rank_forbidden(&c, anchors[i]); last_rank = P.rank[anchors[i]]; }
            run_prefix(&c, &anchors[i], 1);
        }
        for (int d = 0; d <= DMAX; d++) nodes_out[d] += c.nodes[d];
        stats_out[0] += c.lookups; stats_out[1] += c.hits; stats_out[2] += c.false_hits; stats_out[4] += c.cover_pruned;
        stats_out[5] += c.ascent_pruned; stats_out[6] += c.cover_calls;
        free(c.forb); free(c.avail); free(c.used); free(c.kcnt); free(c.cv_load); free(c.cv_stamp);
    }
    if (ntask > task_cap) { free(task_buf); free(rc_bits); free(rc_rows); return 3; }   // too many tasks: lower task_depth
    stats_out[3] = ntask;

    // phase 2: parallel search below each prefix
    #pragma omp parallel
    {
        Ctx c; memset(&c, 0, sizeof(c));
        c.P = &P; c.K = K; c.enum_all = enum_all; c.collect_depth = 0;
        c.forb = (uint8_t *)malloc(N); c.avail = (int *)malloc(M * sizeof(int));
        c.used = (uint8_t *)calloc(P.nclass > 0 ? P.nclass : 1, 1); c.extras = 0;
        c.kcnt = (uint8_t *)calloc(P.nks > 0 ? P.nks : 1, 1);
        c.cv_load = (double *)malloc((size_t)N * sizeof(double));
        c.cv_stamp = (int *)calloc(N, sizeof(int));
        c.stop = &stop; c.best = best; c.sol_cap = sol_cap; c.sol_stride = sol_stride;
        c.sol_buf = sol_buf; c.nsol = nsol; c.deadline = deadline; c.timed_out = &timed_out;
        int last_rank = -(1 << 30);
        #pragma omp for schedule(dynamic, 1) nowait
        for (int64_t i = 0; i < ntask; i++) {
            if (stop) continue;
            const int *pre = task_buf + (size_t)i * td;
            if (P.rank[pre[0]] != last_rank) { set_rank_forbidden(&c, pre[0]); last_rank = P.rank[pre[0]]; }
            run_prefix(&c, pre, td);
        }
        #pragma omp critical(gm_stats)
        {
            for (int d = td + 1; d <= DMAX; d++) nodes_out[d] += c.nodes[d];
            stats_out[0] += c.lookups; stats_out[1] += c.hits; stats_out[2] += c.false_hits;
            stats_out[4] += c.cover_pruned; stats_out[5] += c.ascent_pruned; stats_out[6] += c.cover_calls;
        }
        free(c.forb); free(c.avail); free(c.used); free(c.kcnt); free(c.cv_load); free(c.cv_stamp);
    }
    free(task_buf);
    free(rc_bits); free(rc_rows);
    if (timed_out) return 2;
    return stop ? 1 : 0;
}

int gm_num_threads(void) {
#ifdef _OPENMP
    return omp_get_max_threads();
#else
    return 1;
#endif
}

// ------------------------------------------------------------------ exact completion cost
// Smallest number of columns B with H B = sigma (and, if use_logical, with
// L(B) != lg0), or cap + 1 if more than cap are needed.  Disjointness from the
// prefix and forbidden columns are ignored, so this is the strongest bound a
// function of (sigma, lg0) alone can give.  Without use_logical, `tab` must be
// built with all logical labels zero (it is queried with label 1).  Used to
// measure how much an admissible completion bound could prune.
static int cancel_rec(const Prob *P, const Table *T, uint64_t *s, uint64_t sh, uint64_t sl, uint64_t lg,
                      int use_logical, int r, uint8_t *forb) {
    int pc = 0;
    for (int w = 0; w < P->W; w++) pc += __builtin_popcountll(s[w]);
    if (pc == 0) return use_logical ? lg != 0 : 1;
    if (r <= 0 || pc > P->wmax * r) return 0;
    if (r <= T->k) return tab_lookup(T, sh, sl, use_logical ? lg : 1, r) >= 0;
    int piv = -1, best = 1 << 30;
    for (int w = 0; w < P->W; w++) {
        uint64_t x = s[w];
        while (x) {
            int row = w * 64 + __builtin_ctzll(x);
            x &= x - 1;
            int cnt = 0;
            for (int i = P->row_start[row]; i < P->row_start[row + 1]; i++) cnt += !forb[P->row_cols[i]];
            if (cnt < best) { best = cnt; piv = row; }
        }
    }
    if (best == 0) return 0;
    int marked[4096], nm = 0, ok = 0;
    for (int i = P->row_start[piv]; i < P->row_start[piv + 1] && !ok; i++) {
        int f = P->row_cols[i];
        if (forb[f]) continue;
        const uint64_t *c = P->col + (size_t)f * P->W;
        for (int w = 0; w < P->W; w++) s[w] ^= c[w];
        forb[f] = 1;
        if (nm < 4096) marked[nm++] = f;
        ok = cancel_rec(P, T, s, sh ^ P->tzh[0][f], sl ^ P->tzl[0][f], lg ^ (use_logical ? P->lg[f] : 0),
                        use_logical, r - 1, forb);
        for (int w = 0; w < P->W; w++) s[w] ^= c[w];
    }
    for (int i = 0; i < nm; i++) forb[marked[i]] = 0;
    return ok;
}

int gm_cancel_cost(int W, int N, int M, int wmax, const uint64_t *col, const uint64_t *lgcol,
                   const int *row_start, const int *row_cols,
                   void *tab, const uint64_t *tzh, const uint64_t *tzl,
                   const uint64_t *sigma, uint64_t sh, uint64_t sl, uint64_t lg0, int use_logical, int cap) {
    Prob P;
    memset(&P, 0, sizeof(P));
    P.W = W; P.N = N; P.M = M; P.wmax = wmax; P.col = col; P.lg = lgcol;
    P.row_start = row_start; P.row_cols = row_cols;
    P.ntab = 1; P.tab[0] = (const Table *)tab; P.tzh[0] = tzh; P.tzl[0] = tzl;
    uint64_t s[WMAX];
    for (int w = 0; w < W; w++) s[w] = sigma[w];
    uint8_t *forb = (uint8_t *)calloc(N, 1);
    int res = cap + 1;
    for (int r = 0; r <= cap; r++) {
        if (cancel_rec(&P, P.tab[0], s, sh, sl, lg0, use_logical, r, forb)) { res = r; break; }
    }
    free(forb);
    return res;
}
