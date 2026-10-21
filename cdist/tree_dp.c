/* Exact integer min-plus joins for a binary tree realization.
 *
 * The J binary generators enumerate compatible (left,right,parent) states.
 * Generators 0..parent_bits-1 lift parent coordinate unit vectors; the
 * remaining generators span the kernel of child-state addition.  Gray-code
 * traversal needs two J-entry arrays and scalar indices, not a pair tensor.
 * This kernel is deliberately single-threaded and does not allocate memory.
 */
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#define DEFINE_JOIN(TYPE, NAME)                                                \
void NAME(const TYPE *left, const TYPE *right, TYPE *out,                       \
          const uint64_t *lm, const uint64_t *rm,                               \
          unsigned parent_bits, unsigned generators,                          \
          uint64_t start, uint64_t stop, uint64_t infinity) {                   \
    uint64_t li = 0, ri = 0, pi = 0;                                          \
    uint64_t gray = start ^ (start >> 1);                                     \
    while (gray) {                                                            \
        unsigned bit = (unsigned)__builtin_ctzll(gray);                       \
        li ^= lm[bit]; ri ^= rm[bit];                                         \
        if (bit < parent_bits) pi ^= UINT64_C(1) << bit;                       \
        gray &= gray - 1;                                                     \
    }                                                                         \
    for (uint64_t i = start; i < stop; ++i) {                                 \
        uint64_t a = left[li], b = right[ri];                                 \
        if (a < infinity && b < infinity && a <= infinity - b) {               \
            uint64_t cost = a + b;                                           \
            if (cost < out[pi]) out[pi] = (TYPE)cost;                          \
        }                                                                     \
        if (i + 1 < stop) {                                                   \
            unsigned bit = (unsigned)__builtin_ctzll(i + 1);                  \
            li ^= lm[bit]; ri ^= rm[bit];                                     \
            if (bit < parent_bits) pi ^= UINT64_C(1) << bit;                   \
        }                                                                     \
    }                                                                         \
    (void)generators;                                                         \
}

DEFINE_JOIN(uint8_t, tree_join_u8)
DEFINE_JOIN(uint16_t, tree_join_u16)
DEFINE_JOIN(uint32_t, tree_join_u32)
DEFINE_JOIN(uint64_t, tree_join_u64)

/* Compact the postorder evaluation stack; source and destination may overlap.
 * Unlike an overlapping array copy, memmove requires no proportional scratch.
 */
void tree_move(void *destination, const void *source, size_t bytes) {
    memmove(destination, source, bytes);
}
