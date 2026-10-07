"""Run STAR schedule variants without changing run_parallel.

Usage: OMP_NUM_THREADS=2 .venv/bin/python papers/star_run.py SCHEDULE KEY BASIS OUT
       [rounds=6] [k_coll=2] [kmax=12] [seconds_per_threshold=120]
       [do_full=1] [noise=full]

SCHEDULE is paper, mirror, or an integer index in star.valid_schedules(KEY).
The transported mirror is available for 66 and 78; STAR42's check matrices
are inequivalent to selfdual_bb42, so mirror42 raises instead of silently
constructing a different schedule.  Circuit filenames include the variant.
"""
import json
import os
import sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_parallel
import star


def main(schedule, key, basis, out, rounds=6, k_coll=2, kmax=12,
         time_limit=120, do_full=1, noise="full"):
    key = int(key)
    if schedule in ("paper", "mirror"):
        order = star.PAPER_SCHEDULE if schedule == "paper" else star.mirror_schedule(key)
    else:
        order = star.valid_schedules(key)[int(schedule)]
    if not star.schedule_is_valid(key, order):
        raise ValueError("schedule has residual ancilla back-action")
    codes = dict(star.CODES)
    if schedule != "paper":
        definition, notes, parameters, _ = codes[key]
        codes[key] = (definition, notes + "; schedule variant", parameters, None)
    facade = SimpleNamespace(
        CODES=codes, translations=star.translations,
        tag=lambda size: f"{size}_{schedule}",
        build=lambda size, basis_, rounds_, p=0.001, noise="full":
            star.build(size, basis_, rounds_, p=p, noise=noise, schedule=order))
    sys.modules["star_schedule"] = facade
    run_parallel.main("star_schedule", key, basis, out, rounds, k_coll, kmax,
                      time_limit, do_full, noise)
    if os.path.exists(out):
        with open(out) as f:
            result = json.load(f)
        result["star_schedule_variant"] = str(schedule)
        result["star_schedule"] = order
        with open(out + ".tmp", "w") as f:
            json.dump(result, f, indent=1)
        os.replace(out + ".tmp", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
