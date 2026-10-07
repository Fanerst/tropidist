"""Stim-generated surface and color memory circuits and graph-like exact truth.

Surface detector coordinates alone are relabelled for the CSS exporters.  Noise
and circuit operations are those of Stim's generator, with no parameter tuning.
"""
from __future__ import annotations

from collections import deque

import stim

NOISE = dict(after_clifford_depolarization=0.001,
             before_round_data_depolarization=0.001,
             before_measure_flip_probability=0.001,
             after_reset_flip_probability=0.001)
GENERATORS = {"surface": "surface_code:rotated_memory_z",
              "stim_color": "color_code:memory_xyz"}
DISTANCE_SOURCE = "bench/stim_families.py#graphlike_distance"
SURFACE_NOTE = ("Same generator and noise arguments as the prior benchmark; "
                "our flattened d=11 raw mechanism count is 24483, theirs 24485. "
                "The difference of two is unexplained; no parameters are tuned. "
                "These are generated instances of the same family, not their circuit files.")


def _needs_lead(message):
    # Import lazily: instances imports this module during registry preparation.
    try:
        from .instances import NeedsLead
    except ImportError:
        from instances import NeedsLead
    return NeedsLead(message)


def generated_circuit(family, distance):
    """The unmodified built-in circuit; all four noise arguments are enabled."""
    return stim.Circuit.generated(GENERATORS[family], distance=distance,
                                  rounds=distance, **NOISE)


def instance_metadata(family, distance):
    """Cheap registry metadata, without constructing a circuit or finding truth."""
    n = distance ** 2 if family == "surface" else (3 * distance ** 2 + 1) // 4
    description = ("Stim rotated surface-code Z memory" if family == "surface"
                   else "Stim color-code XYZ memory")
    return dict(n=n, k=1, basis="Z", rounds=distance,
                description=description + ", distance %d, rounds %d" % (distance, distance),
                generator=GENERATORS[family], noise=dict(NOISE), stim_version=stim.__version__)


def _surface_check_types(flat):
    """Read the ancilla readout basis from gates, not from lattice parity.

    Stim measures both types with MR (physical Z).  X checks have a Hadamard
    readout rotation after their last CX.  Track that rotation independently
    at every extraction, including the repeated rounds.
    """
    ancillas = {t.value for inst in flat if inst.name in ("MR", "MRX", "MRY")
                for t in inst.targets_copy()}
    readout_h = dict.fromkeys(ancillas, False)
    types = {}
    for inst in flat:
        targets = [t.value for t in inst.targets_copy() if t.is_qubit_target]
        if inst.name == "H":
            for q in targets:
                if q in ancillas:
                    readout_h[q] = not readout_h[q]
        elif inst.name == "CX":
            for q in targets:
                if q in ancillas:
                    readout_h[q] = False
        elif inst.name in ("MR", "MRX", "MRY"):
            if inst.name == "MRY":
                raise _needs_lead("surface generator has a Y-basis check")
            for q in targets:
                is_x = (inst.name == "MRX") != readout_h[q]
                typ = 0 if is_x else 3
                if q in types and types[q] != typ:
                    raise _needs_lead("surface check changes measurement basis across rounds")
                types[q] = typ
                readout_h[q] = False
        elif inst.name in ("R", "RX", "RY"):
            for q in targets:
                if q in ancillas:
                    readout_h[q] = False
    if set(types.values()) != {0, 3}:
        raise _needs_lead("surface generator does not expose both CSS check bases")
    return types


def rewrite_surface_detectors(circ):
    """Return (circuit, check_perms), changing only flattened DETECTOR arguments.

    Check indices are lexicographic (x, y) ranks within each measured type.
    A single check permutation must act on both index spaces in row_perms.
    Offer the geometric half-turn only if its two induced permutations agree;
    the shared exporter decides whether it is a symmetry of each problem.
    """
    flat = circ.flattened()
    types = _surface_check_types(flat)
    qubit_coords = flat.get_final_qubit_coordinates()
    by_type = {typ: sorted(tuple(qubit_coords[q][:2]) for q in types if types[q] == typ)
               for typ in (0, 3)}
    by_xy = {tuple(qubit_coords[q][:2]): (by_type[typ].index(tuple(qubit_coords[q][:2])), typ)
             for q, typ in types.items()}
    if len(by_xy) != len(types):
        raise _needs_lead("surface measurement qubits have duplicate coordinates")
    out = stim.Circuit()
    for inst in flat:
        if inst.name != "DETECTOR":
            out.append(inst)
            continue
        args = inst.gate_args_copy()
        if len(args) != 3 or tuple(args[:2]) not in by_xy:
            raise _needs_lead("surface detector cannot be associated with a measured check")
        check, typ = by_xy[tuple(args[:2])]
        out.append("DETECTOR", inst.targets_copy(), [check, 0, args[2], typ], tag=inst.tag)

    sx = min(x for x, y in by_xy) + max(x for x, y in by_xy)
    sy = min(y for x, y in by_xy) + max(y for x, y in by_xy)
    maps = []
    for typ in (0, 3):
        index = {xy: i for i, xy in enumerate(by_type[typ])}
        rotated = [(sx - x, sy - y) for x, y in by_type[typ]]
        if any(xy not in index for xy in rotated):
            return out, []
        maps.append([index[xy] for xy in rotated])
    candidates = [maps[0]] if maps[0] == maps[1] else []
    return out, candidates


def surface_circuit(distance):
    return rewrite_surface_detectors(generated_circuit("surface", distance))


def graphlike_distance(h, l, nrows):
    """Exact unit-cost distance for graph-like columns and one observable.

    A one-detector column joins that detector to a common boundary node.
    Two-detector columns join their detectors.  A syndrome-zero edge set is
    Eulerian (also at the boundary); an odd observable set contains an odd
    closed walk.  Conversely cancelling repeated edges of an odd closed walk
    gives an odd syndrome-zero set of no greater weight.  Thus BFS from each
    vertex to its parity-flipped copy finds exactly the minimum fault count.

    Return None if no logical set exists.  Observable bit zero is the sole
    allowed observable.  Unsupported hyperedges/multiple observables require
    a lead rather than being assigned an approximate distance.
    """
    if nrows < 0 or len(h) != len(l):
        raise ValueError("invalid graph-like problem dimensions")
    for syndrome, logical in zip(h, l):
        if syndrome < 0 or syndrome.bit_length() > nrows or logical < 0:
            raise ValueError("column mask outside problem dimensions")
        if bin(syndrome).count("1") > 2:
            raise _needs_lead("graphlike_distance requires at most two detectors per column")
        if logical > 1:
            raise _needs_lead("graphlike_distance requires at most one observable (bit zero)")
    if any(syndrome == 0 and logical for syndrome, logical in zip(h, l)):
        return 1
    adjacency = [[] for _ in range(nrows + 1)]
    for syndrome, logical in zip(h, l):
        if not syndrome:
            continue
        low = syndrome & -syndrome
        u = low.bit_length() - 1
        rest = syndrome ^ low
        v = rest.bit_length() - 1 if rest else nrows
        adjacency[u].append((v, logical))
        adjacency[v].append((u, logical))

    best = None
    for start, edges in enumerate(adjacency):
        if not edges:
            continue
        source, target = 2 * start, 2 * start + 1
        distances = [-1] * (2 * len(adjacency))
        distances[source] = 0
        queue = deque([source])
        while queue:
            state = queue.popleft()
            depth = distances[state] + 1
            if best is not None and depth >= best:
                continue
            vertex, parity = divmod(state, 2)
            for neighbor, logical in adjacency[vertex]:
                nxt = 2 * neighbor + (parity ^ logical)
                if nxt == target:
                    best = depth
                    queue.clear()
                    break
                if distances[nxt] < 0:
                    distances[nxt] = depth
                    queue.append(nxt)
        if best == 2:
            break  # no one-edge logical loop remains after the explicit check
    return best


def record_surface_truth(directory, meta):
    """Compute both graph distances from the actual exported variants."""
    try:
        from . import common
    except ImportError:
        import common
    for variant in ("sector", "collapsed"):
        p = common.load(str(directory), variant)
        if p.nobs != 1:
            raise _needs_lead("surface graph truth requires exactly one observable")
        distance = graphlike_distance(p.h, p.l, p.nrows)
        if distance is None:
            raise _needs_lead("surface graph problem has no logical closed walk")
        meta["variants"][variant].update(distance=distance, distance_kind="exact",
                                         distance_source=DISTANCE_SOURCE)
    for key in ("distance", "distance_kind", "distance_source"):
        meta["variants"]["full"][key] = meta["variants"]["sector"][key]
    common.write_meta(str(directory), meta)
