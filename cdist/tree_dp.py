"""Exact dense min-plus DP on an arbitrary binary tree of fault columns.

``CompiledTreeDP(M, tree).run(t)`` minimizes Hamming weight subject to M e=t.
Columns are nonnegative Python integer bitmasks. A tree is an integer leaf
or a pair of trees; its leaves must be exactly range(len(M)). ``None`` is the
empty tree. This module does not change the existing trellis implementation.

Correctness. Choose a particular solution e0 and write e=e0+x, so M x=0.
At a cut S the state is M_S x_S in I_S=im(M_S) intersect im(M_notS).
The table stores the minimum of sum_{j in S}(x_j xor e0_j) for each state.
At a join A,B -> P=A union B, child states a,b are compatible iff a+b is
in I_P, and their costs add. Every globally completable assignment restricts
to such states. Conversely, assignments realizing a,b can be combined and
completed outside P because a+b is in I_P. Induction gives the exact table;
the root has one state and gives the requested minimum.

The addition map from compatible child pairs onto I_P is surjective. Its
kernel consists of (v,v) for v in im(M_A) intersect im(M_B). Consequently
the exact number of candidate pairs is 2**J, where

    J = dim(I_P) + dim(im(M_A) intersect im(M_B))
      = rank(M_A) + rank(M_B) + rank(M_outside_P) - rank(M).

Compilation stores binary bases and maps only. The executor enumerates these
pairs in Gray-code order, with O(J) scratch. All DP tables occupy one arena;
postorder stack compaction uses memmove. Preflight reports the entire arena,
both child tables plus parent, and map scratch, separately from Python plan
metadata and process RSS. Width alone is not a memory or time estimate.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np


DEFAULT_MEMORY_BYTES = 256 << 20
DEFAULT_JOIN_WORK = 100_000_000
_LIB = None
_CHUNK_PAIRS = 1 << 20
_popcount = getattr(int, "bit_count", lambda value: bin(value).count("1"))


class TreeDPResourceError(RuntimeError):
    """Compilation, dense memory, candidate-pair work, or time limit exceeded."""

    def __init__(self, message, profile=None):
        super().__init__(message)
        self.profile = profile


def _basis(columns):
    pivots = {}
    for value in columns:
        while value:
            pivot = value.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = value
                break
            value ^= pivots[pivot]
    return tuple(pivots.values())


class _LinearMap:
    """Exact column elimination, with original-column coefficient witnesses."""

    def __init__(self, columns, *, kernel=True):
        self.pivots = {}
        self.kernel = []
        for index, value in enumerate(columns):
            witness = 1 << index
            while value:
                pivot = value.bit_length() - 1
                if pivot not in self.pivots:
                    self.pivots[pivot] = (value, witness)
                    break
                other, coefficients = self.pivots[pivot]
                value ^= other
                witness ^= coefficients
            if not value and kernel:
                self.kernel.append(witness)

    def solve(self, value):
        witness = 0
        while value:
            pivot = value.bit_length() - 1
            pair = self.pivots.get(pivot)
            if pair is None:
                return None
            other, coefficients = pair
            value ^= other
            witness ^= coefficients
        return witness


def _combine(columns, mask):
    result = 0
    while mask:
        bit = mask & -mask
        result ^= columns[bit.bit_length() - 1]
        mask ^= bit
    return result


def _intersection(left, right):
    # Both inputs are independent, so dependencies in their concatenation
    # project bijectively onto a basis of their intersection.
    solver = _LinearMap(left + right)
    mask = (1 << len(left)) - 1
    return tuple(_combine(left, v & mask) for v in solver.kernel)


@dataclass(frozen=True)
class TreeNode:
    leaf: int | None
    left: int | None = None
    right: int | None = None


@dataclass(frozen=True)
class TreeJoin:
    left_rank: int
    right_rank: int
    parent_rank: int
    parent_maps: tuple[int, ...]
    free_maps: tuple[int, ...]

    @property
    def join_dimension(self):
        return self.parent_rank + len(self.free_maps)

    @property
    def work(self):
        return 1 << self.join_dimension


def _tree_nodes(tree, ncols):
    """Validate and flatten without recursion, including very deep combs."""
    if ncols == 0:
        if tree is not None:
            raise ValueError("the empty problem requires tree=None")
        return ()
    nodes, stack, completed, seen = [], [(tree, False)], [], set()
    visits = 0
    while stack:
        item, finish = stack.pop()
        if finish:
            right, left = completed.pop(), completed.pop()
            completed.append(len(nodes))
            nodes.append(TreeNode(None, left, right))
            continue
        visits += 1
        if visits > 2 * ncols - 1:
            raise ValueError("tree has too many nodes, repeated leaves, or a cycle")
        if isinstance(item, int) and not isinstance(item, bool):
            if not 0 <= item < ncols or item in seen:
                raise ValueError("tree leaves must be each column index exactly once")
            seen.add(item)
            completed.append(len(nodes))
            nodes.append(TreeNode(item))
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            stack.extend(((item, True), (item[1], False), (item[0], False)))
        else:
            raise ValueError("each tree node must be an integer leaf or a binary pair")
    if len(seen) != ncols or len(completed) != 1:
        raise ValueError("tree leaves must be each column index exactly once")
    return tuple(nodes)


def _owned_size(value):
    """Recursive CPython object size, counting shared objects once."""
    total, seen, stack = 0, set(), [value]
    while stack:
        item = stack.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        total += sys.getsizeof(item)
        if isinstance(item, dict):
            stack.extend(item.keys())
            stack.extend(item.values())
        elif isinstance(item, (tuple, list, set)):
            stack.extend(item)
        elif hasattr(item, "__dict__"):
            stack.append(vars(item))
    return total


def _cost_dtype(ncols):
    for dtype in (np.uint8, np.uint16, np.uint32, np.uint64):
        if ncols + 1 <= np.iinfo(dtype).max:
            return np.dtype(dtype)
    raise ValueError("number of columns exceeds supported exact integer range")


def build_tree_kernel(force=False):
    """Build the single-threaded C kernel next to its source."""
    source = Path(__file__).with_suffix(".c")
    output = source.with_name("libtree_dp.so")
    if force or not output.exists() or output.stat().st_mtime < source.stat().st_mtime:
        # Independent solver processes may request the first build together.
        # Publish only a complete shared library, never an in-progress linker output.
        temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
        command = ["cc", "-O3", "-std=c99", "-shared", "-fPIC", str(source), "-o", str(temporary)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise RuntimeError(f"could not build tree DP kernel: {result.stderr}")
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
    return str(output)


def _lib():
    global _LIB
    if _LIB is None:
        library = ctypes.CDLL(build_tree_kernel())
        for bits in (8, 16, 32, 64):
            function = getattr(library, f"tree_join_u{bits}")
            function.argtypes = [ctypes.c_void_p] * 5 + [ctypes.c_uint] * 2 + [ctypes.c_uint64] * 3
            function.restype = None
        library.tree_move.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
        library.tree_move.restype = None
        _LIB = library
    return _LIB


class CompiledTreeDP:
    """A binary tree realization of M, reusable for arbitrary affine targets.

    ``max_compile_bytes`` limits a conservative bound on polynomial basis
    storage before basis construction. This guard can reject a tree whose
    actual compilation would use less memory; it is distinct from the exact
    dense-arena accounting. ``max_compile_seconds`` is checked between nodes.
    Neither compilation nor preflight allocates any exponential-size array.
    """

    def __init__(self, columns, tree, *, max_compile_bytes=DEFAULT_MEMORY_BYTES,
                 max_compile_seconds=60.0):
        start = time.monotonic()
        self.columns = tuple(columns)
        if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in self.columns):
            raise ValueError("columns must be nonnegative Python integers")
        self.ncols = len(self.columns)
        self.nodes = _tree_nodes(tree, self.ncols)
        self.root = len(self.nodes) - 1
        self.dtype = _cost_dtype(self.ncols).name
        self.itemsize = np.dtype(self.dtype).itemsize
        self.infinity = self.ncols + 1

        def check_time():
            if max_compile_seconds is not None and time.monotonic() - start > max_compile_seconds:
                raise TreeDPResourceError("tree compilation exceeded max_compile_seconds")

        # Basis vectors are at most max(column).bit_length() bits. At a node
        # there are <= min(rank, subtree size) independent vectors. Reserve
        # four such tree collections plus full-rank complement vectors and
        # elimination/witness workspace, conservatively, before building them.
        rank_bound = min(self.ncols, max((v.bit_length() for v in self.columns), default=0))
        counts = []
        for node in self.nodes:
            counts.append(1 if node.leaf is not None else counts[node.left] + counts[node.right])
        vector_bytes = sys.getsizeof(1 << rank_bound) + 8
        ambient_bytes = max((sys.getsizeof(v) for v in self.columns), default=28) + 8
        self.compile_storage_bound_bytes = (
            _owned_size(self.columns) + _owned_size(self.nodes)
            + sum(min(rank_bound, c) for c in counts) * (4 * ambient_bytes + 2 * vector_bytes)
            + len(self.nodes) * rank_bound * (ambient_bytes + vector_bytes)
            + 16 * (rank_bound + 1) ** 2 + len(self.nodes) * 512 + 16384
        )
        if max_compile_bytes is not None and self.compile_storage_bound_bytes > max_compile_bytes:
            raise TreeDPResourceError(
                f"conservative compilation bound {self.compile_storage_bound_bytes} bytes "
                f"exceeds max_compile_bytes={max_compile_bytes}",
                {"compile_storage_bound_bytes": self.compile_storage_bound_bytes})
        self.solver = _LinearMap(self.columns, kernel=False)
        self.matrix_rank = len(self.solver.pivots)
        spaces = {}
        space_ranks = []
        for index, node in enumerate(self.nodes):
            check_time()
            spaces[index] = (_basis((self.columns[node.leaf],)) if node.leaf is not None
                             else _basis(spaces[node.left] + spaces[node.right]))
            space_ranks.append(len(spaces[index]))
        complements = {self.root: ()} if self.nodes else {}
        interfaces = [()] * len(self.nodes)
        complement_ranks = [0] * len(self.nodes)
        for index in reversed(range(len(self.nodes))):
            check_time()
            node = self.nodes[index]
            complement = complements.pop(index)
            complement_ranks[index] = len(complement)
            interfaces[index] = _intersection(spaces.pop(index), complement)
            if node.leaf is None:
                complements[node.left] = _basis(complement + spaces[node.right])
                complements[node.right] = _basis(complement + spaces[node.left])
        self.interfaces = tuple(interfaces)
        self.joins = {}
        self.execution_children = {}
        peaks = []
        for index, node in enumerate(self.nodes):
            check_time()
            parent_rank = len(interfaces[index])
            size = 1 << parent_rank
            if node.leaf is not None:
                peaks.append(size)
                continue
            left, right = interfaces[node.left], interfaces[node.right]
            solver = _LinearMap(left + right)
            maps = tuple(solver.solve(v) for v in interfaces[index])
            if any(v is None for v in maps):
                raise AssertionError("parent interface must be contained in the child sum")
            join = TreeJoin(len(left), len(right), parent_rank, maps, tuple(solver.kernel))
            expected = (space_ranks[node.left] + space_ranks[node.right]
                        + complement_ranks[index] - self.matrix_rank)
            if join.join_dimension != expected:
                raise AssertionError("compatible-pair dimension identity failed")
            self.joins[index] = join
            lsize, rsize = 1 << len(left), 1 << len(right)
            local = lsize + rsize + size
            lr_peak = max(peaks[node.left], lsize + peaks[node.right], local)
            rl_peak = max(peaks[node.right], rsize + peaks[node.left], local)
            if lr_peak <= rl_peak:
                self.execution_children[index] = (node.left, node.right)
                peaks.append(lr_peak)
            else:
                self.execution_children[index] = (node.right, node.left)
                peaks.append(rl_peak)
        order, stack = [], [(self.root, False)] if self.nodes else []
        while stack:
            index, finish = stack.pop()
            if finish or self.nodes[index].leaf is not None:
                order.append(index)
            else:
                first, second = self.execution_children[index]
                stack.extend(((index, True), (second, False), (first, False)))
        self.order = tuple(order)
        self.peak_live_entries = peaks[self.root] if self.nodes else 0
        self.compilation_seconds = time.monotonic() - start
        self.compiled_metadata_bytes = _owned_size(self)

    def preflight(self, *, max_memory_bytes=DEFAULT_MEMORY_BYTES,
                  max_join_work=DEFAULT_JOIN_WORK, max_table_bits=None):
        """Return exact evaluator-array sizes and candidate-pair counts.

        The dense budget covers the single arena plus two uint64 map arrays.
        Python plan storage, interpreter/library memory, and allocator/RSS
        overhead are reported or explicitly excluded, not silently called RAM.
        ``allowed`` means the selected limits permit execution; it says
        nothing about feasibility of a particular affine target.
        """
        ranks = [len(v) for v in self.interfaces]
        max_rank = max(ranks, default=0)
        max_join = max((v.join_dimension for v in self.joins.values()), default=0)
        work = sum(v.work for v in self.joins.values())
        table_bytes = self.peak_live_entries * self.itemsize
        scratch_bytes = 2 * max_join * 8
        peak = table_bytes + scratch_bytes
        reasons = []
        if max_rank >= 63 or max_join >= 63:
            reasons.append("table or join index requires at least 63 bits")
        if table_bytes > np.iinfo(np.intp).max:
            reasons.append("arena exceeds the platform array index range")
        if max_table_bits is not None and max_rank > max_table_bits:
            reasons.append(f"interface rank {max_rank} exceeds max_table_bits={max_table_bits}")
        if max_memory_bytes is not None and peak > max_memory_bytes:
            reasons.append(f"dense workspace {peak} bytes exceeds max_memory_bytes={max_memory_bytes}")
        if max_join_work is not None and work > max_join_work:
            reasons.append(f"join work {work} exceeds max_join_work={max_join_work}")
        return {
            "allowed": not reasons, "rejection_reasons": reasons,
            "ncols": self.ncols, "matrix_rank": self.matrix_rank,
            "dtype": self.dtype, "dtype_bytes": self.itemsize, "infinity": self.infinity,
            "edge_state_dimensions": ranks, "max_interface_rank": max_rank,
            "max_join_dimension": max_join, "join_work": work,
            "join_profiles": [dict(node=index, left_rank=join.left_rank,
                                   right_rank=join.right_rank, parent_rank=join.parent_rank,
                                   kernel_rank=len(join.free_maps),
                                   join_dimension=join.join_dimension, work=join.work,
                                   child_parent_table_bytes=self.itemsize * (
                                       (1 << join.left_rank) + (1 << join.right_rank)
                                       + (1 << join.parent_rank)))
                              for index, join in self.joins.items()],
            "largest_table_bytes": (1 << max_rank) * self.itemsize if self.nodes else 0,
            "peak_live_table_bytes": table_bytes, "arena_bytes": table_bytes,
            "scratch_bytes": scratch_bytes, "peak_dense_bytes": peak,
            "compiled_metadata_bytes": self.compiled_metadata_bytes,
            "compile_storage_bound_bytes": self.compile_storage_bound_bytes,
            "compilation_seconds": self.compilation_seconds,
            "memory_scope": "arena and map arrays; Python plan reported separately; process RSS excluded",
            "threads": 1,
        }

    def run(self, target=0, *, max_memory_bytes=DEFAULT_MEMORY_BYTES,
            max_join_work=DEFAULT_JOIN_WORK, max_table_bits=None,
            max_seconds=60.0, backend="c"):
        """Return (exact minimum weight or None, execution/resource statistics).

        The pure Python backend is a small-instance reference. Both backends
        use the same arena accounting and exact integer arithmetic. Time is
        checked between leaves and between chunks of at most 2**20 join pairs.
        No incomplete result is returned as an exact distance.
        """
        if not isinstance(target, int) or isinstance(target, bool) or target < 0:
            raise ValueError("target must be a nonnegative Python integer")
        if backend not in ("c", "python"):
            raise ValueError("backend must be 'c' or 'python'")
        profile = self.preflight(max_memory_bytes=max_memory_bytes,
                                 max_join_work=max_join_work, max_table_bits=max_table_bits)
        representative = self.solver.solve(target)
        if representative is None:
            return None, dict(profile, feasible=False, seconds=0.0, join_work_done=0,
                              allocated_dense_bytes=0, backend=backend)
        if not profile["allowed"]:
            raise TreeDPResourceError("; ".join(profile["rejection_reasons"]), profile)
        if not self.nodes:
            return 0, dict(profile, feasible=True, seconds=0.0, join_work_done=0,
                           allocated_dense_bytes=0, backend=backend)
        # The C library owns no dense storage. Build before timing the solve.
        library = _lib() if backend == "c" else None
        start = time.monotonic()

        def check_time():
            if max_seconds is not None and time.monotonic() - start > max_seconds:
                raise TreeDPResourceError("tree DP exceeded max_seconds; no exact result returned", profile)

        check_time()
        arena = np.empty(self.peak_live_entries, dtype=self.dtype)
        maps = np.empty((2, profile["max_join_dimension"]), dtype=np.uint64)
        address, item = arena.ctypes.data, self.itemsize
        stack, live, observed_peak, done = [], 0, 0, 0
        for index in self.order:
            check_time()
            node = self.nodes[index]
            size = 1 << len(self.interfaces[index])
            observed_peak = max(observed_peak, live + size)
            output = arena[live:live + size]
            output.fill(self.infinity)
            if node.leaf is not None:
                bit = (representative >> node.leaf) & 1
                # A zero column has a local zero-cost choice for every e0.
                output[0] = bit if self.columns[node.leaf] else 0
                if size == 2:
                    output[1] = bit ^ 1
                stack.append((index, live, size))
                live += size
                continue
            second, first = stack.pop(), stack.pop()
            left, right = (first, second) if first[0] == node.left else (second, first)
            join = self.joins[index]
            mask = (1 << join.left_rank) - 1
            generators = join.parent_maps + join.free_maps
            for bit, value in enumerate(generators):
                maps[0, bit] = value & mask
                maps[1, bit] = value >> join.left_rank
            lo, ro, po = address + left[1] * item, address + right[1] * item, address + live * item
            chunk_size = _CHUNK_PAIRS if backend == "c" else 4096
            for begin in range(0, join.work, chunk_size):
                check_time()
                end = min(begin + chunk_size, join.work)
                if backend == "c":
                    function = getattr(library, f"tree_join_u{item * 8}")
                    function(lo, ro, po, maps[0].ctypes.data, maps[1].ctypes.data,
                             join.parent_rank, join.join_dimension, begin, end, self.infinity)
                else:
                    left_table = arena[left[1]:left[1] + left[2]]
                    right_table = arena[right[1]:right[1] + right[2]]
                    state = _combine(generators, begin ^ (begin >> 1))
                    gray = begin ^ (begin >> 1)
                    parent = gray & ((1 << join.parent_rank) - 1)
                    for counter in range(begin, end):
                        cost = int(left_table[state & mask]) + int(right_table[state >> join.left_rank])
                        if cost < int(output[parent]):
                            output[parent] = cost
                        if counter + 1 < end:
                            bit = ((counter + 1) & -(counter + 1)).bit_length() - 1
                            state ^= generators[bit]
                            if bit < join.parent_rank:
                                parent ^= 1 << bit
                done += end - begin
            destination = first[1]
            if backend == "c":
                library.tree_move(address + destination * item, po, size * item)
            else:
                # Copy toward the lower address in order, with scalar scratch.
                for offset in range(size):
                    arena[destination + offset] = output[offset]
            live = destination + size
            stack.append((index, destination, size))
        check_time()
        if live != 1 or len(stack) != 1 or observed_peak != self.peak_live_entries:
            raise AssertionError("arena schedule disagrees with exact preflight")
        value = int(arena[0])
        if value == self.infinity:
            raise AssertionError("a consistent affine system must have a finite root cost")
        return value, dict(profile, feasible=True, seconds=time.monotonic() - start,
                           join_work_done=done, allocated_dense_bytes=arena.nbytes + maps.nbytes,
                           observed_peak_live_table_bytes=observed_peak * item, backend=backend)


def tree_min_distance_for_mask(h_cols, l_cols, mask, tree, *,
                               max_compile_bytes=DEFAULT_MEMORY_BYTES,
                               max_compile_seconds=60.0, **limits):
    """Solve H e=0, parity(mask & L e)=1 with the supplied binary tree."""
    if len(h_cols) != len(l_cols):
        raise ValueError("H and L must have the same number of columns")
    if not isinstance(mask, int) or isinstance(mask, bool) or mask < 0:
        raise ValueError("observable mask must be a nonnegative Python integer")
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in l_cols):
        raise ValueError("logical columns must be nonnegative Python integers")
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in h_cols):
        raise ValueError("detector columns must be nonnegative Python integers")
    nrows = max((value.bit_length() for value in h_cols), default=0)
    columns = tuple(h | ((_popcount(l & mask) & 1) << nrows)
                    for h, l in zip(h_cols, l_cols))
    program = CompiledTreeDP(columns, tree, max_compile_bytes=max_compile_bytes,
                             max_compile_seconds=max_compile_seconds)
    distance, info = program.run(1 << nrows, **limits)
    info["observable_mask"] = mask
    return distance, info


def preflight_tree_dp(h_cols, l_cols, mask, tree, *,
                       max_compile_bytes=DEFAULT_MEMORY_BYTES,
                       max_compile_seconds=60.0, **limits):
    """Compile the logical query and return resource/affine-feasibility data."""
    if len(h_cols) != len(l_cols):
        raise ValueError("H and L must have the same number of columns")
    if not isinstance(mask, int) or isinstance(mask, bool) or mask < 0:
        raise ValueError("observable mask must be a nonnegative Python integer")
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in (*h_cols, *l_cols)):
        raise ValueError("columns must be nonnegative Python integers")
    nrows = max((value.bit_length() for value in h_cols), default=0)
    columns = tuple(h | ((_popcount(l & mask) & 1) << nrows)
                    for h, l in zip(h_cols, l_cols))
    program = CompiledTreeDP(columns, tree, max_compile_bytes=max_compile_bytes,
                             max_compile_seconds=max_compile_seconds)
    return dict(program.preflight(**limits),
                feasible=program.solver.solve(1 << nrows) is not None, observable_mask=mask)
