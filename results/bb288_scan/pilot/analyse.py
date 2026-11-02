import json, glob, os, re, statistics as st, collections as C
R = "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance/results/bb288_scan/pilot"
plan = json.load(open(R + "/instances/plan.json"))
recs = {}
for f in glob.glob(R + "/results/pilot/ours_pipeline__dp-2/*.json"):
    r = json.load(open(f))
    m = re.match(r"ibm_bb288_s(\d+)_(\d+)_c1_([XZ])", r["instance"])
    s = (tuple(map(int, m.group(1))), tuple(map(int, m.group(2))))
    first_ub = next((p["t"] for p in (r.get("trace") or []) if p.get("ub") is not None), None)
    tub = {}
    for p in r.get("trace") or []:
        if p.get("ub") is not None:
            tub[p["ub"]] = p["t"]
    recs[(s, m.group(3))] = dict(status=r["status"], lb=r["lower_bound"], ub=r["upper_bound"], ok=r["witness_ok"], sec=r["seconds"], first_ub=first_ub, tub=tub, rss=r.get("peak_rss_mb"))
print(len(recs), "records", C.Counter(v["status"] for v in recs.values()))
print("errors:", [k for k, v in recs.items() if v["status"] not in ("exact", "bounds", "timeout")][:5])
std = (tuple(plan["standard"][0]), tuple(plan["standard"][1]))
print("standard", {b: {k: recs[(std, b)][k] for k in ("status", "lb", "ub", "first_ub", "sec")} for b in "XZ"})
sample = [(tuple(a), tuple(b)) for a, b in plan["sample"]]
rows = []
for s in sample:
    x, z = recs[(s, "X")], recs[(s, "Z")]
    ubs = [v["ub"] for v in (x, z) if v["ub"] is not None]
    lbs = [v["lb"] for v in (x, z)]
    ub = min(ubs) if ubs else None
    exact_low = any(v["status"] == "exact" and v["ub"] == ub for v in (x, z)) and all(v["lb"] >= ub or v["ub"] == ub for v in (x, z))
    closed = ub is not None and min(lbs) >= ub
    rows.append((s, x["lb"], x["ub"], z["lb"], z["ub"], ub, min(lbs), closed, x["sec"] + z["sec"]))
print("schedule-level upper bound histogram", sorted(C.Counter(r[5] for r in rows).items(), key=lambda t: (t[0] is None, t[0])))
print("closed schedule values", sorted(C.Counter(r[5] for r in rows if r[7]).items()))
print("not closed: (min lb, ub)", sorted(C.Counter((r[6], r[5]) for r in rows if not r[7]).items(), key=str))
print("basis-level: status by ub", sorted(C.Counter((v["status"], v["ub"]) for k, v in recs.items() if k[0] in sample).items(), key=str))
sec = [v["sec"] for k, v in recs.items() if k[0] in sample]
print("seconds per basis run: median %.0f, mean %.0f, max %.0f" % (st.median(sec), st.mean(sec), max(sec)))
fu = [v["first_ub"] for k, v in recs.items() if k[0] in sample and v["first_ub"] is not None]
print("first upper bound at: median %.0f s, 90%% %.0f s, n %d of %d" % (st.median(fu), sorted(fu)[int(.9 * len(fu))], len(fu), len(sec)))
print("top schedules:")
for r in sorted(rows, key=lambda r: (-(r[5] or 99), r[6]))[:12]:
    print("  ", "".join(map(str, r[0][0])), "".join(map(str, r[0][1])), "X [%s,%s] Z [%s,%s]" % r[1:5], "schedule <= %s" % r[5], "closed" if r[7] else "open", "%.0f s" % r[8])
print("symmetry check:")
for e in plan["symmetry_check"]:
    s, Ts, Ds, DTs = [(tuple(e[k][0]), tuple(e[k][1])) for k in ("s", "T", "D", "DT")]
    def show(a, b):
        v = recs.get((a, b))
        return None if v is None else (v["status"], v["lb"], v["ub"])
    print("  Z(s)", show(s, "Z"), "Z(Ts)", show(Ts, "Z"), "X(Ds)", show(Ds, "X"), "| X(s)", show(s, "X"), "X(Ts)", show(Ts, "X"), "Z(Ds)", show(Ds, "Z"))
