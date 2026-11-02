"""Tally of the two-gross schedule scan: the value of every class without a hook family in a one-round window, from the records in
records/ and deep/, the schedules at each value, and the classes still open.  Classes with such a family are at most 16 by the transferred
fault sets (screen/window_transfer.jsonl), and 48 schedules are exactly 12 (screen/triage_low.jsonl).  Writes scan_table.json.
Usage: python tally_scan.py"""
import glob
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
classes = json.load(open(HERE + "/screen/classes.json"))
windows = {tuple(w["problem"]): w for w in json.load(open(HERE + "/screen/window_types.json"))}


def n_columns(p):
    return [w["columns"] for w in windows[tuple(p)]["windows"]]


no_hook = [i for i, c in enumerate(classes) if all(n_columns(p) == [288, 288] for p in c["problems"])]
assert len(no_hook) == 78 and sum(classes[i]["n"] for i in no_hook) == 1440, (len(no_hook), sum(classes[i]["n"] for i in no_hook))

# Per problem: a run may have ended on a server other than its class's other problem.  A run started at weight 17 (DEEP_KMIN) proves nothing
# without the run that excluded the lighter weights on the same problem, so those records count only after that run is here.
ub, lb, runs_without_replay = {}, {}, []
conditional = []
for f in sorted(glob.glob(HERE + "/records/*/*.jsonl")):
    name = os.path.basename(f)
    kmin_file = name.startswith("exact_k17_") and name != "exact_k17_s_b.jsonl"
    for x in open(f):
        r = json.loads(x)
        if r.get("skipped"):
            continue
        for a in r["runs"]:
            key = tuple(a["problem"])
            if a.get("witness") is not None and a.get("replay_ok") is not True:
                runs_without_replay.append((name, r["index"], a.get("ub")))
            if a.get("kmin", 17 if kmin_file else 1) > 1:
                conditional.append((key, a, a.get("kmin", 17), name, r["index"]))
                continue
            if a.get("ub") is not None and a.get("witness_ok"):
                ub[key] = min(ub.get(key, 99), a["ub"])
            if a.get("lb") is not None:          # a run that was stopped keeps the bound of its finished thresholds
                lb[key] = max(lb.get(key, 0), a["lb"])
without_predecessor = []
for key, a, kmin, name, index in conditional:
    if lb.get(key, 0) < kmin:
        without_predecessor.append((name, index, list(key)))
        continue
    if a.get("ub") is not None and a.get("witness_ok"):
        ub[key] = min(ub.get(key, 99), a["ub"])
    if a.get("lb") is not None:
        lb[key] = max(lb[key], a["lb"])
# the candidate's class: weight 17 exhausted by a direct run (deep/), in the Z basis; the X basis follows by its self-dual symmetry
cand = json.load(open(HERE + "/deep/ibm_bb288_s046135_531620_c1_Z_k17.json"))
assert cand["lower_bound"] == 18
lb[tuple(classes[16]["problems"][0])] = 18

value, still = {}, []
for i in no_hook:
    probs = [tuple(p) for p in classes[i]["problems"]]
    lows = [lb.get(p, 1) for p in probs]
    highs = [ub[p] for p in probs if p in ub]
    if highs and min(highs) <= min(lows):
        value[i] = min(highs)
    elif min(lows) == 18:                       # every schedule has a weight-18 fault set
        value[i] = 18
    else:
        still.append([i, min(lows), classes[i]["n"]])
by = Counter()
for i, v in value.items():
    by[v] += classes[i]["n"]
best = max(value.values())
c2 = HERE + "/deep/ibm_bb288_s046135_531620_c2_Z_k17_only17.json"
out = {"worst": 12, "schedules_at_worst": 48, "best": best, "n_best": by[best], "by_value": {str(k): by[k] for k in sorted(by)},
       "classes_by_value": {str(v): sorted(i for i in value if value[i] == v) for v in sorted(set(value.values()))},
       "classes_at_best": sorted(i for i, v in value.items() if v == best), "open": still,
       "cap_16_schedules": 8496 - 1440, "candidate_c2": json.load(open(c2)) if os.path.exists(c2) else None,
       "conditional_runs_without_predecessor": without_predecessor,
       "witnesses_without_replay_in_queue_record": runs_without_replay}
if out["candidate_c2"] is not None:
    out["candidate_c2"] = {k: out["candidate_c2"].get(k) for k in ("status", "lower_bound", "upper_bound", "witness_ok", "seconds")}
json.dump(out, open(HERE + "/scan_table.json", "w"), indent=1)
print("no-hook classes", len(no_hook), "with a value", len(value), "open", still)
print("schedules by value", out["by_value"], "best", best, "n_best", out["n_best"], "classes at best", out["classes_at_best"])
print("witnesses without replay in the queue record", runs_without_replay)
print("runs started at a threshold, with no earlier record on the problem", without_predecessor)
