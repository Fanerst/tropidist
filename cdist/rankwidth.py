"""Column-matroid decompositions with independently replayable widths.

Graphs here are *fundamental graphs* of the column matroid, not the original
Tanner graph.  Vertices retain the original column IDs.  Every cut therefore
has rank ``rank(H_S) + rank(H_notS) - rank(H)``.  Packed Python integers have
no 32-vertex restriction.  This does not remove the exponential cost of an
exact subset algorithm; exact search has explicit preallocation guards.

A tree is a column ID at a leaf and ``(left, right)`` at a binary join.
JSON lists are accepted as joins.  Witnesses are validated before evaluation.
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass
import operator
import re
import time


_popcount = int.bit_count if hasattr(int, 'bit_count') else lambda value: bin(value).count('1')


def _columns(columns):
    try:
        out = tuple(operator.index(c) for c in columns)
    except TypeError as exc:
        raise ValueError("columns must be integral bitsets") from exc
    if any(c < 0 for c in out):
        raise ValueError("columns must be nonnegative integer bitsets")
    return out


def basis(vectors):
    """An echelon basis for binary integer vectors, with descending pivots."""
    pivots = {}
    for value in vectors:
        try:
            value = operator.index(value)
        except TypeError as exc:
            raise ValueError("vectors must be integral bitsets") from exc
        if value < 0:
            raise ValueError("vectors must be nonnegative")
        while value:
            p = value.bit_length() - 1
            if p not in pivots:
                pivots[p] = value
                break
            value ^= pivots[p]
    return tuple(pivots[p] for p in sorted(pivots, reverse=True))


def rank(vectors):
    return len(basis(vectors))


def _bits(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


@dataclass(frozen=True)
class FundamentalGraph:
    adjacency: tuple[int, ...]
    basis_columns: tuple[int, ...]
    coordinates: tuple[int, ...]


def fundamental_graph(columns, order=None):
    """Return the graph of a systematic representation ``[I | A]``.

    ``order`` selects the column basis; it does not relabel vertices.  The
    coordinate map is injective on the column span, including when the input
    has redundant or zero rows.  Zero columns remain isolated vertices.
    """
    cols = _columns(columns)
    n = len(cols)
    order = tuple(range(n) if order is None else order)
    if sorted(order) != list(range(n)):
        raise ValueError("order must permute all column IDs")
    pivots, selected, coordinates = {}, [], [0] * n
    for j in order:
        value, coefficient = cols[j], 0
        while value:
            p = value.bit_length() - 1
            if p not in pivots:
                identity = 1 << len(selected)
                selected.append(j)
                pivots[p] = (value, coefficient ^ identity)
                coordinates[j] = identity
                break
            pivot, tag = pivots[p]
            value ^= pivot
            coefficient ^= tag
        else:
            coordinates[j] = coefficient
    rows, selected_set = [0] * n, set(selected)
    for j, coefficient in enumerate(coordinates):
        if j in selected_set:
            continue
        for k in _bits(coefficient):
            b = selected[k]
            rows[j] |= 1 << b
            rows[b] |= 1 << j
    return FundamentalGraph(tuple(rows), tuple(selected), tuple(coordinates))


def validate_adjacency(adjacency):
    rows = _columns(adjacency)
    n = len(rows)
    full = (1 << n) - 1
    for i, row in enumerate(rows):
        if row & ~full or row & (1 << i):
            raise ValueError("expected loop-free adjacency within 0..n-1")
        if any(not (rows[j] >> i) & 1 for j in _bits(row)):
            raise ValueError("adjacency must be symmetric")
    return rows


def cut_rank(adjacency, subset):
    """Rank of a graph cut; adjacency is assumed to have been validated."""
    n = len(adjacency)
    full = (1 << n) - 1
    if subset < 0 or subset & ~full:
        raise ValueError("subset contains a vertex outside the graph")
    other = full ^ subset
    if _popcount(subset) > _popcount(other):
        subset, other = other, subset
    return rank(adjacency[j] & other for j in _bits(subset))


def connectivity(columns, subset):
    cols = _columns(columns)
    full = (1 << len(cols)) - 1
    if subset < 0 or subset & ~full:
        raise ValueError("subset contains a column outside the matrix")
    return (rank(cols[j] for j in _bits(subset))
            + rank(cols[j] for j in _bits(full ^ subset)) - rank(cols))


def flatten_tree(tree, ncols):
    """Validate the leaf bijection and return postorder nodes and masks.

    A flat leaf is an integer column ID; a flat join is a pair of earlier
    node IDs.  Traversal is iterative, so deep caterpillars are supported.
    """
    if not isinstance(ncols, int) or ncols < 0:
        raise ValueError("ncols must be a nonnegative integer")
    if ncols == 0:
        if tree is not None:
            raise ValueError("the empty matrix requires tree=None")
        return (), ()
    stack, values, nodes, masks, seen = [(tree, False)], [], [], [], 0
    visits = 0
    while stack:
        node, expanded = stack.pop()
        if not expanded:
            visits += 1
            if visits > 2 * ncols - 1:
                raise ValueError("tree has too many nodes or contains a cycle")
        if isinstance(node, int) and not isinstance(node, bool):
            if node < 0 or node >= ncols or seen & (1 << node):
                raise ValueError("tree leaves must occur exactly once in 0..ncols-1")
            seen |= 1 << node
            values.append(len(nodes))
            nodes.append(node)
            masks.append(1 << node)
        elif isinstance(node, (tuple, list)) and len(node) == 2:
            if expanded:
                right, left = values.pop(), values.pop()
                values.append(len(nodes))
                nodes.append((left, right))
                masks.append(masks[left] | masks[right])
            else:
                stack.extend(((node, True), (node[1], False), (node[0], False)))
        else:
            raise ValueError("tree must contain integer leaves and binary joins")
    if seen != (1 << ncols) - 1 or len(nodes) != 2 * ncols - 1:
        raise ValueError("tree does not contain every column exactly once")
    return tuple(nodes), tuple(masks)


def tree_from_flat(nodes):
    values = []
    for node in nodes:
        if isinstance(node, int):
            values.append(node)
        else:
            a, b = node
            if not 0 <= a < len(values) or not 0 <= b < len(values):
                raise ValueError("flat children must precede their parent")
            values.append((values[a], values[b]))
    tree = values[-1] if values else None
    flatten_tree(tree, (len(nodes) + 1) // 2 if nodes else 0)
    return tree


def caterpillar_tree(order):
    order = list(order)
    if not order:
        return None
    tree = order[0]
    for j in order[1:]:
        tree = (tree, j)
    return tree


def balanced_tree(order):
    order = list(order)
    if not order:
        return None
    def build(start, end):
        if end - start == 1:
            return order[start]
        mid = (start + end) // 2
        return (build(start, mid), build(mid, end))
    return build(0, len(order))


def tree_profile(columns, tree, *, include_nodes=False):
    """Polynomial rank-only analysis: no exponential arrays are allocated.

    At a join with column partition ``A,B,C``, the number of compatible
    interface pairs is exactly ``2**J``, where
    ``J = rank(H_A)+rank(H_B)+rank(H_C)-rank(H)``.  This is invariant under
    rerooting the same unrooted trivalent vertex.  Edge width alone therefore
    does not bound practical join time tightly.  ``single_table_entries``
    is a state count, not a live-memory or implementation feasibility claim.
    """
    cols = _columns(columns)
    nodes, masks = flatten_tree(tree, len(cols))
    if not nodes:
        return dict(ncols=0, matrix_rank=0, width=0, max_join_dimension=0,
                    total_join_work=0, single_table_entries=1)
    spans = []
    for node in nodes:
        spans.append(basis((cols[node],)) if isinstance(node, int)
                     else basis(spans[node[0]] + spans[node[1]]))
    full_rank = len(spans[-1])
    outside = [()] * len(nodes)
    for i in range(len(nodes) - 1, -1, -1):
        node = nodes[i]
        if not isinstance(node, int):
            a, b = node
            outside[a] = basis(outside[i] + spans[b])
            outside[b] = basis(outside[i] + spans[a])
    widths = [len(a) + len(b) - full_rank for a, b in zip(spans, outside)]
    joins = [len(spans[a]) + len(spans[b]) + len(outside[i]) - full_rank
             for i, node in enumerate(nodes) if not isinstance(node, int)
             for a, b in (node,)]
    result = dict(ncols=len(cols), matrix_rank=full_rank, width=max(widths),
                  max_join_dimension=max(joins, default=0),
                  total_join_work=sum(1 << j for j in joins),
                  single_table_entries=1 << max(widths))
    if include_nodes:
        result.update(nodes=[list(x) if isinstance(x, tuple) else x for x in nodes],
                      masks=[hex(x) for x in masks], edge_widths=widths,
                      join_dimensions=joins)
    return result


def graph_tree_width(adjacency, tree):
    rows = validate_adjacency(adjacency)
    _, masks = flatten_tree(tree, len(rows))
    return max((cut_rank(rows, mask) for mask in masks), default=0)


def exact_preflight(n, *, max_n=18, max_memory_bytes=256 << 20,
                    max_split_evaluations=250_000_000):
    """Conservative full recurrence cost, before any exponential allocation."""
    if not isinstance(n, int) or n < 1:
        raise ValueError("exact search needs at least one vertex")
    subsets = 1 << n
    # Small exact DP has an explicit packed-witness ceiling of 64 vertices.
    # Resource guards normally refuse much earlier.  The graph oracle and
    # tree code do not share this ceiling.  Above 64 the byte count below is
    # a storage lower estimate, not a supported allocation strategy.
    witness_type = 'I' if n <= 32 else 'Q' if n <= 64 else None
    witness_bytes = array(witness_type).itemsize if witness_type else (n + 7) // 8
    table_bytes = subsets * (2 + witness_bytes)
    splits = (3 ** n - 2 ** (n + 1) + 1) // 2
    reasons = []
    if n > max_n:
        reasons.append("vertex limit")
    if witness_type is None:
        reasons.append("packed exact witness limit of 64 vertices")
    if table_bytes > max_memory_bytes:
        reasons.append("table memory limit")
    if splits > max_split_evaluations:
        reasons.append("worst-case split limit")
    return dict(n=n, subsets=subsets, table_bytes=table_bytes, witness_type=witness_type,
                witness_bytes=witness_bytes,
                worst_case_split_evaluations=splits, admitted=not reasons,
                refusal_reasons=reasons)


def exact_rankwidth(adjacency, *, max_n=18, max_memory_bytes=256 << 20,
                    max_split_evaluations=250_000_000, time_limit=60.0):
    """Exact direct subset recurrence, *not* fast subset convolution.

    ``D(S)=max(rho(S), min(max(D(A),D(S\\A))))`` over nonempty proper A,
    with singleton ``D=rho``.  Symmetric splits are considered once.  A
    completed result certifies optimal rank-width; a timeout raises and
    does not claim a lower bound.  Witness replay is independent of the DP.
    """
    rows = validate_adjacency(adjacency)
    preflight = exact_preflight(len(rows), max_n=max_n,
                               max_memory_bytes=max_memory_bytes,
                               max_split_evaluations=max_split_evaluations)
    if not preflight['admitted']:
        raise ValueError(f"exact rank-width refused: {preflight}")
    if time_limit <= 0:
        raise ValueError("time_limit must be positive")
    start = time.monotonic()
    deadline = start + time_limit
    count = 1 << len(rows)
    cuts, values = bytearray(count), bytearray(count)
    split = array(preflight['witness_type'], [0]) * count
    for subset in range(1, count):
        cuts[subset] = cut_rank(rows, subset)
        if subset % 1024 == 0 and time.monotonic() > deadline:
            raise TimeoutError("exact rank-width cut table timed out")
    evaluations = 0
    for subset in range(1, count):
        anchor = subset & -subset
        rest = subset ^ anchor
        if not rest:
            values[subset] = cuts[subset]
            continue
        best, best_child = len(rows), 0
        # A contains the anchor, and S\\A is nonempty.
        part = (rest - 1) & rest
        while True:
            child = part | anchor
            candidate = max(values[child], values[subset ^ child])
            evaluations += 1
            if candidate < best:
                best, best_child = candidate, child
                if best <= cuts[subset]:
                    break
            if not part:
                break
            part = (part - 1) & rest
            if evaluations % 65536 == 0 and time.monotonic() > deadline:
                raise TimeoutError("exact rank-width split recurrence timed out")
        values[subset], split[subset] = max(cuts[subset], best), best_child
        if subset % 1024 == 0 and time.monotonic() > deadline:
            raise TimeoutError("exact rank-width subset recurrence timed out")
    def recover(subset):
        if subset & (subset - 1) == 0:
            return subset.bit_length() - 1
        child = split[subset]
        return (recover(child), recover(subset ^ child))
    tree = recover(count - 1)
    width = graph_tree_width(rows, tree)
    if width != values[-1]:
        raise RuntimeError("exact rank-width witness failed independent replay")
    return dict(status="exact", width=width, tree=tree,
                seconds=time.monotonic() - start, split_evaluations=evaluations,
                preflight=preflight)


def connected_components(adjacency):
    rows = validate_adjacency(adjacency)
    remaining, components = (1 << len(rows)) - 1, []
    while remaining:
        pending, reached = remaining & -remaining, 0
        while pending:
            reached |= pending
            neighbors = 0
            for j in _bits(pending):
                neighbors |= rows[j]
            pending = neighbors & remaining & ~reached
        components.append(tuple(_bits(reached)))
        remaining &= ~reached
    return tuple(components)


def exact_rankwidth_by_components(adjacency, *, time_limit=60.0, **limits):
    """Exact disconnected reduction, allowing large unions of small graphs.

    The rank-width of a disjoint union is the maximum component rank-width.
    A component is an induced subgraph (lower bound); joining the component
    trees adds only rank-zero cuts (matching upper bound).  This is a genuine
    structural reduction, not an exponential search on the full vertex set.
    Each component is preflighted *before any* exact search is started.
    """
    start = time.monotonic()
    rows = validate_adjacency(adjacency)
    components = connected_components(rows)
    preflights = [exact_preflight(len(c), **limits) for c in components]
    if any(not p['admitted'] for p in preflights):
        raise ValueError("at least one connected component exceeds exact limits")
    trees, records = [], []
    for vertices in components:
        if time.monotonic() - start >= time_limit:
            raise TimeoutError("component exact rank-width timed out")
        subrows = tuple(sum(((rows[i] >> j) & 1) << k for k, j in enumerate(vertices))
                        for i in vertices)
        solved = exact_rankwidth(subrows, time_limit=time_limit - (time.monotonic() - start), **limits)
        flat, _ = flatten_tree(solved['tree'], len(vertices))
        values = []
        for node in flat:
            values.append(vertices[node] if isinstance(node, int) else (values[node[0]], values[node[1]]))
        trees.append(values[-1])
        records.append(dict(vertices=list(vertices), width=solved['width'],
                            seconds=solved['seconds'], split_evaluations=solved['split_evaluations']))
    tree = balanced_tree(trees)
    width = graph_tree_width(rows, tree)
    if width != max((r['width'] for r in records), default=0):
        raise RuntimeError("component exact certificate failed replay")
    return dict(status='exact_by_components', width=width, tree=tree,
                components=records, seconds=time.monotonic() - start,
                max_component_vertices=max(map(len, components), default=0))


def graph_to_dimacs(adjacency):
    """Gericom-compatible labels, retaining isolated vertices.

    The upstream parser ignores vertex declarations.  Diagonal records force
    every label to exist; they never cross a cut and do not affect cut rank.
    """
    rows = validate_adjacency(adjacency)
    edges = [(i, j) for i, row in enumerate(rows) for j in _bits(row) if i < j]
    lines = ["c diagonal records retain labels and isolates",
             f"p edge {len(rows)} {len(rows) + len(edges)}"]
    lines.extend(f"e v{i} v{i}" for i in range(len(rows)))
    lines.extend(f"e v{i} v{j}" for i, j in edges)
    return '\n'.join(lines) + '\n'


_DOT_EDGE = re.compile(r"^\s*(leaf_v\d+|node_\d+)\s*--\s*"
                       r"(leaf_v\d+|node_\d+)\s*\[\s*label\s*=\s*(\d+)\s*\]\s*;?\s*$")


def parse_gericom_dot(output, adjacency):
    """Strictly validate an external tree and replay *every* cut-rank label."""
    rows = validate_adjacency(adjacency)
    n = len(rows)
    lines = output.splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == 'graph decomposition {']
    if n < 2 or len(starts) != 1:
        raise ValueError("expected one DOT decomposition with at least two leaves")
    start = starts[0]
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == '}'), None)
    if end is None:
        raise ValueError("unterminated DOT decomposition")
    neighbors, labels = {}, {}
    for line in lines[start + 1:end]:
        if not line.strip():
            continue
        match = _DOT_EDGE.fullmatch(line)
        if match is None:
            raise ValueError("unsupported DOT syntax")
        a, b, label = match.groups()
        edge = tuple(sorted((a, b)))
        if a == b or edge in labels:
            raise ValueError("duplicate edge or self-loop in decomposition")
        labels[edge] = int(label)
        neighbors.setdefault(a, set()).add(b)
        neighbors.setdefault(b, set()).add(a)
    leaves = {v: int(v[6:]) for v in neighbors if v.startswith('leaf_v')}
    if sorted(leaves.values()) != list(range(n)):
        raise ValueError("DOT leaves must be a bijection to original columns")
    if any(len(neighbors[v]) != (1 if v in leaves else 3) for v in neighbors):
        raise ValueError("DOT tree is not subcubic with the declared leaves")
    if len(neighbors) != 2 * n - 2 or len(labels) != 2 * n - 3:
        raise ValueError("wrong number of DOT tree vertices or edges")
    reached, stack = set(), [next(iter(neighbors))]
    while stack:
        v = stack.pop()
        if v not in reached:
            reached.add(v)
            stack.extend(neighbors[v] - reached)
    if len(reached) != len(neighbors):
        raise ValueError("DOT tree is disconnected")
    for (a, b), expected in labels.items():
        subset, stack = 0, [(a, b)]
        while stack:
            v, parent = stack.pop()
            if v in leaves:
                subset |= 1 << leaves[v]
            stack.extend((w, v) for w in neighbors[v] if w != parent)
        actual = cut_rank(rows, subset)
        if actual != expected:
            raise ValueError(f"DOT cut label mismatch: expected {expected}, replay {actual}")
    # A leaf edge gives a deterministic root without optimizing a wrong join proxy.
    first = 'leaf_v0'
    second = next(iter(neighbors[first]))
    def orient(v, parent):
        values, stack = {}, [(v, parent, False)]
        while stack:
            node, previous, expanded = stack.pop()
            if node in leaves:
                values[node] = leaves[node]
            elif expanded:
                a, b = sorted(neighbors[node] - {previous})
                values[node] = (values[a], values[b])
            else:
                stack.append((node, previous, True))
                stack.extend((w, node, False) for w in sorted(neighbors[node] - {previous}))
        return values[v]
    tree = (0, orient(second, first))
    width = graph_tree_width(rows, tree)
    return dict(tree=tree, width=width, edges_replayed=len(labels),
                status="verified_upper_bound")
