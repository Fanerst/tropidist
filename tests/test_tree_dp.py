"""Exact tree-realization checks against independent exhaustive enumeration."""
from __future__ import annotations

from contextlib import ExitStack
from itertools import product
import os
import random
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cdist import kernel, trellis
from cdist.tree_dp import (CompiledTreeDP, TreeDPResourceError,
                           preflight_tree_dp, tree_min_distance_for_mask)


def balanced(leaves):
    if not leaves:
        return None
    if len(leaves) == 1:
        return leaves[0]
    middle = len(leaves) // 2
    return balanced(leaves[:middle]), balanced(leaves[middle:])


def comb(leaves):
    if not leaves:
        return None
    tree = leaves[0]
    for leaf in leaves[1:]:
        tree = tree, leaf
    return tree


def random_tree(leaves, rng):
    if len(leaves) == 1:
        return leaves[0]
    split = rng.randrange(1, len(leaves))
    return random_tree(leaves[:split], rng), random_tree(leaves[split:], rng)


def brute_affine(columns):
    """All target minima from all assignments, independent of interface maps."""
    result = {}
    for bits in product((0, 1), repeat=len(columns)):
        target = 0
        for bit, column in zip(bits, columns):
            if bit:
                target ^= column
        weight = sum(bits)
        result[target] = min(result.get(target, len(columns) + 1), weight)
    return result


def brute_logical(h, l, mask):
    best = None
    for bits in product((0, 1), repeat=len(h)):
        syndrome = logical = 0
        for bit, hc, lc in zip(bits, h, l):
            if bit:
                syndrome ^= hc
                logical ^= lc
        if syndrome == 0 and bin(logical & mask).count("1") % 2:
            weight = sum(bits)
            best = weight if best is None else min(best, weight)
    return best


class TestTreeDP(unittest.TestCase):
    def test_all_small_binary_matrices_all_affine_targets(self):
        # All two-row matrices with up to four columns, including every zero,
        # repeated-column, loop, coloop, and row-dependency configuration.
        solved = 0
        for ncols in range(5):
            tree = balanced(list(range(ncols)))
            for columns in product(range(4), repeat=ncols):
                reference = brute_affine(columns)
                program = CompiledTreeDP(columns, tree)
                for target in range(8):
                    got, stats = program.run(target)
                    self.assertEqual(got, reference.get(target), (columns, target))
                    if stats["feasible"] and ncols:
                        self.assertEqual(stats["allocated_dense_bytes"], stats["peak_dense_bytes"])
                        self.assertEqual(stats["observed_peak_live_table_bytes"], stats["arena_bytes"])
                        self.assertEqual(stats["join_work_done"], stats["join_work"])
                    solved += 1
        self.assertEqual(solved, 2728)

    def test_random_logical_queries_and_tree_shapes_against_trellis(self):
        rng = random.Random(20261021)
        for trial in range(160):
            ncols, nrows, nobs = rng.randrange(1, 13), rng.randrange(0, 7), rng.randrange(1, 4)
            h = [rng.randrange(1 << nrows) for _ in range(ncols)]
            l = [rng.randrange(1 << nobs) for _ in range(ncols)]
            order = list(range(ncols))
            rng.shuffle(order)
            mask = rng.randrange(1 << nobs)
            expected = brute_logical(h, l, mask)
            trellis_plan = trellis.build_plan(h, l, mask, order, nrows)
            self.assertEqual(kernel.run_plan(trellis_plan)[0], expected)
            tree = (comb(order), balanced(order), random_tree(order, rng))[trial % 3]
            got, stats = tree_min_distance_for_mask(h, l, mask, tree)
            self.assertEqual(got, expected, (trial, tree, h, l, mask))
            if trial < 40:
                reference, _ = tree_min_distance_for_mask(h, l, mask, tree, backend="python")
                self.assertEqual(reference, expected)
            augmented = [h[j] | ((bin(l[j] & mask).count("1") & 1) << nrows) for j in range(ncols)]
            program = CompiledTreeDP(augmented, tree)
            supports = []
            for index, node in enumerate(program.nodes):
                support = ({node.leaf} if node.leaf is not None
                           else supports[node.left] | supports[node.right])
                supports.append(support)
                before = list(support) + [j for j in range(ncols) if j not in support]
                actual_lambda = trellis.cut_profile(augmented, before)[len(support)]
                self.assertEqual(len(program.interfaces[index]), actual_lambda)
                if node.leaf is None:
                    left, right = supports[node.left], supports[node.right]
                    rank = lambda subset: trellis.rank_profile(augmented, list(subset))[-1]
                    expected_j = rank(left) + rank(right) + rank(set(range(ncols)) - support) - rank(range(ncols))
                    self.assertEqual(program.joins[index].join_dimension, expected_j)

    def test_augmented_cut_rank_can_decrease(self):
        # Adding the target row makes these columns independent. H alone has
        # cut rank one; the shifted augmented realization has cut rank zero.
        distance, stats = tree_min_distance_for_mask([1, 1], [1, 0], 1, (0, 1))
        self.assertEqual(distance, 2)
        self.assertEqual(stats["edge_state_dimensions"], [0, 0, 0])
        self.assertEqual(trellis.cut_profile([1, 1], [0, 1]), [0, 1, 0])

    def test_large_exact_distance_selects_uint16(self):
        for ncols in (254, 255, 300):
            # H e=0 forces every bit equal; l e=1 forces all N bits to one.
            h = [1] + [(1 << (j - 1)) | (1 << j) for j in range(1, ncols - 1)] + [1 << (ncols - 2)]
            l = [1] + [0] * (ncols - 1)
            distance, stats = tree_min_distance_for_mask(h, l, 1, balanced(list(range(ncols))))
            self.assertEqual(distance, ncols)
            self.assertEqual(stats["dtype"], "uint8" if ncols == 254 else "uint16")
            self.assertEqual(stats["infinity"], ncols + 1)

    def test_unbalanced_tree_exceeds_python_recursion_depth(self):
        ncols = 1300
        program = CompiledTreeDP([0] * ncols, comb(list(range(ncols))))
        self.assertEqual(program.run()[0], 0)
        self.assertEqual(program.preflight()["max_interface_rank"], 0)

    def test_preflight_rejects_before_any_dense_allocation(self):
        program = CompiledTreeDP([1, 2, 3, 1, 2, 3], ((0, (1, 2)), (3, (4, 5))))
        profile = program.preflight()
        self.assertGreater(profile["join_work"], 1)
        with ExitStack() as context:
            context.enter_context(patch("cdist.tree_dp.np.empty", side_effect=AssertionError("allocated")))
            for kwargs in (dict(max_memory_bytes=profile["peak_dense_bytes"] - 1),
                           dict(max_join_work=profile["join_work"] - 1),
                           dict(max_table_bits=0), dict(max_seconds=-1)):
                with self.assertRaises(TreeDPResourceError):
                    program.run(**kwargs)
        with self.assertRaises(TreeDPResourceError):
            CompiledTreeDP([1, 2], (0, 1), max_compile_bytes=1)
        profile = preflight_tree_dp([1], [0], 1, 0)
        self.assertFalse(profile["feasible"])

    def test_empty_and_malformed_inputs(self):
        program = CompiledTreeDP([], None)
        self.assertEqual(program.run(0)[0], 0)
        self.assertIsNone(program.run(1)[0])
        for tree in ((0, 0), (0, 2), (0,), (False, 1), 0, None):
            with self.assertRaises(ValueError):
                CompiledTreeDP([1, 2], tree)
        cycle = [0, None]
        cycle[1] = cycle
        with self.assertRaises(ValueError):
            CompiledTreeDP([1, 2], cycle)
        for column in (-1, True, 1.0):
            with self.assertRaises(ValueError):
                CompiledTreeDP([column], 0)
        for target in (-1, True, 1.0):
            with self.assertRaises(ValueError):
                CompiledTreeDP([1], 0).run(target)

    def test_chunk_boundaries_and_map_scratch(self):
        # Several chunk boundaries exercise Gray-state restart, including
        # nonzero parent states and joins with both children nontrivial.
        columns = [1, 2, 4, 7, 3, 5, 6, 1]
        tree = ((0, (1, (2, 3))), ((4, 5), (6, 7)))
        reference = brute_affine(columns)
        with patch("cdist.tree_dp._CHUNK_PAIRS", 3):
            program = CompiledTreeDP(columns, tree)
            for target, expected in reference.items():
                result, stats = program.run(target)
                self.assertEqual(result, expected)
                self.assertEqual(stats["scratch_bytes"], 16 * stats["max_join_dimension"])

    def test_parent_larger_than_both_child_tables_and_overlapping_compaction(self):
        # Each eight-column half has all 256 boundary states. Its two child
        # tables have only 16 states each, so compaction necessarily overlaps.
        columns = [1 << j for j in range(8)] * 2
        program = CompiledTreeDP(columns, balanced(list(range(16))))
        profile = program.preflight()
        self.assertEqual(profile["largest_table_bytes"], 256)
        self.assertEqual(profile["peak_live_table_bytes"], 544)
        for target in (0, 1, 3, 17, 127, 128, 255):
            for backend in ("c", "python"):
                distance, stats = program.run(target, backend=backend)
                self.assertEqual(distance, bin(target).count("1"))
                self.assertEqual(stats["observed_peak_live_table_bytes"], 544)


if __name__ == "__main__":
    unittest.main()
