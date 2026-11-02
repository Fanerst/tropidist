"""The lists of triage_queue.py: every problem of the schedule classes not yet settled, first the classes in which the screen found no fault
set of weight <= 16, each part in the order of classes.json, dealt to the servers in proportion to their slots.

Usage: make_triage.py SCREEN.jsonl OUT_PREFIX SLOTS,SLOTS,... SCAN.jsonl...
Writes OUT_PREFIX_a.json, OUT_PREFIX_b.json, ..."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    screen, prefix, slots, scans = sys.argv[1], sys.argv[2], list(map(int, sys.argv[3].split(","))), sys.argv[4:]
    classes = json.load(open(HERE + "/classes.json"))
    witness = set()
    for line in open(screen):
        r = json.loads(line)
        if r.get("witness"):
            witness.add(("".join(map(str, r["px"])), "".join(map(str, r["pz"]))))
    settled = set()
    for path in scans:
        for line in open(path):
            r = json.loads(line)
            if r.get("settled"):
                settled.add(r["index"])
    first, later = [], []
    for i, c in enumerate(classes):
        if i in settled:
            continue
        part = later if any(tuple(p) in witness for p in c["problems"]) else first
        part += [[i, p] for p in c["problems"]]
    print("classes", len(classes), "settled", len(settled), "problems, no fault set yet", len(first), "with one in the class", len(later))
    lists = [[] for _ in slots]
    load = [0.0] * len(slots)
    for item in first + later:
        k = min(range(len(slots)), key=lambda j: load[j])
        lists[k].append(item)
        load[k] += 1.0 / slots[k]
    for k, x in enumerate(lists):
        name = "%s_%s.json" % (prefix, "abcdefgh"[k])
        json.dump(x, open(name, "w"))
        print(name, len(x))


if __name__ == "__main__":
    main()
