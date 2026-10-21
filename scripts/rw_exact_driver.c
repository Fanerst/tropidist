/* Minimal bounded JSON driver for externally downloaded rw 0.10 (GPL-2.0+).
 * Compile with the upstream rw.c and include path; no libigraph is needed.
 * This driver does not modify or embed the upstream implementation.
 * Input: n followed by n unsigned packed adjacency rows.  n is capped at 18.
 */
#include <stdio.h>
#include <stdlib.h>
#include "rw.h"

static void print_tree(subset_t subset) {
    if ((subset & (subset - 1)) == 0) {
        unsigned j = 0;
        while ((subset >> j) != 1) ++j;
        printf("%u", j);
    } else {
        const subset_t left = cslots[subset];
        printf("["); print_tree(left); printf(",");
        print_tree(subset ^ left); printf("]");
    }
}

int main(void) {
    unsigned n;
    if (scanf("%u", &n) != 1 || n == 0 || n > 18) {
        fprintf(stderr, "bounded audit driver requires 1 <= n <= 18\n");
        return 2;
    }
    if (init_rw_dec(n)) return 3;
    for (unsigned j = 0; j < n; ++j) {
        unsigned value;
        if (scanf("%u", &value) != 1 || value >= (1u << n) || (value & (1u << j))) {
            destroy_rw(); return 4;
        }
        adjacency_matrix[j] = value;
    }
    for (unsigned i = 0; i < n; ++i)
        for (unsigned j = 0; j < n; ++j)
            if (((adjacency_matrix[i] >> j) & 1) != ((adjacency_matrix[j] >> i) & 1)) {
                destroy_rw(); return 5;
            }
    calculate_all();
    printf("{\"width\":%u,\"tree\":", (unsigned)get_rw());
    print_tree(((subset_t)1 << n) - 1);
    printf("}\n");
    destroy_rw();
    return 0;
}
