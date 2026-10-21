"""Independent algebra, exhaustive tree, and external-witness checks."""
import random
import unittest

from cdist import rankwidth as rw


def all_trees(vertices):
    if len(vertices) == 1:
        yield vertices[0]
        return
    anchor, rest = vertices[0], vertices[1:]
    for mask in range((1 << len(rest)) - 1):
        left = (anchor,) + tuple(v for k, v in enumerate(rest) if mask >> k & 1)
        right = tuple(v for k, v in enumerate(rest) if not mask >> k & 1)
        for a in all_trees(left):
            for b in all_trees(right):
                yield (a, b)


class RankwidthTests(unittest.TestCase):
    def test_fundamental_graph_all_cuts_and_basis_coordinates(self):
        rng = random.Random(183)
        for n in (1, 2, 6, 8):
            for _ in range(5):
                columns = [rng.randrange(32) for _ in range(n)]
                order = list(range(n))
                rng.shuffle(order)
                graph = rw.fundamental_graph(columns, order)
                rw.validate_adjacency(graph.adjacency)
                for j, coefficient in enumerate(graph.coordinates):
                    rebuilt = 0
                    for k, b in enumerate(graph.basis_columns):
                        if coefficient >> k & 1:
                            rebuilt ^= columns[b]
                    self.assertEqual(rebuilt, columns[j])
                for subset in range(1 << n):
                    self.assertEqual(rw.cut_rank(graph.adjacency, subset),
                                     rw.connectivity(columns, subset))

    def test_exact_matches_all_binary_trees(self):
        rng = random.Random(71)
        for _ in range(5):
            columns = [rng.randrange(16) for _ in range(6)]
            graph = rw.fundamental_graph(columns)
            brute = min(rw.tree_profile(columns, t)['width'] for t in all_trees(tuple(range(6))))
            solved = rw.exact_rankwidth(graph.adjacency)
            self.assertEqual(solved['width'], brute)
            self.assertEqual(rw.tree_profile(columns, solved['tree'])['width'], brute)

    def test_join_counts_match_direct_compatible_syndromes(self):
        columns = [1, 2, 3, 4, 5, 6]
        tree = ((0, (1, 2)), ((3, 4), 5))
        nodes, masks = rw.flatten_tree(tree, len(columns))
        profile = rw.tree_profile(columns, tree, include_nodes=True)
        def span(mask):
            out = {0}
            for j in range(len(columns)):
                if mask >> j & 1:
                    out |= {x ^ columns[j] for x in list(out)}
            return out
        full = (1 << len(columns)) - 1
        exponents = iter(profile['join_dimensions'])
        for i, node in enumerate(nodes):
            if isinstance(node, int):
                continue
            a, b = node
            A, B, C = span(masks[a]), span(masks[b]), span(full ^ masks[i])
            count = sum(x ^ y in C for x in A for y in B)
            self.assertEqual(count, 1 << next(exponents))

    def test_no_32_vertex_or_32_row_limit(self):
        # Parallel pairs are independent across components. Their optimal
        # decomposition has width one; this also checks row bits above 64.
        columns = [1 << (i // 2) for i in range(320)]
        graph = rw.fundamental_graph(columns)
        tree = rw.balanced_tree([(i, i + 1) for i in range(0, 320, 2)])
        self.assertEqual(rw.tree_profile(columns, tree)['width'], 1)
        self.assertEqual(rw.graph_tree_width(graph.adjacency, tree), 1)
        self.assertFalse(rw.exact_preflight(320)['admitted'])
        self.assertFalse(rw.exact_preflight(32)['admitted'])
        exact = rw.exact_rankwidth_by_components(graph.adjacency)
        self.assertEqual(exact['width'], 1)
        self.assertEqual(exact['max_component_vertices'], 2)
        self.assertEqual(len(exact['components']), 160)

    def test_exact_refuses_before_allocation(self):
        with self.assertRaisesRegex(ValueError, 'refused'):
            rw.exact_rankwidth([0] * 32)
        with self.assertRaisesRegex(ValueError, 'refused'):
            rw.exact_rankwidth([0] * 10, max_memory_bytes=1)
        self.assertEqual(rw.exact_preflight(33)['witness_type'], 'Q')

    def test_zero_loop_coloop_and_dependent_logical_cases(self):
        self.assertEqual(rw.exact_rankwidth([0])['width'], 0)
        for columns in ([0, 0, 0], [1, 2, 4], [1, 1, 0]):
            graph = rw.fundamental_graph(columns)
            result = rw.exact_rankwidth(graph.adjacency)
            self.assertEqual(result['width'], 0 if columns != [1, 1, 0] else 1)
        h = [1, 2, 3, 1]
        dependent_augmented = [c | ((c & 1) << 2) for c in h]
        for subset in range(16):
            self.assertEqual(rw.connectivity(h, subset), rw.connectivity(dependent_augmented, subset))

    def test_flat_tree_and_invalid_witnesses(self):
        tree = rw.caterpillar_tree(range(1200))
        nodes, _ = rw.flatten_tree(tree, 1200)
        replay, _ = rw.flatten_tree(rw.tree_from_flat(nodes), 1200)
        self.assertEqual(nodes, replay)
        for bad in ((0, 0), (0, 2), (0, (1, 2, 3)), True, None):
            with self.assertRaises(ValueError):
                rw.flatten_tree(bad, 2)
        cycle = [0, None]
        cycle[1] = cycle
        with self.assertRaises(ValueError):
            rw.flatten_tree(cycle, 2)
        with self.assertRaises(ValueError):
            rw.fundamental_graph([1.2, 3])

    def test_external_dot_exact_replay_including_isolate(self):
        rows = (2, 1, 0)
        dot = '''graph decomposition {
          leaf_v0 -- node_0 [label = 1]
          leaf_v1 -- node_0 [label = 1]
          leaf_v2 -- node_0 [label = 0]
        }'''
        result = rw.parse_gericom_dot(dot, rows)
        self.assertEqual(result['width'], 1)
        self.assertEqual(result['edges_replayed'], 3)
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            rw.parse_gericom_dot(dot.replace('label = 0', 'label = 1'), rows)
        dimacs = rw.graph_to_dimacs(rows)
        self.assertIn('e v2 v2', dimacs)
        self.assertIn('p edge 3 4', dimacs)


if __name__ == '__main__':
    unittest.main()
