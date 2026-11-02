"""Pilot of a schedule scan of the two-gross code: export a random sample of the 8,496 depth-seven schedules as instances
of IBM's memory instruction (one noisy cycle), for the certified pipeline.  Also the standard schedule, as a control, and
the images of a few schedules under the two symmetries seen on the smaller codes:
  D  swap X and Z checks and the two blocks: (px, pz) -> (pz[3:] + pz[:3], px[3:] + px[:3]), bases exchanged
  T  reverse the slots: (px, pz) -> (6 - px, 6 - pz), bases kept
usage: python pilot_export.py ROOT NAMES.txt
"""
import json
import multiprocessing as mp
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "papers"), HERE, os.path.join(HERE, "bench")]
import bb6_depth7 as B
import common
import ibm_bicycle as IB
import stabcode

KEY = "bb288"
SEED = 20261101
N_SAMPLE, N_SYM = 50, 3


def D(s):
    px, pz = s
    return (pz[3:] + pz[:3], px[3:] + px[:3])


def T(s):
    px, pz = s
    return (tuple(6 - a for a in px), tuple(6 - a for a in pz))


def stag(s):
    return "s%s_%s" % ("".join(map(str, s[0])), "".join(map(str, s[1])))


def export(job):
    root, s, basis, role = job
    name = "ibm_%s_%s_c1_%s" % (KEY, stag(s), basis)
    if os.path.exists(os.path.join(root, name, "meta.json")):
        return name
    circ = IB.build_instruction(KEY, basis, 1, 1e-3, B.to_dicts(*s))
    n, k = stabcode.css_parameters(*B.matrices(KEY))
    meta = {"track": "circuit", "family": "ibm_bicycle", "n": n, "k": k, "basis": basis, "rounds": 1,
            "description": "%s memory instruction, one noisy cycle, schedule %s (%s)" % (KEY, stag(s), role),
            "source": {"builder": "papers/ibm_bicycle.py", "key": KEY, "schedule": stag(s), "cycles": 1, "role": role}}
    common.export_circuit_instance(name, circ, B.translations(KEY), meta, root=root)
    return name


def main(root, names):
    allv = B.all_valid()
    assert len(allv) == 8496
    std = (tuple(B.STANDARD["X"][l] for l in [(s, a) for s in "LR" for a in range(3)]),
           tuple(B.STANDARD["Z"][l] for l in [(s, a) for s in "LR" for a in range(3)]))
    assert std in allv
    rng = random.Random(SEED)
    sample = rng.sample([s for s in allv if s != std], N_SAMPLE)
    jobs = [(root, std, b, "standard") for b in "XZ"]
    jobs += [(root, s, b, "sample") for s in sample for b in "XZ"]
    plan = {"seed": SEED, "standard": std, "sample": sample, "symmetry_check": []}
    for s in sample[:N_SYM]:
        assert T(s) in allv and D(s) in allv and D(T(s)) in allv
        plan["symmetry_check"].append({"s": s, "T": T(s), "D": D(s), "DT": D(T(s))})
        for img, role in ((T(s), "T image"), (D(s), "D image")):
            jobs += [(root, img, b, role) for b in "XZ"]
    jobs = list(dict.fromkeys(jobs))
    with mp.Pool(int(os.environ.get("EXPORT_PROCS", "8"))) as pool:
        out = pool.map(export, jobs, chunksize=1)
    json.dump(plan, open(os.path.join(root, "plan.json"), "w"), indent=1)
    open(names, "w").write(",".join(out))
    print(len(out), "instances")


if __name__ == "__main__":
    main(*sys.argv[1:])
