"""Turn a sector-problem solution into physical circuit faults and replay it.

The replay is independent of the DEM algebra used by the solvers: the faults
are inserted as explicit Pauli gates (or measurement-record flips) into the
noiseless circuit, which is then simulated; the claim is confirmed only if
every detector stays silent and at least one observable flips.
"""
from __future__ import annotations

import stim

from .problem import Problem

NOISE = {"X_ERROR", "Y_ERROR", "Z_ERROR", "DEPOLARIZE1", "DEPOLARIZE2", "PAULI_CHANNEL_1",
         "PAULI_CHANNEL_2", "E", "CORRELATED_ERROR", "ELSE_CORRELATED_ERROR"}


def lift_to_dem(full: Problem, sector: Problem, sector_cols):
    """Raw DEM error indices realising the given sector columns without
    touching detectors outside the sector."""
    rows = sector.notes["sector_rows"]
    lookup = {(a, b): j for j, (a, b) in enumerate(zip(full.h, full.l))}
    out = []
    for j in sector_cols:
        lifted = 0
        m = sector.h[j]
        while m:
            low = m & -m
            lifted ^= 1 << rows[low.bit_length() - 1]
            m ^= low
        pj = lookup[(lifted, sector.l[j])]
        out.append(full.col_meta[pj][0])
    return out


def check_in_dem(circuit: stim.Circuit, raw_indices):
    """XOR the chosen error mechanisms in the full undecomposed DEM."""
    dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=True)
    errs = [inst for inst in dem if inst.type == "error"]
    dets = set()
    obs = set()
    for i in raw_indices:
        for t in errs[i].targets_copy():
            if t.is_relative_detector_id():
                dets ^= {t.val}
            elif t.is_logical_observable_id():
                obs ^= {t.val}
    return sorted(dets), sorted(obs), [str(errs[i]) for i in raw_indices]


def physical_faults(circuit: stim.Circuit, raw_indices):
    """One representative circuit fault per DEM mechanism."""
    dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=True)
    errs = [inst for inst in dem if inst.type == "error"]
    flt = stim.DetectorErrorModel()
    for i in raw_indices:
        flt.append(errs[i])
    expl = circuit.explain_detector_error_model_errors(dem_filter=flt, reduce_to_one_representative_error=True)
    faults = []
    for e in expl:
        loc = e.circuit_error_locations[0]
        fault = {
            "tick": loc.tick_offset,
            "instruction": loc.instruction_targets.gate,
            "paulis": [(t.gate_target.pauli_type, t.gate_target.value) for t in loc.flipped_pauli_product],
            "stack": [(f.instruction_offset, f.iteration_index, f.instruction_repetitions_arg)
                      for f in loc.stack_frames],
            "flipped_measurement": (None if loc.flipped_measurement is None
                                    else loc.flipped_measurement.record_index),
            "dem_terms": [str(t) for t in e.dem_error_terms],
        }
        faults.append(fault)
    return faults


def _expand(circuit):
    """Instruction list with REPEAT blocks unrolled (nothing else changed)."""
    out = []
    for inst in circuit:
        if isinstance(inst, stim.CircuitRepeatBlock):
            body = _expand(inst.body_copy())
            for _ in range(inst.repeat_count):
                out.extend(body)
        else:
            out.append(inst)
    return out


def _flat_index(circuit: stim.Circuit, stack):
    """Index into _expand(circuit) of the instruction named by stack frames."""
    def count(c):
        n = 0
        for inst in c:
            if isinstance(inst, stim.CircuitRepeatBlock):
                n += inst.repeat_count * count(inst.body_copy())
            else:
                n += 1
        return n

    def locate(c, frames):
        off = frames[0][0]
        n = 0
        for k, inst in enumerate(c):
            if k == off:
                if isinstance(inst, stim.CircuitRepeatBlock):
                    body = inst.body_copy()
                    # the iteration of this loop is recorded on the inner frame
                    return n + frames[1][1] * count(body) + locate(body, frames[1:])
                return n
            if isinstance(inst, stim.CircuitRepeatBlock):
                n += inst.repeat_count * count(inst.body_copy())
            else:
                n += 1
        raise ValueError("bad stack frame")

    return locate(circuit, stack)


MEASURE = ("M", "MX", "MY", "MZ", "MR", "MRX", "MRY", "MRZ")


def _noiseless(flat, before=None, after=None):
    clean = stim.Circuit()
    for k, inst in enumerate(flat):
        for pauli, qb in (before or {}).get(k, ()):
            clean.append(pauli, [qb])
        if inst.name in NOISE:
            pass
        elif inst.name in MEASURE and inst.gate_args_copy():
            clean.append(inst.name, inst.targets_copy())
        else:
            clean.append(inst)
        for pauli, qb in (after or {}).get(k, ()):
            clean.append(pauli, [qb])
    return clean


def replay(circuit: stim.Circuit, faults):
    """Simulate the noiseless circuit with the faults inserted as explicit
    Pauli gates.  Returns (fired detectors, flipped observables)."""
    import numpy as np

    flat = _expand(circuit)
    before, after = {}, {}
    record_flips = []
    for f in faults:
        idx = _flat_index(circuit, f["stack"])
        inst = flat[idx]
        assert inst.name == f["instruction"], (inst.name, f["instruction"])
        if not f["paulis"]:
            # classical readout error: only the record flips
            assert f["flipped_measurement"] is not None
            record_flips.append(f["flipped_measurement"])
            continue
        if inst.name in NOISE or inst.name in MEASURE:
            # the channel acts where it stands; a measurement flip is the
            # Pauli that anticommutes with the measured operator, applied
            # just before the measurement
            before.setdefault(idx, []).extend(f["paulis"])
        else:
            after.setdefault(idx, []).extend(f["paulis"])
    reference = _noiseless(flat)
    faulty = _noiseless(flat, before, after)
    assert reference.num_measurements == faulty.num_measurements
    sim = stim.TableauSimulator()
    sim.do(faulty)
    meas = np.array([sim.current_measurement_record()], dtype=np.bool_)
    for i in record_flips:
        meas[0, i] ^= True
    # detectors and observables are evaluated against the fault-free circuit
    conv = reference.compile_m2d_converter()
    d, o = conv.convert(measurements=meas, separate_observables=True)
    return [int(i) for i in np.flatnonzero(d[0])], [int(i) for i in np.flatnonzero(o[0])]
