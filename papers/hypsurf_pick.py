"""The rebuilt square-module circuits of arXiv:2610.03682 with a chosen schedule assignment, for
papers/run_parallel.py.  Key: "<hypsurf key>@<i>", the i-th sampled assignment of the survey
(results/papers4/hypsurf/table_s2_square*.json, written by papers/hypsurf_table.py), or
"<hypsurf key>@v<digits>", the assignment given face by face (one digit 0-7 per base face).

Usage: python papers/run_parallel.py hypsurf_pick q8_L5_NZ_fb@228 Z out.json 5 3 12
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hypsurf

_ASSIGN = {}
for _f in sorted(glob.glob(os.path.join(os.path.dirname(HERE), "results", "papers4", "hypsurf", "table_s2_square*.json"))):
    for _k, _v in json.load(open(_f)).get("assignments", {}).items():
        _ASSIGN.setdefault(_k, _v["values"])


def _split(key):
    base, sel = str(key).split("@")
    q, L, kind, fb = hypsurf._key_parts(base)
    values = [int(ch) for ch in sel[1:]] if sel.startswith("v") else _ASSIGN["q%d_%s" % (q, kind)][int(sel)]
    return base, tuple(values)


class _Codes(dict):
    def __missing__(self, key):
        base, _ = _split(key)
        q, L, code, _paper = hypsurf.CODES[base]
        return (q, L, code, None)


CODES = _Codes()
sector_high = hypsurf.sector_high


def build(key, basis, rounds=5, **kw):
    base, values = _split(key)
    return hypsurf.build(base, basis, rounds, assignment=values, **kw)


def tag(key):
    base, values = _split(key)
    return hypsurf.tag(base) + "_v" + "".join(map(str, values))


def translations(key):
    return []
