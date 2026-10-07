"""Survey Table S2 square circuits without selecting schedules by distance.

Usage: hypsurf_table.py out.json [samples=256] [seconds=240] [q=all] [seed=382] [kind=all] [basis=all]
The seed is 382. Re-run the same command to resume a bounded invocation.
All samples are uniform without replacement from the exactly counted CSP.
Use zero seconds to disable the budget on a server. OMP defaults to two.
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import sys
import time
from collections import Counter
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS","2")
sys.path.insert(0,str(Path(__file__).resolve().parent))
import hypsurf as codes


def _save(path,payload):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary = path.with_name(path.name+".tmp")
    temporary.write_text(json.dumps(payload,indent=2)+"\n")
    temporary.replace(path)


def main(out,samples=256,seconds=240,only="all",seed=382,only_kind="all",only_basis="all"):
    samples,seconds,seed = int(samples),float(seconds),int(seed)
    if samples<1 or seconds<0:
        raise ValueError("positive sample count and nonnegative seconds required")
    qs = (6,8,10,12) if str(only)=="all" else (int(only),)
    if any(q not in codes.LINS_SOURCES for q in qs):
        raise ValueError("q must be 6,8,10,12 or all")
    kinds = ("ZZ","NZ") if only_kind=="all" else (str(only_kind).upper(),)
    if any(kind not in ("ZZ","NZ") for kind in kinds):
        raise ValueError("kind must be ZZ, NZ or all")
    bases = ("X","Z") if only_basis=="all" else (str(only_basis).upper(),)
    if any(basis not in ("X","Z") for basis in bases):
        raise ValueError("basis must be X, Z or all")
    started = time.monotonic()
    deadline = started+seconds if seconds else float("inf")
    path = Path(out)
    payload = json.loads(path.read_text()) if path.exists() else {}
    settings = dict(L=5,rounds=5,multi_rate=True,samples_requested=samples,seed=seed,
                    p=0.001,p_seam=0.001,
                    method="stim.Circuit.shortest_graphlike_error(ignore_ungraphlike_errors=True, canonicalize_circuit_errors=True)",
                    sampling="exact uniform subset without replacement; no distance-based selection",
                    equivalence="labeled faces; no automorphism quotient",boundary="flush pending cat; no additional data coupling",
                    cat="cyclic incidences cut before first; left middle root; first expansion right")
    if payload and payload.get("settings")!=settings:
        raise ValueError("checkpoint settings differ; use another output file")
    version = codes.stim.__version__
    if payload.get("stim_version",version)!=version:
        raise ValueError("checkpoint Stim version differs; use another output file")
    payload.update(schema=1,settings=settings)
    payload["stim_version"] = version
    payload.setdefault("assignments",{})
    payload.setdefault("rows",[])
    rows = {(r["q"],r["schedule"],r["alternating"],r["basis"]):r for r in payload["rows"]}
    complete = True
    added = 0
    def save():
        payload["invocation_seconds"] = time.monotonic()-started
        payload["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=="darwin" else 1024)
        payload["covered_graphlike_calls"] = sum(len(r["distances"]) for r in rows.values())
        payload["complete_for_selected_q"] = all(
            len(rows.get((q,k,f,b),{}).get("distances",[]))==min(samples,codes.count_schedules(q,k))
            for q in qs for k in ("ZZ","NZ") for f in (False,True) for b in ("X","Z"))
        payload["complete_for_selection"] = all(
            len(rows.get((q,k,f,b),{}).get("distances",[]))==min(samples,codes.count_schedules(q,k))
            for q in qs for k in kinds for f in (False,True) for b in bases)
        payload["selected_q"] = list(qs)
        payload["selected_schedules"] = list(kinds)
        payload["selected_bases"] = list(bases)
        _save(out,payload)
    for q in qs:
        for kind in kinds:
            groupkey = f"q{q}_{kind}"
            total = codes.count_schedules(q,kind)
            assignments = codes.sample_schedules(q,kind,count=samples,seed=seed)
            digest = hashlib.sha256(repr(assignments).encode()).hexdigest()
            info = payload["assignments"].setdefault(groupkey,dict(total_valid_assignments=total,
                                        exhaustive=len(assignments)==total,
                                        sampled=len(assignments),sha256=digest,values=assignments))
            if info["sha256"]!=digest:
                raise ValueError("schedule sample changed")
            for fb in (False,True):
                for basis in bases:
                    key = (q,kind,fb,basis)
                    if key not in rows:
                        row = dict(q=q,tiling=codes.tiling(q)["name"],modules="Square",module_count=q,
                                   N=q*61,n=q*25,k=q-2,d_code=10,L=5,rounds=5,schedule=kind,alternating=fb,
                                   basis=basis,paper_value=codes.PAPER_SQUARE[q][kind][int(fb)],
                                   total_valid_assignments=total,distances=[],distribution={})
                        rows[key]=row
                        payload["rows"].append(row)
                    row = rows[key]
                    if row["distances"]:
                        expected = row.get("example_circuit_sha256",row.get("example_matrix_sha256"))
                        reference = codes.build(q,basis,5,p=settings["p"],p_seam=settings["p_seam"],
                                                schedule=kind,alternating=fb,assignment=assignments[0],
                                                multi_rate=True,noise="full")
                        if expected!=hashlib.sha256(str(reference).encode()).hexdigest():
                            raise ValueError("checkpoint circuit changed; use another output file")
            for i,assignment in enumerate(assignments):
                for fb in (False,True):
                    for basis in bases:
                        row = rows[q,kind,fb,basis]
                        if len(row["distances"])>i:
                            continue
                        if time.monotonic()>=deadline:
                            complete = False
                            save()
                            print(f"Saved {payload['covered_graphlike_calls']} calls; budget reached, re-run to resume.",flush=True)
                            return payload
                        try:
                            circuit = codes.build(q,basis,5,p=settings["p"],p_seam=settings["p_seam"],
                                                  schedule=kind,alternating=fb,assignment=assignment,
                                                  multi_rate=True,noise="full")
                            errors = circuit.shortest_graphlike_error(ignore_ungraphlike_errors=True,
                                                                      canonicalize_circuit_errors=True)
                            distance = len(errors)
                            assert distance>0 and all(e.circuit_error_locations for e in errors)
                        except Exception as e:
                            payload["failure"] = dict(q=q,schedule=kind,alternating=fb,basis=basis,
                                                       sample_index=i,assignment=assignment,error=str(e))
                            complete = False
                            save()
                            raise
                        row["distances"].append(distance)
                        row["covered"] = len(row["distances"])
                        row["distribution"] = dict(sorted(Counter(row["distances"]).items()))
                        row["paper_value_occurs"] = row["paper_value"] in row["distances"]
                        row["paper_value_is_mode"] = (row["paper_value_occurs"] and
                                                       Counter(row["distances"])[row["paper_value"]]==max(Counter(row["distances"]).values()))
                        if i==0:
                            suffix = "_fb" if fb else ""
                            stem = f"q{q}_L5_{kind}{suffix}_{basis}_r5_a000"
                            circuit.to_file(path.parent/(stem+".stim"))
                            row["example_circuit"] = stem+".stim"
                            row["example_circuit_sha256"] = hashlib.sha256(str(circuit).encode()).hexdigest()
                        added += 1
                        if added%16==0:
                            save()
                if (i+1)%32==0:
                    print(f"{{4,{q}}} {kind}: {i+1}/{len(assignments)} assignments, "
                          f"elapsed {time.monotonic()-started:.1f}s",flush=True)
            print(f"{{4,{q}}} {kind}: complete {len(assignments)} samples; "
                  +"; ".join(f"{b} {'fb' if f else 'std'} {rows[q,kind,f,b]['distribution']}"
                              for f in (False,True) for b in bases),flush=True)
            save()
    save()
    return payload


if __name__=="__main__":
    main(*sys.argv[1:])
