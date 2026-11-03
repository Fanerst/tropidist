"""Timesteps per cycle of the 8,496 schedules in the timing of Tour de gross (papers/ibm_bicycle_matched.py) against the one-round
windows of their problems (window_types.json).  A schedule has a hook family if a window of either basis holds more than the 288
single-qubit columns.  Writes timesteps.json.
Usage: python timesteps.py"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(HERE + "/../../..")
os.environ.setdefault("CD_ROOT", ROOT)
sys.path[:0] = [ROOT + "/papers", HERE]
import bb6_depth7 as B
import ibm_bicycle_matched as IBM
import symmetry_classes as SC

windows = {tuple(w["problem"]): [x["columns"] for x in w["windows"]] for w in json.load(open(HERE + "/window_types.json"))}
rep, _ = SC.z_problems("bb288", B.all_valid())
name = lambda s: tuple("".join(map(str, t)) for t in s)
count = Counter()
for s in B.all_valid():
    hook = any(windows[name(rep[(s, b)][0])] != [288, 288] for b in "ZX")
    count[(IBM.timing(B.to_dicts(*s))[1], hook)] += 1
table = {str(t): {"with_hook_family": count[(t, True)], "without": count[(t, False)]} for t in sorted({k[0] for k in count})}
assert sum(sum(v.values()) for v in table.values()) == 8496
json.dump(table, open(HERE + "/timesteps.json", "w"), indent=1)
print(table)
